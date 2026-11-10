"""Short-range projections of a patient's own daily measurements (owner: Sindhu).

If a signal has a strong, lasting trend, project where it is heading over the next 30 and 90 days, with an
uncertainty range, and say whether that path would cross a reference boundary. It never predicts a condition, a
diagnosis or a risk score: only "if this trend continues, this measurement will be about X, probably between A and B".

Method (kept simple so it can be explained and checked)
  fit      weekly means of the last 16 weeks -> straight-line fit
  centre   today's level + 0.75 x the fitted weekly slope x weeks ahead  (a damped trend: trends rarely continue at full pace)
  range    the fit's 95% prediction interval, widened by 25% so it holds up on unseen data
  gate     shown only if the trend is very strong (Mann-Kendall p < 0.001) AND the 90-day change is at least half the
           minimum meaningful change the pattern detector uses (for example 1 kg for weight). Otherwise: "no lasting trend", no projection.

Why these settings: with a looser gate a straight-line projection was WORSE than assuming nothing changes. The strict gate
and damping were chosen on one set of patients and the size rule on a second; the numbers quoted by the portal come from a third set
that none of those choices saw (scripts/backtest_forecast.py).
In this project's data nearly all strong, lasting trends are in weight, so that is what will mostly be projected.

Labs are not projected: with 4 to 6 results a year the ranges were not reliable (the true value fell inside the 95% range
in only 56 to 78% of cases), so showing a number would claim precision we do not have.
"""
from __future__ import annotations

import json
import math
from datetime import timedelta
from functools import lru_cache

import numpy as np
import pandas as pd
from scipy import stats

from prana.analysis.baseline import mann_kendall, parse_min_change
from prana.analysis.reference import reference_config
from prana.config import RESULTS_DIR, column_map, scenarios_config
from prana.data.timeline import daily_series
from prana.insight.evidence import LABELS

WEEKS_FIT = 16
MIN_WEEKS = 10
GATE_P = 0.001       # trend must be very strong
DAMP = 0.75          # share of the fitted slope assumed to continue
INTERVAL_K = 1.25    # widening of the prediction interval, calibrated on unseen patients
SIZE_SHARE = 0.5     # the 90-day change must be at least this share of the detector's minimum meaningful change
DAILY_KEYS = ["sbp", "dbp", "resting_hr", "weight_kg", "steps", "sleep_hours", "active_minutes", "spo2", "hrv_ms"]
UNITS = {"sbp": "mmHg", "dbp": "mmHg", "resting_hr": "bpm", "weight_kg": "kg", "steps": "steps", "sleep_hours": "h",
         "active_minutes": "min", "spo2": "%", "hrv_ms": "ms"}
NAMES = {"spo2": "Blood oxygen (%)"}
# blood pressure has no band table in the reference file; these are the category edges used by reference.bp_category
BP_EDGES = {"sbp": [(120, "Typical", "Slightly above typical"), (130, "Slightly above typical", "Above typical"), (140, "Above typical", "Well above typical")],
            "dbp": [(80, "Typical", "Above typical"), (90, "Above typical", "Well above typical")]}


