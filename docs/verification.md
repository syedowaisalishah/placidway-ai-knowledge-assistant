# Verification record

Checked October 27, 2026. The application was evaluated in explicit `ANSWER_MODE=extractive` (source-reading mode). No Gemini request was made; `scripts/verify_gemini.py` returned `verified: false` because no key and no free-tier confirmation were available.

| Check | Observed result |
| --- | --- |
| PDF hyperlink verification | Seven of seven exact allowlisted URLs match embedded hyperlinks in the supplied PDF. |
| Live source refresh | Seven of seven pages indexed after robots check and ten-second crawl delay. 295 evidence chunks and 29 structured price records. 295 unchanged chunks reused prior embeddings. |
| Backend tests | 82 passed; one upstream Starlette `httpx` deprecation warning. Includes greetings, help, vague package questions, unrelated questions, and checks that every suggested question has a cited answer. |
| Python lint | `ruff check backend scripts` passed. |
| Frontend | TypeScript check and Next.js production static build passed. |
| Browser | Five Playwright tests passed against the running FastAPI frontend: desktop pricing and citations, seven-source library and dialog, greeting plus clickable questions, unrelated scope guidance, package clarification, mobile Arabic, and network error handling. Results in `evaluation/browser-results.json`. |
| Required and extended evaluation | Eight of eight required cases and 30 of 30 total cases passed in source-reading mode. Actual outputs in `evaluation/assessment_8_tests.md` and `evaluation/full_test_results.md`. |
| Public URL | Ten of ten live HTTP checks passed. Exact timestamp and URL in `docs/public-smoke.json`. It is a temporary tunnel, not verified seven-day hosting. |
| Source repository | Public GitHub repository at `https://github.com/syedowaisalishah/placidway-ai-knowledge-assistant` returned HTTP 200 without authentication. |
| Container | Compose configuration and the full Docker image build passed. A fresh container with a 512 MiB memory limit restored its index and passed ten of ten HTTP smoke checks, including greeting and unrelated-question behavior. Observed memory after the checks was 92.9 MiB with no OOM. Evidence in `docs/container-smoke.json`. |

The public tests check page serving, healthy source index, the exact outpatient price row, the package starting-price qualifier, approved citations, follow-up suggestions, abstention on an unknown destination, greeting behavior, unrelated-question guidance, and administrator authorization. The public service runs under Linux user services with automatic restart. User lingering is enabled on this host, but availability still depends on the computer remaining awake and online.

At the time of this October 27 record, the Gemini integration and a stable public URL for seven days remained open. Evidence for the temporary URL is a point-in-time smoke test only.

## Local update — October 28, 2026

The user confirmed that the key's Google AI Studio project displays **Free + Active**. No payment card or billing account was added by this project work. The locally saved key is ignored by Git and was not included in the repository. `scripts/verify_gemini.py` reported the configured model visible and two validated passages from a real generation request. The local server at `127.0.0.1:8765` now reports `answer_mode: gemini`, `gemini_configured: true`, and a ready knowledge index.

A reported failure in the suggested ITC treatments question was reproduced: retrieval found two eligible passages, while Gemini selected exact sentences inside longer source lines and the citation gate rejected them. The validator now expands those sentences to their complete original lines. The live local flow `Hi` → all four English suggested questions returned `answered`; each factual response had an approved source citation. The first full Gemini run passed 28/30; two anal-cancer inclusion cases failed because Gemini did not know the treatment identity of otherwise eligible excerpts. Adding the approved source title and treatment label to the evidence payload resolved this. The rerun passed **30/30 live Gemini cases**, including the required eight, with actual outputs in local `artifacts/evaluation-gemini/`. Backend tests: **86 passed**; Python lint passed. No seven-day hosting claim is made.

The chat interface was then restyled using the current PlacidWay homepage's coral, white, and charcoal palette and its official logo image. The static frontend build and TypeScript check passed. The live desktop and mobile views were inspected with the logo loaded and no horizontal overflow; all **5 Playwright browser tests** passed against the local Gemini-mode service. Browser test output is in `evaluation/browser-results.json`.

## Vercel package check — October 28, 2026

The root `Dockerfile.vercel` built locally. A fresh container under a 512 MiB memory limit restored the seven-page index from the packaged snapshot. The homepage, PlacidWay logo, `/api/health`, and `/api/knowledge/status` all returned HTTP 200. In default source-reading mode, the greeting, ITC treatments question, and adenocarcinoma price question returned answers; the factual responses carried approved citations. A second fresh container received the existing local Gemini configuration **at runtime**, reported `answer_mode: gemini` and `gemini_configured: true`, and returned a cited answer to the ITC treatments question. The API key was not placed in the image or committed. These are local container checks; a Vercel URL has not yet been deployed or tested.
