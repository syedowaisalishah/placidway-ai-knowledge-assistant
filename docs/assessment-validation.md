# Assessment validation — October 28, 2026

Compared the pasted **AI Automation Assessment: Website Knowledge Chatbot** with the repository and the running production site at [placidway-ai.vercel.app](https://placidway-ai.vercel.app). “Met” below means the reviewed implementation and sampled behavior support the requirement; it is not a claim about every hidden question or future uptime.

| Assessment requirement | Result | Evidence and limit |
| --- | --- | --- |
| Only the seven supplied pages; respectful ingestion | **Met** | `scripts/verify_sources.py` matched all 7 allowlisted URLs to embedded PDF hyperlinks. `backend/app/ingestion/crawler.py` identifies the crawler, reads robots.txt, and uses the observed 10-second crawl delay. `config/approved_sources.yaml` is the exact allowlist; `docs/placidway-data.md` is excluded from the index. |
| Searchable knowledge base | **Met** | The packaged snapshot restores Chroma with local MiniLM vectors; structured price rows supplement passage retrieval. Live `/api/knowledge/status` reported 7 sources. See `docs/architecture.md`. |
| Source-grounded answers with source URLs | **Met in tested cases** | The renderer validates passage text and backend-owned allowlisted URLs. Live cost and inclusion answers in `evaluation/assessment_8_live.md` each cite the correct package page. Passage fidelity does not guarantee relevance for every unseen phrasing. |
| Honest unknowns, wrong premises, and medical safety | **Met in tested cases** | Live cases 4–8 declined unsupported recovery, booking, weather, and personal safety claims or rejected a false $50 premise. Unknown/booking responses expose a verified quote route where appropriate. |
| Price comparison when both listed figures exist | **Met with caveat** | Case 2 compares the two exact ozone-therapy clinic listings on the approved comparison page. It names the numerically lower displayed figure and warns that the clinics' sessions and inclusions are not proven equivalent. Missing or ambiguous listings still cause an unknown response. |
| Prices with currency and context | **Met in tested cases** | Live case 1 returned USD $18,995 outpatient starting price and $30,000 inpatient price with three-week program context and a source URL. |
| Simple public chat UI | **Met** | Production frontend and FastAPI share the public URL without login. The UI supports questions, source cards, language selection, and a larger-text preference. Five local browser tests passed after the readability update. |
| Refresh when pages change | **Met with operational limit** | `scripts/ingest.py --refresh --export data/snapshot` refreshes the exact seven sources; committing the snapshot and redeploying makes it durable. `/api/admin/refresh` works only within an ephemeral Vercel instance, so it is not a durable production refresh by itself. |
| Public deployment | **Met** | The Vercel project `placidway-ai` serves the frontend and backend. Live `/api/health` returned `knowledge_ready: true`, `answer_mode: gemini`, and `gemini_configured: true`. |
| Remain available seven days after submission | **Pending time** | The cloud deployment began October 28. A point-in-time HTTP check cannot establish seven days of availability, and no submission timestamp has been recorded. Keep the deployment and free-tier quota active through that period. |

## Deliverables and optional features

- **Code, setup, architecture, and model choices:** public [GitHub repository](https://github.com/syedowaisalishah/placidway-ai-knowledge-assistant), `README.md`, and `docs/architecture.md`.
- **Required test answers:** `evaluation/assessment_8_live.md` contains actual production Gemini answers. `evaluation/assessment_8_tests.md` is the latest local source-reading run. The current local Gemini evaluation passed **30/30** on October 28; its actual answers are in `evaluation/full_test_results_gemini.md`, with machine-readable responses in `evaluation/actual_responses_gemini.json`.
- **Write-up:** `docs/assessment_writeup.md` now reflects the live deployment and known limits.
- **Optional features:** Spanish and Arabic framing, bounded follow-up context, relevant medical disclaimers, and privacy-preserving unanswered-topic logging exist. Lead capture was intentionally omitted; the chat does not collect patient contact details.
- **Submission:** the assessment asks for an email with the repository, live URL, test results, and write-up. That email has not been sent as part of this validation.

## Checks run for this audit

- PDF hyperlinks: **7/7** verified; PDF SHA-256 matches `docs/source-verification.json`.
- Backend: **88 passed** after adding comparison checks; Python lint and frontend TypeScript check passed.
- Production Gemini: **8/8 required cases passed after the comparison deployment** on October 28, including the cited ozone listing comparison and expected refusals. The live source-status endpoint reported 7 sources.
- Current risks: one live package-inclusions response took about **34 seconds**; the source snapshot can become stale until refreshed and redeployed; Vercel instance-local state and free-tier quotas do not provide a seven-day uptime guarantee. The Google project’s Free + Active status was user-confirmed, not independently audited for future billing changes.
