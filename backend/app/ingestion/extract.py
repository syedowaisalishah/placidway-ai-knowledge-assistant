"""Keep source sections and whole table rows; discard the surrounding site chrome."""

import hashlib
import re
from datetime import UTC, datetime
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from app.schemas import Chunk, PriceRecord, Section, Source

MONEY = re.compile(
    r"(?:USD\s*|US\$\s*|\$\s*|€\s*|EUR\s*|£\s*|GBP\s*)\d[\d,]*(?:\.\d{1,2})?(?:\s*(?:-|–|to)\s*(?:(?:USD|US\$|\$|€|EUR|£|GBP)\s*)?\d[\d,]*(?:\.\d{1,2})?)?(?:\s*(?:USD|EUR|GBP))?"
)


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract(source: Source, html: str) -> tuple[str, list[Section], str | None]:
    soup = BeautifulSoup(html, "html.parser")
    canonical = soup.find("link", rel="canonical")
    if canonical and canonical.get("href") != source.url:
        raise ValueError(f"{source.id}: canonical URL differs from approved URL")
    h1 = soup.find("h1")
    if not h1:
        raise ValueError(f"{source.id}: no main heading; possible challenge page")
    title = clean(h1.get_text(" ", strip=True))
    if len(title) < 12 or "cloudflare" in title.lower():
        raise ValueError("Source failed content validation")
    quote_url = None
    for a in soup.select("a[href]"):
        if "free quote" in clean(a.get_text(" ", strip=True)).lower():
            url = urljoin(source.url, a["href"])
            parsed = urlsplit(url)
            if (
                parsed.scheme == "https"
                and parsed.netloc == "www.placidway.com"
                and parsed.path.startswith(("/rfi/", "/request-info"))
            ):
                quote_url = url
                break
    root = soup.select_one("main.article-dt-desc") or soup.find("main")
    if root is None:
        raise ValueError("Main content not found; extraction requires review")
    for node in root.select(
        'script,style,nav,footer,form,button,iframe,[role="dialog"],.request-vido-popup-main,.breadcrumb'
    ):
        node.decompose()
    sections = [Section(heading=title, text=title)]
    hero_price = next(
        (
            node
            for node in soup.select(".actual-price")
            if MONEY.search(node.get_text(" ", strip=True))
            and "starting from" in node.get_text(" ", strip=True).lower()
        ),
        None,
    )
    if source.treatment and hero_price:
        sections.append(
            Section(
                heading="Published starting price",
                text=clean(hero_price.get_text(" ", strip=True)),
                kind="price",
            )
        )
    heading = title
    lines: list[str] = []
    seen: set[str] = set()

    def flush():
        if lines:
            sections.append(Section(heading=heading, text="\n".join(lines)))
            lines.clear()

    for node in root.find_all(["h2", "h3", "h4", "p", "li", "table"]):
        if node.find_parent("table") or (node.name != "li" and node.find_parent("li")):
            continue
        if node.name == "p" and node.find(["p", "h2", "h3", "h4", "table", "ul", "ol"]):
            continue
        text = clean(node.get_text(" ", strip=True))
        if not text:
            continue
        if re.match(
            r"(Related Experiences|Unlock the Best|Explore Top Medical Centers|About PlacidWay|Accreditations & Certifications)",
            text,
            re.IGNORECASE,
        ):
            break
        if node.name.startswith("h"):
            flush()
            heading = text
            if (
                source.category == "clinic_videos"
                and node.name == "h3"
                and node.parent
                and "desc" in node.parent.get("class", [])
                and len(text.split()) >= 5
            ):
                sections.append(
                    Section(heading="Video titles", text=text, kind="video")
                )
            continue
        if node.name == "table":
            flush()
            rows = node.find_all("tr")
            headers: list[str] = []
            for row in rows:
                cells = row.find_all(["th", "td"], recursive=False)
                if not cells:
                    continue
                values = [clean(cell.get_text(" ", strip=True)) for cell in cells]
                if any(cell.name == "th" for cell in cells):
                    headers = values
                    continue
                if (
                    not headers
                    and row == rows[0]
                    and not MONEY.search(" ".join(values))
                ):
                    headers = values
                    continue
                row_text = " | ".join(
                    f"{headers[i]}: {value}" if i < len(headers) else value
                    for i, value in enumerate(values)
                    if value
                    and (
                        i >= len(headers)
                        or headers[i].lower() not in ("actions", "action")
                    )
                )
                if row_text and row_text not in seen:
                    sections.append(
                        Section(heading=heading, text=row_text, kind="table_row")
                    )
                    seen.add(row_text)
            continue
        if node.name == "li" and node.find_parent("li"):
            continue
        if text not in seen and len(text) > 15:
            lines.append(text)
            seen.add(text)
    flush()
    if sum(len(section.text) for section in sections) < 200:
        raise ValueError("Too little meaningful source content")
    return title, sections, quote_url


