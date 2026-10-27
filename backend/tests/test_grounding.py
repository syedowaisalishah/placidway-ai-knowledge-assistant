import pytest
from app.grounding.verify import eligible_hits, validate_answer
from app.retrieval.store import Hit
from app.safety.query import analyze
from app.schemas import Chunk, GeneratedAnswer


def sample():
    chunk = Chunk(
        id="c1",
        source_id="source-2",
        url="https://www.placidway.com/approved",
        title="Package",
        category="treatment_package",
        heading="Cost",
        text="Price starting from $18,995 USD.\nFlights are not included.",
        content_hash="abc",
        ingested_at="2026-10-27",
        treatment="adenocarcinoma",
    )
    return [Hit(chunk, 0.9, 0.9)], {"source-2": chunk.url}


@pytest.mark.parametrize(
    "chunk_id,quote",
    [
        ("invented", "Price starting from $18,995 USD."),
        ("c1", "Price starting from $50 USD."),
        ("c1", "Price starting from €18,995 EUR."),
        ("c1", "$18,995 USD."),
        ("c1", "Flights are included."),
    ],
)
def test_unsupported_numbers_currencies_qualifiers_and_citations_rejected(
    chunk_id, quote
):
    hits, approved = sample()
    answer = GeneratedAnswer(
        status="answered", selections=[{"chunk_id": chunk_id, "quote": quote}]
    )
    with pytest.raises(ValueError):
        validate_answer(answer, hits, approved)


def test_valid_complete_passage_is_accepted():
    hits, approved = sample()
    answer = GeneratedAnswer(
        status="answered",
        selections=[{"chunk_id": "c1", "quote": "Price starting from $18,995 USD."}],
    )
    assert validate_answer(answer, hits, approved)[0][1].startswith(
        "Price starting from"
    )


def test_complete_sentence_inside_line_expands_to_full_source_line():
    hits, approved = sample()
    line = (
        "The clinic describes a tailored treatment approach. "
        "Its page lists laser therapy, hyperthermia, and biomagnetic therapy as examples."
    )
    hits[0].chunk.text = line
    quote = "Its page lists laser therapy, hyperthermia, and biomagnetic therapy as examples."
    answer = GeneratedAnswer(
        status="answered", selections=[{"chunk_id": "c1", "quote": quote}]
    )
    assert validate_answer(answer, hits, approved) == [(hits[0].chunk, line)]


def test_list_item_body_expands_to_its_full_source_line():
    hits, approved = sample()
    line = (
        "Treatment Explanation: Physicians explain therapies such as laser therapy, "
        "hyperthermia, and biomagnetic therapy to patients."
    )
    hits[0].chunk.text = line
    quote = "Physicians explain therapies such as laser therapy, hyperthermia, and biomagnetic therapy to patients."
    answer = GeneratedAnswer(
        status="answered", selections=[{"chunk_id": "c1", "quote": quote}]
    )
    assert validate_answer(answer, hits, approved) == [(hits[0].chunk, line)]


def test_valid_quote_with_unapproved_url_rejected():
    hits, approved = sample()
    with pytest.raises(ValueError):
        validate_answer(
            GeneratedAnswer(
                status="answered",
                selections=[{"chunk_id": "c1", "quote": hits[0].chunk.text}],
            ),
            hits,
            {"source-2": "https://evil.example"},
        )


def test_recovery_is_not_program_duration(knowledge):
    q = analyze("What is the recovery time for adenocarcinoma?")
    assert eligible_hits(q, knowledge.retrieve(q)) == []


def test_wrong_country_cannot_borrow_mexican_package(knowledge):
    q = analyze("What is included in the adrenal cancer package in Turkey?")
    assert eligible_hits(q, knowledge.retrieve(q)) == []


def test_missing_specific_inclusion_is_not_answered_by_unrelated_inclusions(knowledge):
    q = analyze("Are flights included in the adenocarcinoma package?")
    assert eligible_hits(q, knowledge.retrieve(q)) == []
