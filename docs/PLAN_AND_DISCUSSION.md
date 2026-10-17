# Checkpoint discussion: pros, cons, proposed changes and the remaining plan

## Where we are
10 equal work packages (WP) cover the term. **WP 1–4 are done (≈ 40 %)** and are what this repository contains.

| WP | Content | Status |
|---|---|---|
| 1 | Kickoff, discovery, setup report | done |
| 2 | Loading & cleaning the 11-sheet workbooks, unified timeline, SQLite database | done |
| 3 | Personal baselines, trend + change-point tests, multi-signal patterns for 3 health areas | done |
| 4 | History linking, evidence pack, missing-data requests, template explanation, dashboard, validation on test data | done |
| 5 | Run and check on all 900 real workbooks | week 6 |
| 6 | Tune rules with Prana Chain feedback; PostgreSQL for the full cohort; REST API | week 7 |
| 7 | Adherence + habits as signals; medication-aware baseline; "add missing data and re-run" | week 8 |
| 8 | **AI suggestions** (LLM reword of the evidence pack via a HIPAA-eligible service, with output checks); patient vs clinician view; user testing | weeks 7–8 |
| 9 | 4th health area as configuration only (kidney); fairness by sex/age; sensitivity analysis | weeks 8–9 |
| 10 | Handoff docs, final validation, final pitch | weeks 9–10 |

## Pros of the current demo
* **End to end and explainable:** every flag shows which signals changed, when, by how much, and the exact readings.
* **Personal baseline, not population thresholds:** far fewer false alarms (0 % vs 80 % of stable test people).
* **Multi-signal rule:** a single high reading or one changed signal is not called a pattern, which is what Prana Chain asked for.
* **Connected to history:** links to findings, medications, family history and earlier labs, and says "not linked" when there is nothing.
* **Handles missing data the way the business asked:** analyses what exists, then lists what is missing and why.
* **Safe wording:** template explanations, fixed disclaimer, 0 of 303 texts with diagnosis or alarm wording.
* **Extensible:** the three areas are configuration in `config/scenarios.yaml`; a new area needs no new code.
* **Built on the real layout** (checked against PC0001.xlsx) and runs on a laptop with no cloud or API key.

## Cons / risks of the current demo
* **Accuracy measured only on our own planted patterns**: near-perfect numbers prove the wiring, not clinical accuracy. Not yet run on all 900 real files.
* **Rule sizes are our choice** (weight 2 kg, systolic BP 6 mmHg, steps 15 %, cycle 5 days, 3 signals, 150 days): need review by Prana Chain / a clinician.
* **Quiet by design:** subtle or short-lived changes will be missed; a change must still be present in the last 60 days.
* **Baseline = first 60 days:** if the person was already unwell then, the change is under-stated.
* **Labs are sparse** (≈ 5 a year) and PCOS has ≈ 12 cycles a year: these parts are the least certain.
* **History linking is keyword-based**; unusual wording in notes can be missed.
* **Not used yet:** Medication Adherence, Habits Weekly, clinical notes text (loaded and shown, not analysed).
* **Medications are context only:** starting a BP drug should change what we expect; not modelled yet.
* **Template wording is stiff;** no user testing yet.
* **Overlapping areas:** our one test error is a woman flagged for PCOS because weight, sleep and testosterone moved.

## Client question: past data only, or biological reference values too?
Answered in `docs/REFERENCE_VALUES.md`. In short: pattern detection uses only the person's own baseline (by design); a separate reference-value layer now reports where each recent level sits against published ranges and the lab's own range, and flags levels that are **steady but outside the usual range**, which a change-only method cannot see. Next step: clinician review of `config/reference_ranges.yaml`; open question whether reference values should ever influence detection (we recommend not).

## Planned: AI suggestions (next weeks)
Not built yet. An LLM may only reword the existing evidence pack (changes, reference position, history links, missing data) into suggestions such as questions to bring to a clinician or data worth adding. Numbers must come from the pack; automatic checks reject new numbers, condition names, diagnosis wording and medicine advice; the template text stays as the fallback; the clinician view marks AI-worded sentences.

## Changes we propose (for discussion with Prana Chain)
1. Review the "meaningful change" sizes and the 3-signal rule with the business contact; make them visible on the dashboard.
2. Add a "most stable 60 days" baseline option and re-baseline after a related medication starts.
3. Use adherence ("BP rose in months with adherence below 80 %") and habits as context.
4. Show an episode that started and ended mid-year as "past change" instead of hiding it.
5. LLM rewording of the evidence pack only, through a HIPAA-eligible route, with automatic checks (no new numbers, no diagnosis or alarm words).
6. Two views: plain-language patient view and evidence-first clinician view.

## Who does what next (each person keeps their module and pushes their own work)
| Week | Sneha (data) | Sindhu (analysis) | Uday (insight, lead) | Tanusree (dashboard, repo) |
|---|---|---|---|---|
| 6 | Real data: profile 900 files, fix column map | Real-data plausibility checks | Merge checkpoint PRs; keyword lists from real findings | CI green, tag `checkpoint-1` |
| 7 | PostgreSQL for full cohort | Tune rules with feedback | REST API; LLM wording + checks | Patient / clinician views; cohort page |
| 8 | Adherence + habits signals | Medication-aware baseline; 4th area | Adherence/habits in explanations; re-run loop | User testing; validation page |
| 9 | Data handoff doc | Fairness + sensitivity analysis | Architecture + API docs | Backup demo video |
| 10 | Pitch: data part | Pitch: results | Pitch lead | Final deck; tag `v2.0` |
