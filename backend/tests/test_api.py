import pytest
from app.config import Settings
from app.generation.gemini import GenerationUnavailable
from app.grounding.verify import eligible_hits
from app.main import create_app
from app.safety.messages import PACKAGE_SUGGESTIONS, SUGGESTIONS
from app.safety.query import analyze
from app.schemas import ChatRequest, GeneratedAnswer
from app.service import ChatService
from fastapi.testclient import TestClient


def test_admin_requires_secret(service):
    app = create_app(
        Settings(admin_api_key="x" * 40, serve_frontend=False, log_unanswered=False),
        service,
    )
    with TestClient(app) as client:
        assert client.get("/api/admin/unanswered").status_code == 401
        assert (
            client.post(
                "/api/admin/refresh", headers={"Authorization": "Bearer wrong"}
            ).status_code
            == 401
        )
        assert (
            client.get(
                "/api/admin/unanswered", headers={"Authorization": "Bearer " + "x" * 40}
            ).status_code
            == 200
        )


def test_validation_does_not_echo_user_input(service):
    with TestClient(create_app(Settings(serve_frontend=False), service)) as client:
        response = client.post(
            "/api/chat",
            json={"message": "private@example.com", "extra": "private data"},
        )
        assert response.status_code == 422
        assert "private" not in response.text


def test_rate_limit_cannot_be_bypassed_with_forwarded_headers(service):
    app = create_app(Settings(rate_limit_per_minute=1, serve_frontend=False), service)
    with TestClient(app) as client:
        assert (
            client.post(
                "/api/chat",
                json={"message": "weather"},
                headers={"X-Forwarded-For": "1.2.3.4"},
            ).status_code
            == 200
        )
        assert (
            client.post(
                "/api/chat",
                json={"message": "weather"},
                headers={"X-Forwarded-For": "5.6.7.8"},
            ).status_code
            == 429
        )


