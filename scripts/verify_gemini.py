"""Verify the configured model without enabling billing or switching models.

API model visibility does not prove a free billing tier. The operator must check
AI Studio's billing page and set GEMINI_FREE_TIER_CONFIRMED=true first.
"""

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.config import get_settings
from app.generation.gemini import GeminiGenerator, GenerationUnavailable
from app.grounding.verify import eligible_hits, validate_answer
from app.retrieval.store import KnowledgeStore
from app.safety.query import analyze


async def main():
    settings = get_settings()
    if not settings.generation_enabled:
        print(
            json.dumps(
                {
                    "verified": False,
                    "reason": "A Gemini key and explicit free-tier confirmation are required. No request sent.",
                }
            )
        )
        raise SystemExit(2)
    from google import genai

    client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())
    try:
        model = client.models.get(model=settings.gemini_model)
        print(json.dumps({"model_visible": True, "model": model.name}))
    except Exception:
        print(
            json.dumps(
                {
                    "verified": False,
                    "reason": "Configured model could not be accessed. No fallback selected.",
                }
            )
        )
        raise SystemExit(2)
    finally:
        client.close()
    store = KnowledgeStore(settings)
    query = analyze("What is included in the adenocarcinoma package?")
    hits = eligible_hits(query, store.retrieve(query))
    generator = GeminiGenerator(settings)
    try:
        response = await generator.generate(query, hits)
        selections = validate_answer(
            response, hits, {s.id: s.url for s in store.sources}
        )
        print(
            json.dumps(
                {
                    "verified": bool(selections),
                    "model": settings.gemini_model,
                    "validated_passages": len(selections),
                }
            )
        )
        if not selections:
            raise SystemExit(2)
    except GenerationUnavailable as exc:
        print(json.dumps({"verified": False, "reason": exc.reason}))
        raise SystemExit(2)
    finally:
        await generator.close()


if __name__ == "__main__":
    asyncio.run(main())
