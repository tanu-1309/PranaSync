# Limitations (checkpoint)

## What v1 cannot do
* **Not a diagnosis, no risk score.** It reports co-occurring changes in a person's own data. Prana Chain asked us not to show a confidence score; uncertainty is shown as evidence (effect sizes, trend p-values, number of lab results, coverage) and a limitations list per insight.
* **Accuracy is measured on synthetic data** with planted patterns. Real labels do not exist; the real-data check is a plausibility check only.
* **Subtle changes may be missed.** The rules are strict on purpose (few false alarms); how small a change we can still find is measured in week 9.
* **Baseline = first 60 days.** If someone was already unwell at the start, the change is understated. A future version could use the most stable 60-day block.
* **Patterns must still be present in the last 60 days.** An episode that started and fully resolved mid-year is shown on the timeline but not surfaced.
* **Labs are sparse** (≈ 5 draws a year): lab changes use mean-of-first-two vs mean-of-last-two and are not used for timing.
* **PCOS has little data per year** (≈ 12 cycles) and overlaps with metabolic changes; it is the weakest scenario.
* **Context linking is keyword-based** (`config/scenarios.yaml`). Free-text notes with unusual wording can be missed; the keyword lists must be reviewed against all real history findings (`results/data_profile.csv`, column `history_findings`).
* **Medications that change signals** (e.g. starting a BP drug) are listed as context but are not yet modelled as "expected change".
* **Habits Weekly, Medication Adherence and Encounters & Notes** are loaded and shown but not yet used as pattern signals.
* **Thresholds** (`min_change`, effect size 0.8, 3 signals, 150 days) were set from clinical common sense and the synthetic data; they need review with Prana Chain / a clinician.

* **Reference values** (`config/reference_ranges.yaml`) are standard published numbers but have **not been clinically reviewed**; age, pregnancy and medication do not adjust them yet (only sex, for HDL), and home or wearable readings differ from clinic readings. The layer is covered by unit tests and a run over all 900 workbooks, not by the planted-pattern validation, because it makes no detection claim. See `docs/REFERENCE_VALUES.md`.
* **Accounts are a prototype scheme** (issued ID + random password, signed cookie, lockout, idle sign-out, sessions end on password reset). Production needs the platform's identity provider with MFA, TLS (`https_only=True`), and a self-service password reset.

## Next steps
See `docs/PLAN_AND_DISCUSSION.md`.
