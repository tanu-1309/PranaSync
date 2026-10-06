"""Personal baselines and trend detection (owner: Sindhu).

Every signal is compared with the person's OWN earlier values, not a fixed
population threshold. A signal only counts as "changed" when ALL of these hold:

  1. enough data            coverage >= min_coverage and >= 20 baseline days
  2. meaningful size        |recent mean - baseline mean| >= min_change (config)
  3. large vs. normal noise effect size = shift / baseline SD >= min_effect_size
  4. a real trend           Mann-Kendall test on weekly means, p < trend_alpha,
                            in the direction of concern
  5. still present          "recent" = the last 60 days, so a dip that recovered
                            (holiday, short illness) is not reported

Onset date = single change point on weekly means (ruptures Binseg; falls back
to a CUSUM if ruptures is not installed).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import stats

try:
    import ruptures as rpt
except ImportError:  # optional
    rpt = None

RECENT_DAYS = 60


def parse_min_change(spec, baseline_mean: float) -> float:
    if spec is None:
        return 0.0
    if isinstance(spec, str) and spec.strip().endswith("%"):
        return abs(baseline_mean) * float(spec.strip()[:-1]) / 100.0
    return float(spec)


def mann_kendall(x: np.ndarray) -> tuple[float, float]:
    """Return (z, two-sided p) of the Mann-Kendall trend test (no ties correction needed for means)."""
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 6:
        return 0.0, 1.0
    s = sum(np.sign(x[j] - x[i]) for i in range(n - 1) for j in range(i + 1, n))
    var = n * (n - 1) * (2 * n + 5) / 18.0
    z = (s - np.sign(s)) / math.sqrt(var) if s != 0 else 0.0
    return float(z), float(2 * (1 - stats.norm.cdf(abs(z))))


def change_point(weekly: pd.Series) -> pd.Timestamp | None:
    w = weekly.dropna()
    if len(w) < 8:
        return None
    y = w.values.astype(float)
    if rpt is not None:
        try:
            bkp = rpt.Binseg(model="l2", min_size=3).fit(y.reshape(-1, 1)).predict(n_bkps=1)[0]
            return w.index[min(bkp, len(w) - 1)]
        except Exception:  # pragma: no cover
            pass
    c = np.cumsum(y - y.mean())
    return w.index[int(np.argmax(np.abs(c)))]


def assess_daily(series: pd.Series, direction: str, defaults: dict, min_change_spec=None) -> dict:
    s = series.astype(float)
    n_total = len(s)
    out = {"kind": "daily", "direction": direction, "n_days": int(s.notna().sum()),
           "coverage": round(float(s.notna().mean()), 2) if n_total else 0.0}
    base = s.iloc[: defaults["baseline_days"]].dropna()
    if n_total == 0 or out["coverage"] < defaults["min_coverage"] or len(base) < 20:
        out["status"] = "insufficient_data"
        return out
    recent = s.iloc[-RECENT_DAYS:].dropna()
    if len(recent) < 15:
        out["status"] = "insufficient_data"
        return out
    b_mean, b_sd = float(base.mean()), float(base.std(ddof=1)) or 1e-6
    r_mean = float(recent.mean())
    shift = r_mean - b_mean
    signed = shift if direction == "up" else -shift
    min_change = parse_min_change(min_change_spec, b_mean)
    weekly = s.resample("W").mean()
    z, p = mann_kendall(weekly.values)
    slope = stats.theilslopes(weekly.dropna().values).slope if weekly.notna().sum() >= 4 else 0.0
    trend_ok = p < defaults["trend_alpha"] and (z > 0 if direction == "up" else z < 0)
    effect = signed / b_sd
    changed = signed >= min_change and effect >= defaults["min_effect_size"] and trend_ok
    improving = (-signed >= min_change and p < defaults["trend_alpha"]
                 and (z < 0 if direction == "up" else z > 0))
    status = "changed" if changed else ("improving" if improving else "stable")
    out.update({
        "status": status, "baseline_mean": round(b_mean, 2), "baseline_sd": round(b_sd, 2),
        "recent_mean": round(r_mean, 2), "change": round(shift, 2),
        "change_pct": round(100 * shift / b_mean, 1) if b_mean else None,
        "effect_size": round(effect, 2), "min_change": round(min_change, 2),
        "trend_p": round(p, 4), "slope_per_month": round(slope * 4.345, 3),
        "onset_date": None,
    })
    if changed:
        cp = change_point(weekly)
        out["onset_date"] = str(cp.date()) if cp is not None else None
    return out


def assess_lab(series: pd.Series, direction: str, min_delta: float) -> dict:
    s = series.dropna().sort_index()
    out = {"kind": "lab", "direction": direction, "n_results": int(len(s)),
           "values": [{"date": str(d.date()), "value": float(v)} for d, v in s.items()]}
    if len(s) < 2:
        out["status"] = "insufficient_data"
        out["last_date"] = str(s.index[-1].date()) if len(s) else None
        return out
    # Single lab draws are noisy: with >=4 results compare the mean of the first
    # two with the mean of the last two instead of one value against another.
    k = 2 if len(s) >= 4 else 1
    first, last = float(s.iloc[:k].mean()), float(s.iloc[-k:].mean())
    shift = last - first
    signed = shift if direction == "up" else -shift
    slope_ok = True
    if len(s) >= 3:
        days = (s.index - s.index[0]).days.values.astype(float)
        sl = stats.theilslopes(s.values, days).slope
        slope_ok = sl > 0 if direction == "up" else sl < 0
    changed = signed >= min_delta and slope_ok
    onset = None
    if changed:
        for d, v in s.iloc[k:].items():
            if (v - first if direction == "up" else first - v) >= min_delta / 2:
                onset = str(d.date())
                break
    out.update({"status": "changed" if changed else "stable", "first": first, "last": last,
                "change": round(shift, 2), "min_change": min_delta, "onset_date": onset,
                "last_date": str(s.index[-1].date())})
    return out


def assess_cycles(series: pd.Series, min_change: float = 5.0) -> dict:
    s = series.dropna().sort_index()
    out = {"kind": "cycle", "direction": "up", "n_cycles": int(len(s)),
           "values": [{"date": str(d.date()), "value": float(v)} for d, v in s.items()]}
    if len(s) < 5:
        out["status"] = "insufficient_data"
        return out
    b, r = s.iloc[:3], s.iloc[-3:]
    shift = float(r.mean() - b.mean())
    long_cycles = int((s > 35).sum())
    changed = shift >= min_change
    onset = None
    if changed:
        over = s[s > b.mean() + min_change]
        onset = str(over.index[0].date()) if len(over) else None
    out.update({"status": "changed" if changed else "stable", "baseline_mean": round(float(b.mean()), 1),
                "recent_mean": round(float(r.mean()), 1), "change": round(shift, 1),
                "recent_sd": round(float(s.iloc[-4:].std()), 1), "cycles_over_35_days": long_cycles,
                "min_change": min_change, "onset_date": onset})
    return out


def rolling_view(series: pd.Series, baseline_days: int = 60, window: int = 30) -> pd.DataFrame:
    """For charts: daily value, 30-day rolling mean, baseline band and z-score."""
    s = series.astype(float)
    base = s.iloc[:baseline_days].dropna()
    mu, sd = (base.mean(), base.std(ddof=1) or 1e-6) if len(base) else (np.nan, np.nan)
    return pd.DataFrame({"value": s, "rolling": s.rolling(window, min_periods=window // 2).mean(),
                         "baseline_mean": mu, "baseline_low": mu - sd, "baseline_high": mu + sd,
                         "z": (s - mu) / sd})
