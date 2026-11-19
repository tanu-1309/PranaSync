"""What the Analytics & Intelligence page shows that is computed by code.

Nothing here changes a calculation. It reads the patient package the analysis already produced (the stored values: baselines, tests, change points, patterns,
reference results, risk scores, forecasts, missing data) and lays them out. Where the page needs a number the package does not carry (the Mann-Kendall test
statistic, the before and after values around a change point) it is recomputed with the SAME functions the analysis uses, from the stored daily series.
No AI writes anything in this module. A value that is not available is None, never a guess, and never zero.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from prana.analysis import baseline
from prana.config import ROOT, scenarios_config

NOTE_ROUNDED = "Recomputed from the stored daily series (rounded to 2 decimals), so it can differ slightly from the value the analysis stored."


def _f(x, nd=3):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(v) or math.isinf(v) else round(v, nd)


def _series(S: dict) -> pd.Series:
    idx = pd.date_range(S["start"], periods=len(S["v"]), freq="D")
    return pd.Series([np.nan if v is None else v for v in S["v"]], index=idx, dtype=float)


def _seg(s: pd.Series) -> dict:
    d = s.dropna()
    return {"n": int(len(d)), "mean": _f(d.mean(), 2) if len(d) else None, "sd": _f(d.std(ddof=1), 2) if len(d) > 1 else None}


def _label(p: dict, key: str) -> str:
    return (p.get("series", {}).get(key, {}).get("label") or p.get("labs", {}).get(key, {}).get("label") or p.get("labels", {}).get(key) or key.replace("_", " "))


def _unit(p: dict, key: str) -> str | None:
    return p.get("series", {}).get(key, {}).get("unit") or p.get("labs", {}).get(key, {}).get("unit")


def _signal_rows(p: dict):
    for sc in p.get("scenarios", []):
        if sc.get("status") == "not_applicable":
            continue
        for key, a in (sc.get("signals") or {}).items():
            yield sc, key, a


# ---------------------------------------------------------------- sections
def _baseline(p: dict, cfg: dict) -> list[dict]:
    d = cfg["defaults"]
    rows = []
    for sc, key, a in _signal_rows(p):
        row = {"key": key, "label": _label(p, key), "unit": _unit(p, key), "area": sc["title"], "kind": a.get("kind"), "status": a.get("status"), "direction": a.get("direction"),
               "baseline_mean": a.get("baseline_mean", a.get("first")), "recent_mean": a.get("recent_mean", a.get("last")), "baseline_sd": a.get("baseline_sd"),
               "effect_size": a.get("effect_size"), "change": a.get("change"), "change_pct": a.get("change_pct"), "min_change": a.get("min_change"),
               "baseline_period": None, "recent_period": None,
               "basis": {"daily": f"first {d['baseline_days']} days vs the last {baseline.RECENT_DAYS} days", "lab": "mean of the first results vs the mean of the last results",
                         "cycle": "mean of the first 3 cycles vs the last 3 cycles"}.get(a.get("kind"), None)}
        S = p.get("series", {}).get(key)
        if a.get("kind") == "daily" and S and a.get("status") != "insufficient_data":
            s = _series(S)
            row["baseline_period"] = [str(s.index[0].date()), str(s.index[min(d["baseline_days"], len(s)) - 1].date())]
            row["recent_period"] = [str(s.index[-baseline.RECENT_DAYS:][0].date()), str(s.index[-1].date())]
        rows.append(row)
    return rows


def _trend(p: dict, cfg: dict) -> list[dict]:
    alpha = cfg["defaults"]["trend_alpha"]
    rows = []
    for sc, key, a in _signal_rows(p):
        if a.get("kind") != "daily":
            continue
        S = p.get("series", {}).get(key)
        row = {"key": key, "label": _label(p, key), "unit": _unit(p, key), "area": sc["title"], "status": a.get("status"), "n_observations": a.get("n_days"),
               "coverage": a.get("coverage"), "p_value": a.get("trend_p"), "slope_per_month": a.get("slope_per_month"), "statistic_z": None, "weekly_points": None,
               "period": None, "trend": None, "threshold": {"p_below": alpha, "effect_size_at_least": cfg["defaults"]["min_effect_size"], "min_change": a.get("min_change")},
               "recomputed_p": None, "note": None}
        if S and a.get("status") != "insufficient_data":
            s = _series(S)
            weekly = s.resample("W").mean()
            z, pv = baseline.mann_kendall(weekly.values)
            row.update(statistic_z=_f(z), recomputed_p=_f(pv, 4), weekly_points=int(weekly.notna().sum()), period=[str(s.index[0].date()), str(s.index[-1].date())], note=NOTE_ROUNDED)
            row["trend"] = "rising" if (pv < alpha and z > 0) else "falling" if (pv < alpha and z < 0) else "no significant trend"
        rows.append(row)
    return rows


def _change_points(p: dict, cfg: dict) -> dict:
    using = "ruptures Binseg (l2 cost, one breakpoint)" if baseline.rpt is not None else "CUSUM (the fallback: the ruptures package is not installed)"
    rows, not_run = [], 0
    for sc, key, a in _signal_rows(p):
        if a.get("status") != "changed" or not a.get("onset_date"):
            not_run += a.get("status") != "changed"
            continue
        onset = pd.Timestamp(a["onset_date"])
        row = {"key": key, "label": _label(p, key), "unit": _unit(p, key), "area": sc["title"], "kind": a.get("kind"), "breakpoint": a["onset_date"], "before": None, "after": None}
        S = p.get("series", {}).get(key)
        if a.get("kind") == "daily" and S:
            s = _series(S)
            row.update(algorithm=using, before=_seg(s[s.index < onset]), after=_seg(s[s.index >= onset]))
        elif a.get("kind") == "lab":
            pts = pd.Series({pd.Timestamp(x["d"]): x["v"] for x in p.get("labs", {}).get(key, {}).get("points", [])}, dtype=float).sort_index()
            row.update(algorithm="first result that moved by at least half the minimum change", before=_seg(pts[pts.index < onset]), after=_seg(pts[pts.index >= onset]))
        else:
            row["algorithm"] = "first cycle longer than the early cycles by the minimum change"
        rows.append(row)
    return {"algorithm": using, "ruptures_available": baseline.rpt is not None, "rows": rows, "signals_not_run": int(not_run),
            "note": "The change-point search runs only for a signal whose change was detected. For every other signal it is not run, and that is not a finding of no change point."}


def _multi_signal(p: dict, cfg: dict) -> list[dict]:
    d = cfg["defaults"]
    out = []
    for sc in p.get("scenarios", []):
        if sc.get("status") == "not_applicable":
            continue
        sig = sc.get("signals", {})
        out.append({"area": sc["title"], "status": sc.get("status_text"), "surfaced": bool(sc.get("surfaced")), "pattern_signals": sc.get("pattern_signals", []), "n_signals": len(sc.get("pattern_signals", [])),
                    "changed_signals": sc.get("changed_signals", []), "pattern_start": sc.get("pattern_start"),
                    "onsets": {k: {"label": _label(p, k), "onset": sig[k].get("onset_date")} for k in sc.get("changed_signals", []) if k in sig},
                    "rule": f"at least {d['min_signals']} signals, including a core signal, starting to change within {d['co_occurrence_days']} days of each other",
                    "context": sc.get("context", []), "evidence": sc.get("evidence", []), "limitations": sc.get("limitations")})
    return out


def _reference(p: dict) -> dict:
    items = p.get("reference", {}).get("items", [])
    return {"counts": p.get("reference", {}).get("counts"), "items": [{k: i.get(k) for k in ("key", "label", "value_text", "unit", "reference_text", "category", "flag", "source", "as_of", "relation", "soft", "n")} for i in items]}


def _risk(p: dict) -> dict:
    """The three-area model: a class, the parameters behind it, evidence strength. No probability."""
    try:
        from prana.risk import service as risk_service
        areas = risk_service.brief(p.get("id", ""))
    except Exception:
        areas = []
    return {"available": bool(areas), "areas": areas, "calculation": "Gradient-boosted model per area with exact per-parameter contributions (TreeSHAP)",
            "validation": "No clinical validation. Trained on recorded diagnoses in synthetic practice data, not on outcomes, and these are estimates for groups of people, not predictions for one person."}


def _forecast(p: dict) -> dict:
    fc = p.get("outlook", {}).get("forecast") or {}
    charts = []
    for it in fc.get("items", []):
        S = p.get("series", {}).get(it["key"])
        if not S or not it.get("projection"):
            continue
        weekly = _series(S).resample("W").mean().dropna().iloc[-int(it.get("weeks_used") or 16):]
        charts.append({"key": it["key"], "label": it["label"], "unit": it["unit"], "weekly": [[str(i.date()), _f(v, 2)] for i, v in weekly.items()], "projection": it["projection"], "as_of": fc.get("as_of")})
    return {"method": fc.get("method"), "as_of": fc.get("as_of"), "items": fc.get("items", []), "steady": fc.get("steady", []), "charts": charts,
            "gate": "A projection is shown only if the trend is very strong (Mann-Kendall p below 0.001) and the 90-day change is at least half the minimum meaningful change (src/prana/ai/forecast.py).",
            "labs_not_projected": (fc.get("evidence") or {}).get("labs_not_projected")}


def _missing(p: dict) -> dict:
    per_series = []
    for key, S in p.get("series", {}).items():
        n, have = len(S["v"]), sum(1 for v in S["v"] if v is not None)
        per_series.append({"key": key, "label": S["label"], "unit": S["unit"], "group": S["group"], "days": n, "with_reading": have, "share": _f(have / n, 3) if n else None})
    rules = [{"area": sc["title"], "item": m.get("item"), "reason": m.get("reason")} for sc in p.get("scenarios", []) if sc.get("status") != "not_applicable" for m in sc.get("missing_data", [])]
    q = p.get("quality", {})
    return {"rules_triggered": rules, "series": per_series, "blank_cells": {"vitals": q.get("vitals_blank_cells"), "wearable": q.get("wearable_blank_cells")},
            "limitations": [sc.get("limitations") for sc in p.get("scenarios", []) if sc.get("limitations")][:3],
            "note": "A blank reading is a missing measurement. It is never counted as zero and never treated as normal."}


# ---------------------------------------------------------------- the page
def build_analytics(p: dict, built_at: str | None = None) -> dict:
    cfg = scenarios_config()
    base, trend, cps = _baseline(p, cfg), _trend(p, cfg), _change_points(p, cfg)
    multi, ref, risk, fc, miss = _multi_signal(p, cfg), _reference(p), _risk(p), _forecast(p), _missing(p)
    analysed = [r for r in base if r["status"] not in (None, "insufficient_data")]
    shares = [s["share"] for s in miss["series"] if s["share"] is not None]
    watch = p.get("outlook", {}).get("watch", {}).get("items", [])
    overview = {"signals_in_scope": len(base), "signals_analysed": len(analysed), "signals_insufficient_data": len(base) - len(analysed),
                "signals_changed": sum(1 for r in base if r["status"] == "changed"), "patterns_detected": sum(1 for m in multi if m["surfaced"]),
                "reference_outside": (ref["counts"] or {}).get("outside"), "reference_watch": (ref["counts"] or {}).get("watch"), "reference_within": (ref["counts"] or {}).get("within"),
                "missing_items": len(miss["rules_triggered"]), "data_completeness": _f(sum(shares) / len(shares), 3) if shares else None,
                "risk_available": risk["available"],
                "forecasts_available": len(fc["charts"]), "forecasts_considered": len(fc["items"]) + len(fc["steady"]), "watch_items": len(watch),
                "record_from": (p.get("window") or [None, None])[0], "record_to": (p.get("window") or [None, None])[1], "analysis_built_at": built_at}
    effect = [{"key": r["key"], "label": r["label"], "area": r["area"], "effect_size": r["effect_size"], "status": r["status"]} for r in base if r["effect_size"] is not None]
    return {"overview": overview, "thresholds": cfg["defaults"], "baseline": base, "trend": trend, "change_points": cps, "multi_signal": multi, "reference": ref, "risk": risk,
            "forecast": fc, "missing": miss, "charts": {"effect_sizes": effect, "completeness": miss["series"], "forecast": fc["charts"], "effect_threshold": cfg["defaults"]["min_effect_size"]},
            "correlation": {"available": False, "note": "Pearson and Spearman correlation are not part of this analysis, so none is shown. Signals that change around the same time are a co-occurrence, not a correlation."}}


# ---------------------------------------------------------------- architecture, with a runtime state for every part
def _exists(*files: str) -> bool:
    return all((ROOT / f).is_file() for f in files)


def models_status() -> dict:
    from prana.ai import knowledge, llm, medgemma, model_router
    r = model_router.routes()
    kb = knowledge.stats()
    return {"routes": {"general": r["general"], "medical": r["medical"]}, "nemotron": {"enabled": llm.enabled(), "model": (llm.status().split(":", 1) + [""])[1] if llm.enabled() else None},
            "medgemma": medgemma.status(), "comparison_enabled": r["comparison_enabled"], "knowledge": {"sources": len(kb["sources"]), "passages": kb["passages"], "mode": kb["mode"]}}


def architecture(models: dict | None = None) -> dict:
    m = models or models_status()
    mg, kb = m["medgemma"], m["knowledge"]
    nodes = [
        {"id": "data", "name": "Patient data layer", "layer": 1, "responsibility": "Reads each patient's Excel workbook (11 sheets) into one record and one timeline.",
         "files": ["src/prana/data/loader.py", "src/prana/data/timeline.py", "src/prana/data/profiling.py"], "input": "Patient workbooks (.xlsx)", "output": "A patient record and a long-format timeline", "to": ["processing"],
         "state": "in use"},
        {"id": "processing", "name": "Data processing layer", "layer": 2, "responsibility": "Cleans and stores the data in PostgreSQL and builds the package the portal draws from.",
         "files": ["src/prana/data/db.py", "src/prana/api/payload.py", "scripts/run_pipeline.py"], "input": "Record and timeline", "output": "Stored patient package (records table)", "to": ["stats"], "state": "in use"},
        {"id": "stats", "name": "Statistical analytics engine", "layer": 3, "responsibility": "Baselines, Mann-Kendall trends, change points, multi-signal patterns, reference ranges, risk scores and forecasts. Code only, no AI.",
         "files": ["src/prana/analysis/baseline.py", "src/prana/analysis/patterns.py", "src/prana/analysis/reference.py", "src/prana/ai/risk.py", "src/prana/ai/forecast.py", "src/prana/ai/outlook.py"],
         "input": "Patient package", "output": "Statistical results per signal, pattern and risk", "to": ["evidence"], "state": "in use"},
        {"id": "evidence", "name": "Evidence generation", "layer": 4, "responsibility": "Turns the results into evidence packs and compact facts. The only numbers an AI model may quote come from here.",
         "files": ["src/prana/insight/evidence.py", "src/prana/insight/context_linker.py", "src/prana/insight/missing_data.py", "src/prana/ai/facts.py"], "input": "Statistical results",
         "output": "Evidence packs and facts (about 2,500 tokens)", "to": ["router"], "state": "in use"},
        {"id": "router", "name": "AI model orchestration", "layer": 5, "responsibility": "Chooses which model answers which task. One model per request; both only in comparison mode. Failures are isolated and labelled.",
         "files": ["src/prana/ai/model_router.py", "src/prana/ai/llm.py", "src/prana/ai/medgemma.py"], "input": "A task and the facts", "output": "A labelled model result", "to": ["nemotron", "medgemma"],
         "state": f"in use. Comparison {'on' if m['comparison_enabled'] else 'off'}"},
        {"id": "nemotron", "name": "NVIDIA Nemotron", "layer": 6, "branch": "left", "responsibility": "The general model: the portal's written text and chat, from the facts.",
         "files": ["src/prana/ai/llm.py", "src/prana/ai/narrative.py", "src/prana/ai/ai_chat.py"], "input": "Facts", "output": "Checked text, stored per patient", "to": ["knowledge"],
         "state": f"on ({m['nemotron']['model']})" if m["nemotron"]["enabled"] else "off"},
        {"id": "medgemma", "name": "Google MedGemma", "layer": 6, "branch": "right", "responsibility": "The medical model: medical-context explanations of the analytical evidence, as validated structured output.",
         "files": ["src/prana/ai/medgemma.py", "src/prana/ai/medical_explain.py", "src/prana/ai/schemas.py"], "input": "Facts, approved references", "output": "A validated assessment", "to": ["knowledge"],
         "state": "on" if mg["configured"] else ("switched on but not set up" if mg["enabled"] else "off (no endpoint connected yet)")},
        {"id": "knowledge", "name": "Medical knowledge retrieval", "layer": 7, "responsibility": "Approved documents only, stored with source, date, version and licence. Supplies references the AI may cite.",
         "files": ["src/prana/ai/knowledge.py", "config/knowledge_sources.yaml"], "input": "A query of measure names (no numbers)", "output": "Passages and citable references", "to": ["safety"],
         "state": f"built, {kb['passages']} passages ({kb['sources']} sources)" if kb["passages"] else "built, empty: no approved documents added yet"},
        {"id": "safety", "name": "Safety and validation", "layer": 8, "responsibility": "Fixed emergency, medicine and diagnosis replies; every number checked against the facts; unsafe wording rejected; urgency owned by code.",
         "files": ["src/prana/ai/chat.py", "src/prana/ai/medical_explain.py", "src/prana/ai/facts.py", "src/prana/ai/recommend.py"], "input": "Model output", "output": "An accepted answer or a safe error", "to": ["dashboard"], "state": "in use"},
        {"id": "dashboard", "name": "Analytics & Intelligence dashboard", "layer": 9, "responsibility": "This page: the statistics, both models' results, the comparison and the report.",
         "files": ["src/prana/api/analytics.py", "src/prana/api/analytics_routes.py", "web/js/analytics.js", "web/css/analytics.css"], "input": "Statistics, checked model output", "output": "What you are reading", "to": [], "state": "in use"}]
    for n in nodes:
        n["files_found"] = {f: _exists(f) for f in n["files"]}
        n["implemented"] = all(n["files_found"].values())
    return {"nodes": nodes, "note": "Every part listed here exists in the project. Its state is read from the running system, so a part that is built but switched off says so."}


# ---------------------------------------------------------------- the consolidated report
def _tag(kind: str, text: str, **kw) -> dict:
    return {"kind": kind, "text": text, **kw}


def build_report(stats: dict, nemotron: dict | None, medgemma: dict | None, recommendations: dict | None) -> dict:
    o, sections = stats["overview"], []
    ai_n = nemotron if nemotron and nemotron.get("status") == "ok" else None
    ai_m = (medgemma or {}).get("assessment") if medgemma and medgemma.get("status") == "ok" else None

    def add(title, items):
        sections.append({"title": title, "items": items})

    add("Overall analytical summary", [_tag("statistical", f"{o['signals_analysed']} of {o['signals_in_scope']} signals had enough data to analyse; {o['signals_changed']} changed against the patient's own baseline; "
                                           f"{o['patterns_detected']} multi-signal pattern(s) detected; {o['reference_outside']} result(s) outside and {o['reference_watch']} near the edge of their reference range.")]
        + ([_tag("ai", ai_n["headline"], model=ai_n.get("model_name"))] if ai_n and ai_n.get("headline") else []))
    add("Statistical findings", [_tag("statistical", f"{r['label']}: {r['baseline_mean']} to {r['recent_mean']} {r['unit'] or ''} (change {r['change']}, effect size {r['effect_size']}).".replace("  ", " ")) for r in stats["baseline"] if r["status"] == "changed"]
        or [_tag("statistical", "No signal met the rule for a change against the patient's own baseline.")])
    add("Important trends", [_tag("statistical", f"{t['label']}: {t['trend']} (Mann-Kendall p {t['p_value']}, {t['slope_per_month']} per month).") for t in stats["trend"] if t["trend"] and t["trend"] != "no significant trend"]
        or [_tag("statistical", "No signal shows a statistically significant trend on weekly means.")])
    add("Detected patterns", [_tag("statistical", f"{m['area']}: {', '.join(m['pattern_signals'])}, starting {m['pattern_start']}.") for m in stats["multi_signal"] if m["surfaced"]]
        or [_tag("statistical", "No multi-signal pattern was detected.")])
    rk = stats["risk"]
    add("Risk classes", ([_tag("statistical", f"{x['area']}: {x['class']} (evidence {x['evidence_strength'].lower()}).") for x in rk["areas"]] or [_tag("statistical", "No risk class is available for this record.")]) + [_tag("statistical", rk["validation"])])
    add("Forecasts", [_tag("statistical", f"{c['label']}: about {c['projection'][-1]['value']} {c['unit']} in {c['projection'][-1]['days']} days (probably {c['projection'][-1]['low']} to {c['projection'][-1]['high']}), if the trend continues.") for c in stats["forecast"]["charts"]]
        or [_tag("statistical", "No signal passed the strict rule for a projection.")])
    add("Medical-context interpretation", [_tag("ai", t, model=(medgemma or {}).get("model", {}).get("model_name")) for t in ai_m["medical_interpretations"]] if ai_m else
        [_tag("unavailable", (medgemma or {}).get("message") or "The MedGemma explanation has not been generated for this record.")])
    add("Supporting evidence", [_tag("ai", t) for t in ai_m["supporting_evidence"]] if ai_m else [_tag("unavailable", "Not available until the MedGemma explanation exists.")])
    add("Missing information", [_tag("statistical", f"{m['item']}: {m['reason']}") for m in stats["missing"]["rules_triggered"]] + ([_tag("ai", t) for t in ai_m["missing_information"]] if ai_m else [])
        or [_tag("statistical", "The analysis found nothing important missing for the areas it checks.")])
    steps = [_tag("rule_based", f"{i.get('title')}: {i.get('why')}") for g in (recommendations or {}).get("groups", []) for i in g.get("items", [])]
    add("Recommended next steps", steps + ([_tag("ai", t) for t in ai_m["recommended_next_steps"]] if ai_m else []) or [_tag("unavailable", "No suggestions are available for this record.")])
    refs = (medgemma or {}).get("references") or []
    add("Medical references", [_tag("ai", f"{r['title']} ({r['source']}, {r['published']})", url=r.get("url"), use=r.get("use")) for r in refs]
        or [_tag("unavailable", "No approved reference was cited. The knowledge base may be empty or nothing fit.")])
    add("Limitations", [_tag("fixed", "This portal describes the patient's own data. It does not diagnose and does not advise on medicines."),
                        _tag("fixed", "No part of this report has been clinically validated. Clinician review, privacy approval and a regulatory assessment are separate steps still to do.")]
        + ([_tag("ai", t) for t in ai_m["limitations"] + ai_m["uncertainty"]] if ai_m else []))
    return {"sections": sections, "legend": {"statistical": "Calculated by code from the record", "rule_based": "Written by the portal's fixed rules", "ai": "Written by an AI model and checked", "fixed": "Fixed text",
                                              "unavailable": "Not available yet", "clinically_validated": "None of this report is clinically validated"},
            "models": {"nemotron": bool(ai_n), "medgemma": bool(ai_m)}}
