"""Run actual responses and write separate required-eight and extended reports.

Default evaluates explicit source-reading mode. Use --mode gemini only with a
configured, confirmed free-tier key. Never label local outputs as Gemini outputs.
"""

import argparse
import asyncio
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.config import Settings
from app.schemas import ChatRequest
from app.service import ChatService


async def evaluate(mode: str, output: Path):
    settings = Settings(answer_mode=mode, log_unanswered=False)
    service = ChatService(settings)
    cases = json.loads((ROOT / "evaluation/test_questions.json").read_text())
    results = []
    for case in cases:
        sid = None
        for preceding in case.get("context", []):
            response = await service.chat(
                ChatRequest(message=preceding, conversation_id=sid)
            )
            sid = response.conversation_id
        started = time.perf_counter()
        response = await service.chat(
            ChatRequest(message=case["question"], conversation_id=sid)
        )
        failures = []
        if response.status not in case["statuses"]:
            failures.append(f"Expected {case['statuses']}, received {response.status}")
        for text in case.get("must_contain", []):
            if text.lower() not in response.answer.lower():
                failures.append(f"Missing: {text}")
        for text in case.get("must_not_contain", []):
            if text.lower() in response.answer.lower():
                failures.append(f"Forbidden: {text}")
        if "source_ids" in case and {s.id for s in response.sources} != set(
            case["source_ids"]
        ):
            failures.append("Unexpected source selection")
        allowed = {s.id: s.url for s in service.knowledge.sources}
        if any(allowed.get(s.id) != s.url for s in response.sources):
            failures.append("Unapproved citation")
        if (
            response.status == "answered"
            and not response.sources
            and not response.quote_url
        ):
            failures.append("Factual answer has no citation or verified quote route")
        if case.get("language") and response.language != case["language"]:
            failures.append("Wrong language")
        results.append(
            dict(
                case,
                actual=response.model_dump(),
                latency_ms=round((time.perf_counter() - started) * 1000, 2),
                passed=not failures,
                failure_reason="; ".join(failures),
            )
        )
    output.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).isoformat()
    (output / f"actual_responses_{mode}.json").write_text(
        json.dumps(
            dict(mode=mode, run_at=timestamp, results=results),
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )
    for filename, subset in [
        ("assessment_8_tests.md", results[:8]),
        ("full_test_results.md", results),
    ]:
        lines = [
            f"# {'Required eight assessment cases' if len(subset) == 8 else 'Full application evaluation'}",
            f"\nExecuted: {timestamp}. Mode: **{mode}**.",
            "\nThese are actual application outputs. Source-reading mode uses local MiniLM retrieval and validated source excerpts; it does not call Gemini. Price answers use exact structured rows. Gemini live evaluation requires a key with confirmed free-tier billing.",
            f"\nResult: **{sum(r['passed'] for r in subset)}/{len(subset)} checks passed**. These checks cover the stated assertions; they are not a guarantee for all possible questions.",
        ]
        for result in subset:
            lines += [
                f"\n## {result['id']} — {result['category']}",
                f"\nQuestion: {result['question']}",
                f"\nExpected: {result['expected']}",
                f"\nStatus: **{'PASS' if result['passed'] else 'FAIL'}** · {result['latency_ms']} ms · `{result['actual']['status']}`",
            ]
            if result.get("context"):
                lines.append("\nPrior turns: " + " → ".join(result["context"]))
            lines += ["\nActual answer:\n", result["actual"]["answer"]]
            for source in result["actual"]["sources"]:
                lines.append(f"\nSource: [{source['title']}]({source['url']})")
            if result["failure_reason"]:
                lines.append("\nFailure: " + result["failure_reason"])
        (output / filename).write_text("\n".join(lines) + "\n")
    await service.generator.close()
    print(
        json.dumps(
            {
                "mode": mode,
                "passed": sum(r["passed"] for r in results),
                "total": len(results),
                "output": str(output),
            }
        )
    )
    if any(not r["passed"] for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode", choices=["gemini", "extractive"], default="extractive"
    )
    parser.add_argument("--output", type=Path, default=ROOT / "evaluation")
    args = parser.parse_args()
    asyncio.run(evaluate(args.mode, args.output))
