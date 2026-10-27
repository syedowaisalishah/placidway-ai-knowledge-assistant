"""Versioned ingestion and atomic promotion of complete, validated indexes."""

import fcntl
import hashlib
import json
import os
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from app.config import Settings
from app.ingestion.crawler import ControlledCrawler
from app.ingestion.extract import extract, extract_prices, make_chunks
from app.retrieval.embeddings import Embedder
from app.sources import load_sources, source_fingerprint

COLLECTION = "placidway_approved"
SCHEMA_VERSION = 2
EMBEDDING_PIPELINE = "minilm-window180-stride150-mean-l2-v1"


@contextmanager
def refresh_lock(data_dir: Path):
    data_dir.mkdir(parents=True, exist_ok=True)
    with (data_dir / ".refresh.lock").open("w") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("Another knowledge refresh is already running.") from exc
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def read_current(data_dir: Path) -> Path | None:
    pointer = data_dir / "current.json"
    if not pointer.exists():
        return None
    name = json.loads(pointer.read_text())["version"]
    if (
        not isinstance(name, str)
        or not name.startswith("v-")
        or "/" in name
        or ".." in name
    ):
        raise ValueError("Invalid index pointer")
    path = data_dir / "indexes" / name
    return path if (path / "manifest.json").exists() else None


def promote(data_dir: Path, name: str):
    temporary = data_dir / f".pointer-{uuid.uuid4().hex}.json"
    temporary.write_text(json.dumps({"version": name}))
    os.replace(temporary, data_dir / "current.json")


def build_chroma(path: Path, chunks: list[dict], vectors: np.ndarray):
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    client = chromadb.PersistentClient(
        path=str(path / "chroma"), settings=ChromaSettings(anonymized_telemetry=False)
    )
    collection = client.create_collection(
        COLLECTION, metadata={"hnsw:space": "cosine"}, embedding_function=None
    )
    for start in range(0, len(chunks), 100):
        batch = chunks[start : start + 100]
        collection.add(
            ids=[c["id"] for c in batch],
            documents=[c["text"] for c in batch],
            embeddings=vectors[start : start + 100].tolist(),
            metadatas=[
                {k: v for k, v in c.items() if k not in ("id", "text")} for c in batch
            ],
        )
    if collection.count() != len(chunks):
        raise RuntimeError("Incomplete vector index; refusing to promote")
    probe = collection.query(query_embeddings=[vectors[0].tolist()], n_results=1)
    if not probe["ids"][0]:
        raise RuntimeError("Index query verification failed")


def write_snapshot(
    path: Path,
    manifest: dict,
    chunks: list[dict],
    prices: list[dict],
    vectors: np.ndarray,
):
    path.mkdir(parents=True, exist_ok=True)
    (path / "chunks.json").write_text(
        json.dumps(chunks, ensure_ascii=False, indent=2) + "\n"
    )
    (path / "prices.json").write_text(
        json.dumps(prices, ensure_ascii=False, indent=2) + "\n"
    )
    np.save(path / "vectors.npy", vectors, allow_pickle=False)
    manifest = dict(
        manifest,
        artifacts={
            name: hashlib.sha256((path / name).read_bytes()).hexdigest()
            for name in ("chunks.json", "prices.json", "vectors.npy")
        },
    )
    (path / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    )


def validate_snapshot(
    path: Path, settings: Settings
) -> tuple[dict, list[dict], list[dict], np.ndarray]:
    manifest = json.loads((path / "manifest.json").read_text())
    sources = load_sources(settings.source_config)
    if manifest.get("source_fingerprint") != source_fingerprint(sources):
        raise ValueError("Index source allowlist does not match configuration")
    if manifest.get("embedding_model") != settings.embedding_model:
        raise ValueError("Embedding model changed; rebuild the index")
    if manifest.get("embedding_backend") != settings.embedding_backend:
        raise ValueError(
            "Embedding backend changed; rebuild or verify compatible vectors first"
        )
    if manifest.get("embedding_pipeline") != EMBEDDING_PIPELINE:
        raise ValueError("Embedding pipeline changed; rebuild")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Index schema version changed; rebuild")
    for name in ("chunks.json", "prices.json", "vectors.npy"):
        if (
            hashlib.sha256((path / name).read_bytes()).hexdigest()
            != manifest["artifacts"][name]
        ):
            raise ValueError(f"Index checksum mismatch: {name}")
    chunks = json.loads((path / "chunks.json").read_text())
    prices = json.loads((path / "prices.json").read_text())
    vectors = np.load(path / "vectors.npy", allow_pickle=False)
    allowed = {s.id: s.url for s in sources}
    if not chunks or len(chunks) != len(vectors) or not np.isfinite(vectors).all():
        raise ValueError("Invalid or empty vectors")
    if any(allowed.get(c["source_id"]) != c["url"] for c in chunks):
        raise ValueError("Unapproved source in knowledge index")
    if any(allowed.get(p["source_id"]) != p["source_url"] for p in prices):
        raise ValueError("Unapproved price source")
    return manifest, chunks, prices, vectors


