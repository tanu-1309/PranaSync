"""The portal's package for one patient: signals, labs, medicines, patterns, reference results.

Built once from the analysed workbook and stored in the `records` table, so the web server does not re-analyse
the Excel file on every visit.
"""
from __future__ import annotations

import json
import math

import pandas as pd

from prana.ai.outlook import build_outlook
from prana.analysis.baseline import rolling_view
from prana.data.timeline import daily_series
from prana.insight.evidence import LABELS

# (key, label, unit, group) for every daily line the patient page can draw
DAILY = [
    ("sbp", "Systolic BP", "mmHg", "Heart"), ("dbp", "Diastolic BP", "mmHg", "Heart"),
    ("resting_hr", "Resting heart rate", "bpm", "Heart"), ("hrv_ms", "Heart-rate variability", "ms", "Heart"),
    ("weight_kg", "Weight", "kg", "Body"), ("spo2", "Blood oxygen", "%", "Body"),
    ("steps", "Daily steps", "steps", "Movement"), ("active_minutes", "Active minutes", "min", "Movement"),
    ("sedentary_hours", "Sedentary time", "h", "Movement"), ("sleep_hours", "Sleep", "h", "Rest"),
    ("stress_score", "Stress score", "pts", "Rest"),
]
LAB_KEYS = ["hba1c", "fasting_glucose", "ldl_cholesterol", "hdl_cholesterol", "triglycerides", "total_cholesterol",
            "testosterone", "lh_fsh_ratio", "fasting_insulin", "tsh", "vitamin_d", "egfr"]


def _num(x, nd=2):
    if x is None:
        return None
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) or math.isinf(f) else round(f, nd)


def _d(x) -> str | None:
    return None if x is None or pd.isna(x) else pd.Timestamp(x).strftime("%Y-%m-%d")



def build_payload(result: dict, rec, tl) -> dict:
    """Everything the portal draws for one patient, as plain JSON."""
    start = rec.window[0] if rec.window else None

    series = {}
    for key, label, unit, group in DAILY:
        s = daily_series(rec, key)
        if s.empty or s.dropna().empty:
            continue
        rv = rolling_view(s)
        series[key] = {"label": label, "unit": unit, "group": group,
                       "start": _d(s.index[0]), "n": len(s),
                       "v": [_num(x) for x in rv["value"]], "r": [_num(x) for x in rv["rolling"]],
                       "base": {"mean": _num(rv["baseline_mean"].iloc[0]), "lo": _num(rv["baseline_low"].iloc[0]),
                                "hi": _num(rv["baseline_high"].iloc[0])}}

    labs = {}
    L = rec.get("labs")
    if not L.empty:
        for key in LAB_KEYS:
            d = L[L.test_key == key].sort_values("date")
            if d.empty:
                continue
            labs[key] = {"label": LABELS.get(key, d.test.iloc[0]), "unit": d.unit.iloc[0], "ref": str(d.ref_range.iloc[0]),
                         "points": [{"d": _d(r.date), "v": _num(r.value)} for r in d.itertuples()]}

    events = []
    for r in tl[tl.source.isin(["history", "medications", "symptoms", "notes"])].itertuples():
        events.append({"d": _d(r.date), "t": r.source, "text": r.text})
    meds = [{"id": r.med_id, "name": r.medication, "dose": r.dose, "freq": r.frequency, "start": _d(r.start_date), "end": _d(r.end_date),
             "status": r.status, "for": r.indication, "tolerance": r.tolerance, "why": r.change_rationale}
            for r in rec.get("medications").itertuples()] if not rec.get("medications").empty else []
    adherence = [{"d": _d(r.date), "med": r.med_id, "pct": _num(r.adherence_pct, 0), "missed": _num(r.missed_doses, 0), "src": r.source}
                 for r in rec.get("adherence").itertuples()] if not rec.get("adherence").empty else []
    cycles = [{"d": _d(r.date), "len": _num(r.cycle_length, 0), "bleed": _num(r.bleeding_days, 0)}
              for r in rec.get("women").itertuples()] if not rec.get("women").empty else []

    scenarios = json.loads(json.dumps(result["scenarios"], default=str))
    for s in scenarios:
        s["signals"] = {k: {kk: vv for kk, vv in a.items() if kk != "values"} for k, a in s.get("signals", {}).items()}
        for e in s["evidence"]:
            e.pop("values", None)

    prof = result["profile"]
    return {"id": result["patient_id"], "window": result["window"], "start": _d(start),
            "profile": {"age": _num(prof.get("Age"), 0), "sex": prof.get("Sex"), "height": prof.get("Height (cm)"),
                        "blood": prof.get("Blood Group"), "allergies": prof.get("Allergies"),
                        "family": prof.get("Family History")},
            "quality": result["quality"], "scenarios": scenarios, "labels": LABELS, "series": series, "labs": labs,
            "events": events, "meds": meds, "adherence": adherence, "cycles": cycles,
            "reference": result["reference"], "outlook": build_outlook(result, rec)}


