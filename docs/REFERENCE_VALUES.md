# Client question: do we rely only on the person's past data, or also on biological reference values?

## Short answer
**Both, for two different jobs, and we keep them apart.**

| Question | What it uses | Where it lives |
|---|---|---|
| *Has this changed for this person?* (finding patterns) | **Only the person's own past data**: first 60 days = personal baseline | `src/prana/analysis/baseline.py`, `patterns.py` |
| *Is this level within a usual range?* | **General reference values**: published guidelines plus the range printed on the person's own lab report | `config/reference_ranges.yaml`, `src/prana/analysis/reference.py` |

Until this checkpoint the second question was only answered in small ways (see "What we found in the code"). It is now a first-class, visible layer.

## What we found in the code (audit)
1. **Pattern detection is purely personal-baseline.** A signal counts as changed only if it moved away from the person's own first 60 days by a clinically meaningful amount, a multiple of their own noise, with a real trend, and still present in the last 60 days. No population value is involved. This is deliberate: a resting heart rate of 80 is normal for one person and not for another, and it is why a threshold alert false-alarms on 80% of stable test people while ours flags 0%.
2. **Reference values were used in only three narrow places**:
   * the lab's own printed range was *shown* next to lab results;
   * a few thresholds in `config/scenarios.yaml` (`lab_flags`: HbA1c ≥ 5.7, fasting glucose ≥ 100, LDL ≥ 160, total cholesterol ≥ 240, testosterone ≥ 50, LH/FSH ≥ 2) decided which history items count as "linked context";
   * plausibility limits in `config/column_map.yaml` removed impossible values during cleaning.
3. **The real gap.** A level that was already outside the usual range on day one and never moved is invisible to a change-only method. Example from the real data (PC0001): systolic blood pressure sits flat at about 132 mmHg all year. Nothing "changed", so nothing was raised, yet the level is above the usual range. Another (PC0502): BMI 27.5 and a TSH above the lab's own range are not part of any pattern, so they were never mentioned.
4. **A second limitation that reference values help with.** The baseline is the first 60 days. If the person was already unwell then, the change is under-stated. Showing where the level sits against a general range gives the reader a second, independent anchor.

## What we built
`assess_reference()` runs after the existing analysis and adds `reference` to every result. It does **not** change detection, scores or the validated numbers.

For each measure it reports: the recent level (mean of the last 30 days, or the latest lab result), the usual reference and its source, where the level sits (*typical / slightly above / above / well above*), and how that relates to change detection:

| Relation | Meaning |
|---|---|
| `within` | In the usual range |
| `steady_outside` | **Outside the usual range but not changed for the person** (what a change-only view misses) |
| `changed_outside` | Changed for the person and outside the usual range |
| `changed_within` | Changed for the person but still inside the usual range |

* **Daily signals**: blood pressure (ACC/AHA categories, higher of the two readings decides), resting heart rate (AHA), blood oxygen, sleep (AASM/SRS), BMI (WHO), steps and active minutes (soft general guides, never rated "outside"), and cycle length (ACOG, 21–35 days).
* **Labs**: the range printed on the person's own lab report is the primary reference (it is lab- and method-specific). Guideline bands are added for HbA1c and fasting glucose (ADA), LDL, total cholesterol and triglycerides (NCEP ATP III), and HDL (sex-specific). Guideline numbers are applied only if the lab's unit matches.
* **Deliberately personal-only**: heart-rate variability, weight, stress score, sedentary time and calories have no population range worth comparing a person with, so they are judged against the person only.

### In the interface
* **Overview, section 02 "Where your levels sit"**: two questions side by side, a one-line summary, a callout for measures that are *steady but outside the usual range*, and a table (sources shown in the clinician view). Measures within range are tucked behind a disclosure to keep the page calm.
* **Timeline, "Show usual range"**: draws the reference range behind each chart.
* **How it works, section 04**: the same explanation in plain language.

### Safety wording
Categories are *typical / above typical / well above typical*, never condition names. A test asserts no category contains "diabetes", "hypertension" or "diagnos". Every table carries: reference ranges are general guides that differ with age, sex, pregnancy, medicines and conditions; they say where a number sits and do not diagnose.

## Limits and open questions for PranaChain's clinician
* The numbers are standard published ones, but **a clinician must review `config/reference_ranges.yaml`** before any real use (for example whether "slightly above typical" blood pressure should be shown at all, and age-specific sleep and heart-rate ranges).
* Age, pregnancy and medication do not yet adjust the ranges (only sex, for HDL).
* Wearable and home readings differ from clinic readings; the notes say so.
* The reference layer is **not covered by the planted-pattern validation**, because it makes no detection claim. It is covered by unit tests of the bands and relations, and by a run over all 900 real workbooks that checks nothing crashes and every item carries a source.
* Option for discussion: let reference values *also* influence detection (for example only raise a pattern when at least one signal is outside its range). We did not, because it would trade away the personal-baseline advantage and invalidate the current results.

## Planned next: AI suggestions (coming weeks)
Not built yet, by design. The plan:
* An LLM, through a HIPAA-eligible route, may only **reword the existing evidence pack** (changes, reference position, history links, missing data) into suggestions such as questions to ask a clinician or data worth adding.
* **Code computes, words only describe**: every number in a suggestion must come from the evidence pack; automatic checks reject output that adds numbers, names a condition, gives a diagnosis, or advises changing medicine.
* The fixed disclaimer stays, the template text remains as the fallback, and the clinician view shows which sentences were AI-worded.
* The reference layer makes this safer: suggestions can cite "above the usual range" with its source rather than inventing thresholds.
