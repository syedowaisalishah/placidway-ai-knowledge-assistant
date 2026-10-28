import json
import re
from dataclasses import dataclass
from threading import RLock

from app.config import Settings
from app.ingestion.pipeline import COLLECTION, read_current, validate_snapshot
from app.retrieval.embeddings import Embedder
from app.safety.query import Query, normalize
from app.schemas import Chunk, PriceRecord
from app.sources import load_sources


@dataclass
class Hit:
    chunk: Chunk
    score: float
    semantic: float


class KnowledgeStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.sources = load_sources(settings.source_config)
        self.embedder = Embedder(
            settings.embedding_model,
            settings.data_dir / "models/minilm",
            settings.embedding_backend,
        )
        self._lock = RLock()
        self.path = None
        self.manifest = {}
        self.chunks: dict[str, Chunk] = {}
        self.prices: list[PriceRecord] = []
        self.collection = None
        self.client = None

    def load(self):
        with self._lock:
            current = read_current(self.settings.data_dir)
            if current is None:
                raise RuntimeError("Knowledge index has not been built")
            if current == self.path:
                return
            manifest, chunks, prices, _ = validate_snapshot(current, self.settings)
            model_metadata = (
                self.settings.data_dir / "models/minilm/model-metadata.json"
            )
            if (
                model_metadata.exists()
                and json.loads(model_metadata.read_text()).get("revision")
                != manifest["embedding_revision"]
            ):
                raise ValueError(
                    "Model asset revision differs from the index; download pinned assets or rebuild"
                )
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            client = chromadb.PersistentClient(
                path=str(current / "chroma"),
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            collection = client.get_collection(COLLECTION, embedding_function=None)
            if collection.count() != len(chunks):
                raise ValueError("Vector collection is incomplete")
            self.manifest, self.chunks = (
                manifest,
                {c["id"]: Chunk.model_validate(c) for c in chunks},
            )
            self.prices = [PriceRecord.model_validate(p) for p in prices]
            self.client, self.collection, self.path = client, collection, current

    def status(self) -> dict:
        try:
            self.load()
            return dict(
                ready=True,
                source_count=len(self.manifest["sources"]),
                chunk_count=len(self.chunks),
                last_updated=self.manifest["created_at"],
                embedding_model=self.settings.embedding_model,
                sources=self.manifest["sources"],
            )
        except (ValueError, RuntimeError, OSError, KeyError):
            return dict(
                ready=False,
                source_count=0,
                chunk_count=0,
                last_updated=None,
                sources=[
                    dict(s.model_dump(), status="unavailable") for s in self.sources
                ],
            )

    def quote_url(self) -> str | None:
        # Only a route actually observed in an approved page; no lead submission.
        for source in self.manifest.get("sources", []):
            if source.get("quote_url"):
                return source["quote_url"]
        return None

    def retrieve(self, query: Query) -> list[Hit]:
        self.load()
        with self._lock:
            package_sources = {
                "adenocarcinoma": "source-2",
                "adrenal cancer": "source-3",
                "anal cancer": "source-4",
            }
            source_id = package_sources.get(query.topic)
            if query.intent == "videos":
                source_id = "source-5"
            if source_id:
                candidates = [
                    c for c in self.chunks.values() if c.source_id == source_id
                ]
            elif query.topic == "ITC" and query.intent != "pricing":
                candidates = [
                    c for c in self.chunks.values() if c.source_id == "source-1"
                ]
            else:
                candidates = list(self.chunks.values())
            if not candidates:
                return []
            vector = self.embedder.encode([query.retrieval_text])[0].tolist()
            results = self.collection.query(
                query_embeddings=[vector],
                n_results=min(30, len(candidates)),
                where={"source_id": source_id} if source_id else None,
            )
            semantic = {
                key: 1 - distance
                for key, distance in zip(results["ids"][0], results["distances"][0])
            }
            words = set(re.findall(r"\w+", normalize(query.retrieval_text))) - {
                "the",
                "and",
                "in",
                "of",
                "itc",
                "cancer",
                "therapy",
                "center",
            }
            hits = []
            for chunk in candidates:
                tokens = set(re.findall(r"\w+", normalize(chunk.text)))
                lexical = len(words & tokens) / max(len(words), 1)
                title_bonus = 0.0
                h = normalize(chunk.heading)
                expected = {
                    "inclusions": ["included in", "inclusions"],
                    "recovery": ["recovery time", "recovery period"],
                    "pricing": ["cost", "price"],
                    "exclusions": ["excluded"],
                    "duration": ["itinerary", "duration"],
                    "aftercare": ["follow-up", "post-care"],
                    "doctors": ["doctor", "medical director"],
                    "location": ["location", "about itc"],
                    "treatments": [
                        "treatments offered",
                        "treatment approach",
                        "alternative cancer treatments",
                    ],
                    "languages": ["bilingual", "language"],
                    "videos": ["video"],
                }.get(query.intent, ["about itc", "profile overview"])
                if any(term in h for term in expected):
                    title_bonus = 0.35
                score = (
                    0.65 * semantic.get(chunk.id, 0.0) + 0.35 * lexical + title_bonus
                )
                hits.append(Hit(chunk, score, semantic.get(chunk.id, 0.0)))
            return sorted(hits, key=lambda h: h.score, reverse=True)[
                : self.settings.retrieval_k
            ]

    def matching_prices(self, query: Query) -> list[PriceRecord]:
        self.load()
        matched = []
        for price in self.prices:
            if price.price is None:
                continue
            topic = normalize(query.topic)
            treatment = normalize(price.treatment)
            if topic not in ("itc", "") and topic not in treatment:
                continue
            if topic == "itc" and price.source_id not in ("source-6",):
                continue
            if query.countries and price.country not in query.countries:
                continue
            if (
                query.clinic
                and query.clinic != "ITC"
                and query.clinic.lower() not in (price.clinic or "").lower()
            ):
                continue
            if query.clinic == "ITC" and price.source_id == "source-7":
                continue
            if query.program and query.program not in price.label.lower():
                continue
            matched.append(price)
        # Conflicting rows for the same treatment/program/currency cannot become
        # a single confident price. Retain them in the index for diagnosis only.
        identities = {}
        for record in matched:
            identity = (
                record.treatment,
                record.country,
                record.clinic,
                record.label,
                record.currency,
            )
            amount = re.sub(r"[\s,]", "", record.price or "")
            if identity in identities and identities[identity] != amount:
                return []
            identities[identity] = amount
        return matched[:8]

    def comparison_prices(self, query: Query) -> list[PriceRecord]:
        """Return one exact listing per requested country or no comparison.

        The comparison page includes broad package ranges and clinic-specific
        listings. Only the latter can be paired by exact procedure name; even
        then the answer must not imply equal sessions or inclusions.
        """
        self.load()
        countries = set(query.countries)
        if (
            len(countries) != 2
            or not query.topic
            or query.clinic
            or query.program
            or query.aspect
        ):
            return []
        matched = [
            price
            for price in self.prices
            if price.source_id == "source-7"
            and price.scope == "listed_price"
            and price.country in countries
            and normalize(price.treatment).split(",", 1)[0].strip()
            == normalize(query.topic)
            and price.price
            and re.fullmatch(r"\$\d[\d,]*(?:\.\d{2})?", price.price)
        ]
        if len(matched) != 2 or {p.country for p in matched} != countries:
            return []
        if len({p.currency for p in matched}) != 1:
            return []
        return sorted(matched, key=lambda p: p.country or "")