async def ingest(
    settings: Settings, cached: bool = False, export: Path | None = None
) -> dict:
    with refresh_lock(settings.data_dir):
        sources = load_sources(settings.source_config)
        timestamp = datetime.now(UTC).isoformat()
        raw_dir = settings.data_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        report = {"started_at": timestamp, "sources": []}
        crawler = ControlledCrawler(sources)
        chunks, prices, source_records = [], [], []
        cached_report = (
            json.loads((settings.data_dir / "source-report.json").read_text())
            if cached
            else None
        )
        try:
            if not cached:
                robots = await crawler.read_robots()
                (raw_dir / "robots.txt").write_text(robots)
                report["crawl_delay_seconds"] = crawler.delay
            for source in sources:
                try:
                    if cached:
                        status = next(
                            r for r in cached_report["sources"] if r["id"] == source.id
                        )
                        html = (
                            (raw_dir / f"{source.id}.html").read_bytes().decode("utf-8")
                        )
                        if (
                            status["url"] != source.url
                            or status["status"] not in ("fetched", "indexed")
                            or hashlib.sha256(html.encode()).hexdigest()
                            != status["checksum"]
                        ):
                            raise ValueError("Cached fetch provenance is invalid")
                    else:
                        html = await crawler.fetch(source)
                        (raw_dir / f"{source.id}.html").write_text(html)
                    title, sections, quote_url = extract(source, html)
                    page_chunks = make_chunks(source, title, sections, timestamp)
                    chunks.extend(c.model_dump() for c in page_chunks)
                    prices.extend(
                        p.model_dump() for p in extract_prices(source, page_chunks)
                    )
                    record = dict(
                        source.model_dump(),
                        status="indexed",
                        page_title=title,
                        checksum=hashlib.sha256(html.encode()).hexdigest(),
                        content_checksum=hashlib.sha256(
                            "\n".join(c.text for c in page_chunks).encode()
                        ).hexdigest(),
                        ingested_at=timestamp,
                        quote_url=quote_url,
                        chunk_count=len(page_chunks),
                    )
                    source_records.append(record)
                    report["sources"].append(record)
                except Exception as exc:
                    report["sources"].append(
                        dict(source.model_dump(), status="unavailable", error=str(exc))
                    )
                    raise RuntimeError(
                        f"{source.id} failed; previous index retained"
                    ) from exc
        finally:
            await crawler.close()
            if not cached:
                (settings.data_dir / "source-report.json").write_text(
                    json.dumps(report, indent=2)
                )
        previous = read_current(settings.data_dir)
        cache = {}
        if previous:
            try:
                old_manifest, old_chunks, _, old_vectors = validate_snapshot(
                    previous, settings
                )
                cache = {c["content_hash"]: v for c, v in zip(old_chunks, old_vectors)}
            except ValueError:
                pass
        missing = [c for c in chunks if c["content_hash"] not in cache]
        if missing:
            embedder = Embedder(
                settings.embedding_model,
                settings.data_dir / "models/minilm",
                settings.embedding_backend,
            )
            for start in range(0, len(missing), 24):
                batch = missing[start : start + 24]
                vectors = embedder.encode([c["text"] for c in batch])
                cache.update({c["content_hash"]: v for c, v in zip(batch, vectors)})
        vectors = np.asarray(
            [cache[c["content_hash"]] for c in chunks], dtype=np.float32
        )
        name = "v-" + uuid.uuid4().hex
        path = settings.data_dir / "indexes" / name
        manifest = dict(
            schema_version=SCHEMA_VERSION,
            version=name,
            created_at=timestamp,
            embedding_model=settings.embedding_model,
            embedding_backend=settings.embedding_backend,
            embedding_pipeline=EMBEDDING_PIPELINE,
            embedding_revision=json.loads(
                (settings.data_dir / "models/minilm/model-metadata.json").read_text()
            )["revision"],
            source_fingerprint=source_fingerprint(sources),
            sources=source_records,
            chunk_count=len(chunks),
            price_count=sum(p["price"] is not None for p in prices),
            embedded_chunks=len(missing),
            reused_chunks=len(chunks) - len(missing),
        )
        write_snapshot(path, manifest, chunks, prices, vectors)
        validate_snapshot(path, settings)
        build_chroma(path, chunks, vectors)
        promote(settings.data_dir, name)
        if export:
            write_snapshot(export, manifest, chunks, prices, vectors)
        return manifest


def restore_snapshot(settings: Settings, snapshot: Path) -> dict:
    with refresh_lock(settings.data_dir):
        manifest, chunks, prices, vectors = validate_snapshot(snapshot, settings)
        name = "v-" + uuid.uuid4().hex
        path = settings.data_dir / "indexes" / name
        write_snapshot(path, dict(manifest, version=name), chunks, prices, vectors)
        build_chroma(path, chunks, vectors)
        promote(settings.data_dir, name)
        return dict(manifest, version=name)
