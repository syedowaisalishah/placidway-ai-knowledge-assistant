# 45-minute technical walkthrough

## 0–5 minutes: problem and boundaries

Open `README.md`, the assessment PDF, and `config/approved_sources.yaml`. Explain the seven-source restriction and why `placidway-data.md` is business context rather than chatbot evidence. Show `docs/source-verification.json`: exact hyperlinks and a checksum establish where the allowlist came from.

## 5–12 minutes: ingestion

Open `backend/app/ingestion/crawler.py`. Walk through robots permissions, the ten-second observed delay, request limits, redirects, and failure behavior. Explain that permission metadata is not additional factual knowledge.

Open `extract.py`: main-article selection, duplicate/navigation removal, table-row preservation, starting-price extraction, and no currency inference. Explain why the three cancer packages must keep distinct source IDs even when their prices match.

Open `pipeline.py`: new version directory, unchanged embedding reuse, checksums, Chroma validation, atomic promotion, and rollback by retaining the previous pointer. Show `data/snapshot/manifest.json` and explain why a portable snapshot is necessary on an ephemeral host.

## 12–20 minutes: embeddings and retrieval

Open `retrieval/embeddings.py`. Explain MiniLM, normalized vectors, cosine similarity, the tokenizer limit, and averaging overlapping windows. The ONNX serving path is the same model and mean-pooling calculation, not a replacement embedding model. Sentence Transformers remains available for local ingestion and compatibility checks.

Open `retrieval/store.py`. Trace an adenocarcinoma query to source-2. Explain the combination of semantic search, lexical matching, and heading relevance. Show that pricing follows exact structured records and checks treatment, country, clinic, and program.

## 20–28 minutes: safety and generation

Open `safety/query.py` and `service.py`. Trace a normal query, a follow-up, a personalized medical question, and an unknown country. Show the constrained description that reaches Gemini; raw visitor text and prior answers do not.

Open `generation/gemini.py` and `grounding/verify.py`. Explain structured selections, exact contiguous passages, complete-line checks, backend-owned URLs, and explicit unavailable responses. Be candid: exact quoting guarantees fidelity, not universal relevance or clinical validity. Source-reading mode is a separate explicit setting; it never silently replaces a failed Gemini call.

## 28–35 minutes: API and UI

Open `main.py`: lifespan restoration, one worker, request validation, restricted CORS, rate limiting, bearer admin authorization, refresh task, and sanitized errors. Explain why a proxy shares the rate limit when forwarding headers are not trusted.

Show desktop and mobile chat, source cards, source library, quote handoff, clear-chat, language selection, and network failure state. Explain that Arabic/Spanish framing is localized while source quotations remain original English.

## 35–40 minutes: results and deployment

Show `evaluation/assessment_8_live.md`, `evaluation/assessment_8_tests.md`, `evaluation/full_test_results.md`, and `docs/verification.md`. Distinguish production Gemini responses from local source-reading results, deterministic tests, and browser tests. Open `Dockerfile.vercel` and `docs/vercel-deployment.md`. Explain cold-start restoration, ephemeral refresh state, free-tier limits, and why seven-day availability is still pending.

## 40–45 minutes: a small live change

Choose one bounded change:

- **Change retrieval breadth:** update `RETRIEVAL_K` in `backend/.env` or the default in `config.py`. Restart the API and rerun `python scripts/evaluate.py`.
- **Change the Gemini instruction:** edit `SYSTEM_INSTRUCTION` in `generation/gemini.py`. Keep exact passage selection and no external tools. Run grounding tests. A live model evaluation requires the configured free-tier key.
- **Add a test:** add a row to `evaluation/test_questions.json` or a focused Pytest case. Run the evaluator or that test file. Do not update expectations just to make a failure pass.
- **Add a supported phrase:** add an alias to an existing approved topic in `safety/query.py`, then test that it selects the same source and that similar unsupported phrases still abstain.
- **Refresh content:** run `python scripts/ingest.py --refresh --export data/snapshot`, inspect the report, rerun evaluation, and redeploy the new snapshot. Never add an eighth page.

Useful commands from an activated virtual environment:

```bash
python -m pytest backend/tests/test_grounding.py -q
python scripts/evaluate.py
python scripts/verify_sources.py
python scripts/verify_gemini.py
```
