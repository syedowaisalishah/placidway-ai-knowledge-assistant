"""Validate and display the configured PlacidWay source inventory."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

def main() -> None:
    from app.config import get_settings
    from app.sources import load_sources, source_fingerprint

    sources = load_sources(get_settings().source_config)
    print(
        json.dumps(
            {
                "source_count": len(sources),
                "fingerprint": source_fingerprint(sources),
                "sources": [
                    {"id": source.id, "category": source.category, "url": source.url}
                    for source in sources
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
