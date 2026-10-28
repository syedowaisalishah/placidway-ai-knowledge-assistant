"""Chat orchestration: local safety → retrieval → evidence gate → verified rendering."""

import asyncio
import json
import logging
import re
import time
from collections import deque
from datetime import UTC, datetime
from decimal import Decimal
from threading import Lock

from app.config import Settings
from app.conversation import ConversationStore
from app.generation.gemini import GeminiGenerator, GenerationUnavailable
from app.grounding.verify import eligible_hits, extractive_selection, validate_answer
from app.retrieval.store import KnowledgeStore
from app.safety.messages import MESSAGES, PACKAGE_SUGGESTIONS, SUGGESTIONS
from app.safety.query import analyze
from app.schemas import ChatRequest, ChatResponse, Citation

logger = logging.getLogger(__name__)


class UnansweredLog:
    """Logs only constrained topic metadata. Raw questions may contain health data."""

    def __init__(self, settings: Settings):
        self.path = settings.data_dir / "logs/unanswered.jsonl"
        self.enabled = settings.log_unanswered
        self.lock = Lock()

    def record(self, query, reason: str):
        if not self.enabled:
            return
        item = {
            "timestamp": datetime.now(UTC).isoformat(),
            "topic": query.topic,
            "intent": query.intent,
            "countries": query.countries,
            "language": query.language,
            "reason": reason,
        }
        try:
            with self.lock:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                if self.path.exists() and self.path.stat().st_size > 1_000_000:
                    # Bounded retention; no visitor identifiers or raw question text.
                    self.path.write_text(
                        "".join(self.path.read_text().splitlines(keepends=True)[-1000:])
                    )
                with self.path.open("a") as handle:
                    handle.write(json.dumps(item, ensure_ascii=False) + "\n")
        except OSError:
            logger.warning("unanswered_log_unavailable")

    def read(self) -> list[dict]:
        with self.lock:
            if not self.path.exists():
                return []
            return [
                json.loads(line) for line in self.path.read_text().splitlines()[-100:]
            ]


class Budget:
    def __init__(self, daily: int):
        self.daily = daily
        self.timestamps = deque()
        self.lock = Lock()

    def take(self):
        with self.lock:
            now = time.monotonic()
            while self.timestamps and self.timestamps[0] < now - 86400:
                self.timestamps.popleft()
            if len(self.timestamps) >= self.daily:
                raise GenerationUnavailable("local_budget")
            self.timestamps.append(now)


def markdown_quote(text: str) -> str:
    # Escape website Markdown control characters; URLs are displayed only as trusted citations.
    text = re.sub(r"([\\`*_{}\[\]<>])", r"\\\1", text)
    return "\n".join("> " + line for line in text.splitlines())


