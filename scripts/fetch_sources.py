"""Fetch only the seven approved documents, recording failures and crawl permissions."""

import asyncio
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.config import get_settings
from app.ingestion.crawler import ControlledCrawler
from app.sources import load_sources


async def fetch_all() -> dict:
    settings = get_settings()
    sources = load_sources(settings.source_config)
    raw = settings.data_dir / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    crawler = ControlledCrawler(sources)
    report = {"started_at": datetime.now(UTC).isoformat(), "sources": []}
    try:
        robots = await crawler.read_robots()
        (raw / "robots.txt").write_text(robots)
        report["crawl_delay_seconds"] = crawler.delay
        for source in sources:
            record = source.model_dump()
            try:
                html = await crawler.fetch(source)
                (raw / f"{source.id}.html").write_text(html)
                record.update(
                    status="fetched", checksum=hashlib.sha256(html.encode()).hexdigest()
                )
            except Exception as exc:
                record.update(status="unavailable", error=str(exc))
            record["checked_at"] = datetime.now(UTC).isoformat()
            report["sources"].append(record)
            print(f"{source.id}: {record['status']}", flush=True)
    finally:
        await crawler.close()
        (settings.data_dir / "source-report.json").write_text(
            json.dumps(report, indent=2)
        )
    return report


if __name__ == "__main__":
    asyncio.run(fetch_all())
