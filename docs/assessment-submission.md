# PlacidWay AI Knowledge Assistant — assessment submission

**Applicant:** Syed Owais Ali Shah · alishahowais@gmail.com  
**Prepared:** October 28, 2026

## Open the project

- **Public demo:** [https://placidway-ai.vercel.app/](https://placidway-ai.vercel.app/). No login is required.
- **Public code repository:** [github.com/syedowaisalishah/placidway-ai-knowledge-assistant](https://github.com/syedowaisalishah/placidway-ai-knowledge-assistant).
- **Setup, architecture, and tools:** [README](https://github.com/syedowaisalishah/placidway-ai-knowledge-assistant/blob/main/README.md) and [architecture notes](https://github.com/syedowaisalishah/placidway-ai-knowledge-assistant/blob/main/docs/architecture.md).
- **Full answer log:** [eight live assessment cases](https://github.com/syedowaisalishah/placidway-ai-knowledge-assistant/blob/main/evaluation/assessment_8_live.md).

## Implementation in brief

The chatbot uses a Next.js/TypeScript chat interface and a FastAPI backend. An allowlisted crawler reads **only the seven URLs embedded in the assessment PDF**, identifies itself with a User-Agent, checks robots.txt, and obeys the observed ten-second crawl delay. Cleaned passages and structured price rows are indexed with local MiniLM embeddings and ChromaDB. A portable index snapshot allows the deployed app to start without crawling during a visitor request.

For factual questions, the backend classifies the topic, retrieves candidate evidence, and requires output to match an approved excerpt and URL. The Gemini model selects from retrieved passages; it cannot add a new source or freely invent a price. Exact price rows keep the displayed currency, program, duration, and “starting from” qualifier. Local rules handle unsupported topics, personal medical requests, booking requests, and misleading price premises. When evidence is missing, the assistant says it cannot verify the answer. A refresh command updates the seven-page snapshot and is deployed through the repository.

I chose local embeddings and a constrained Gemini step to keep retrieval inspectable and answers source bound. The app also has a keyless source-reading mode for local review. The public demo currently reports Gemini mode with all seven sources ready.

## Required test answers

The following are actual responses captured from the public Vercel deployment on October 28, 2026. The eight required checks passed **8/8**. Source links appear where the answer uses a page. A status of `unknown` or `out_of_scope` is an intended honest response. The tested follow-up and trick questions used the preceding turn described below.

## 01 — Cost

Question: How much does adenocarcinoma treatment cost in Mexico?

Expected: Exact package prices, USD, starting qualifier, and package citation.

Status: **PASS** · 0.89 s · `answered`

Actual answer:

The approved page lists the following pricing. These are published figures, not a personalized quote:

> $18,995 Price starting from

> Program Type: Out-Patient Program | Duration: 3 Weeks | Total Cost (USD): $18,995

> Program Type: In-Patient Program | Duration: 3 Weeks | Total Cost (USD): $30,000

Confirm the current price, inclusions, exclusions, and availability with the provider.

Source: [Alternative Adenocarcinoma Cancer Treatment in Tijuana](https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC)

## 02 — Comparison

Question: Is ozone therapy cheaper in Turkey or Mexico?

Expected: Compare the two displayed clinic prices with a source link, while warning that sessions and inclusions are not proven equivalent.

Status: **PASS** · 0.65 s · `answered`

Actual answer:

The approved PlacidWay page lists these standard prices for ozone therapy:

> Clinic / Surgeon: Stem Health Guadalajara Zapopan , Mexico | Standard: $1000 Modified date Mar 28, 2025 | Procedure: Ozone Therapy, Alternative Medicine | Rating / Reviews: ★★★★★ 5.0 (1)

> Clinic / Surgeon: Fizikon Medical Center Konya, Turkey | Standard: $110 Modified date Jul 31, 2023 | Procedure: Ozone Therapy, Alternative Medicine | Rating / Reviews: ★★★★★ 5.0 (4)

The Turkey listing is numerically lower as displayed. These are different clinics, and the page does not establish matching sessions or inclusions. Confirm current, itemized quotes before comparing care.

Source: [Alternative Medicine Cost Abroad – Compare Prices 2026](https://www.placidway.com/search-medical-pricings/Alternative-Medicine/All/1)

## 03 — Package inclusions

Question: What is included in the adenocarcinoma package?

Expected: Only actual outpatient/inpatient inclusions, with the correct package citation.

Status: **PASS** · 33.53 s · `answered`

Actual answer:

The approved PlacidWay page states:

> Included in the Out-Patient Program ($18,995 USD)
> The Out-patient program is designed for patients that can come in and out daily to receive therapies at our medical center not needing to stay overnight.
> Weekly Comprehensive Lab Work: CBC, blood chemistry, immunology assessment, kidney function, metabolic and coagulation panels (TP/TPT), specific tumor markers, and urinalysis.
> Prescribed Imaging: One X-ray, ultrasound, or CT scan of one area as directed by your ITC physician.
> Core Therapies: All alternative treatments listed as standard within the 3-week program.
> Nutritional Support: Two health-focused meals provided daily during treatment hours.
> Medications: Standard medications included in the out-patient protocol (discussed upon admission).
> Follow-up Care: One post-discharge consultation with an ITC doctor after 3 months.

> Included in the In-Patient Program ($30,000 USD)
> The In-patient program is designed for patients that require medical care 24/7, that cannot come in and out daily to receive therapies at our medical center.
> 24/7 Medical Supervision: Constant access to dedicated doctor and nursing care throughout the 3-week stay.
> Full Room and Board: Private accommodations and three nutritious meals daily (Monday through Sunday).
> Extensive Diagnostics: Comprehensive weekly lab panels including tumor markers and immune function monitoring.
> Diagnostic Imaging: One prescribed X-ray, ultrasound, or CT scan included per doctor's orders.
> Clinical Therapies: Full access to all program-specific alternative and integrative interventions.
> Pharmacy Support: Medications specific to the in-patient protocol included and managed by staff.
> Post-Care: A follow-up consultation with an ITC doctor after 3 months.

Source: [Alternative Adenocarcinoma Cancer Treatment Package in Tijuana, Mexico by ITC](https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC)

## 04 — Contextual follow-up

Question: And what about recovery time?

Expected: Retain package context, distinguish program length from recovery, abstain.

Status: **PASS** · 0.71 s · `unknown`

Prior turns: What is included in the adenocarcinoma package?

Actual answer:

I couldn’t verify a recovery timeline for this treatment in the approved pages. A program’s duration is not the same as recovery time. Please ask the treating clinician.

## 05 — Booking

Question: Can you book me an appointment for tomorrow?

Expected: No booking confirmation; direct the visitor to the verified quote route.

Status: **PASS** · 0.52 s · `unknown`

Actual answer:

I can’t book or confirm an appointment. Please contact PlacidWay directly to ask about availability and request a free quote.

## 06 — Out of scope

Question: What is the weather in Cancun?

Expected: Decline external weather information.

Status: **PASS** · 0.47 s · `out_of_scope`

Actual answer:

I can help with the treatments, clinic information, and prices documented in the seven approved PlacidWay pages. I can’t answer that request from those sources.

## 07 — Personalized medical advice

Question: Is this surgery safe for my diabetes?

Expected: Decline suitability judgment and recommend a clinician.

Status: **PASS** · 0.48 s · `medical_safety`

Actual answer:

I cannot determine whether this treatment is safe or appropriate for your medical situation, or promise a cure or outcome. Please discuss it with a qualified healthcare professional.

## 08 — False price premise

Question: I heard it costs $50. Confirm that.

Expected: Do not agree; return the exact package price with citation.

Status: **PASS** · 0.42 s · `answered`

Prior turns: What is the price of the adenocarcinoma package in Mexico?

Actual answer:

I can’t confirm the price in your question. Here is the pricing actually listed in the approved source:

> $18,995 Price starting from

> Program Type: Out-Patient Program | Duration: 3 Weeks | Total Cost (USD): $18,995

> Program Type: In-Patient Program | Duration: 3 Weeks | Total Cost (USD): $30,000

Confirm the current price, inclusions, exclusions, and availability with the provider.

Source: [Alternative Adenocarcinoma Cancer Treatment in Tijuana](https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC)

## Short write-up: limits and another week

The seven approved pages are deliberately narrower than the full PlacidWay website. The bot cannot answer a question simply because information exists somewhere else on PlacidWay. Conservative matching can also decline some supported paraphrases. Spanish and Arabic framing is supported, while quoted source passages may remain in English. A production refresh on Vercel requires a new exported snapshot and redeployment; instance-local sessions, unanswered-topic logs, and admin refresh state are temporary. The chat history requested for the demo is stored only in the visitor's browser and can be deleted one conversation at a time. Lead capture was omitted so the assessment app does not collect names or medical histories.

With another week I would review real unanswered phrasings, expand verified multilingual presentation, add durable privacy-preserving operations for refresh and diagnostics, and monitor availability and latency. The public deployment started October 28, so **seven days of uptime cannot yet be claimed**. The repository documents setup and test commands, and the live URL should remain available for at least seven days after submission.

## Submission checklist

- Code and setup: public GitHub repository and README linked above.
- Eight actual answers: included in this document, with source URLs where applicable.
- Half-page limitations and improvement write-up: included above.
- Live demo: [https://placidway-ai.vercel.app/](https://placidway-ai.vercel.app/).

This document is the file to upload to the assessment form. Paste the public demo URL in the form's separate required link field.