# ----------------------------------------------------------------------------- the maths
def fit_xy(x, y) -> dict | None:
    """Ordinary least squares y = a + b x with what is needed for a prediction interval. None if too few points."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    keep = ~(np.isnan(x) | np.isnan(y))
    x, y = x[keep], y[keep]
    n = len(y)
    if n < 4 or np.ptp(x) == 0:
        return None
    xbar, sxx = x.mean(), float(((x - x.mean()) ** 2).sum())
    b = float(((x - xbar) * (y - y.mean())).sum() / sxx)
    a = float(y.mean() - b * xbar)
    se = math.sqrt(float(((y - (a + b * x)) ** 2).sum()) / (n - 2))
    return {"a": a, "b": b, "n": n, "se": se, "sxx": sxx, "xbar": float(xbar), "p": float(stats.linregress(x, y).pvalue)}


def predict(fit: dict, t: float, level: float = 0.95) -> tuple[float, float, float]:
    """(value, low, high) at position t, with a prediction interval that widens the further t is from the data."""
    yhat = fit["a"] + fit["b"] * t
    tcrit = float(stats.t.ppf(0.5 + level / 2, fit["n"] - 2))
    half = tcrit * fit["se"] * math.sqrt(1 + 1 / fit["n"] + (t - fit["xbar"]) ** 2 / fit["sxx"])
    return yhat, yhat - half, yhat + half


def _clip(key: str, v: float) -> float:
    lim = column_map().get("plausible", {}).get(key)
    return min(max(v, lim[0]), lim[1]) if lim else v


def _min_change(key: str, level: float, sd: float) -> float:
    spec = scenarios_config()["defaults"]["min_change"].get(key)
    return parse_min_change(spec, level) if spec is not None else 0.5 * sd


@lru_cache(maxsize=None)
def _edges(key: str) -> list[tuple[float, str, str]]:
    """Reference boundaries for a measurement: (threshold, band below, band above)."""
    if key in BP_EDGES:
        return BP_EDGES[key]
    bands = (reference_config()["daily"].get(key) or {}).get("bands")
    if not bands:
        return []
    return [(bands[i]["hi"], bands[i]["label"], bands[i + 1]["label"]) for i in range(len(bands) - 1) if bands[i].get("hi") is not None]


def next_boundary(key: str, value: float, slope: float) -> tuple[float, str] | None:
    """The first reference boundary on the way the trend is heading, and the band it leads into."""
    edges = _edges(key)
    if slope > 0:
        ahead = [e for e in edges if e[0] > value]
        return (min(ahead)[0], min(ahead)[2]) if ahead else None
    if slope < 0:
        behind = [e for e in edges if e[0] < value]
        return (max(behind)[0], max(behind)[1]) if behind else None
    return None


# ----------------------------------------------------------------------------- one signal
def forecast_daily(s: pd.Series, key: str, horizons: tuple[int, ...] = (30, 90)) -> dict | None:
    """Project one daily signal. `s` is the daily series (dates as index). None if there is no data at all."""
    if s.empty or s.dropna().empty:
        return None
    base = {"key": key, "kind": "daily", "label": NAMES.get(key) or LABELS.get(key, key), "unit": UNITS.get(key, ""), "reliable": False}
    wk = s.resample("W").mean().iloc[-WEEKS_FIT:]
    if wk.notna().sum() < MIN_WEEKS:
        return {**base, "why": "not enough recent weeks of data to see a trend"}
    y = wk.to_numpy(float)
    fit = fit_xy(np.arange(len(y)), y)
    if fit is None:
        return {**base, "why": "not enough recent weeks of data to see a trend"}
    _, p = mann_kendall(y)
    last = len(y) - 1
    now = float(s.dropna().iloc[-14:].mean())
    change90 = fit["b"] * (90 / 7)
    need = _min_change(key, now, float(np.nanstd(y)))
    out = {**base, "now": round(now, 2), "slope_per_week": round(fit["b"], 3), "trend_p": round(p, 5), "weeks_used": int(fit["n"]),
           "change_90d": round(change90, 2), "min_change": round(need, 2), "scale": round(float(np.nanstd(y)), 3)}
    if not (p < GATE_P and abs(change90) >= SIZE_SHARE * need):
        return {**out, "why": "no lasting trend large enough to matter"}
    proj = []
    for d in horizons:
        ahead = d / 7
        _, lo, hi = predict(fit, last + ahead)
        centre = now + DAMP * fit["b"] * ahead
        half = (hi - lo) / 2 * INTERVAL_K
        proj.append({"days": d, "value": round(_clip(key, centre), 2), "low": round(_clip(key, centre - half), 2), "high": round(_clip(key, centre + half), 2)})
    out.update(reliable=True, trend="rising" if fit["b"] > 0 else "falling", projection=proj, why="a strong, lasting trend")
    nb = next_boundary(key, now, fit["b"])
    if nb:
        days = (nb[0] - now) / (DAMP * fit["b"] / 7)
        if 0 < days <= 180:
            out["crosses"] = {"threshold": nb[0], "into": nb[1], "in_days": int(round(days)), "within_range": bool(days <= 90)}
    return out


# ----------------------------------------------------------------------------- whole patient
@lru_cache(maxsize=1)
def backtest_summary() -> dict | None:
    p = RESULTS_DIR / "forecast_backtest.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    return {k: d[k] for k in ("patients", "daily", "labs_not_projected") if k in d}


def build_forecasts(rec) -> dict:
    """Projections for every daily signal with a strong trend, plus the signals with no lasting trend."""
    items, steady = [], []
    for key in DAILY_KEYS:
        f = forecast_daily(daily_series(rec, key), key)
        if f:
            (items if f["reliable"] else steady).append(f)
    items.sort(key=lambda f: (0 if f.get("crosses") else 1, -abs(f["change_90d"] / (f["min_change"] or 1))))
    end = rec.window[1] if rec.window else None
    return {"items": items, "steady": [{"key": f["key"], "label": f["label"], "why": f["why"]} for f in steady],
            "as_of": end.strftime("%Y-%m-%d") if end is not None else None,
            "method": "A straight-line trend of the last 16 weeks, assuming 75% of it continues, with a 95% range. Shown only for strong, lasting trends. Lab results are not projected: there are too few of them to do it reliably.",
            "evidence": backtest_summary()}


def projected_date(as_of: str | None, days: int) -> str | None:
    if not as_of:
        return None
    return (pd.Timestamp(as_of) + timedelta(days=days)).strftime("%Y-%m-%d")
