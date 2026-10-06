"""Multi-signal pattern detection (owner: Sindhu).

A scenario is SURFACED only when
  * at least `min_signals` of its signals changed in the direction of concern,
  * the daily signals started changing within `co_occurrence_days` of each other
    (labs are sparse, so they join the group without the timing rule), and
  * at least one of the scenario's `core_signals` is in the group
    (e.g. a hypertension pattern needs blood pressure itself to move).

One isolated change (e.g. only systolic BP) is shown on the timeline but is
not surfaced as a pattern. This is the main difference from a high/low alert.
"""
from __future__ import annotations

import pandas as pd

from prana.analysis.baseline import assess_cycles, assess_daily, assess_lab
from prana.config import scenarios_config
from prana.data.loader import PatientRecord
from prana.data.timeline import cycle_series, daily_series, lab_series


def assess_scenario(rec: PatientRecord, key: str, scfg: dict, defaults: dict) -> dict:
    result = {"scenario": key, "title": scfg["title"], "applicable": True, "signals": {}}
    if scfg.get("applies_to") == "female" and rec.sex != "female":
        result.update({"applicable": False, "surfaced": False, "changed_signals": [], "pattern_signals": []})
        return result

    mc = defaults.get("min_change", {})
    for sig, direction in scfg.get("signals", {}).items():
        if sig == "cycle_length":
            a = assess_cycles(cycle_series(rec), float(mc.get("cycle_length", 5)))
        else:
            a = assess_daily(daily_series(rec, sig), direction, defaults, mc.get(sig))
        result["signals"][sig] = a
    for lab, (direction, delta) in scfg.get("lab_signals", {}).items():
        result["signals"][lab] = assess_lab(lab_series(rec, lab), direction, float(delta))

    changed = [s for s, a in result["signals"].items() if a["status"] == "changed"]
    group = co_occurring_group(result["signals"], changed, defaults["co_occurrence_days"])
    has_core = any(s in group for s in scfg.get("core_signals", group))
    result.update({
        "changed_signals": changed,
        "pattern_signals": group,
        "surfaced": len(group) >= defaults["min_signals"] and has_core,
        "window_start": _pattern_start(result["signals"], group),
    })
    return result


def _pattern_start(signals: dict, group: list[str]) -> str | None:
    """Earliest onset among the daily/cycle signals (sparse labs only if nothing else)."""
    dense = [signals[s]["onset_date"] for s in group if signals[s]["kind"] != "lab" and signals[s].get("onset_date")]
    labs = [signals[s]["onset_date"] for s in group if signals[s]["kind"] == "lab" and signals[s].get("onset_date")]
    return min(dense) if dense else (min(labs) if labs else None)


def co_occurring_group(signals: dict, changed: list[str], span_days: int) -> list[str]:
    """Largest set of changed signals whose onset dates fit inside `span_days`.
    Labs (sparse) and cycle data are always included if they changed."""
    sparse = [s for s in changed if signals[s]["kind"] != "daily"]
    daily = [(s, pd.Timestamp(signals[s]["onset_date"])) for s in changed
             if signals[s]["kind"] == "daily" and signals[s].get("onset_date")]
    daily.sort(key=lambda t: t[1])
    best: list[str] = []
    for i in range(len(daily)):
        grp = [s for s, d in daily[i:] if (d - daily[i][1]).days <= span_days]
        if len(grp) > len(best):
            best = grp
    return best + sparse


def detect_all(rec: PatientRecord) -> list[dict]:
    cfg = scenarios_config()
    return [assess_scenario(rec, k, s, cfg["defaults"]) for k, s in cfg["scenarios"].items()]
