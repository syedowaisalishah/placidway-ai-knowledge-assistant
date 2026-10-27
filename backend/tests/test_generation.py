import json
from types import SimpleNamespace

from app.config import Settings
from app.generation.gemini import GeminiGenerator
from app.grounding.verify import eligible_hits
from app.safety.query import analyze


async def test_gemini_receives_approved_package_metadata(knowledge):
    query = analyze("What is included in the anal cancer package?")
    hits = eligible_hits(query, knowledge.retrieve(query))
    captured = {}

    class FakeModels:
        async def generate_content(self, **kwargs):
            captured.update(json.loads(kwargs["contents"]))
            return SimpleNamespace(
                text='{"status":"unknown","selections":[],"needs_quote":false}'
            )

    generator = GeminiGenerator(
        Settings(gemini_api_key="test-key", gemini_free_tier_confirmed=True)
    )
    generator.client = SimpleNamespace(aio=SimpleNamespace(models=FakeModels()))
    await generator.generate(query, hits)

    assert captured["question"].startswith("inclusions; anal cancer")
    assert captured["evidence"]
    assert all(item["source_id"] == "source-4" for item in captured["evidence"])
    assert all(item["treatment"] == "anal cancer" for item in captured["evidence"])
    assert all("Anal Cancer" in item["source_title"] for item in captured["evidence"])