class ChatService:
    def __init__(self, settings: Settings, knowledge=None, generator=None):
        self.settings = settings
        self.knowledge = knowledge or KnowledgeStore(settings)
        self.generator = generator or GeminiGenerator(settings)
        self.sessions = ConversationStore()
        self.unanswered = UnansweredLog(settings)
        self.budget = Budget(settings.global_generation_per_day)
        self.generation_slots = asyncio.Semaphore(2)

    async def chat(self, request: ChatRequest) -> ChatResponse:
        session_id, context = self.sessions.get(request.conversation_id)
        query = analyze(request.message, context, request.language)
        messages = MESSAGES[query.language]
        normalized_request = request.message.casefold().rstrip("?.؟")
        suggested_questions = [
            question
            for question in SUGGESTIONS[query.language]
            if question.casefold().rstrip("?.؟") != normalized_request
        ]

        def fallback(key: str, status: str = "unknown", quote: bool = False):
            self.unanswered.record(query, key)
            return ChatResponse(
                status=status,
                answer=messages[key],
                conversation_id=session_id,
                language=query.language,
                needs_quote=quote,
                quote_url=self.knowledge.quote_url() if quote else None,
                suggested_questions=(
                    suggested_questions
                    if key
                    in (
                        "unknown",
                        "price_unknown",
                        "out_of_scope",
                        "multiple_treatments",
                        "comparison",
                        "recovery",
                    )
                    else []
                ),
            )

        if query.block:
            if query.block in ("privacy", "medical_safety", "out_of_scope"):
                return fallback(query.block, query.block)
            if query.block == "unsupported_topic" and not query.topic:
                return fallback("out_of_scope", "unknown")
            return fallback(
                "multiple_treatments"
                if query.block == "multiple_treatments"
                else "unknown",
                quote=query.block != "multiple_treatments",
            )
        status = await asyncio.to_thread(self.knowledge.status)
        if not status["ready"]:
            return fallback("knowledge_unavailable", "unavailable")
        if query.intent in ("greeting", "help", "thanks", "clarify_topic"):
            return ChatResponse(
                status="answered",
                answer=messages[query.intent],
                conversation_id=session_id,
                language=query.language,
                suggested_questions=(
                    PACKAGE_SUGGESTIONS[query.language]
                    if query.intent == "clarify_topic"
                    else suggested_questions
                    if query.intent != "thanks"
                    else []
                ),
            )
        if query.intent in ("quote", "booking"):
            return ChatResponse(
                status="answered" if query.intent == "quote" else "unknown",
                answer=messages[query.intent],
                sources=[],
                conversation_id=session_id,
                language=query.language,
                needs_quote=True,
                quote_url=self.knowledge.quote_url(),
                suggested_questions=suggested_questions,
            )
        self.sessions.update(session_id, query)
        if query.intent == "comparison":
            prices = await asyncio.to_thread(self.knowledge.comparison_prices, query)
            if not prices:
                return fallback("comparison", quote=True)
            amounts = [Decimal(p.price.replace("$", "").replace(",", "")) for p in prices]
            comparison = (
                messages["comparison_equal"]
                if amounts[0] == amounts[1]
                else messages["comparison_lower"].format(
                    country=prices[0].country
                    if amounts[0] < amounts[1]
                    else prices[1].country
                )
            )
            source = next(s for s in self.knowledge.sources if s.id == "source-7")
            evidence = "\n".join(p.raw_evidence for p in prices)
            return ChatResponse(
                status="answered",
                answer=(
                    messages["comparison_intro"].format(treatment=query.topic)
                    + "\n\n"
                    + "\n\n".join(markdown_quote(p.raw_evidence) for p in prices)
                    + "\n\n"
                    + comparison
                ),
                sources=[
                    Citation(
                        id=source.id,
                        title=source.title,
                        url=source.url,
                        excerpt=evidence,
                    )
                ],
                conversation_id=session_id,
                language=query.language,
                needs_quote=True,
                quote_url=self.knowledge.quote_url(),
                suggested_questions=suggested_questions,
            )
        if query.intent == "pricing":
            prices = await asyncio.to_thread(self.knowledge.matching_prices, query)
            if not prices:
                return fallback("price_unknown", quote=True)
            # For a specific package, all program rows and starting qualifier come
            # from that package only. Never borrow a similar treatment's amount.
            intro = messages["false_price" if query.false_premise else "price_intro"]
            body = "\n\n".join(markdown_quote(p.raw_evidence) for p in prices)
            citations = []
            for source_id in dict.fromkeys(p.source_id for p in prices):
                source = next(s for s in self.knowledge.sources if s.id == source_id)
                citations.append(
                    Citation(
                        id=source_id,
                        title=source.title,
                        url=source.url,
                        excerpt="\n".join(
                            p.raw_evidence for p in prices if p.source_id == source_id
                        ),
                    )
                )
            return ChatResponse(
                status="answered",
                answer=f"{intro}\n\n{body}\n\n{messages['price_note']}",
                sources=citations,
                conversation_id=session_id,
                language=query.language,
                needs_quote=True,
                quote_url=self.knowledge.quote_url(),
                suggested_questions=suggested_questions,
            )
        try:
            hits = await asyncio.to_thread(self.knowledge.retrieve, query)
        except Exception:
            logger.warning("retrieval_unavailable")
            return fallback("knowledge_unavailable", "unavailable")
        hits = eligible_hits(query, hits)
        if not hits:
            return fallback(
                "recovery" if query.intent == "recovery" else "unknown", quote=True
            )
        try:
            if self.settings.answer_mode == "extractive":
                result = extractive_selection(query, hits)
            else:
                self.budget.take()
                async with self.generation_slots:
                    result = await self.generator.generate(query, hits)
            selections = validate_answer(
                result, hits, {s.id: s.url for s in self.knowledge.sources}
            )
        except GenerationUnavailable as exc:
            logger.info("generation_unavailable reason=%s", exc.reason)
            return fallback("unavailable", "unavailable")
        except ValueError:
            logger.warning("grounding_validation_rejected")
            return fallback("unknown", quote=True)
        if not selections:
            return fallback("unknown", quote=True)
        citations = []
        for source_id in dict.fromkeys(chunk.source_id for chunk, _ in selections):
            chunk = next(
                chunk for chunk, _ in selections if chunk.source_id == source_id
            )
            citations.append(
                Citation(
                    id=source_id,
                    title=chunk.title,
                    url=chunk.url,
                    excerpt="\n\n".join(
                        quote for c, quote in selections if c.source_id == source_id
                    ),
                )
            )
        medical = query.intent in ("overview", "treatments", "videos", "recovery")
        return ChatResponse(
            status="answered",
            answer=messages["intro"]
            + "\n\n"
            + "\n\n".join(markdown_quote(quote) for _, quote in selections),
            sources=citations,
            conversation_id=session_id,
            language=query.language,
            disclaimer=messages["medical_note"] if medical else None,
            suggested_questions=suggested_questions,
        )
