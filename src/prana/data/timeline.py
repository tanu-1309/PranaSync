"""Unified timeline (owner: Sneha).

Turns the separate sheets into ONE long table:
    patient_id | date | source | signal | value | unit | text
so that labs, vitals, wearables, cycles, history, medications and symptoms
can be read on the same time axis (user story 1).
"""
from __future__ import annotations

import pandas as pd

from prana.data.loader import PatientRecord

UNITS = {"sbp": "mmHg", "dbp": "mmHg", "resting_hr": "bpm", "wearable_rhr": "bpm", "weight_kg": "kg",
         "bmi": "kg/m²", "spo2": "%", "temp_c": "°C", "resp_rate": "/min", "steps": "steps",
         "sleep_hours": "h", "active_minutes": "min", "hrv_ms": "ms", "calories": "kcal",
         "sedentary_hours": "h", "stress_score": "1-10", "cycle_length": "days"}


def build_timeline(rec: PatientRecord) -> pd.DataFrame:
    parts = []
    for source in ("vitals", "wearable"):
        df = rec.get(source)
        if df.empty:
            continue
        long = df.melt(id_vars="date", var_name="signal", value_name="value").dropna(subset=["value"])
        long["source"] = source
        parts.append(long)
    labs = rec.get("labs")
    if not labs.empty:
        parts.append(pd.DataFrame({"date": labs["date"], "signal": labs["test_key"], "value": labs["value"],
                                   "unit": labs["unit"], "source": "lab", "text": labs["test"]}))
    women = rec.get("women")
    if not women.empty:
        parts.append(pd.DataFrame({"date": women["date"], "signal": "cycle_length", "value": women["cycle_length"],
                                   "source": "women_health"}))
    for key, col in (("history", "finding"), ("symptoms", "symptom"), ("notes", "note")):
        df = rec.get(key)
        if not df.empty and col in df:
            parts.append(pd.DataFrame({"date": df["date"], "signal": key, "text": df[col].astype(str), "source": key}))
    meds = rec.get("medications")
    if not meds.empty:
        parts.append(pd.DataFrame({"date": meds["start_date"], "signal": "medication_start",
                                   "text": meds["medication"].astype(str) + " (" + meds["status"].astype(str) + ")",
                                   "source": "medications"}))
    if not parts:
        return pd.DataFrame(columns=["patient_id", "date", "source", "signal", "value", "unit", "text"])
    tl = pd.concat(parts, ignore_index=True)
    tl["patient_id"] = rec.patient_id
    tl["unit"] = tl.get("unit", pd.Series(index=tl.index, dtype=object))
    tl["unit"] = tl["unit"].fillna(tl["signal"].map(UNITS))
    for c in ("value", "text"):
        if c not in tl:
            tl[c] = None
    return tl[["patient_id", "date", "source", "signal", "value", "unit", "text"]].sort_values("date").reset_index(drop=True)


def daily_series(rec: PatientRecord, signal: str) -> pd.Series:
    """One daily signal over the whole data window (missing days = NaN)."""
    for source in ("vitals", "wearable"):
        df = rec.get(source)
        if not df.empty and signal in df:
            s = df.set_index("date")[signal].sort_index()
            if rec.window and pd.notna(rec.window[0]):
                s = s.reindex(pd.date_range(rec.window[0], rec.window[1], freq="D"))
            return s
    return pd.Series(dtype=float)


def lab_series(rec: PatientRecord, key: str) -> pd.Series:
    labs = rec.get("labs")
    if labs.empty:
        return pd.Series(dtype=float)
    return labs[labs["test_key"] == key].set_index("date")["value"].sort_index()


def cycle_series(rec: PatientRecord) -> pd.Series:
    w = rec.get("women")
    if w.empty:
        return pd.Series(dtype=float)
    return w.set_index("date")["cycle_length"].dropna().sort_index()
