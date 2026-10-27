"""Usage: python scripts/ingest.py --refresh [--export data/snapshot]."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.config import get_settings
from app.ingestion.pipeline import ingest, restore_snapshot

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh", action="store_true", help="Fetch the seven approved sources again"
    )
    parser.add_argument(
        "--cached",
        action="store_true",
        help="Use checksum-verified previous raw fetches",
    )
    parser.add_argument(
        "--restore", type=Path, help="Restore a portable snapshot without re-embedding"
    )
    parser.add_argument(
        "--export", type=Path, help="Write a portable snapshot for deployment"
    )
    args = parser.parse_args()
    if args.restore:
        report = restore_snapshot(get_settings(), args.restore)
    else:
        if args.refresh == args.cached:
            parser.error("Choose exactly one of --refresh or --cached")
        report = asyncio.run(
            ingest(get_settings(), cached=args.cached, export=args.export)
        )
    print(json.dumps(report, indent=2, ensure_ascii=False))
