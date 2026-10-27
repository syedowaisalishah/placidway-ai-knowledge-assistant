import pytest
from app.config import Settings
from app.retrieval.store import KnowledgeStore
from app.service import ChatService


@pytest.fixture(scope="session")
def knowledge():
    settings = Settings(answer_mode="extractive", log_unanswered=False)
    store = KnowledgeStore(settings)
    store.load()
    return store


@pytest.fixture
def service(knowledge):
    return ChatService(
        Settings(answer_mode="extractive", log_unanswered=False), knowledge=knowledge
    )
