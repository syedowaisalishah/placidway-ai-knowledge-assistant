"""Recover the approved hyperlinks from the supplied assessment, without crawling."""

import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def main() -> None:
    from app.config import get_settings
    from app.sources import load_sources

    pdf = ROOT / "docs/AI Automation Assessment Website Knowledge Chatbot.pdf"
    xml = subprocess.check_output(["pdftohtml", "-xml", "-stdout", "-i", str(pdf)])
    tree = ET.fromstring(xml)
    links = {
        node.attrib["href"] for node in tree.findall(".//a") if "href" in node.attrib
    }
    sources = load_sources(get_settings().source_config)
    report = {
        "assessment_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
        "verification": "Embedded PDF hyperlinks; not inferred from page titles",
        "sources": [
            dict(source.model_dump(), hyperlink_verified=source.url in links)
            for source in sources
        ],
    }
    output = ROOT / "docs/source-verification.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not all(s["hyperlink_verified"] for s in report["sources"]):
        raise SystemExit("Approved configuration differs from PDF hyperlinks.")


if __name__ == "__main__":
    main()
