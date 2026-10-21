"""Missing-data suggestions (owner: Uday).

Kickoff answer from Prana Chain: run on whatever data is available, explain
the findings, then tell the user which data is still missing and ask for it.
"""
from __future__ import annotations

import pandas as pd

from prana.data.loader import PatientRecord
from prana.data.timeline import cycle_series, daily_series, lab_series

GOOD_COVERAGE = 0.7


def missing_for_scenario(rec: PatientRecord, scfg: dict) -> list[dict]:
    end = rec.window[1] if rec.window else pd.Timestamp.today()
    asks = []
    for w in scfg.get("wanted_data", []):
        key = w["key"]
        if w["type"] == "lab":
            s = lab_series(rec, key)
            if s.empty:
                asks.append({"item": w["item"], "key": key, "reason": "no result in the record"})
            elif (end - s.index.max()).days > w.get("max_age_days", 365):
                asks.append({"item": w["item"], "key": key,
                             "reason": f"latest result is from {s.index.max().date()} (older than {w['max_age_days']} days)"})
        elif key == "cycle_length":
            if len(cycle_series(rec)) < 5:
                asks.append({"item": w["item"], "key": key, "reason": "fewer than 5 cycles recorded"})
        else:
            s = daily_series(rec, key)
            cov = float(s.notna().mean()) if len(s) else 0.0
            if cov == 0:
                asks.append({"item": w["item"], "key": key, "reason": "not recorded"})
            elif cov < GOOD_COVERAGE:
                asks.append({"item": w["item"], "key": key, "reason": f"only {cov:.0%} of days recorded"})
    return asks
