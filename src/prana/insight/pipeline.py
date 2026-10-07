"""End-to-end pipeline for one patient (owner: Uday, uses everyone's modules).

workbook -> load & clean -> timeline -> scenario detection -> context + evidence
-> missing data -> explanation, plus a reference-range check of the recent levels.

Planned (week 8): let the user add the data the system asked for and re-run.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from prana.analysis.patterns import assess_scenario
from prana.analysis.reference import assess_reference
from prana.config import scenarios_config
from prana.data.loader import PatientRecord, load_workbook
from prana.data.timeline import build_timeline
from prana.insight.evidence import build_evidence
from prana.insight.explainer import explain


def analyze_record(rec: PatientRecord) -> dict:
    cfg = scenarios_config()
    out = {"patient_id": rec.patient_id, "profile": {k: str(v) for k, v in rec.profile.items()},
           "quality": rec.quality, "window": [str(d.date()) for d in rec.window] if rec.window else None,
           "scenarios": []}
    for key, scfg in cfg["scenarios"].items():
        res = assess_scenario(rec, key, scfg, cfg["defaults"])
        pack = build_evidence(rec, res, scfg)
        pack["explanation"] = explain(pack)
        out["scenarios"].append(pack)
    # second, separate question: where do the recent levels sit against general reference ranges?
    out["reference"] = assess_reference(rec, out["scenarios"])
    return out


def analyze_workbook(path: str | Path) -> tuple[dict, PatientRecord, pd.DataFrame]:
    rec = load_workbook(path)
    return analyze_record(rec), rec, build_timeline(rec)
