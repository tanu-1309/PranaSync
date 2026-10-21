"""Context linker (owner: Uday).

Pulls out what is ALREADY KNOWN about the person that relates to a scenario:
past findings in Medical History / clinical notes, related medications,
family history, related symptoms, and earlier lab values above the
scenario's lab flag (e.g. HbA1c >= 5.7). Each item records whether it came
BEFORE the detected pattern (prior context) or DURING it.
"""
from __future__ import annotations

import pandas as pd

from prana.data.loader import PatientRecord


def _match(text: str, keywords: list[str]) -> str | None:
    t = str(text).lower()
    return next((k for k in keywords if k in t), None)


def _when(date, pattern_start) -> str:
    if pattern_start is None or pd.isna(date):
        return "on record"
    return "before pattern" if pd.Timestamp(date) < pd.Timestamp(pattern_start) else "during pattern"


def link_context(rec: PatientRecord, scfg: dict, pattern_start: str | None) -> list[dict]:
    ctx = scfg.get("context", {})
    items: list[dict] = []

    hist = rec.get("history")
    for _, r in hist.iterrows():
        text = f"{r.get('finding', '')} {r.get('notes', '')}"
        k = _match(text, ctx.get("history_keywords", []))
        if k:
            items.append({"type": "history", "date": _d(r.get("date")), "text": str(r.get("finding")),
                          "detail": f"status: {r.get('status', 'n/a')}", "timing": _when(r.get("date"), pattern_start)})

    notes = rec.get("notes")
    for _, r in notes.iterrows():
        if _match(r.get("note", ""), ctx.get("history_keywords", [])):
            items.append({"type": "clinical_note", "date": _d(r.get("date")), "text": str(r.get("note")),
                          "detail": str(r.get("encounter", "")), "timing": _when(r.get("date"), pattern_start)})

    meds = rec.get("medications")
    for _, r in meds.iterrows():
        if _match(f"{r.get('medication', '')} {r.get('indication', '')}", ctx.get("medication_keywords", [])):
            items.append({"type": "medication", "date": _d(r.get("start_date")), "text": f"{r.get('medication')} {r.get('dose', '')}".strip(),
                          "detail": f"{r.get('indication', '')}; {r.get('status', '')}", "timing": _when(r.get("start_date"), pattern_start)})

    fam = rec.profile.get("Family History", "")
    if _match(fam, ctx.get("family_keywords", [])):
        items.append({"type": "family_history", "date": None, "text": str(fam), "detail": "", "timing": "on record"})

    labs = rec.get("labs")
    for lab, threshold in ctx.get("lab_flags", {}).items():
        sub = labs[labs["test_key"] == lab] if not labs.empty else labs
        high = sub[sub["value"] >= threshold] if not sub.empty else sub
        if not high.empty:
            r = high.iloc[0]
            items.append({"type": "lab", "date": _d(r["date"]), "text": f"{r['test']} {r['value']:g} {_unit(r.get('unit'))}".strip(),
                          "detail": f"at or above {threshold:g} (reference {r.get('ref_range', 'n/a')})",
                          "timing": _when(r["date"], pattern_start)})

    sym = rec.get("symptoms")
    related = sym[sym["symptom"].astype(str).str.lower().apply(lambda t: _match(t, ctx.get("symptom_keywords", [])) is not None)] if not sym.empty else sym
    if not related.empty:
        items.append({"type": "symptoms", "date": _d(related["date"].min()),
                      "text": ", ".join(sorted(related["symptom"].astype(str).unique())),
                      "detail": f"{len(related)} entries in Symptoms Timeline", "timing": _when(related["date"].min(), pattern_start)})
    return items


def has_prior_finding(items: list[dict]) -> bool:
    """True when the record held a related finding BEFORE the pattern started
    (symptoms and lab values that only crossed a threshold during the pattern
    are part of the pattern, not prior context)."""
    return any(i["type"] in ("history", "family_history") or
               (i["type"] in ("clinical_note", "medication", "lab") and i["timing"] != "during pattern")
               for i in items)


def _d(v):
    return None if v is None or pd.isna(v) else str(pd.Timestamp(v).date())


def _unit(u) -> str:
    return "" if u is None or str(u).lower() in ("ratio", "nan", "none") else str(u)
