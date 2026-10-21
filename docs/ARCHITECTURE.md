# Architecture (checkpoint)

## Data flow for one patient

| Step | Module | What happens |
|---|---|---|
| 1. Load & clean | `prana.data.loader` | Reads the 11 sheets, renames columns via `config/column_map.yaml`, converts Excel serial dates (45901 = 2025-09-01), coerces numbers, removes impossible values (plausibility limits), merges duplicate days, converts glucose mmol/L → mg/dL, derives LH/FSH ratio, keeps the `Data Window` from the profile. Every fix is counted in `record.quality`. |
| 2. Timeline | `prana.data.timeline` | One long table `patient_id, date, source, signal, value, unit, text` with vitals, wearables, labs, cycles, history, medications, symptoms, notes. Stored in the `timeline` table. |
| 3. Signal check | `prana.analysis.baseline` | For each daily signal: baseline = first 60 days; recent = last 60 days. "Changed" only if the shift is (a) ≥ the clinical minimum in `min_change`, (b) ≥ 0.8 baseline SDs, (c) a significant Mann-Kendall trend on weekly means in the direction of concern. Onset = change point (ruptures Binseg) on weekly means. Labs: mean of first two vs last two results ≥ minimum delta + Theil-Sen slope sign. Cycles: last 3 vs first 3 cycle lengths ≥ 5 days. |
| 4. Pattern | `prana.analysis.patterns` | A scenario is surfaced if ≥ 3 of its signals changed, their onsets fit in 150 days (labs exempt — they are sparse), and at least one *core* signal is included (BP for hypertension, cycle length/testosterone for PCOS, HbA1c/glucose/weight/steps for diabetes). |
| 5. Context | `prana.insight.context_linker` | Keyword matches in Medical History and clinical notes, related medications, family history, symptoms, and labs above the scenario's flag value. Each item is tagged *before pattern* / *during pattern*; only prior items count as "linked to history". |
| 6. Missing data | `prana.insight.missing_data` | Per scenario `wanted_data`: lab absent or older than `max_age_days`, daily signal absent or < 70 % of days, < 5 cycles. |
| 7. Evidence pack | `prana.insight.evidence` | Status (pattern with/without context, known finding but stable, no pattern, not enough data, not applicable), evidence rows, context, missing data, limitations. |
| 8. Explanation | `prana.insight.explainer` | Template text built only from the evidence pack, plus a fixed disclaimer. *Planned (week 7): LLM rewording with output checks.* |
| 8b. Reference check | `prana.analysis.reference` | Separate from detection: for each measure, recent level (30-day mean or latest lab) vs `config/reference_ranges.yaml` and the lab's own printed range. Reports a neutral category and a relation to change detection (`within`, `steady_outside`, `changed_outside`, `changed_within`). Never alters steps 3–7. |
| 9. Re-run loop | *planned (week 8)* | User adds the requested data and the analysis runs again. |


## Why these choices
* **Personal baseline** — a resting HR of 80 is normal for one person and not another; we have 12 months per person.
* **Size + effect size + trend + persistence** — each rule removes one kind of false alarm: tiny drifts, noisy signals, random wiggles, and dips that recovered (holiday, short illness).
* **≥ 3 signals + core signal** — one high reading or one changed signal is exactly the "high/low alert" Prana Chain does not want. Validation shows this removes the false alarms a threshold alert produces (80 % → 0 % of stable people).
* **Code computes, words only describe** — patterns and numbers come from code; the planned LLM layer may only reword the evidence pack, and its output will be checked against it.
* **Config, not models** — `config/scenarios.yaml` holds signals, directions, minimum changes, core signals, context keywords and wanted data.

## Storage
SQLAlchemy; SQLite file `data/prana.db` by default, PostgreSQL with `DATABASE_URL`. Tables: `patients` (profile + quality JSON), `timeline`, `findings` (one row per patient × scenario with the full evidence JSON).

## Interfaces
Patient portal (`web/`, plain ES modules) served by FastAPI (`src/prana/api/`): `POST /api/login`, `POST /api/logout`, `GET /api/me` (the signed-in patient's record and analysis; the patient comes from the signed session cookie, never the URL), `GET /api/validation` (aggregate metrics only). Accounts: `scripts/create_users.py` (scrypt hashes, random 12-character passwords from `secrets`). Planned: re-analysis with user-added data, AI suggestions.

## Real dataset notes (from PC0001.xlsx)
11 sheets: Patient Profile (Field/Value incl. `Data Window`), Medical History, Medication History, Lab Results (Date/Test Name/Result/Unit/Reference Range; ~18 tests × 5 draws), Vitals Daily (365 rows), Wearable Daily (365 rows), Habits Weekly (52 rows), Symptoms Timeline, Encounters & Notes, Medication Adherence (monthly), Women Health (Cycle/Start Date/Cycle Length/Bleeding Days/Symptoms/Severity). History findings are short phrases such as "Borderline glycemic markers" with status "Monitoring".