def make_chunks(
    source: Source, title: str, sections: list[Section], timestamp: str | None = None
) -> list[Chunk]:
    """Heading-aware ~450-word windows. Table rows always remain atomic.

    MiniLM has a 256-wordpiece limit, so embeddings separately average overlapping
    180-word windows; the longer original evidence stays readable and traceable.
    """
    timestamp = timestamp or datetime.now(UTC).isoformat()
    chunks = []
    for section in sections:
        words = section.text.split()
        windows = (
            [section.text]
            if section.kind == "table_row" or len(words) <= 420
            else [
                " ".join(words[start : start + 420])
                for start in range(0, len(words), 365)
            ]
        )
        for text in windows:
            content = f"{section.heading}\n{text}" if section.heading != text else text
            digest = hashlib.sha256(content.encode()).hexdigest()
            chunk_id = f"{source.id}-{digest[:16]}"
            if any(c.id == chunk_id for c in chunks):
                continue
            chunks.append(
                Chunk(
                    id=chunk_id,
                    source_id=source.id,
                    url=source.url,
                    title=title,
                    category=source.category,
                    heading=section.heading,
                    text=content,
                    content_hash=digest,
                    ingested_at=timestamp,
                    treatment=source.treatment,
                )
            )
    return chunks


def extract_prices(source: Source, chunks: list[Chunk]) -> list[PriceRecord]:
    """Conservative row extraction. No implicit '$ means USD' and no inferred prices."""
    records: list[PriceRecord] = []
    for chunk in chunks:
        for line in chunk.text.splitlines():
            matches = list(MONEY.finditer(line))
            if not matches:
                continue
            is_row = " | " in line
            starting = bool(re.search(r"price starting from", line, re.IGNORECASE))
            if not is_row and not starting:
                continue
            # Do not index unnamed clinic-price rows or narrative add-on costs as a package.
            treatment = source.treatment
            label = line.split(" | ")[0]
            if not treatment:
                if "Procedure:" in line:
                    treatment = line.split("Procedure:")[-1].split(" | ")[0].strip()
                elif source.category == "price_comparison":
                    treatment = label.split(":", 1)[-1].strip()
                if not treatment:
                    continue
            country = (
                "Mexico"
                if source.id != "source-7"
                else next(
                    (c for c in ("Mexico", "Turkey", "Thailand") if c in line), None
                )
            )
            currency = (
                "USD"
                if "USD" in line
                else (
                    "EUR"
                    if "EUR" in line or "€" in line
                    else ("GBP" if "GBP" in line or "£" in line else "$")
                )
            )
            price = " – ".join(m.group(0).strip() for m in matches)
            qualifier = (
                "starting from"
                if starting
                else (
                    "listed package price"
                    if source.treatment
                    else ("range" if len(matches) > 1 else "listed price")
                )
            )
            scope = "package" if source.treatment else "listed_price"
            records.append(
                PriceRecord(
                    treatment=treatment,
                    label=label,
                    scope=scope,
                    clinic="ITC Immunity Therapy Center"
                    if source.id != "source-7"
                    else label.split(":", 1)[-1],
                    country=country,
                    price=price,
                    currency=currency,
                    qualifier=qualifier,
                    source_id=source.id,
                    source_url=source.url,
                    raw_evidence=line,
                    chunk_id=chunk.id,
                )
            )
    if not records:
        records.append(
            PriceRecord(
                treatment=source.treatment or source.title,
                source_id=source.id,
                source_url=source.url,
                raw_evidence="",
                price=None,
            )
        )
    return records
