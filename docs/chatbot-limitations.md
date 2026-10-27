# Chatbot coverage and limitations

## What the assistant can answer

The assessment requires factual answers from exactly the seven URLs in `config/approved_sources.yaml`. These cover one ITC clinic profile, three named cancer packages, clinic videos, an ITC price list, and one alternative-medicine price comparison page. The assistant can answer when a relevant passage or exact price row is present and can be cited. `docs/placidway-data.md` contains broader research but is deliberately not ingested because it is outside the approved chatbot corpus.

The app first classifies the question locally, then retrieves source passages. An evidence gate checks the requested treatment, destination, clinic, program, and question type. Gemini selects exact passages from those results, and a final validator checks the quote and approved URL. The local mode uses the same source checks without Gemini. Each stage can return an unknown answer if it cannot establish support.

## Why a supported question failed

On October 28, the suggested question “What treatments does ITC offer?” returned unknown even though the approved clinic profile contains treatment information. Retrieval found two relevant passages. Gemini copied complete sentences from within longer source lines; the final validator required newline-to-newline quotes, so it rejected them. The validator now expands an exactly matched sentence to its full original source line before display. It still rejects invented wording, unapproved sources, and fragments from the middle of a sentence such as a price missing “starting from.” A live local check answered all four English suggested questions with approved citations after the fix.

The first full Gemini evaluation then passed 28/30. Both failures were the anal-cancer package inclusion question. The inclusion excerpts did not repeat the treatment name inside their text, so Gemini sometimes returned unknown despite retrieval correctly restricting them to the anal-cancer page. The Gemini evidence payload now includes the approved source title and treatment label alongside each excerpt. The model still has to quote facts from the excerpt text, and the final validator still checks exact text and URL. The rerun passed 30/30; its real outputs are stored locally in `artifacts/evaluation-gemini/`.

## Deliberate limits

| Situation | Current behavior | Reason |
| --- | --- | --- |
| A fact appears only elsewhere on PlacidWay | Declines to verify it | The seven-URL assessment allowlist excludes other pages. |
| A treatment, clinic, or destination is not named in the approved evidence | Declines or asks for a more specific treatment | Similar packages and places cannot be treated as identical. |
| A published program duration is given but recovery time is not | Declines the recovery estimate | A three-week program does not establish a recovery period. |
| A personal diagnosis, safety judgment, or promised outcome is requested | Gives a safety response | Website claims cannot determine individual clinical suitability. |
| A question uses an entity or phrasing outside the local vocabulary | May decline even if a page contains a relevant fact | Raw personal text is not sent to the free-tier model; local parsing is intentionally constrained. |
| Gemini hits a quota, credential, or provider error | Says answers are temporarily unavailable | The app does not disguise a model failure as a sourced answer. |

The app cannot truthfully guarantee an answer to every possible question. More model freedom cannot create missing or verified source facts.

## Improving coverage

For the existing assessment, add actual unanswered user phrasings to an evaluation set, inspect which stage rejected each one, and improve local query recognition or retrieval only when an approved passage directly supports the answer. Keep regression tests for wrong package, country, price qualifier, citation, privacy, and medical safety cases.

Answering questions about the entire PlacidWay website would be a **different knowledge scope**. It would require approval to change the seven-URL assessment requirement, a verified source inventory, crawl permissions, refreshed indexing, citation checks, and new evaluations for the added topics. The broader research note alone is not a substitute for verified website evidence.