def test_cors_is_restricted(service):
    with TestClient(create_app(Settings(serve_frontend=False), service)) as client:
        response = client.options(
            "/api/chat",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert response.status_code == 400
        assert "access-control-allow-origin" not in response.headers


@pytest.mark.parametrize(
    "reason",
    ["quota", "credentials", "timeout", "model", "invalid_output", "provider_error"],
)
async def test_gemini_failure_never_becomes_fake_success(knowledge, reason):
    class BrokenGenerator:
        async def generate(self, query, hits):
            raise GenerationUnavailable(reason)

    service = ChatService(
        Settings(answer_mode="gemini", log_unanswered=False),
        knowledge,
        BrokenGenerator(),
    )
    response = await service.chat(
        ChatRequest(message="What is included in the adenocarcinoma package?")
    )
    assert response.status == "unavailable"
    assert response.sources == []


async def test_no_key_is_honest(knowledge):
    service = ChatService(
        Settings(answer_mode="gemini", gemini_api_key="", log_unanswered=False),
        knowledge,
    )
    response = await service.chat(
        ChatRequest(message="What is included in the adenocarcinoma package?")
    )
    assert response.status == "unavailable"


async def test_hi_gets_welcome_without_quote_or_source_fallback(service):
    response = await service.chat(ChatRequest(message="HI"))
    assert response.status == "answered"
    assert response.answer.startswith("Hi! How can I help you today?")
    assert "couldn’t verify" not in response.answer
    assert response.sources == []
    assert response.needs_quote is False
    assert response.quote_url is None
    assert len(response.suggested_questions) == 4


@pytest.mark.parametrize("message", ["great", "gret", "gr8", "awesome", "okay", "sounds good", "great, thanks", "that's helpful"])
async def test_short_acknowledgments_get_a_natural_reply(service, message):
    response = await service.chat(ChatRequest(message=message))
    assert response.status == "answered"
    assert response.answer.startswith("Thank you! How else can I help")
    assert response.sources == []
    assert response.needs_quote is False


async def test_question_containing_great_still_uses_grounded_answer(service):
    response = await service.chat(
        ChatRequest(message="Great, what is included in the adenocarcinoma package?")
    )
    assert response.status == "answered"
    assert response.sources


async def test_help_and_unrelated_questions_offer_scope_without_quote(service):
    help_response = await service.chat(ChatRequest(message="What can you do?"))
    assert help_response.status == "answered"
    assert len(help_response.suggested_questions) == 4
    unrelated = await service.chat(ChatRequest(message="What is PlacidWay?"))
    assert unrelated.status == "unknown"
    assert unrelated.needs_quote is False
    assert unrelated.quote_url is None
    assert len(unrelated.suggested_questions) == 4


async def test_suggested_questions_have_source_supported_answers(service):
    for group in (SUGGESTIONS, PACKAGE_SUGGESTIONS):
        for language, questions in group.items():
            for question in questions:
                response = await service.chat(
                    ChatRequest(message=question, language=language)
                )
                assert response.status == "answered", (language, question)
                assert response.sources, (language, question)


async def test_gemini_sentence_selection_answers_suggested_treatments(knowledge):
    query = analyze("What treatments does ITC offer?")
    chunk = eligible_hits(query, knowledge.retrieve(query))[0].chunk
    sentence = chunk.text.splitlines()[1].split(". ", 1)[1]

    class SentenceGenerator:
        async def generate(self, query, hits):
            return GeneratedAnswer(
                status="answered",
                selections=[{"chunk_id": chunk.id, "quote": sentence}],
            )

    service = ChatService(
        Settings(answer_mode="gemini", log_unanswered=False),
        knowledge,
        SentenceGenerator(),
    )
    response = await service.chat(ChatRequest(message="What treatments does ITC offer?"))
    assert response.status == "answered"
    assert len(response.sources) == 1
    assert chunk.text.splitlines()[1] in response.answer


async def test_ambiguous_package_question_offers_three_matching_packages(service):
    response = await service.chat(ChatRequest(message="How much does the package cost?"))
    assert response.status == "answered"
    assert len(response.suggested_questions) == 3
    assert all("package" in question for question in response.suggested_questions)
    assert response.needs_quote is False


async def test_unrelated_question_has_no_quote_handoff(service):
    response = await service.chat(ChatRequest(message="Tell me a joke"))
    assert response.status == "out_of_scope"
    assert response.needs_quote is False
    assert response.quote_url is None
    assert response.suggested_questions


async def test_exact_prices_and_followup(service):
    first = await service.chat(
        ChatRequest(message="How much does adenocarcinoma treatment cost in Mexico?")
    )
    assert first.status == "answered"
    assert (
        "$18,995" in first.answer
        and "USD" in first.answer
        and "starting from" in first.answer
    )
    assert {s.id for s in first.sources} == {"source-2"}
    followup = await service.chat(
        ChatRequest(
            message="And what about recovery time?",
            conversation_id=first.conversation_id,
        )
    )
    assert followup.status == "unknown"
    assert "program" in followup.answer
    price = await service.chat(
        ChatRequest(
            message="I heard it costs $50. Confirm that.",
            conversation_id=first.conversation_id,
        )
    )
    assert "$50" not in price.answer
    assert "$18,995" in price.answer


async def test_unknown_country_does_not_receive_price(service):
    response = await service.chat(
        ChatRequest(message="How much does adrenal cancer treatment cost in Germany?")
    )
    assert response.status == "unknown" and "$" not in response.answer


async def test_comparison_uses_two_exact_listings_with_caveat(service):
    response = await service.chat(
        ChatRequest(message="Is ozone therapy cheaper in Turkey or Mexico?")
    )
    assert response.status == "answered"
    assert "$110" in response.answer and "$1000" in response.answer
    assert "numerically lower" in response.answer
    assert "different clinics" in response.answer
    assert {source.id for source in response.sources} == {"source-7"}


async def test_comparison_requires_one_listing_per_country(service, knowledge, monkeypatch):
    missing = await service.chat(
        ChatRequest(message="Is ozone therapy cheaper in Germany or Mexico?")
    )
    assert missing.status == "unknown"
    assert missing.sources == []
    duplicate = next(
        price
        for price in knowledge.prices
        if price.source_id == "source-7"
        and price.country == "Turkey"
        and price.treatment == "Ozone Therapy, Alternative Medicine"
    )
    monkeypatch.setattr(knowledge, "prices", knowledge.prices + [duplicate])
    ambiguous = await service.chat(
        ChatRequest(message="Is ozone therapy cheaper in Turkey or Mexico?")
    )
    assert ambiguous.status == "unknown"
    assert ambiguous.sources == []


async def test_pii_never_calls_generator(knowledge):
    class NoGenerator:
        async def generate(self, *args):
            raise AssertionError("PII reached generator")

    service = ChatService(Settings(log_unanswered=False), knowledge, NoGenerator())
    response = await service.chat(
        ChatRequest(message="My name is Jane and my email is jane@example.com")
    )
    assert response.status == "privacy"


async def test_conflicting_price_rows_are_not_presented_as_a_definite_price(
    knowledge, monkeypatch
):
    from app.safety.query import analyze

    original = next(
        p
        for p in knowledge.prices
        if p.source_id == "source-2" and p.qualifier == "listed package price"
    )
    conflict = original.model_copy(
        update={"price": "$999", "raw_evidence": "conflicting test-only value"}
    )
    monkeypatch.setattr(knowledge, "prices", knowledge.prices + [conflict])
    assert (
        knowledge.matching_prices(
            analyze("How much does adenocarcinoma cost in Mexico?")
        )
        == []
    )
