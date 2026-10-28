# Coverage and limitations

## Source coverage

The chatbot answers from the seven URLs in [config/approved_sources.yaml](../config/approved_sources.yaml): one ITC clinic profile, three cancer treatment packages, clinic videos, an ITC price list, and an alternative medicine price comparison page. Other PlacidWay pages and the broader notes in `docs/placidway-data.md` are outside the index.

A factual answer needs a relevant passage or exact price row and a source URL. The backend classifies the question, retrieves matching content, checks evidence for the requested treatment, place, and program, and verifies the final passage and citation. If any step cannot establish support, it returns a limited or unknown response.

## Common reasons for an unknown answer

| Question or situation | Behavior | Why |
| --- | --- | --- |
| Information exists elsewhere on PlacidWay | Says it cannot verify it | The page is outside the configured source list. |
| Treatment, clinic, or destination is not named in the evidence | Declines or asks for clarification | A similar package or location is not the same one. |
| A program length is shown but recovery time is not | Declines a recovery estimate | Duration of care does not establish recovery time. |
| Two price listings are not directly comparable | Reports the displayed figures with a caveat or declines | Sessions and inclusions may differ between clinics. |
| A personal diagnosis or safety judgment is requested | Refers the visitor to a clinician | Public page content cannot determine individual suitability. |
| A supported fact is phrased in an unexpected way | May decline | Local topic matching and evidence checks favor precision over guessing. |
| Gemini has a quota, credential, or provider error | Reports temporary unavailability | The app does not present an unverified fallback as an AI answer. |

The assistant cannot reliably answer every possible question from these pages. Medical claims are attributed to the website and are not independently verified clinical findings.

## Improving coverage

Review real unanswered phrasings, identify whether classification, retrieval, or verification rejected the answer, and add a regression case before changing that stage. New source pages require an intentional update to the allowlist, crawl checks, indexing, and citation tests. Broader background notes alone are not a substitute for verified page content.
