# PlacidWay AI Knowledge Assistant

Repository: [github.com/syedowaisalishah/placidway-ai-knowledge-assistant](https://github.com/syedowaisalishah/placidway-ai-knowledge-assistant).

Live deployment: [placidway-ai.vercel.app](https://placidway-ai.vercel.app).

Assessment upload: [single submission PDF](docs/PlacidWay-Chatbot-Assessment-Submission.pdf), with [editable Markdown source](docs/assessment-submission.md). It contains the repository and public demo links, architecture summary, eight real live answers, and short limitations write-up.

A working, source-cited assessment chatbot built from the seven PlacidWay pages linked in the supplied PDF. It has a Next.js chat interface and a FastAPI API. Local MiniLM embeddings and ChromaDB retrieve passages; exact price rows are stored separately. An optional Gemini stage selects source passages through the official SDK. A checkout without a confirmed free-tier Gemini key runs in **source-reading mode**. It never presents local output as Gemini output.

The app answers only from the approved pages. It links each factual answer to its source, preserves displayed price qualifiers, and abstains when the exact treatment, destination, clinic, program, or evidence is absent. It does not give personal medical advice or treat the website's promotional claims as independently verified facts.

Visitors can greet the assistant, ask what it can do, or use clickable follow-up questions. A vague package question prompts for the treatment; an unrelated request gets a clear description of the seven-page scope. The suggested questions were checked against the approved index. The assistant still declines to invent facts beyond those pages.

The interface uses the [official PlacidWay logo](https://www.placidway.com/frontend/images/PlacidWay-logo-opt.png) stored locally in `frontend/public/brand/` and a coral, white, and charcoal theme based on the current PlacidWay homepage. This visual branding does not expand the assistant's seven-page factual knowledge scope.

The chat uses larger default reading text, clearer source labels and controls, and a wider answer column. The **Text size** button switches to an even larger view and saves the preference in the browser. On narrow screens, topic cards stack vertically and the composer remains usable without horizontal scrolling.

Recent chats are saved only in the current browser (up to 20 conversations and 60 messages per conversation). You can reopen or delete individual chats from the sidebar. Short replies such as “great,” “gret,” and “thanks” receive conversational responses. This does not expand the seven approved pages used for factual answers. Avoid entering personal health details because chat history is stored on this device.

See [chatbot limitations](docs/chatbot-limitations.md) for why some questions receive an unknown response and what expanding coverage would require. In particular, the assessment explicitly limits factual answers to the seven linked pages; the broader research note is not part of the chatbot index.

## Run locally

Requires Python 3.12, Node 22, and roughly 1 GB free for the local embedding model and dependencies. From the repository root:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r backend/requirements-runtime.txt
.venv/bin/python scripts/download_model.py --runtime-only
cp backend/.env.example backend/.env
# In backend/.env set ANSWER_MODE=extractive and a random ADMIN_API_KEY of 32+ characters.
cd frontend && npm ci && npm run build && cd ..
PORT=8765 bash scripts/start_local.sh
```

Open `http://127.0.0.1:8765`. The committed portable snapshot restores Chroma automatically on first launch. `GET /api/health` and `GET /api/knowledge/status` show the active mode and index status. The source-reading path needs no paid service or API key. The app defaults to Gemini mode in a new `.env`, so setting extractive mode is necessary for the keyless demo.

For Gemini mode, set `ANSWER_MODE=gemini`, `GEMINI_API_KEY`, `GEMINI_MODEL=gemini-3.1-flash-lite`, and `GEMINI_FREE_TIER_CONFIRMED=true` only after checking that the specific project and region qualify for free usage and paid billing is disabled. Then run `.venv/bin/python scripts/verify_gemini.py` and `.venv/bin/python scripts/evaluate.py --mode gemini`. A local, untracked key passed the generation check and 30/30 live evaluation cases on October 28. The app never silently falls back from a Gemini failure to local mode.

## Source and index operations

The exact allowlist is [config/approved_sources.yaml](config/approved_sources.yaml); [docs/source-verification.json](docs/source-verification.json) ties it to the PDF's embedded hyperlinks. [docs/placidway-data.md](docs/placidway-data.md) is broader background research and is outside the chatbot's knowledge scope. The crawler checks robots.txt and observes the site's ten-second crawl delay. It does not follow unrelated pages.

```bash
.venv/bin/python scripts/verify_sources.py
.venv/bin/python scripts/ingest.py --refresh --export data/snapshot
.venv/bin/python scripts/ingest.py --cached --export data/snapshot
```

Refresh writes a new index and switches to it only after validation. If a refresh fails, the previous index remains active. The portable `data/snapshot` is tracked in Git so a fresh deployment can rebuild Chroma without recrawling or re-embedding. The local model files, raw HTML, Chroma files, secrets, and logs are ignored.

## Evaluation and API

```bash
.venv/bin/pytest -q
.venv/bin/ruff check backend scripts
.venv/bin/python scripts/evaluate.py --mode extractive
cd frontend && npm run typecheck && npm run build && npm run test:e2e
```

The [required eight live cases](evaluation/assessment_8_live.md), [local Gemini evaluation](evaluation/full_test_results_gemini.md), and [source-reading evaluation](evaluation/full_test_results.md) contain real application outputs. The 30 cases cover pricing, exact treatment scope, unknown information, patient safety, multilingual framing, follow-up context, and injection attempts. [docs/verification.md](docs/verification.md) records the latest test and deployment checks.

`POST /api/chat` accepts `{ "message": "What is the outpatient adenocarcinoma package price?", "language": "en" }`. It returns an answer, status, approved source citations, and a conversation ID. `GET /api/health` and `GET /api/knowledge/status` are public. `POST /api/admin/refresh` and `GET /api/admin/unanswered` require `Authorization: Bearer <ADMIN_API_KEY>`. The OpenAPI schema is at `/api/docs`.

## Deployment and project notes

[Dockerfile](Dockerfile), [docker-compose.yml](docker-compose.yml), and [render.yaml](render.yaml) prepare additional deployment options. The Compose and Render templates start in source-reading mode until an eligible Gemini project is configured. The active public deployment uses [Dockerfile.vercel](Dockerfile.vercel). [docs/deployment.md](docs/deployment.md) distinguishes it from the earlier temporary tunnel. The seven-day availability requirement remains unverified until seven days have elapsed after submission.

For a personal demo on the free Vercel Hobby plan, use the root `Dockerfile.vercel` and follow [Vercel deployment](docs/vercel-deployment.md). It serves the static frontend and FastAPI together, with a temporary Chroma index reconstructed from the packaged snapshot on cold start. The local Gemini key is never bundled; configure it as a Vercel Secret after verifying the project's free-tier status.

Read [architecture](docs/architecture.md) for trust boundaries, [assessment validation](docs/assessment-validation.md) for the requirement-by-requirement audit, [live required-test answers](evaluation/assessment_8_live.md), [assessment write-up](docs/assessment_writeup.md) for trade-offs and limitations, and [interview walkthrough](docs/interview_walkthrough.md) for the assessment demonstration. The [implementation brief](docs/implementation-brief.md) preserves the supplied requirements.
