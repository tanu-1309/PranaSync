# Risk model, document uploads and registration

Client feedback this answers: the dataset is only for training; real patients upload documents one at a time; the model must give risk scores and risk factors from a single document; the back-end must build each person's data document by document; there must be an upload section. Also: say how strong the evidence is, show missing parameters on Home, show no probability in Outlook (not enough backing), and do not make accuracy the agenda.

## What was built

| Part | Where |
|---|---|
| Parameters, document groups, plausible limits (one place) | `src/prana/risk/params.py` |
| Training table from the 900 workbooks | `scripts/build_risk_table.py` -> `data/risk/training_table.csv` |
| Explainable model: train, predict, explain | `src/prana/risk/model.py`, `scripts/train_risk_model.py` -> `models/` |
| Reading values out of uploaded documents | `src/prana/risk/extract.py` |
| Merging documents into one picture | `src/prana/risk/service.py` |
| Register, upload, list, delete, risk routes | `src/prana/api/risk_routes.py` |
| Database tables | `accounts`, `documents`, `observations`, `risk_snapshots` in `src/prana/data/db.py` |
| Screens | `web/js/risk.js` (Home glance, Outlook, Upload), `web/js/register.js` |
| Tests | `tests/test_risk_documents.py` |

## The three risk areas

Heart and circulation, blood sugar (diabetes), blood pressure. Each shows a class (lower, moderate, higher, or "not enough information yet"), the parameters behind it, an evidence strength from 0 to 100, and the missing parameters.

**No probability is shown anywhere** (Home, Outlook, chat, Analytics page, or the text the AI models receive). The training data has no follow-up outcomes, so a percentage would claim more than it can support.

## How the model is explainable

- One small gradient-boosted model per area. Every parameter has a fixed direction (a higher LDL can only raise heart risk), so an explanation can never point the wrong way.
- Each answer lists the exact contribution of each parameter (TreeSHAP), compared with the typical person in the training data. "Pushes it up / down, small / moderate / large" are words for those contributions.
- **Evidence strength** = the share of the model's information that the person's documents supply. It is not a chance of being right. Below 25 the answer is "not enough information yet".
- It works from one document because the model was trained with whole documents hidden at random (profile, vitals, blood-sugar tests, cholesterol tests, activity tracker, habits).
- Class cut-offs are fixed at training time from the training scores.

## What the model learned from (be clear about this)

The answers it learned are the diagnoses and treatments *recorded in the training workbooks*, not future outcomes. So a class means "your measurements resemble those of people who already carry the recorded condition". Definitions:

| Area | Recorded as present when the workbook's history or medicines mention |
|---|---|
| Heart and circulation | high cholesterol, or a heart or stroke condition |
| Blood sugar | diabetes or prediabetes |
| Blood pressure | high blood pressure |

The data is synthetic practice data. Smoking and family history effects in it may not match real life. The model has not been checked by a clinician and must not be used to diagnose.

A development check (5-fold by patient) is printed by `scripts/train_risk_model.py` and saved in `models/risk_model.json` for the team. It is not shown to patients, because the agenda is the explanation and the evidence, not accuracy.

## Database: building a person's data document by document

```
accounts (patient_id PK, display_name, created_at)        one row per self-registered person; password hash is in `users`
documents (doc_id PK, patient_id FK, filename, sha256, size, kind, status, message, n_values, uploaded_at)
          unique (patient_id, sha256): the same file cannot be added twice
observations (id PK, patient_id, doc_id FK -> documents, param, value, unit, observed_on, source_text)
          one row per value read; source_text is the line it came from
risk_snapshots (id PK, patient_id, doc_id, result JSON, created_at)   the picture after each upload or delete
```

- A person's current picture = the newest value of each parameter in `observations`. Deleting a document deletes its values, and the picture is recomputed.
- People from the training workbooks start from their workbook values; later uploads replace matching values (same code path).
- Files are kept in `data/uploads/<id>/` under generated names (git-ignored). They are not encrypted at rest yet.

## What the reader can and cannot do

Reads text-based PDF, Word, text, CSV and Excel (including the project's 11-sheet workbook). It converts units (mmol/L to mg/dL, HbA1c mmol/mol to %), ignores impossible values with a note, and records the line each value came from. It refuses photos and scans: that needs OCR, which is not installed. Files are limited to 10 MB, PDFs to 40 pages; Office files are checked for decompression bombs; uploads are rate limited and guests cannot upload.

## Run it

```bash
python scripts/build_risk_table.py --raw <folder of the 900 .xlsx files>
python scripts/train_risk_model.py
python -m pytest tests/test_risk_documents.py
```

## Known limits and next steps

- Registration has no email, so a lost password cannot be recovered. Add identity provider / MFA before real use.
- No OCR for scans and photos; extraction is pattern based, so unusual layouts may be missed (the page shows what was read so the person can check).
- Trends, labs and medicines pages are not shown for upload-only accounts: one document has no time series.
- Clinician review of the parameters, directions, wording and thresholds is still needed.
