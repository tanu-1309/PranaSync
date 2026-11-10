"""The patient's outlook: projections plus recommendations, built once and stored in their portal package."""
from __future__ import annotations

from prana.ai.forecast import build_forecasts
from prana.ai.recommend import build_recommendations
from prana.ai.risk import build_diabetes_risk, build_risk
from prana.data.timeline import daily_series, lab_series


def build_outlook(result: dict, rec) -> dict:
    forecast = build_forecasts(rec)
    _drivers(forecast, result)
    return {"forecast": forecast, "recommendations": build_recommendations(result, forecast, rec), "risk": build_risk(result, rec),
            "diabetes": build_diabetes_risk(result, rec), "watch": build_watchlist(result, rec, forecast)}


def _drivers(forecast: dict, result: dict) -> None:
    """For each projected trend, list in plain words what produced it and what else moved with it."""
    moved = {e["signal"]: [x["label"].split(" (")[0] for x in sc["evidence"] if x["signal"] != e["signal"]]
             for sc in result["scenarios"] if sc.get("surfaced") for e in sc["evidence"]}
    for f in forecast["items"]:
        up = f["trend"] == "rising"
        f["drivers"] = [
            f"Over the last {f['weeks_used']} weeks the weekly average has been {'rising' if up else 'falling'} by about {abs(f['slope_per_week']):.2g} {f['unit']} a week.",
            f"Over 90 days it changed by {abs(f['change_90d']):.2g} {f['unit']}, which is well above everyday ups and downs.",
            "A trend test says this is very unlikely to be chance (p below 0.001)."]
        if moved.get(f["key"]):
            f["drivers"].append("It moved together with " + ", ".join(moved[f["key"]][:3]) + " in a pattern found in your data.")


SERIES_FOR = {"bp": "sbp", "bmi": "weight_kg"}   # a reference measure that is drawn from a different series
WATCH_LIMIT = 6


def _direction(first: float, last: float, flat_pct: float) -> tuple[str, float]:
    pct = (last - first) / abs(first) * 100 if first else 0.0
    return ("rising" if pct > flat_pct else "falling" if pct < -flat_pct else "steady"), pct


def build_watchlist(result: dict, rec, forecast: dict) -> dict:
    """Every measure that sits outside its usual range, each with its own trend line and, only if the trend is strong enough, a projection."""
    proj = {f["key"]: f for f in forecast["items"]}
    rank = {"outside": 0, "watch": 1}
    out = []
    for it in sorted((i for i in result["reference"]["items"] if i["flag"] != "within" and not i["soft"]), key=lambda i: rank.get(i["flag"], 2)):
        key = SERIES_FOR.get(it["key"], it["key"])
        if it["kind"] == "daily":
            s = daily_series(rec, key).dropna()
            if len(s) < 30:
                continue
            weekly = s.resample("W").mean().dropna().tail(26)
            pts = [{"d": d.strftime("%Y-%m-%d"), "v": round(float(v), 2)} for d, v in weekly.items()]
            direction, pct = _direction(float(s.tail(90).head(14).mean()), float(s.tail(14).mean()), 2.0)
            change = {"rising": f"Up about {abs(pct):.0f}% over the last 3 months", "falling": f"Down about {abs(pct):.0f}% over the last 3 months", "steady": "Steady over the last 3 months"}[direction]
        else:
            s = lab_series(rec, key).dropna()
            if len(s) < 2:
                continue
            pts = [{"d": d.strftime("%Y-%m-%d"), "v": round(float(v), 2)} for d, v in s.items()]
            direction, pct = _direction(float(s.iloc[0]), float(s.iloc[-1]), 4.0)
            change = f"{len(s)} results, from {s.iloc[0]:.4g} to {s.iloc[-1]:.4g}" + ("" if direction == "steady" else f" ({direction})")
        f = proj.get(key)
        projection = None
        if f:
            p90 = next(x for x in f["projection"] if x["days"] == 90)
            projection = {"value": p90["value"], "low": p90["low"], "high": p90["high"], "days": 90}
        out.append({"key": it["key"], "label": it["label"].split(" (")[0], "unit": it["unit"], "kind": it["kind"], "flag": it["flag"], "category": it["category"],
                    "value_text": it["value_text"], "reference_text": it["reference_text"], "direction": direction, "change": change, "points": pts, "projection": projection, "drivers": f.get("drivers") if f else None,
                    "note": None if projection else "No strong, lasting trend, so no projection is made. That is a reason to keep watching, not a forecast of no change."})
    return {"items": out[:WATCH_LIMIT], "more": [x["label"] for x in out[WATCH_LIMIT:]]}
