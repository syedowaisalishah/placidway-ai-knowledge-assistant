import gzip
import json

import httpx
import pytest
from app.config import ROOT, Settings
from app.ingestion.crawler import ControlledCrawler, CrawlError
from app.ingestion.extract import extract, extract_prices, make_chunks
from app.ingestion.pipeline import (
    ingest,
    read_current,
    restore_snapshot,
    validate_snapshot,
)
from app.sources import load_sources, require_allowed

SOURCES = load_sources(ROOT / "config/approved_sources.yaml")


def test_exact_allowlist_rejects_expansion():
    for url in [
        SOURCES[0].url + "?x=1",
        "https://www.placidway.com/",
        "http://www.placidway.com/profile/5/test",
        "https://evil.example",
    ]:
        with pytest.raises(ValueError):
            require_allowed(url, SOURCES)


def test_pdf_hyperlinks_match_allowlist():
    proof = json.loads((ROOT / "docs/source-verification.json").read_text())
    assert all(s["hyperlink_verified"] for s in proof["sources"])
    assert {s["url"] for s in proof["sources"]} == {s.url for s in SOURCES}


async def test_robots_denial_prevents_page_request():
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(
            200,
            text="User-agent: *\nDisallow: /",
            headers={"content-type": "text/plain"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        crawler = ControlledCrawler(SOURCES, client)
        with pytest.raises(CrawlError, match="Disallowed"):
            await crawler.fetch(SOURCES[0])
    assert len(seen) == 1 and seen[0].endswith("/robots.txt")


async def test_decoded_compressed_response_is_not_decoded_twice():
    def handler(request):
        return httpx.Response(
            200,
            content=gzip.compress(b"User-agent: *\nAllow: /\nCrawl-delay: 10"),
            headers={"content-encoding": "gzip", "content-type": "text/plain"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        crawler = ControlledCrawler(SOURCES, client)
        assert "Crawl-delay: 10" in await crawler.read_robots()
        assert crawler.delay == 10


async def test_redirect_cannot_escape_allowlist():
    seen = []

    def handler(request):
        seen.append(str(request.url))
        if str(request.url).endswith("/robots.txt"):
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        return httpx.Response(302, headers={"location": "http://127.0.0.1/secrets"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        crawler = ControlledCrawler(SOURCES, client)
        await crawler.read_robots()
        crawler.delay = 0
        with pytest.raises(ValueError, match="allowlist"):
            await crawler.fetch(SOURCES[0])
    assert len(seen) == 2


def test_table_and_qualifier_are_preserved():
    source = SOURCES[1]
    html = f'''<link rel="canonical" href="{source.url}"><h1>Approved package information</h1>
    <div class="pack-title-price-header"><div class="actual-price">$123 Price starting from</div></div>
    <main class="article-dt-desc"><h2>Cost</h2><p>{"Public package information. " * 12}</p>
    <table><tr><th>Program</th><th>Price (USD)</th></tr><tr><td>Out-patient</td><td>$123</td></tr></table>
    <h2>Related Experiences:</h2><p>Unrelated package $999</p></main>'''
    title, sections, _ = extract(source, html)
    chunks = make_chunks(source, title, sections)
    text = "\n".join(c.text for c in chunks)
    assert "Price starting from" in text
    assert "Program: Out-patient | Price (USD): $123" in text
    assert "$999" not in text
    prices = extract_prices(source, chunks)
    assert any(p.qualifier == "starting from" for p in prices)
    assert any(p.currency == "USD" for p in prices)


def test_wrong_canonical_page_fails_closed():
    with pytest.raises(ValueError, match="canonical"):
        extract(
            SOURCES[0],
            '<link rel="canonical" href="https://evil.example"><h1>Wrong page</h1>',
        )


def test_snapshot_restore_and_reopen(tmp_path):
    settings = Settings(data_dir=tmp_path, log_unanswered=False)
    restore_snapshot(settings, ROOT / "data/snapshot")
    current = read_current(tmp_path)
    manifest, chunks, prices, vectors = validate_snapshot(current, settings)
    assert len(manifest["sources"]) == 7
    assert len(chunks) == len(vectors) > 0
    from app.retrieval.store import KnowledgeStore

    assert KnowledgeStore(settings).status()["ready"]


def test_changed_embedding_model_is_rejected():
    with pytest.raises(ValueError, match="Embedding model changed"):
        validate_snapshot(
            ROOT / "data/snapshot", Settings(embedding_model="different-model")
        )


async def test_failed_refresh_keeps_previous_pointer(tmp_path, monkeypatch):
    settings = Settings(data_dir=tmp_path, log_unanswered=False)
    restore_snapshot(settings, ROOT / "data/snapshot")
    old = (tmp_path / "current.json").read_text()

    async def fail(self):
        raise CrawlError("Blocked")

    monkeypatch.setattr(ControlledCrawler, "read_robots", fail)
    with pytest.raises(CrawlError):
        await ingest(settings)
    assert (tmp_path / "current.json").read_text() == old
