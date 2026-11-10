"""Test the forecasts on data they have not seen, and report honestly how good they are.

    python scripts/backtest_forecast.py                 # random patients that were never used to choose the settings
    python scripts/backtest_forecast.py --n 500 --seed 3

Daily signals: cut each series 28 days before its end, forecast the weekly average 4 weeks ahead, compare with what really
happened. Every forecast is compared with the baseline any forecast must beat to be worth showing: "nothing changes"
(carry today's level forward). Only forecasts that pass the same reliability gate the app uses are scored. Errors are
divided by the signal's own spread so steps and blood pressure can be averaged fairly.

Labs: the last result is left out and forecast from the earlier ones. This only documents why labs are NOT projected.

The settings (gate p < 0.001, damping 0.75, interval x1.25, size rule 0.5) were chosen while looking at two other samples of patients.
Those patients are excluded here, so these numbers are a fair test. Writes results/forecast_backtest.json, which the portal quotes.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from prana.ai.forecast import DAILY_KEYS, DAMP, GATE_P, INTERVAL_K, SIZE_SHARE, fit_xy, forecast_daily, predict  # noqa: E402
from prana.config import RAW_DIR, RESULTS_DIR, SYNTHETIC_DIR  # noqa: E402
from prana.data.loader import list_workbooks, load_workbook  # noqa: E402
from prana.data.timeline import daily_series  # noqa: E402

HOLD = 28
LAB_KEYS = ["hba1c", "fasting_glucose", "ldl_cholesterol", "total_cholesterol", "triglycerides", "hdl_cholesterol", "tsh", "vitamin_d", "egfr", "testosterone"]


def summarise(rows: list[dict]) -> dict:
    if not rows:
        return {"n": 0}
    err = np.array([r["err"] for r in rows])
    naive = np.array([r["naive"] for r in rows])
    return {"n": len(rows), "error_vs_nothing_changes": round(float(err.mean() / naive.mean()), 3),
            "better_than_nothing_changes": round(float((err < naive).mean()), 3), "inside_95_range": round(float(np.mean([r["inside"] for r in rows])), 3)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--seed", type=int, default=21)
    a = ap.parse_args()
    files = list_workbooks(RAW_DIR) or list_workbooks(SYNTHETIC_DIR)
    # patients that influenced the settings are never scored: the first sample (seed 7), then a second drawn from the rest (seed 11)
    used_to_choose = set(random.Random(7).sample(files, min(200, len(files))))
    used_to_choose |= set(random.Random(11).sample([f for f in files if f not in used_to_choose], 300))
    pool = [f for f in files if f not in used_to_choose]
    sample = random.Random(a.seed).sample(pool, min(a.n, len(pool)))

    daily, tried, shown, labs = [], 0, 0, []
    lab_tried = 0
    for i, path in enumerate(sample, 1):
        rec = load_workbook(path)
        for key in DAILY_KEYS:
            s = daily_series(rec, key)
            if len(s) < 120 or s.notna().mean() <= 0.5:
                continue
            train, test = s.iloc[:-HOLD], s.iloc[-HOLD:]
            truth = test.iloc[-7:].mean()
            f = forecast_daily(train, key, horizons=(HOLD,))
            if f is None or pd.isna(truth) or "scale" not in f:
                continue
            tried += 1
            if not f["reliable"]:
                continue
            shown += 1
            p = f["projection"][0]
            sc = f["scale"] or 1.0
            daily.append({"err": abs(p["value"] - truth) / sc, "naive": abs(f["now"] - truth) / sc, "inside": p["low"] <= truth <= p["high"]})
        L = rec.get("labs")
        if not L.empty:
            for key in LAB_KEYS:
                d = L[L.test_key == key].dropna(subset=["value"]).sort_values("date")
                if len(d) < 5:
                    continue
                pts = list(zip(pd.to_datetime(d["date"]), d["value"]))
                train, (td, tv) = pts[:-1], pts[-1]
                d0 = train[0][0]
                fit = fit_xy([(x - d0).days for x, _ in train], [v for _, v in train])
                if fit is None:
                    continue
                lab_tried += 1
                if fit["p"] >= 0.05:  # the most generous gate that gave any benefit
                    continue
                v, lo, hi = predict(fit, (td - d0).days)
                sc = float(np.std([x for _, x in train])) or 1.0
                labs.append({"err": abs(v - tv) / sc, "naive": abs(train[-1][1] - tv) / sc, "inside": lo <= tv <= hi})
        if i % 50 == 0:
            print(f"  {i}/{len(sample)}", flush=True)

    out = {"patients": len(sample), "settings": {"gate_p": GATE_P, "damping": DAMP, "interval_widening": INTERVAL_K, "size_share": SIZE_SHARE},
           "daily": {**summarise(daily), "series_tested": tried, "projections_shown": shown},
           "labs_not_projected": {**summarise(labs), "series_tested": lab_tried,
                                  "reason": "Even with a generous gate, the true value fell inside the 95% range far too rarely, because labs have only 4 to 6 results a year."},
           "note": "Scored only on forecasts that passed the reliability gate, on patients not used to choose the settings. error_vs_nothing_changes below 1 means better than assuming no change. Test workbooks, not clinical validation."}
    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "forecast_backtest.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
