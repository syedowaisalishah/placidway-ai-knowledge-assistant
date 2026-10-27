import hashlib
from pathlib import Path
from urllib.parse import urlsplit

import yaml

from app.schemas import Source


def load_sources(path: Path) -> list[Source]:
    records = yaml.safe_load(path.read_text())["sources"]
    sources = [Source.model_validate(record) for record in records]
    if len(sources) != 7 or len({s.id for s in sources}) != 7:
        raise ValueError("Exactly seven unique approved sources are required.")
    if len({s.url for s in sources}) != 7:
        raise ValueError("Approved source URLs must be unique.")
    for source in sources:
        parsed = urlsplit(source.url)
        if (
            parsed.scheme != "https"
            or parsed.netloc != "www.placidway.com"
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Only exact HTTPS PlacidWay source URLs are permitted.")
    return sources


def source_fingerprint(sources: list[Source]) -> str:
    return hashlib.sha256(
        "\n".join(sorted(s.id + ":" + s.url for s in sources)).encode()
    ).hexdigest()


def require_allowed(url: str, sources: list[Source]) -> None:
    if url not in {s.url for s in sources}:
        raise ValueError("URL is outside the exact seven-source allowlist.")
