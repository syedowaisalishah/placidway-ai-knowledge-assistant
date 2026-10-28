# PlacidWay AI Knowledge Assistant

A source-cited chatbot for a focused set of PlacidWay clinic, treatment package, video, and pricing pages.

**Live app:** [placidway-ai.vercel.app](https://placidway-ai.vercel.app)
**Source list:** [config/approved_sources.yaml](config/approved_sources.yaml)

## How it works

The Next.js interface sends questions to a FastAPI service. The service searches a local Chroma index built with MiniLM embeddings and checks exact price records when a question asks about cost. Gemini can select relevant excerpts from the retrieved evidence; the backend verifies the selected text and source URL before returning an answer. If the evidence does not support a response, the assistant says so instead of guessing.

The knowledge base contains seven specified PlacidWay URLs. The crawler respects robots.txt and the site's crawl delay, and it does not follow links to other pages. Broader background notes in [docs/placidway-data.md](docs/placidway-data.md) are not part of the chatbot index. See [architecture](docs/architecture.md) for the data flow and [coverage limits](docs/chatbot-limitations.md) for cases the assistant cannot answer.

The UI shows source cards for factual answers, offers English, Spanish, and Arabic responses, and includes a larger-text option. Recent chats are saved in the visitor's browser and can be deleted individually. Do not enter personal health details in the chat.

## Run locally

Use Python 3.12 and Node 22. From the repository root:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r backend/requirements-runtime.txt
.venv/bin/python scripts/download_model.py --runtime-only
cp backend/.env.example backend/.env
# Set ANSWER_MODE=extractive in backend/.env for a keyless local run.
cd frontend && npm ci && npm run build && cd ..
PORT=8765 bash scripts/start_local.sh
```

Open `http://127.0.0.1:8765`. The included snapshot restores the local search index on first start. Source-reading mode needs no API key. To use Gemini, set `ANSWER_MODE=gemini`, `GEMINI_API_KEY`, `GEMINI_MODEL`, and `GEMINI_FREE_TIER_CONFIRMED` in `backend/.env`. Keep that file out of Git. Gemini errors return an unavailable message; they do not silently switch to another answer mode.

## Update the source index

The source list is validated by `scripts/verify_sources.py`. To fetch those pages again and export a new portable snapshot:

```bash
.venv/bin/python scripts/verify_sources.py
.venv/bin/python scripts/ingest.py --refresh --export data/snapshot
```

The crawler checks robots.txt and uses the site's observed ten-second delay. A failed rebuild leaves the previous index active. Commit the new `data/snapshot` and redeploy to update the public app. An in-process admin refresh alone is temporary on Vercel.

## Check the app

```bash
.venv/bin/python -m pytest backend/tests -q
.venv/bin/ruff check backend scripts
.venv/bin/python scripts/evaluate.py --mode extractive
cd frontend && npm run typecheck && npm run build && npm run test:e2e
```

The [production scenario results](evaluation/live_scenarios.md), [Gemini evaluation](evaluation/full_test_results_gemini.md), and [source-reading evaluation](evaluation/full_test_results.md) show actual answers and source links. The test set covers prices, comparisons, package details, follow-up context, unknown facts, privacy, and medical safety.

## API and deployment

`POST /api/chat` accepts a message and optional conversation ID and language. `GET /api/health` and `GET /api/knowledge/status` report service and index status. Admin refresh and unanswered-topic endpoints require a bearer secret. The OpenAPI page is at `/api/docs`.

The public app uses [Dockerfile.vercel](Dockerfile.vercel) to serve the static frontend and FastAPI from one origin. See [Vercel deployment](docs/vercel-deployment.md) for environment variables and storage behavior. [Dockerfile](Dockerfile), [docker-compose.yml](docker-compose.yml), and [render.yaml](render.yaml) are additional deployment options. The local `.env`, raw crawled pages, model files, and logs are excluded from Git.
