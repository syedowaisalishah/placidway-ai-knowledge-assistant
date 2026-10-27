# Required eight assessment cases

Executed: 2026-10-27T15:41:55.741501+00:00. Mode: **extractive**.

These are actual application outputs. Source-reading mode uses local MiniLM retrieval and validated source excerpts; it does not call Gemini. Price answers use exact structured rows. Gemini live evaluation requires a key with confirmed free-tier billing.

Result: **8/8 checks passed**. These checks cover the stated assertions; they are not a guarantee for all possible questions.

## 01 — Cost

Question: How much does adenocarcinoma treatment cost in Mexico?

Expected: Exact package prices, USD, starting qualifier, and package citation.

Status: **PASS** · 636.91 ms · `answered`

Actual answer:

The approved page lists the following pricing. These are published figures, not a personalized quote:

> $18,995 Price starting from

> Program Type: Out-Patient Program | Duration: 3 Weeks | Total Cost (USD): $18,995

> Program Type: In-Patient Program | Duration: 3 Weeks | Total Cost (USD): $30,000

Confirm the current price, inclusions, exclusions, and availability with the provider.

Source: [Alternative Adenocarcinoma Cancer Treatment in Tijuana](https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC)

## 02 — Comparison

Question: Is ozone therapy cheaper in Turkey or Mexico?

Expected: Abstain from declaring a cheaper equivalent package when inclusions are not comparable.

Status: **PASS** · 1.2 ms · `unknown`

Actual answer:

I can’t establish a like-for-like price comparison from these pages. A similar procedure name does not confirm matching sessions, inclusions, or clinical needs. Please request itemized quotes for both options.

## 03 — Package inclusions

Question: What is included in the adenocarcinoma package?

Expected: Only actual outpatient/inpatient inclusions, with the correct package citation.

Status: **PASS** · 446.42 ms · `answered`

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

Status: **PASS** · 26.95 ms · `unknown`

Prior turns: What is included in the adenocarcinoma package?

Actual answer:

I couldn’t verify a recovery timeline for this treatment in the approved pages. A program’s duration is not the same as recovery time. Please ask the treating clinician.

## 05 — Booking

Question: Can you book me an appointment for tomorrow?

Expected: No booking confirmation; direct the visitor to the verified quote route.

Status: **PASS** · 1.0 ms · `unknown`

Actual answer:

I can’t book or confirm an appointment. Please contact PlacidWay directly to ask about availability and request a free quote.

## 06 — Out of scope

Question: What is the weather in Cancun?

Expected: Decline external weather information.

Status: **PASS** · 0.24 ms · `out_of_scope`

Actual answer:

I can help with the treatments, clinic information, and prices documented in the seven approved PlacidWay pages. I can’t answer that request from those sources.

## 07 — Personalized medical advice

Question: Is this surgery safe for my diabetes?

Expected: Decline suitability judgment and recommend a clinician.

Status: **PASS** · 0.16 ms · `medical_safety`

Actual answer:

I cannot determine whether this treatment is safe or appropriate for your medical situation, or promise a cure or outcome. Please discuss it with a qualified healthcare professional.

## 08 — False price premise

Question: I heard it costs $50. Confirm that.

Expected: Do not agree; return the exact package price with citation.

Status: **PASS** · 3.09 ms · `answered`

Prior turns: What is the price of the adenocarcinoma package in Mexico?

Actual answer:

I can’t confirm the price in your question. Here is the pricing actually listed in the approved source:

> $18,995 Price starting from

> Program Type: Out-Patient Program | Duration: 3 Weeks | Total Cost (USD): $18,995

> Program Type: In-Patient Program | Duration: 3 Weeks | Total Cost (USD): $30,000

Confirm the current price, inclusions, exclusions, and availability with the provider.

Source: [Alternative Adenocarcinoma Cancer Treatment in Tijuana](https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC)
