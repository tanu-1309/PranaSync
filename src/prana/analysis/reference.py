"""Reference-value layer: where does the recent level sit against general reference ranges?

Change detection (baseline.py, patterns.py) only compares a person with their own first 60 days. This module
adds the other question without touching those rules: a level that is steady for the person can still be outside
the usual range, and a level that moved can still be well inside it. Both facts are reported side by side.

Non-diagnostic by design: bands are worded "typical / above typical / well above typical", never as conditions.
Values and sources live in config/reference_ranges.yaml so a clinician can review and change them.
"""
from __future__ import annotations

import re

import pandas as pd

from prana.config import load_yaml
from prana.data.loader import PatientRecord
from prana.data.timeline import daily_series
from prana.insight.evidence import LABELS

RECENT = 30          # days averaged for "recent level", matching the 30-day line on the charts
MIN_RECENT = 10      # readings needed in those days
FLAG_RANK = {"within": 0, "watch": 1, "outside": 2}


def reference_config() -> dict:
    return load_yaml("reference_ranges.yaml")


def band_for(value: float, bands: list[dict]) -> dict:
    for b in bands:
        lo, hi = b.get("lo"), b.get("hi")
        if (lo is None or value >= lo) and (hi is None or value < hi):
            return b
    return bands[-1]


def parse_ref_range(text) -> tuple[float | None, float | None] | None:
    """Parse a lab report's own range: '4.0–5.6', '<5.7', '>40'. Returns (low, high) or None."""
    r = str(text or "").replace(",", "")
    m = re.search(r"(-?\d+(?:\.\d+)?)\s*[–-]\s*(-?\d+(?:\.\d+)?)", r)
    if m:
        return float(m.group(1)), float(m.group(2))
    m = re.match(r"^\s*[<≤]\s*(\d+(?:\.\d+)?)", r)
    if m:
        return None, float(m.group(1))
    m = re.match(r"^\s*[>≥]\s*(\d+(?:\.\d+)?)", r)
    if m:
        return float(m.group(1)), None
    return None


def bp_category(sbp: float, dbp: float) -> dict:
    """ACC/AHA 2017 categories, worded neutrally. The higher of the two readings decides."""
    if sbp >= 140 or dbp >= 90:
        return {"flag": "outside", "label": "Well above typical"}
    if sbp >= 130 or dbp >= 80:
        return {"flag": "watch", "label": "Above typical"}
    if sbp >= 120:
        return {"flag": "watch", "label": "Slightly above typical"}
    if sbp < 90 or dbp < 60:
        return {"flag": "watch", "label": "Below typical"}
    return {"flag": "within", "label": "Typical"}


def _changed_status(scenarios: list[dict], keys: list[str]) -> str | None:
    """'changed' if any scenario found the signal changed; else improving / stable / None (never assessed)."""
    seen = []
    for sc in scenarios:
        for k in keys:
            a = sc.get("signals", {}).get(k)
            if a and a.get("status") not in (None, "insufficient_data"):
                seen.append(a["status"])
    if not seen:
        return None
    for want in ("changed", "improving"):
        if want in seen:
            return want
    return "stable"


def _relation(flag: str, change: str | None) -> str:
    outside = flag in ("watch", "outside")
    if change == "changed":
        return "changed_outside" if outside else "changed_within"
    return "steady_outside" if outside else "within"


def _recent(rec: PatientRecord, sig: str) -> tuple[float | None, int]:
    s = daily_series(rec, sig)
    if s.empty:
        return None, 0
    r = s.iloc[-RECENT:].dropna()
    return (float(r.mean()), len(r)) if len(r) >= MIN_RECENT else (None, len(r))


def _daily_item(key: str, cfg: dict, rec: PatientRecord, scenarios: list[dict]) -> dict | None:
    if key == "bp":
        sbp, n1 = _recent(rec, "sbp")
        dbp, n2 = _recent(rec, "dbp")
        if sbp is None or dbp is None:
            return None
        cat = bp_category(sbp, dbp)
        change = _changed_status(scenarios, ["sbp", "dbp"])
        base = {"sbp": [90, 120], "dbp": [60, 80]}
        return {"key": key, "label": cfg["label"], "kind": "daily", "unit": cfg["unit"], "value": round(sbp, 1),
                "value_text": f"{sbp:.0f}/{dbp:.0f}", "as_of": f"last {RECENT} days", "n": min(n1, n2),
                "category": cat["label"], "flag": cat["flag"], "reference_text": cfg["reference_text"],
                "source": cfg["source"], "note": cfg.get("note"), "soft": False, "change": change,
                "relation": _relation(cat["flag"], change), "panel_ranges": base}
    val, n = _recent(rec, key)
    if val is None:
        return None
    band = band_for(val, cfg["bands"])
    flag = band["flag"]
    if cfg.get("soft") and flag == "outside":
        flag = "watch"
    change = _changed_status(scenarios, [key])
    within = [b for b in cfg["bands"] if b["flag"] == "within"]
    lo = min((b["lo"] for b in within if b.get("lo") is not None), default=None)
    hi = max((b["hi"] for b in within if b.get("hi") is not None), default=None)
    return {"key": key, "label": cfg["label"], "kind": "daily", "unit": cfg["unit"], "value": round(val, 1),
            "value_text": f"{val:,.0f}" if val >= 100 else f"{val:.1f}", "as_of": f"last {RECENT} days", "n": n,
            "category": band["label"], "flag": flag, "reference_text": cfg["reference_text"], "source": cfg["source"],
            "note": cfg.get("note"), "soft": bool(cfg.get("soft")), "change": change,
            "relation": _relation(flag, change), "panel_ranges": {key: [lo, hi]}}


