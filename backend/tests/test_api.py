import pytest
from app.config import Settings
from app.generation.gemini import GenerationUnavailable
from app.main import create_app
from app.schemas import ChatRequest
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
