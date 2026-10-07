"""Evidence pack builder (owner: Uday).

The evidence pack is the single source of truth for one scenario: what changed,
when, by how much, which past finding it relates to, what is missing, and the
limits of the analysis. The explanation layer may only reword this pack.
"""
from __future__ import annotations

from prana.data.loader import PatientRecord
from prana.insight.context_linker import has_prior_finding, link_context
from prana.insight.missing_data import missing_for_scenario

LABELS = {
    "steps": "Daily steps", "active_minutes": "Active minutes", "sedentary_hours": "Sedentary hours",
    "weight_kg": "Weight (kg)", "sleep_hours": "Sleep (hours)", "sbp": "Systolic BP (mmHg)",
    "dbp": "Diastolic BP (mmHg)", "resting_hr": "Resting heart rate (bpm)", "hrv_ms": "Heart-rate variability (ms)",
    "cycle_length": "Cycle length (days)", "hba1c": "HbA1c (%)", "fasting_glucose": "Fasting glucose (mg/dL)",
    "triglycerides": "Triglycerides (mg/dL)", "ldl_cholesterol": "LDL cholesterol (mg/dL)",
    "total_cholesterol": "Total cholesterol (mg/dL)", "testosterone": "Testosterone (ng/dL)",
    "fasting_insulin": "Fasting insulin", "lh_fsh_ratio": "LH/FSH ratio",
}

STATUS_TEXT = {
    "pattern_with_context": "Several related signals changed together, and this links to something already in the history",
    "pattern_no_context": "Several related signals changed together; nothing related was found in the history",
    "known_context_stable": "There is a related finding in the history, and the ongoing data has stayed stable",
    "no_pattern": "No multi-signal pattern found",
    "insufficient_data": "Not enough data to look for this pattern",
    "not_applicable": "Not applicable for this person",
}


def build_evidence(rec: PatientRecord, scenario_result: dict, scfg: dict) -> dict:
    key = scenario_result["scenario"]
    if not scenario_result["applicable"]:
        return {"scenario": key, "title": scfg["title"], "status": "not_applicable",
                "status_text": STATUS_TEXT["not_applicable"], "surfaced": False, "changed_signals": [],
                "pattern_signals": [], "evidence": [], "context": [], "missing_data": [], "limitations": [], "signals": {}}

    signals = scenario_result["signals"]
    context = link_context(rec, scfg, scenario_result.get("window_start"))
    missing = missing_for_scenario(rec, scfg)
    prior = has_prior_finding(context)
    n_usable = sum(1 for a in signals.values() if a["status"] != "insufficient_data")

    if scenario_result["surfaced"]:
        status = "pattern_with_context" if prior else "pattern_no_context"
    elif n_usable < 2:
        status = "insufficient_data"
    elif prior:
        status = "known_context_stable"
    else:
        status = "no_pattern"

    evidence = []
    for s in scenario_result["pattern_signals"] if scenario_result["surfaced"] else scenario_result["changed_signals"]:
        a = signals[s]
        item = {"signal": s, "label": LABELS.get(s, s), "kind": a["kind"], "direction": a["direction"],
                "change": a.get("change"), "onset_date": a.get("onset_date")}
        if a["kind"] == "daily":
            item.update({"baseline_mean": a["baseline_mean"], "recent_mean": a["recent_mean"],
                         "change_pct": a["change_pct"], "effect_size": a["effect_size"],
                         "trend_p": a["trend_p"], "coverage": a["coverage"]})
        elif a["kind"] == "lab":
            item.update({"first": a["first"], "last": a["last"], "values": a["values"]})
        else:
            item.update({"baseline_mean": a["baseline_mean"], "recent_mean": a["recent_mean"],
                         "cycles_over_35_days": a["cycles_over_35_days"], "values": a["values"]})
        evidence.append(item)

    limitations = ["Personal baseline = first 60 days of the record; if those days were already unusual, changes are under- or over-stated.",
                   "Synthetic/anonymised data; patterns describe co-occurring changes, not causes."]
    for s, a in signals.items():
        if a["status"] == "insufficient_data":
            limitations.append(f"{LABELS.get(s, s)}: not enough data to assess.")
        elif a["kind"] == "lab" and a.get("n_results", 0) < 3:
            limitations.append(f"{LABELS.get(s, s)}: only {a['n_results']} results, trend is uncertain.")

    return {
        "scenario": key, "title": scfg["title"], "status": status, "status_text": STATUS_TEXT[status],
        "surfaced": scenario_result["surfaced"], "pattern_start": scenario_result.get("window_start"),
        "changed_signals": scenario_result["changed_signals"], "pattern_signals": scenario_result["pattern_signals"],
        "evidence": evidence, "context": context, "missing_data": missing, "limitations": limitations,
        "signals": signals,
    }
