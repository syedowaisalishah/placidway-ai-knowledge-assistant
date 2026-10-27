from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Source(BaseModel):
    id: str
    title: str
    category: str
    url: str
    treatment: str = ""


class Section(BaseModel):
    heading: str
    text: str
    kind: str = "text"


class Chunk(BaseModel):
    id: str
    source_id: str
    url: str
    title: str
    category: str
    heading: str
    text: str
    content_hash: str
    ingested_at: str
    treatment: str = ""


class PriceRecord(BaseModel):
    treatment: str
    label: str = ""
    scope: str = "listed_price"
    clinic: str | None = None
    country: str | None = None
    price: str | None = None
    currency: str | None = None
    qualifier: str | None = None
    package_inclusions: list[str] = []
    source_id: str
    source_url: str
    raw_evidence: str
    chunk_id: str = ""


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=1500)
    conversation_id: str | None = Field(default=None, pattern=r"^[a-f0-9-]{36}$")
    language: Literal["en", "es", "ar"] | None = None

    @field_validator("message")
    @classmethod
    def nonempty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Please enter a question.")
        return value


class Citation(BaseModel):
    id: str
    title: str
    url: str
    excerpt: str


class ChatResponse(BaseModel):
    status: Literal[
        "answered",
        "unknown",
        "out_of_scope",
        "medical_safety",
        "unavailable",
        "privacy",
    ]
    answer: str
    sources: list[Citation] = []
    conversation_id: str
    needs_quote: bool = False
    disclaimer: str | None = None
    language: str = "en"
    quote_url: str | None = None
    suggested_questions: list[str] = Field(default_factory=list)


class EvidenceSelection(BaseModel):
    chunk_id: str
    # Exact contiguous excerpt. The backend rejects paraphrases and invented text.
    quote: str = Field(min_length=8, max_length=1200)


class GeneratedAnswer(BaseModel):
    status: Literal["answered", "unknown"]
    selections: list[EvidenceSelection] = Field(default_factory=list, max_length=4)
    needs_quote: bool = False
