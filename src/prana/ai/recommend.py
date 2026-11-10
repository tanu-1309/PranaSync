"""Recommendations built from the patient's own analysed data (owner: Uday).

Each recommendation is produced by a rule that looks at the analysis (patterns, reference results, forecasts, missing data,
adherence) and fills a template from config/recommendations.yaml with numbers taken from the record. There is no free
text generation here, so nothing can be invented. Every item says why (the evidence), what to ask, and where to see it.

Groups:  raise (worth raising with the care team) / watch / data (what would help) / habits (general public-health guidance).
Never:   a diagnosis, a medicine instruction, a dose change. The banned phrases in the YAML are tested on every patient.
"""
from __future__ import annotations

import re

import pandas as pd

from prana.config import load_yaml

AREA = {"t2d": "metabolic health", "htn": "cardiovascular", "pcos": "women’s health"}
CROSS_SEVERE = ("Well above", "Above the lab")
trim = lambda s: re.sub(r"\s*\(.*\)$", "", str(s))  # noqa: E731


def _fmt(v, nd=1) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "n/a"
    return f"{v:,.0f}" if abs(v) >= 1000 else f"{round(float(v), nd):g}"


def _sentence(s: str) -> str:
    s = s.strip()
    return (s[:1].upper() + s[1:] + ("" if s.endswith(".") else ".")) if s else s


def _item(rule_id, group, priority, title, why, ask=None, source=None, link="#/", keys=()):
    return {"id": rule_id, "group": group, "priority": priority, "title": title, "why": why, "ask": ask, "source": source, "link": link, "keys": list(keys)}


def _pattern_items(result, rules) -> tuple[list[dict], set]:
    out, covered = [], set()
    for sc in result["scenarios"]:
        if not sc.get("surfaced"):
            continue
        moved = []
        for e in sc["evidence"][:4]:
            covered.add(e["signal"])
            a, b = (e.get("first"), e.get("last")) if e["kind"] == "lab" else (e.get("baseline_mean"), e.get("recent_mean"))
            moved.append(f"{trim(e['label'])} {_fmt(a, 2)} to {_fmt(b, 2)}")
        r = rules["pattern"]
        why = [r["why"].format(n=len(sc["pattern_signals"]), date=sc.get("pattern_start") or "this year", moved="; ".join(moved))]
        ctx = next((c for c in sc["context"] if c["type"] != "symptoms" and "during" not in (c.get("timing") or "")), None)
        if ctx and sc["status"] == "pattern_with_context":
            why.append(r["context"].format(context=ctx["text"] + (f" ({ctx['date']})" if ctx.get("date") else "")))
        out.append(_item("pattern_" + sc["scenario"], "raise", 1, r["title"].format(area=AREA.get(sc["scenario"], sc["title"])), why, r["ask"], keys=sc["pattern_signals"]))
    return out, covered


def _reference_items(result, rules, covered) -> list[dict]:
    out = []
    for it in result["reference"]["items"]:
        if it["soft"] or it["key"] in covered or it["flag"] == "within":
            continue
        fields = dict(label=trim(it["label"]), value=it["value_text"], unit=it["unit"], reference=it["reference_text"])
        if it["relation"] == "changed_outside":
            r = rules["changed_outside"]
            out.append(_item("changed_" + it["key"], "raise", 1, r["title"].format(**fields), [r["why"].format(**fields)], r["ask"], it["source"], keys=[it["key"]]))
        elif it["relation"] == "steady_outside":
            r = rules["steady_outside"]
            group, pr = ("raise", 2) if it["flag"] == "outside" else ("watch", 2)
            out.append(_item("steady_" + it["key"], group, pr, r["title"].format(**fields), [r["why"].format(**fields)], r["ask"], it["source"], keys=[it["key"]]))
    return out


def _forecast_items(forecasts, rules) -> list[dict]:
    out = []
    for f in forecasts["items"]:
        horizon = 90
        p = next(x for x in f["projection"] if x["days"] == horizon)
        fields = dict(label=trim(f["label"]), unit=f["unit"], now=_fmt(f["now"], 1), trend="rising" if f["trend"] == "rising" else "falling",
                      slope=_fmt(abs(f["slope_per_week"]), 2), value=_fmt(p["value"], 1), horizon=horizon, low=_fmt(p["low"], 1), high=_fmt(p["high"], 1))
        c = f.get("crosses")
        if c and c["in_days"] <= 120:
            r = rules["forecast_cross"]
            severe = any(c["into"].startswith(s) for s in CROSS_SEVERE)
            out.append(_item("cross_" + f["key"], "raise" if severe else "watch", 2, r["title"].format(into=c["into"].lower(), days=c["in_days"], **fields),
                             [r["why"].format(**fields)], r["ask"], link="#/outlook", keys=[f["key"]]))
        else:
            r = rules["forecast_trend"]
            out.append(_item("trend_" + f["key"], "watch", 3, r["title"].format(**fields), [r["why"].format(**fields)], r["ask"], link="#/outlook", keys=[f["key"]]))
    return out


