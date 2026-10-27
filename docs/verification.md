# Verification record

Checked October 27, 2026. The application was evaluated in explicit `ANSWER_MODE=extractive` (source-reading mode). No Gemini request was made; `scripts/verify_gemini.py` returned `verified: false` because no key and no free-tier confirmation were available.

| Check | Observed result |
| --- | --- |
| PDF hyperlink verification | Seven of seven exact allowlisted URLs match embedded hyperlinks in the supplied PDF. |
| Live source refresh | Seven of seven pages indexed after robots check and ten-second crawl delay. 295 evidence chunks and 29 structured price records. 295 unchanged chunks reused prior embeddings. |
| Backend tests | 61 passed; one upstream Starlette `httpx` deprecation warning. |
| Python lint | `ruff check backend scripts` passed. |
| Frontend | TypeScript check and Next.js production static build passed. |
| Browser | Four Playwright tests passed against the running FastAPI frontend: desktop pricing and citations, seven-source library and dialog, mobile Arabic, and network error handling. Results in `evaluation/browser-results.json`. |
| Required and extended evaluation | Eight of eight required cases and 30 of 30 total cases passed in source-reading mode. Actual outputs in `evaluation/assessment_8_tests.md` and `evaluation/full_test_results.md`. |
| Public URL | Seven of seven live HTTP checks passed. Exact timestamp and URL in `docs/public-smoke.json`. It is a temporary tunnel, not verified seven-day hosting. |
| Container | `docker compose config --quiet` passed. Full image build is being checked separately; this line does not claim it passed. |

The public tests check page serving, healthy source index, the exact outpatient price row, the package starting-price qualifier, approved citations, abstention on an unknown destination, and administrator authorization. The public service runs under Linux user services with automatic restart while the host remains awake and the user manager remains active.

The stated acceptance goal of a verified Gemini free-tier integration and a stable public URL for seven days remains open. The local and public source-reading implementation is functional, but model credentials, account eligibility, and durable hosting were not supplied in this workspace. Evidence for the current temporary URL is a point-in-time smoke test only.
