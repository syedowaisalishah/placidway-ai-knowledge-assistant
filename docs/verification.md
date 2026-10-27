# Verification record

Checked October 27, 2026. The application was evaluated in explicit `ANSWER_MODE=extractive` (source-reading mode). No Gemini request was made; `scripts/verify_gemini.py` returned `verified: false` because no key and no free-tier confirmation were available.

| Check | Observed result |
| --- | --- |
| PDF hyperlink verification | Seven of seven exact allowlisted URLs match embedded hyperlinks in the supplied PDF. |
| Live source refresh | Seven of seven pages indexed after robots check and ten-second crawl delay. 295 evidence chunks and 29 structured price records. 295 unchanged chunks reused prior embeddings. |
| Backend tests | 67 passed; one upstream Starlette `httpx` deprecation warning. Includes greeting and mixed greeting-plus-question regression checks. |
| Python lint | `ruff check backend scripts` passed. |
| Frontend | TypeScript check and Next.js production static build passed. |
| Browser | Five Playwright tests passed against the running FastAPI frontend: desktop pricing and citations, seven-source library and dialog, greeting without an irrelevant quote link, mobile Arabic, and network error handling. Results in `evaluation/browser-results.json`. |
| Required and extended evaluation | Eight of eight required cases and 30 of 30 total cases passed in source-reading mode. Actual outputs in `evaluation/assessment_8_tests.md` and `evaluation/full_test_results.md`. |
| Public URL | Eight of eight live HTTP checks passed. Exact timestamp and URL in `docs/public-smoke.json`. It is a temporary tunnel, not verified seven-day hosting. |
| Source repository | Public GitHub repository at `https://github.com/syedowaisalishah/placidway-ai-knowledge-assistant` returned HTTP 200 without authentication. |
| Container | Compose configuration and the full Docker image build passed. A fresh container with a 512 MiB memory limit restored its index and passed seven of seven HTTP smoke checks. A semantic retrieval question also returned a cited answer; observed memory after that request was 211 MiB with no OOM. Evidence in `docs/container-smoke.json`. |

The public tests check page serving, healthy source index, the exact outpatient price row, the package starting-price qualifier, approved citations, abstention on an unknown destination, greeting behavior, and administrator authorization. The public service runs under Linux user services with automatic restart. User lingering is enabled on this host, but availability still depends on the computer remaining awake and online.

The stated acceptance goal of a verified Gemini free-tier integration and a stable public URL for seven days remains open. The local and public source-reading implementation is functional, but model credentials, account eligibility, and durable hosting were not supplied in this workspace. Evidence for the current temporary URL is a point-in-time smoke test only.