def _missing_items(result, rules) -> list[dict]:
    seen, out = set(), []
    for sc in result["scenarios"]:
        for m in sc.get("missing_data", []):
            if m["key"] in seen:
                continue
            seen.add(m["key"])
            r = rules["missing"]
            out.append(_item("missing_" + m["key"], "data", 2 if sc.get("surfaced") else 3, r["title"].format(item=m["item"]), [_sentence(r["why"].format(reason=m["reason"]))], link="#/help", keys=[m["key"]]))
    return out


def _adherence_items(rec, rules) -> list[dict]:
    ad, meds = rec.get("adherence"), rec.get("medications")
    if ad is None or ad.empty or meds is None or meds.empty:
        return []
    names = meds.sort_values("start_date").groupby("med_id")["medication"].last()
    out = []
    for med_id, g in ad.groupby("med_id"):
        pct = float(g["adherence_pct"].mean())
        if pct >= 80 or med_id not in names:
            continue
        words = "many missed doses" if pct < 60 else "some missed doses"
        r = rules["adherence_low"]
        name = str(names[med_id]).split(" ")[0]
        out.append(_item("adherence_" + str(med_id), "raise" if pct < 60 else "watch", 2, r["title"].format(pct=round(pct), med=name),
                         [r["why"].format(n=len(g), pct=round(pct), words=words)], r["ask"], link="#/medications", keys=[str(med_id)]))
    return out


def _habit_items(result, rules) -> list[dict]:
    out = []
    by = {it["key"]: it for it in result["reference"]["items"]}
    for key, rule in (("steps", "steps_low"), ("active_minutes", "activity_low"), ("sleep_hours", "sleep_off")):
        it = by.get(key)
        if it and it["flag"] != "within":
            r = rules[rule]
            out.append(_item(rule, "habits", 3, r["title"], [r["why"].format(value=it["value_text"])], r["ask"], r.get("source"), link="#/timeline", keys=[key]))
    return out


def _home_bp(result, rules) -> list[dict]:
    bp = next((it for it in result["reference"]["items"] if it["key"] == "bp"), None)
    if not bp or bp["flag"] == "within":
        return []
    r = rules["home_bp"]
    return [_item("home_bp", "data", 2, r["title"], [r["why"].format(value=bp["value_text"], category=bp["category"].lower())], r["ask"], r["source"], link="#/timeline", keys=["sbp", "dbp"])]


def build_recommendations(result: dict, forecasts: dict, rec) -> dict:
    cfg = load_yaml("recommendations.yaml")
    rules = cfg["rules"]
    patterns, covered = _pattern_items(result, rules)
    items = patterns + _reference_items(result, rules, covered) + _forecast_items(forecasts, rules) + _missing_items(result, rules) \
        + _adherence_items(rec, rules) + _home_bp(result, rules) + _habit_items(result, rules)
    groups = []
    for gid, title in cfg["groups"].items():
        mine = sorted((i for i in items if i["group"] == gid), key=lambda i: (i["priority"], i["title"]))[: cfg["limits"][gid]]
        if mine:
            groups.append({"id": gid, "title": title, "items": mine})
    n = {g["id"]: len(g["items"]) for g in groups}
    if n.get("raise"):
        summary = f"{n['raise']} thing{'s' if n['raise'] > 1 else ''} worth raising with your care team"
        summary += f", {n['watch']} to keep an eye on" if n.get("watch") else ""
        summary += f" and {n['data']} piece{'s' if n['data'] > 1 else ''} of information that would help." if n.get("data") else "."
    elif n.get("watch") or n.get("data"):
        summary = "Nothing needs raising urgently. A few things are worth keeping an eye on, and some information would sharpen the picture."
    else:
        summary = "Nothing needs raising right now. Keep tracking so we can keep watching for changes."
    return {"summary": summary, "groups": groups, "disclaimer": cfg["disclaimer"],
            "method": "Each suggestion comes from a rule applied to your own data and a fixed wording template. Nothing is written freely, so nothing is invented."}


def banned_hits(text: str) -> list[str]:
    low = text.lower()
    return [b for b in load_yaml("recommendations.yaml")["banned_phrases"] if b in low]
