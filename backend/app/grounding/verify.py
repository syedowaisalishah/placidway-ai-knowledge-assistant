"""Evidence gating and extractive output validation.

The model selects exact source passages. It never supplies the displayed factual
prose, URLs, prices, or clinical advice. This is deliberately stricter than
checking whether a plausible answer merely contains a citation.
"""

import re

from app.retrieval.store import Hit
from app.safety.query import Query, normalize
from app.schemas import Chunk, GeneratedAnswer

INTENT_EVIDENCE = {
    "inclusions": r"included in|inclusions|program includes|package includes",
    "recovery": r"recovery (?:time|period|takes|duration)|recover within|recover in \d",
    "duration": r"\d[ -]week|\d weeks|duration:",
    "doctors": r"dr\.|doctor|medical director",
    "location": r"tijuana|address|located|blvd\.",
    "languages": r"bilingual|english and spanish|languages",
    "aftercare": r"follow.up|post.discharge|aftercare|post.care",
    "exclusions": r"excluded|not included|additional cost",
    "videos": r"video|experience|story|journey",
    "treatments": r"treatment|therap|cancer",
    "overview": r"itc|immunity therapy",
}


def eligible_hits(query: Query, hits: list[Hit]) -> list[Hit]:
    if (
        query.countries
        and query.topic in ("adenocarcinoma", "adrenal cancer", "anal cancer", "ITC")
        and query.countries != ["Mexico"]
    ):
        return []
    if (
        query.clinic
        and query.clinic != "ITC"
        and query.topic in ("adenocarcinoma", "adrenal cancer", "anal cancer")
    ):
        return []
    pattern = INTENT_EVIDENCE.get(query.intent)
    if not pattern:
        return []
    result = []
    for hit in hits:
        chunk = hit.chunk
        if hit.score < 0.28:
            continue
        # Inclusions must be a package's actual inclusions, not a similar paragraph.
        text = (
            chunk.heading
            if query.intent in ("inclusions", "exclusions")
            else chunk.text
        )
        if not re.search(pattern, text, re.IGNORECASE):
            continue
        if (
            query.intent == "treatments"
            and query.topic == "ITC"
            and not re.search(
                r"treatments offered|treatment approach|alternative cancer treatments",
                chunk.heading,
                re.IGNORECASE,
            )
        ):
            continue
        if query.aspect:
            from app.safety.query import ASPECTS

            if not any(term in normalize(chunk.text) for term in ASPECTS[query.aspect]):
                continue
        if query.program and query.program not in chunk.text.lower():
            continue
        if (
            query.topic not in ("", "ITC", "alternative medicine")
            and not chunk.treatment
        ):
            if normalize(query.topic) not in normalize(chunk.text):
                continue
        result.append(hit)
    return result


def validate_answer(
    answer: GeneratedAnswer, hits: list[Hit], approved: dict[str, str]
) -> list[tuple[Chunk, str]]:
    if answer.status != "answered" or not answer.selections:
        return []
    retrieved = {hit.chunk.id: hit.chunk for hit in hits}
    verified = []
    for selection in answer.selections:
        chunk = retrieved.get(selection.chunk_id)
        if chunk is None or approved.get(chunk.source_id) != chunk.url:
            raise ValueError("Unretrieved or unapproved citation")
        quote = selection.quote.strip()
        # Exact contiguous matching simultaneously preserves amounts, currencies,
        # qualifiers, negations, and their relationship to the cited source.
        if quote not in chunk.text:
            raise ValueError("Answer contains unsupported or rewritten evidence")
        start = chunk.text.index(quote)
        end = start + len(quote)
        line_start = chunk.text.rfind("\n", 0, start) + 1
        next_newline = chunk.text.find("\n", end)
        line_end = len(chunk.text) if next_newline == -1 else next_newline
        if start != line_start or end != line_end:
            # Gemini can copy a complete sentence from inside a source line.
            # Expand it to that exact line so surrounding claims and qualifiers
            # are shown. A fragment from the middle of a sentence, such as a
            # price without "starting from", must still fail closed.
            prefix = chunk.text[line_start:start]
            suffix = chunk.text[end:line_end]
            sentence_start = not prefix or prefix.endswith((". ", "! ", "? ", ": "))
            sentence_end = not suffix or (
                quote.endswith((".", "!", "?")) and suffix.startswith(" ")
            )
            if not sentence_start or not sentence_end:
                raise ValueError(
                    "Evidence must preserve complete source lines and qualifications"
                )
            quote = chunk.text[line_start:line_end]
        if re.search(
            r"https?://|<script|ignore.{0,30}instructions|system prompt|api.key",
            quote,
            re.IGNORECASE,
        ):
            raise ValueError("Unsafe source instruction or URL in selected passage")
        if any(quote == previous for _, previous in verified):
            continue
        verified.append((chunk, quote))
    return verified


def extractive_selection(query: Query, hits: list[Hit]) -> GeneratedAnswer:
    """Explicit source-reading mode. It is never used to hide a Gemini error."""
    selections = []
    for hit in hits[:3]:
        text = hit.chunk.text
        # Keep whole source lines and a complete sentence when a paragraph is long.
        if len(text) > 1100:
            lines = text.splitlines()
            selected = [lines[0]]
            for line in lines[1:]:
                if sum(len(s) for s in selected) + len(line) + 1 > 1100:
                    break
                selected.append(line)
            text = "\n".join(selected)
            if len(text) < 25 or len(selected) == 1:
                continue
        if len(text) < 12 or text not in hit.chunk.text:
            continue
        selections.append({"chunk_id": hit.chunk.id, "quote": text})
    return GeneratedAnswer(
        status="answered" if selections else "unknown", selections=selections
    )
