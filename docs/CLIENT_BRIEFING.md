# PranaSync: what has changed, in plain words

Prepared for PranaChain by Team 8 (University of Windsor, COMP 8967). PranaSync is a patient health-record portal. It shows a person what is changing in their own record and why it may matter. It never diagnoses and never advises on medicines.

## The short version

1. **It is simpler to read.** Pages are shorter, and each fact appears in one place only.
2. **An AI now writes the explanations.** Two AI models share the work, and each is labelled with its name. Our statistics still produce every number; the AI only explains them.
3. **There is a new "Analytics & Intelligence" page.** It shows the analysis, what the AI made of it, how confident the analysis is, and what led to each statement.
4. **Safety comes first.** Dangerous questions get a fixed reply written by us, and every number an AI writes is checked against the record.
5. **It is tested and honest about its limits.** About 300 automated tests pass. Nothing has been clinically validated yet.

## What you asked for, and what we did

| Your feedback | What changed |
|---|---|
| The interface was too long | Home is now a short summary. Details sit on their own pages (what changed, levels, outlook). We also removed repeated charts and tables. |
| Show a trend together with the factors behind it | Each result is shown with its numbers, the usual range, how it moved from the person's own baseline, and what is missing. |
| Answer risk questions with their reasons | Heart and diabetes estimates show their inputs, assumptions and limits. They are estimates for groups of people, never predictions for one person. |
| Use AI for the wording | All explanation text is now written by an AI model from the record's facts. |

## The two AI models, and why two

- **NVIDIA Nemotron** writes the plain-language summary and a short explanation under each graph. It only sees the numbers the graphs show.
- **Google MedGemma** is a medical model. It reads the patient's data and gives a few ranked insights. For each one it shows **what made it say so** (its steps and the numbers behind them), **how medical information helps** read the finding, and **how confident the analysis is**.

If one model fails, the other keeps working. Every result is labelled with the model that wrote it. Our MedGemma runs on our own computer, so patient data does not leave it.

## How "confidence" works

- **Evidence strength (0 to 100).** Our code calculates it from the statistics: how big the change is, how strong the trend test is, and how complete the data is. For a reading against its usual range, it uses how far outside the range it is and how many readings exist. It is a transparent rule of thumb, not a probability, and the inputs are shown.
- **The model's own confidence (low, moderate or high).** It can never be higher than the evidence supports. If it is lowered, the page says so.

## How we keep it safe

- Emergency, medicine and diagnosis questions get a fixed, careful reply and never reach a model.
- Every number an AI writes must be in the record, or the text is not shown.
- Diagnosis claims, medicine advice and false reassurance are rejected.
- Missing information is always listed and never treated as "normal".
- Only our code can set "seek urgent care", never the model.
- A patient only ever sees their own record.

## What we built to support it

- The data now sits in a PostgreSQL database: 900 patient records, about 5 million measurements. A record loads in a few milliseconds.
- A small library of approved medical documents the AI may cite. **It is empty today**, so no insight cites a source yet. We need your approved documents to fill it.
- About 300 automated tests, browser tests and a screenshot comparison. The older pages look the same as before.

## What is not done yet

- **Clinical validation.** A clinician has not reviewed the wording, the reference ranges or the safety rules.
- **Data origin.** The project does not record whether the 900 workbooks are real, synthetic or de-identified.
- **Privacy and regulation.** Consent, provider agreements, Ontario's PHIPA and Health Canada's software-as-a-medical-device question have not been assessed.
- **Speed.** On our computer (no GPU) the medical model takes minutes per patient, so we write results ahead of time. A GPU or a hosted service would fix this.
- **Small-model limits.** The medical model we run locally is small. It sometimes names evidence that is not in the record, and then we drop that insight.
- **Not tested with real patients or users.**

## What we need from PranaChain

1. **The origin and permission of the data**, and whether it may be sent to an outside AI service.
2. **A clinician** to review the AI wording, the reference ranges and the safety rules.
3. **Approved medical documents** (and their licences) for the knowledge base.
4. **A decision on consent, a provider agreement and a regulatory assessment** before any real patient use.
5. **A decision on hosting**, if you want faster results: a GPU or a paid hosted model (we have not provisioned any).

## Next steps (WP 8)

User testing with patients and clinicians, clinician review, the items moved from the original plan (adherence and habits as signals, a medication-aware baseline, "add missing data and re-run"), and the consent and provider-agreement work.