def _lab_item(key: str, cfg: dict | None, rec: PatientRecord, scenarios: list[dict]) -> dict | None:
    labs = rec.get("labs")
    if labs.empty:
        return None
    d = labs[labs.test_key == key].dropna(subset=["value"]).sort_values("date")
    if d.empty:
        return None
    last = d.iloc[-1]
    value, unit = float(last["value"]), str(last.get("unit", ""))
    own = parse_ref_range(last.get("ref_range"))
    flag, label, ref_text, source = "within", "Typical", None, None
    if own:  # the lab's own printed range is the primary reference
        lo, hi = own
        low_bad, high_bad = lo is not None and value < lo, hi is not None and value > hi
        if low_bad or high_bad:
            flag, label = "watch", ("Below the lab’s range" if low_bad else "Above the lab’s range")
        else:
            label = "Within the lab’s range"
        ref_text, source = f"Lab’s range: {last.get('ref_range')} {unit}".strip(), "Reference range printed on the lab report"
    guide = None
    if cfg:
        if "by_sex" in cfg:
            guide = cfg["by_sex"].get("female" if rec.sex.startswith("f") else "male")
            guide_src = cfg["source"]
        else:
            guide, guide_src = cfg, cfg["source"]
        if guide and cfg.get("unit") and unit.replace(" ", "").lower() != cfg["unit"].replace(" ", "").lower():
            guide = None  # different unit: don't apply guideline numbers
    if guide:
        band = band_for(value, guide["bands"])
        if FLAG_RANK[band["flag"]] >= FLAG_RANK[flag]:
            flag, label = band["flag"], band["label"]
        ref_text = guide["reference_text"] + (f" · {ref_text}" if ref_text and own else "")
        source = f"{guide_src}" + ("; and the lab’s printed range" if own else "")
    if ref_text is None:
        return None
    change = _changed_status(scenarios, [key])
    return {"key": key, "label": LABELS.get(key, str(last.get("test", key))), "kind": "lab", "unit": unit, "value": round(value, 2),
            "value_text": f"{value:g}", "as_of": f"result of {pd.Timestamp(last['date']).strftime('%d %b %Y').lstrip('0')}",
            "n": len(d), "category": label, "flag": flag, "reference_text": ref_text, "source": source, "note": None,
            "soft": False, "change": change, "relation": _relation(flag, change), "panel_ranges": {}}


def _cycle_item(cfg: dict, rec: PatientRecord, scenarios: list[dict]) -> dict | None:
    w = rec.get("women")
    if w.empty or "cycle_length" not in w:
        return None
    s = w.sort_values("date")["cycle_length"].dropna()
    if len(s) < 3:
        return None
    val = float(s.iloc[-3:].mean())
    flag = "within" if cfg["lo"] <= val <= cfg["hi"] else "outside"
    label = "Typical" if flag == "within" else ("Longer than the usual range" if val > cfg["hi"] else "Shorter than the usual range")
    change = _changed_status(scenarios, ["cycle_length"])
    return {"key": "cycle_length", "label": cfg["label"], "kind": "cycle", "unit": cfg["unit"], "value": round(val, 1),
            "value_text": f"{val:.0f}", "as_of": "last 3 cycles", "n": len(s), "category": label, "flag": flag,
            "reference_text": cfg["reference_text"], "source": cfg["source"], "note": cfg.get("note"), "soft": False,
            "change": change, "relation": _relation(flag, change), "panel_ranges": {}}


def assess_reference(rec: PatientRecord, scenarios: list[dict]) -> dict:
    cfg = reference_config()
    items = []
    for key, c in cfg["daily"].items():
        it = _daily_item(key, c, rec, scenarios)
        if it:
            items.append(it)
    if rec.sex.startswith("f"):
        it = _cycle_item(cfg["cycle"], rec, scenarios)
        if it:
            items.append(it)
    labs = rec.get("labs")
    if not labs.empty:
        keys = list(cfg["labs"]) + [k for k in labs.test_key.dropna().unique() if k not in cfg["labs"]]
        for key in keys:
            it = _lab_item(key, cfg["labs"].get(key), rec, scenarios)
            if it:
                items.append(it)
    counts = {"within": 0, "watch": 0, "outside": 0}
    for it in items:
        counts[it["flag"]] += 1
    return {"items": items, "counts": counts, "personal_only": cfg["personal_only"],
            "steady_outside": [it["key"] for it in items if it["relation"] == "steady_outside" and not it["soft"]]}
