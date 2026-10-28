"""Check a deployed demo and record what was actually observed."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.sources import load_sources


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/public-smoke.json")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    approved = {s.url for s in load_sources(ROOT / "config/approved_sources.yaml")}
    with httpx.Client(base_url=base, timeout=30, follow_redirects=False) as client:
        page = client.get("/")
        health = client.get("/api/health")
        knowledge = client.get("/api/knowledge/status")
        price = client.post(
            "/api/chat",
            json={"message": "What is the outpatient adenocarcinoma package price?"},
        )
        starting = client.post(
            "/api/chat",
            json={"message": "What does the adenocarcinoma package cost?"},
        )
        unknown = client.post(
            "/api/chat",
            json={"message": "What is the price for an adenocarcinoma package in Atlantis?"},
        )
        greeting = client.post("/api/chat", json={"message": "HI"})
        unrelated = client.post("/api/chat", json={"message": "Tell me a joke"})
        admin = client.get("/api/admin/unanswered")
    health_data = health.json() if health.status_code == 200 else {}
    knowledge_data = knowledge.json() if knowledge.status_code == 200 else {}
    price_data = price.json() if price.status_code == 200 else {}
    starting_data = starting.json() if starting.status_code == 200 else {}
    unknown_data = unknown.json() if unknown.status_code == 200 else {}
    greeting_data = greeting.json() if greeting.status_code == 200 else {}
    unrelated_data = unrelated.json() if unrelated.status_code == 200 else {}
    source_urls = [source["url"] for source in price_data.get("sources", [])]
    checks = {
        "page_served": page.status_code == 200 and b"PlacidWay" in page.content,
        "health_ready": health.status_code == 200
        and health_data.get("knowledge_ready") is True,
        "seven_sources_indexed": knowledge.status_code == 200
        and len(knowledge_data.get("sources", [])) == 7
        and all(s.get("status") == "indexed" for s in knowledge_data["sources"]),
        "price_grounded": price.status_code == 200
        and price_data.get("status") == "answered"
        and "$18,995" in price_data.get("answer", "")
        and "Out-Patient Program" in price_data.get("answer", "")
        and "3 Weeks" in price_data.get("answer", "")
        and bool(source_urls)
        and all(url in approved for url in source_urls),
        "grounded_answer_offers_followups": price.status_code == 200
        and len(price_data.get("suggested_questions", [])) >= 3,
        "starting_qualifier_preserved": starting.status_code == 200
        and starting_data.get("status") == "answered"
        and "starting from" in starting_data.get("answer", "")
        and "$18,995" in starting_data.get("answer", ""),
        "unknown_destination_abstained": unknown.status_code == 200
        and unknown_data.get("status") != "answered",
        "greeting_welcomes_without_quote": greeting.status_code == 200
        and greeting_data.get("status") == "answered"
        and greeting_data.get("answer", "").startswith("Hi! How can I help")
        and not greeting_data.get("needs_quote")
        and not greeting_data.get("quote_url")
        and len(greeting_data.get("suggested_questions", [])) == 4,
        "unrelated_question_redirects_without_quote": unrelated.status_code == 200
        and unrelated_data.get("status") == "out_of_scope"
        and not unrelated_data.get("needs_quote")
        and len(unrelated_data.get("suggested_questions", [])) == 4,
        "admin_protected": admin.status_code == 401,
    }
    result = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "base_url": base,
        "mode": health_data.get("answer_mode"),
        "gemini_configured": health_data.get("gemini_configured"),
        "checks": checks,
        "http_statuses": {
            "page": page.status_code,
            "health": health.status_code,
            "knowledge": knowledge.status_code,
            "price": price.status_code,
            "starting": starting.status_code,
            "unknown": unknown.status_code,
            "greeting": greeting.status_code,
            "unrelated": unrelated.status_code,
            "admin": admin.status_code,
        },
        "price_source_urls": source_urls,
        "unknown_status": unknown_data.get("status"),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"passed": sum(checks.values()), "total": len(checks), "url": base}))
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
