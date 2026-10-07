# How we validate (and how to read the numbers)

The real Prana Chain workbooks have **no labels** — nobody tells us which patient "really" has a pattern. So accuracy is
measured on generated workbooks that use the **exact real sheet layout** but where we planted the pattern ourselves
(`prana.data.generate_synthetic`, file `ground_truth.json`). The real data is then used for a plausibility check (below).

## Test population (120 patients, `--seed 8`)

| Group | n | What was planted | Correct answer |
|---|---|---|---|
| t2d | 18 | steps ↓, active min ↓, sedentary ↑, weight ↑, sleep ↓, HbA1c & glucose ↑ + "Borderline glycemic markers" in history | diabetes pattern, linked |
| htn | 18 | SBP ↑, DBP ↑, resting HR ↑, HRV ↓, sleep ↓, LDL ↑ + "Elevated blood pressure readings" | hypertension pattern, linked |
| pcos | 14 | cycle length 29 → ~41 days, weight ↑, sleep ↓, testosterone ↑ + "Irregular menstrual cycles" | PCOS pattern, linked |
| drift_no_context | 10 | diabetes- or hypertension-like drift, nothing in history | pattern, **not** linked |
| control | 24 | stable year | nothing |
| noisy_control | 14 | 1.6× noise + a 2-week dip that recovers | nothing |
| context_only | 12 | finding in history, signals stable | nothing (status "known finding, stable") |
| single_signal | 10 | only systolic BP rises 14–20 mmHg | nothing (one signal ≠ pattern) |

Every workbook also contains data-quality problems (duplicate days, ~3 % blank cells, weight 0, SBP 400, one glucose in mmol/L),
and some pattern patients have data removed (42 % of wearable days, recent HbA1c, hormone labs).

## What we measure (`scripts/validate.py`)
1. precision / recall / specificity per scenario, against a **threshold-alert baseline** (any HbA1c ≥ 5.7 or glucose ≥ 100; ≥ 5 days with BP ≥ 140/90; any cycle > 35 days)
2. false alarms on people with no planted pattern
3. detected start vs planted start
4. linked-to-history correctness
5. missing-data requests
6. robustness when the whole wearable sheet is removed
7. guardrails on every explanation

Planned (week 9): recall and false-positive rate by sex and age band, and a sensitivity analysis that repeats everything with smaller planted changes (how small a change we can still find).

## Reading the results honestly
* **Near-perfect scores at effect 1.0 are expected** — we planted clear patterns. They prove the pipeline is wired correctly end to end, not that it is clinically accurate.
* **The open question is subtle change:** all planted changes here are clear. How small a change the method can still find is the week-9 sensitivity analysis; our design choice is to stay quiet unless several signals agree.
* **The threshold alert catches almost everything but also flags 80 % of stable people** — this is the comparison that shows why multi-signal + personal baseline matters.
* **Detected start lags the planted start by ~1 month** (median +32 days) — the change point sits where the shift becomes visible in weekly means, not where it begins.
* The one false positive (a woman in the diabetes group flagged for PCOS because weight, sleep and testosterone moved) shows that scenarios overlap biologically; we report it rather than tune it away.

## Plausibility check on the real data (run this on the 900 workbooks)
```bash
python scripts/run_pipeline.py --data data/raw
```
Then check in `results/summary.csv`: (a) diabetes patterns should be more common among patients whose history contains
"Borderline glycemic markers" than among others; (b) PCOS should be "not applicable" for every male; (c) the share of patients with
any surfaced pattern should be well below the threshold-alert share; (d) open 5 surfaced and 5 non-surfaced patients in the dashboard
and confirm by eye that the evidence matches the charts. Record these numbers in the final report.
