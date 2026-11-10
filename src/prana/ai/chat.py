"""Chatbot that answers questions about ONE patient's own record (owner: Uday).

How it stays safe and truthful
  1. Safety first. Possible emergencies, medicine/dose questions and requests for a diagnosis never reach the analysis:
     they get a fixed, careful reply that points to emergency services or the care team.
  2. Grounded. Every answer is assembled from the patient's own package (reference results, patterns, medicines,
     forecasts, recommendations). The numbers in an answer are the numbers in the record. Nothing is generated freely,
     so nothing can be invented. If a question is not understood, it says what it can answer instead of guessing.
  3. Private. It only ever sees the package of the signed-in patient; the server passes it in, never an ID from the user.
  4. Honest about limits. Answers are descriptions of the data. They never diagnose, advise on medicines or predict illness.

An optional language model (prana.ai.llm) can only reword an answer already built here, and is checked against it.
"""
from __future__ import annotations

import re

AREAS = {"t2d": "metabolic health", "htn": "cardiovascular health", "pcos": "women’s health"}
trim = lambda s: re.sub(r"\s*\(.*\)$", "", str(s))  # noqa: E731

EMERGENCY = re.compile(
    r"chest (pain|pressure|tightness)|can'?t breathe|cannot breathe|short(ness)? of breath|(difficulty|trouble) breathing|faint(ed|ing)|pass(ed|ing) out|unconscious|"
    r"seizure|(think i'?m having|might be having|i am having|i'?m having|is having) (a )?(stroke|heart attack)|face (is )?droop|slurred speech|suicid|kill myself|end my life|self[- ]?harm|overdos|severe (pain|bleeding)|bleeding (heavily|a lot)|"
    r"cough(ing)? (up )?blood|vomit(ing)? blood")
RISK = re.compile(r"(chance|chances|risk|likelihood|probability|odds|how likely).*(heart attack|stroke|heart disease|cardiovascular|cardiac|heart)|(heart attack|stroke|heart disease).*(chance|chances|risk|likely|odds)|heart risk|ascvd")
PRED_WORDS = re.compile(r"chance|chances|risk|likelihood|likely|probab|odds|will i\b|will my|decline|go up|go down|going up|going down|going to (get|develop)|prone|predict|develop|heading|worse")
CONDITIONS = [  # (key, pattern): what a predictive question can be about
    ("heart", r"heart attack|stroke|heart disease|cardiovascular|cardiac|\bheart\b|ascvd"),
    ("diabetes", r"diabet|blood sugar|prediabet|glycemic|\bsugar\b"),
    ("bp", r"blood pressure|hypertens|\bbp\b"),
    ("kidney", r"kidney|egfr|renal"),
    ("cholesterol", r"cholesterol|\bldl\b|lipid"),
    ("weight", r"\bweight\b|obes|\bbmi\b|overweight"),
]
OVERVIEW = re.compile(r"(what|which).*(risks?|conditions?).*(have|face|am i|my)|my (health )?risks?|any risks?|risk overview|am i at risk|health risks")
UNSUPPORTED = re.compile(r"cancer|tumou?r|dementia|alzheimer|covid|depress|anxiety|arthritis|asthma|copd|lung|liver|thyroid cancer|pregnan|fertil")
DIAGNOSIS = re.compile(
    r"do i have\b|am i (diabetic|prediabetic|hypertensive|pre-diabetic)|diagnose|what('s| is) wrong with me|have i got|will i (get|develop)|am i going to (get|develop)|"
    r"is it (cancer|diabetes)|how long (do|will) i have|do i suffer")
ADVICE_VERB = r"(stop|skip|quit|start|double|increase|decrease|reduce|lower|raise|change|switch|adjust|miss|take)"
MED_GENERIC = re.compile(rf"\b{ADVICE_VERB}\b.*\b(dose|dosage|medicine|medication|pill|tablet|meds?)\b|\b(dose|dosage)\b|how (much|many) .*\b(take|mg)\b")

MEASURES = [  # (pattern, reference/series keys it refers to)
    (r"blood pressure|\bbp\b|systolic|diastolic", ["bp"]),
    (r"hba1c|\ba1c\b|glycated|glycosylated", ["hba1c"]),
    (r"glucose|blood sugar|\bsugar\b", ["fasting_glucose"]),
    (r"\bldl\b", ["ldl_cholesterol"]), (r"\bhdl\b", ["hdl_cholesterol"]), (r"triglycerid", ["triglycerides"]),
    (r"cholesterol|lipid", ["ldl_cholesterol", "hdl_cholesterol", "total_cholesterol", "triglycerides"]),
    (r"\bweight\b|\bbmi\b|body mass|overweight|\bkg\b", ["weight_kg", "bmi"]),
    (r"\bsleep|\bslept|insomnia", ["sleep_hours"]),
    (r"\bsteps?\b|walking|step count", ["steps"]), (r"\bactivity\b|\bactive\b|exercise|workout", ["active_minutes", "steps"]),
    (r"resting heart rate|\bpulse\b|heart rate|\bhr\b", ["resting_hr"]), (r"oxygen|spo2|saturation", ["spo2"]),
    (r"\bhrv\b|variability", ["hrv_ms"]), (r"\btsh\b|thyroid", ["tsh"]), (r"vitamin d", ["vitamin_d"]), (r"egfr|kidney", ["egfr"]),
    (r"testosterone", ["testosterone"]), (r"\bcycles?\b|\bperiods?\b|menstrua", ["cycle_length"]),
]
AREA_WORDS = [("t2d", r"metabolic|diabet|glycemic|glycaemic"), ("htn", r"cardio|hypertens|heart health"), ("pcos", r"pcos|women|polycystic")]
SERIES_OF = {"bp": ["sbp", "dbp"]}
CHANGE = {"changed": "It has changed for you over the year.", "improving": "It has been improving for you.", "stable": "It has been steady for you.", None: "We do not track this one for change."}
NOT_DIAGNOSIS = "This describes your data. It is not a diagnosis."


def _fmt(v, nd=1) -> str:
    if v is None:
        return "n/a"
    return f"{v:,.0f}" if abs(v) >= 1000 else f"{round(float(v), nd):g}"


def _reply(intent, paras, sources=None, suggestions=None, keys=None):
    return {"intent": intent, "answer": paras, "sources": sources or [], "suggestions": suggestions or [], "state": {"last": {"intent": intent, "keys": keys or []}}}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s%./’'-]", " ", text.lower())).strip()


def measure_keys(text: str) -> list[str]:
    out = []
    for rx, keys in MEASURES:
        if re.search(rx, text):
            out += [k for k in keys if k not in out]
    return out


def _med_words(p: dict) -> set[str]:
    return {m["name"].split(" ")[0].lower() for m in p.get("meds", []) if m.get("name")}


# ----------------------------------------------------------------------------- safety
def triage(text: str, p: dict) -> str | None:
    if EMERGENCY.search(text):
        return "emergency"
    meds = "|".join(re.escape(m) for m in sorted(_med_words(p)))
    if MED_GENERIC.search(text) or (meds and re.search(rf"\b{ADVICE_VERB}\b.*\b({meds})\b|\b({meds})\b.*\b{ADVICE_VERB}\b.*\b(dose|more|less|today|tonight)\b|\b({meds})\b.*\b(dose|mg)\b", text)):
        return "medicine"
    if DIAGNOSIS.search(text):
        return "diagnosis"
    return None


SAFETY_REPLY = {
    "emergency": ["If you think this could be an emergency, call your local emergency number now or go to the nearest emergency department. I can’t assess symptoms.",
                  "For anything that is not urgent, please contact your care team."],
    "medicine": ["I can’t advise on medicines or doses, and I’d never suggest changing how you take one.",
                 "Please ask your pharmacist or the clinician who prescribed it. I can show you what is on your record and how consistently doses were taken."],
    "diagnosis": ["I can’t diagnose, and I can’t say whether you have or will develop a condition. Only a clinician can.",
                  "What I can do is show what your own data shows and give you questions to bring to your care team."],
}


# ----------------------------------------------------------------------------- helpers over the package
def _ref(p, key):
    return next((i for i in p.get("reference", {}).get("items", []) if i["key"] == key), None)


def _last_roll(s):
    return next((v for v in reversed(s["r"]) if v is not None), None)


def _forecast_of(p, key):
    return next((f for f in p.get("outlook", {}).get("forecast", {}).get("items", []) if f["key"] == key), None)


def _projection_line(f) -> str:
    pr = next((x for x in f["projection"] if x["days"] == 90), f["projection"][-1])
    return f"It has been {f['trend']} steadily. In about 3 months it may be around {_fmt(pr['value'])} {f['unit']} (likely {_fmt(pr['low'])} to {_fmt(pr['high'])})."


def _suggest(p, current) -> list[str]:
    s = []
    if any(sc["surfaced"] for sc in p["scenarios"]):
        sc = next(sc for sc in p["scenarios"] if sc["surfaced"])
        s.append(f"Tell me about my {AREAS.get(sc['scenario'], 'health')} pattern")
    off = [i for i in p.get("reference", {}).get("items", []) if i["flag"] != "within" and not i["soft"]]
    if off:
        s.append(f"Is my {trim(off[0]['label']).lower()} normal?")
    s += ["What should I ask my doctor?", "Will anything change in the next few months?"]
    if any(sc["missing_data"] for sc in p["scenarios"]):
        s.append("What is missing from my record?")
    if p.get("meds"):
        s.append("Which medicines am I taking?")
    s.insert(0, "Give me a summary")
    s.insert(1, "What are my health risks?")
    return [x for x in s if current not in x.lower()][:4]


# ----------------------------------------------------------------------------- handlers
def h_help(p, text, state):
    return _reply("help", ["Hello. I can answer questions about your own record, in plain language. I can’t diagnose, advise on medicines, or assess urgent symptoms.",
                           "Try one of these, or ask in your own words."], suggestions=_suggest(p, "help"))


def h_thanks(p, text, state):
    return _reply("thanks", ["You’re welcome. Ask anything else about your record whenever you like."], suggestions=_suggest(p, "thanks"))


def h_summary(p, text, state):
    paras = []
    surfaced = [sc for sc in p["scenarios"] if sc["surfaced"]]
    if surfaced:
        names = ", ".join(AREAS.get(sc["scenario"], sc["title"]) for sc in surfaced)
        sc = surfaced[0]
        paras.append(f"**Where things stand:** a pattern was found in {names}. In {AREAS.get(sc['scenario'])}, {len(sc['pattern_signals'])} related measurements began moving together around {sc.get('pattern_start')}.")
    else:
        paras.append("**Where things stand:** none of your related measurements has moved away from your own usual in a lasting way.")
    R = p.get("reference", {})
    if R.get("items"):
        off = [trim(i["label"]) for i in R["items"] if i["flag"] != "within"]
        paras.append(f"**Against usual ranges:** {len(R['items']) - len(off)} of {len(R['items'])} measures sit within their usual ranges" + (f". Outside: {', '.join(off)}." if off else "."))
    rec = p.get("outlook", {}).get("recommendations")
    if rec:
        paras.append(f"**What to do with this:** {rec['summary']}")
    paras.append(NOT_DIAGNOSIS)
    return _reply("summary", paras, [{"label": "Overview", "link": "#/"}], _suggest(p, "summary"))


def h_area(p, text, state, area):
    sc = next((s for s in p["scenarios"] if s["scenario"] == area), None)
    if not sc or sc["status"] == "not_applicable":
        return _reply("area", [f"{AREAS[area].capitalize()} does not apply to your record."], suggestions=_suggest(p, "area"))
    paras = [f"**{AREAS[area].capitalize()}:** {sc['status_text']}."]
    if sc["surfaced"]:
        paras.append(f"{len(sc['pattern_signals'])} related measurements began moving together around {sc.get('pattern_start')}:")
        for e in sc["evidence"][:5]:
            a, b = (e.get("first"), e.get("last")) if e["kind"] == "lab" else (e.get("baseline_mean"), e.get("recent_mean"))
            paras.append(f"- {trim(e['label'])}: {_fmt(a, 2)} to {_fmt(b, 2)}")
        ctx = [c for c in sc["context"] if c["type"] != "symptoms" and "before" in (c.get("timing") or "")]
        if ctx:
            paras.append("It links to something already in your record: " + "; ".join(f"{c['text']}" + (f" ({c['date']})" if c.get("date") else "") for c in ctx[:3]) + ".")
    paras.append(NOT_DIAGNOSIS)
    return _reply("area", paras, [{"label": "Overview, what we found", "link": "#/"}], _suggest(p, "area"), keys=[area])


def h_measure(p, text, state, keys):
    paras, src, shown = [], [], []
    wanted = []
    for k in keys:
        wanted += [k]
    for k in wanted:
        it = _ref(p, k)
        label = trim(it["label"]) if it else trim(p["series"].get(k, {}).get("label") or p["labels"].get(k, k))
        block = []
        if it:
            block.append(f"**{label}:** recent level **{it['value_text']} {it['unit']}** ({it['as_of']}). Usual reference: {it['reference_text']}. Where it sits: {it['category'].lower()}. {CHANGE.get(it['change'], CHANGE[None])}")
            src.append({"label": "Where your levels sit", "link": "#/"})
        for sk in SERIES_OF.get(k, [k]):
            s = p["series"].get(sk)
            if s and s["base"]["mean"] is not None and _last_roll(s) is not None:
                block.append(f"Your first-60-day average {trim(s['label']).lower()} was {_fmt(s['base']['mean'])} {s['unit']}; the latest 30-day average is {_fmt(_last_roll(s))}.")
                src.append({"label": "Timeline", "link": "#/timeline"})
        lab = p["labs"].get(k)
        if lab:
            pts = lab["points"][-5:]
            block.append("Results: " + "; ".join(f"{_fmt(x['v'], 2)} on {x['d']}" for x in pts) + f" (lab range {lab['ref']} {lab['unit']}).")
            src.append({"label": "Labs", "link": "#/labs"})
        for fk in SERIES_OF.get(k, [k]):
            f = _forecast_of(p, fk)
            if f:
                block.append(_projection_line(f))
                src.append({"label": "Outlook", "link": "#/outlook"})
        if block:
            paras += block
            shown.append(k)
    if not paras:
        return _reply("measure", ["I couldn’t find that measurement in your record."], suggestions=_suggest(p, "measure"))
    paras.append(NOT_DIAGNOSIS)
    seen, dedup = set(), []
    for s_ in src:
        if s_["link"] not in seen:
            seen.add(s_["link"])
            dedup.append(s_)
    return _reply("measure", paras, dedup, _suggest(p, "measure"), keys=shown)


def h_forecast(p, text, state):
    fc = p.get("outlook", {}).get("forecast")
    if not fc:
        return _reply("forecast", ["Projections are not available for your record yet."], suggestions=_suggest(p, "forecast"))
    keys = measure_keys(text)
    items = [f for f in fc["items"] if not keys or f["key"] in sum((SERIES_OF.get(k, [k]) for k in keys), [])]
    paras = []
    if items:
        paras.append("Here is where your steady trends may be heading:")
        for f in items:
            line = f"- **{trim(f['label'])}:** {_projection_line(f)}"
            c = f.get("crosses")
            if c and c["in_days"] <= 120:
                line += f" At that pace it would reach “{c['into'].lower()}” in about {c['in_days']} days."
            paras.append(line)
    else:
        paras.append("I can’t project anything for that: there is no strong, lasting trend in your recent data, so assuming it stays about where it is would be as good as any forecast." if keys
                     else "I don’t see any strong, lasting trend in your recent data, so there is nothing to project. Assuming things stay about where they are is as good as any forecast.")
    paras.append("This is a guess from your trend, not a diagnosis. Labs are not forecast.")
    return _reply("forecast", paras, [{"label": "Outlook", "link": "#/outlook"}], _suggest(p, "forecast"), keys=[f["key"] for f in items])


def h_recommend(p, text, state):
    rec = p.get("outlook", {}).get("recommendations")
    if not rec or not rec["groups"]:
        return _reply("recommend", ["Nothing needs raising right now."], suggestions=_suggest(p, "recommend"))
    keys = sum((SERIES_OF.get(k, [k]) for k in measure_keys(text)), [])
    paras = [rec["summary"]]
    shown = 0
    for g in rec["groups"]:
        items = [i for i in g["items"] if not keys or set(i["keys"]) & set(keys)]
        if not items:
            continue
        paras.append(f"**{g['title']}**")
        for i in items:
            paras.append(f"- {i['title']}. {' '.join(i['why'])}" + (f" {i['ask']}" if i.get("ask") else ""))
            shown += 1
    if keys and not shown:
        paras = ["I don’t have a specific suggestion about that. Nothing in your data about it needs raising right now."]
    paras.append(rec["disclaimer"])
    return _reply("recommend", paras, [{"label": "Outlook, suggestions", "link": "#/outlook"}], _suggest(p, "recommend"))


def h_visit(p, text, state):
    rec = p.get("outlook", {}).get("recommendations")
    asks, bring = [], []
    for g in (rec or {}).get("groups", []):
        for i in g["items"]:
            if g["id"] in ("raise", "watch") and i.get("ask") and i["ask"] not in asks:
                asks.append(i["ask"])
            if g["id"] == "data":
                bring.append(i["title"])
    paras = ["**To bring up with your care team:**"] + ([f"- {a}" for a in asks[:6]] or ["- Nothing urgent from your data. You could ask whether anything should be rechecked this year."])
    if bring:
        paras += ["**Worth having ready:**"] + [f"- {b}" for b in bring[:5]]
    off = [i for i in p.get("reference", {}).get("items", []) if i["flag"] != "within" and not i["soft"]]
    if off:
        paras += ["**Your key numbers:**"] + [f"- {trim(i['label'])}: {i['value_text']} {i['unit']} ({i['category'].lower()})" for i in off[:6]]
    return _reply("visit", paras, [{"label": "Outlook", "link": "#/outlook"}, {"label": "Print or save as PDF", "link": "#/"}], _suggest(p, "visit"))


def h_meds(p, text, state):
    meds = p.get("meds", [])
    if not meds:
        return _reply("meds", ["No medicines are on your record."], suggestions=_suggest(p, "meds"))
    named = [w for w in _med_words(p) if w in text]
    groups = {}
    for m in meds:
        groups.setdefault(m["id"] or m["name"], []).append(m)
    paras = []
    for mid, rows in groups.items():
        rows.sort(key=lambda r: r.get("start") or "")
        last = rows[-1]
        if named and last["name"].split(" ")[0].lower() not in named:
            continue
        now = not last.get("end")
        line = f"- **{last['name']} {last['dose']}**, {str(last.get('freq') or '').lower()}: {'taking now' if now else 'stopped ' + str(last['end'])}, for {str(last.get('for') or 'a reason not recorded').lower()}, since {rows[0].get('start')}."
        if len(rows) > 1:
            line += f" It has changed {len(rows) - 1} time{'s' if len(rows) > 2 else ''} (see the Medications page)."
        ad = [a["pct"] for a in p.get("adherence", []) if a["med"] == mid]
        if ad:
            line += f" About {round(sum(ad) / len(ad))}% of doses were taken across {len(ad)} records."
        paras.append(line)
    if not paras:
        return _reply("meds", ["I couldn’t find that medicine on your record."], suggestions=_suggest(p, "meds"))
    paras.append("I can’t advise on medicines or doses. For that, ask your pharmacist or prescriber.")
    return _reply("meds", ["**Your medicines:**"] + paras, [{"label": "Medications", "link": "#/medications"}], _suggest(p, "meds"))


def h_missing(p, text, state):
    asks = [(a, sc) for sc in p["scenarios"] for a in sc["missing_data"]]
    if not asks:
        return _reply("missing", ["Nothing important is missing for the areas we check."], suggestions=_suggest(p, "missing"))
    seen, lines = set(), []
    for a, _ in asks:
        if a["key"] not in seen:
            seen.add(a["key"])
            lines.append(f"- **{a['item']}**: {a['reason']}.")
    return _reply("missing", ["Information that would sharpen the picture:"] + lines, [{"label": "What would help", "link": "#/help"}], _suggest(p, "missing"))


def h_history(p, text, state):
    ev = p.get("events", [])
    earlier = [e for e in ev if e["t"] == "history"]
    sym = sorted((e for e in ev if e["t"] == "symptoms"), key=lambda e: e["d"], reverse=True)[:5]
    paras = []
    if earlier:
        paras += ["**On your record:**"] + [f"- {e['text']} ({e['d']})" for e in sorted(earlier, key=lambda e: e["d"])]
    if sym:
        paras += ["**Recent symptoms you logged:**"] + [f"- {e['text']} ({e['d']})" for e in sym]
    if not paras:
        paras = ["No history or symptoms are on your record."]
    return _reply("history", paras, [{"label": "History and notes", "link": "#/history"}], _suggest(p, "history"))


def h_quality(p, text, state):
    q = p["quality"]
    return _reply("quality", [f"Your record has {q.get('vitals_days')} days of vitals and {q.get('wearable_days')} days of wearable data, with {q.get('vitals_blank_cells')} blank vitals cells and {q.get('wearable_blank_cells')} blank wearable cells. "
                              f"{(q.get('vitals_impossible_values') or 0) + (q.get('wearable_impossible_values') or 0)} impossible values were removed and {q.get('lab_unit_conversions') or 0} lab units were converted. Every cleaning step is counted, not hidden."],
                  [{"label": "Data quality", "link": "#/quality"}], _suggest(p, "quality"))


def h_method(p, text, state):
    return _reply("method", ["Each of your measurements is compared with your own first 60 days, not with other people. A pattern is raised only when several related measurements move together and stay moved. A separate check shows where each level sits against published reference ranges.",
                             "We have tested this on data where we planted patterns, which shows it works as designed. It has not been validated clinically, and it never diagnoses.",
                             "The wording in answers and suggestions comes from fixed templates filled with numbers from your record, so nothing is invented."],
                  [{"label": "How it works", "link": "#/method"}, {"label": "The evidence", "link": "#/evidence"}], _suggest(p, "method"))


def h_privacy(p, text, state):
    return _reply("privacy", ["You only ever see your own record, and I only see yours: the server decides who you are from your sign-in, never from what you type.",
                              "Sign-ins and chat topics are logged for security, but not your passwords and not the text of your messages. You are signed out after 20 idle minutes."], suggestions=_suggest(p, "privacy"))


def h_why(p, text, state):
    last = (state or {}).get("last") or {}
    keys = last.get("keys") or []
    rec = p.get("outlook", {}).get("recommendations", {"groups": []})
    hits = [i for g in rec["groups"] for i in g["items"] if set(i["keys"]) & set(keys)]
    if hits:
        return _reply("why", [f"- {i['title']}. {' '.join(i['why'])}" for i in hits[:3]] + [NOT_DIAGNOSIS], [{"label": "Overview", "link": "#/"}], _suggest(p, "why"), keys=keys)
    return _reply("why", ["The short reason is that each answer comes straight from the numbers in your record. Ask about a specific measurement and I’ll show the figures behind it."], suggestions=_suggest(p, "why"))


def h_changes(p, text, state):
    """What changed for this patient: the patterns found, then any measure that is moving."""
    surfaced = [sc for sc in p["scenarios"] if sc["surfaced"]]
    paras = []
    if surfaced:
        paras.append("**Yes, something changed.**")
        for sc in surfaced:
            paras += h_area(p, text, state, sc["scenario"])["answer"][:-1]
    else:
        paras.append("**Nothing has moved away from your own usual in a lasting way.** No group of related measurements has changed together.")
    moving = [w for w in p.get("outlook", {}).get("watch", {}).get("items", []) if w["direction"] != "steady"]
    if moving:
        paras.append("**Still moving:** " + "; ".join(f"{w['label']} is {w['direction']} ({re.sub(r' [(](rising|falling)[)]', '', w['change']).lower()})" for w in moving[:4]) + ".")
    paras.append(NOT_DIAGNOSIS)
    return _reply("changes", paras, [{"label": "Overview, what we found", "link": "#/"}, {"label": "Where things are heading", "link": "#/outlook"}], _suggest(p, "change"), keys=[sc["scenario"] for sc in surfaced])


def h_risk(p, text, state):
    r = p.get("outlook", {}).get("risk")
    if not r:
        return _reply("risk", ["A heart-risk estimate is not available for this record yet."], suggestions=_suggest(p, "heart attack"))
    src = [{"label": "Heart risk, with the factors", "link": "#/outlook"}]
    if not r["available"]:
        paras = [f"**I can’t give a percentage for this record.** {r['reason']}"]
        if r["drivers"]:
            paras += ["Heart-related measures that sit outside their usual range:"] + [f"- {d['label']}: {d['text']}" for d in r["drivers"]]
        else:
            paras.append("None of your heart-related measures sits outside its usual range.")
        paras.append("Ask your clinician about your overall heart health. " + r["caveat"])
        return _reply("risk", paras, src, _suggest(p, "heart attack"), keys=["risk"])
    paras = [f"**Estimated chance of a heart attack or stroke in the next 10 years: about {r['per100']} in 100 ({r['percent']}%), which falls in the “{r['band']}” band.**",
             "This is an estimate for groups of people with the same readings, not a prediction about you.",
             "**What went into it (all from your record):**"] + [f"- {i['label']}: {i['value']}" + (" (assumed)" if i["source"] == "assumed" else "") for i in r["inputs"]]
    ups = [d for d in r["drivers"] if not d["fixed"]]
    paras.append("**What is pushing it up, and by how much:**")
    paras += [f"- {d['label']} ({d['text']}): about {d['points']} percentage points" for d in ups] or ["- None of the changeable factors is above its healthy level."]
    paras += [f"- {d['label']}: {d['text']}" for d in r["drivers"] if d["fixed"]]
    paras += ["**What this does not include:** " + " ".join(r["assumptions"]), r["bands"], f"Method: {r['method']}.", r["caveat"]]
    return _reply("risk", paras, src, _suggest(p, "heart attack"), keys=["risk"])


def _dm_range(r) -> str:
    return f"about {r['per100_min']} in 100" if r["per100_min"] == r["per100_max"] else f"between {r['per100_min']} and {r['per100_max']} in 100"


def h_risk_diabetes(p, text, state):
    r = p.get("outlook", {}).get("diabetes")
    src = [{"label": "Your health risks", "link": "#/outlook"}]
    if not r or not r["available"]:
        return _reply("risk", [f"**I can’t score diabetes risk for this record.** {(r or {}).get('reason', 'It is not available.')}"], src, _suggest(p, "diabetes"), keys=["diabetes"])
    band = r["band_min"] if r["band_min"] == r["band_max"] else f"{r['band_min']} to {r['band_max']}"
    paras = [f"**Chance of developing type 2 diabetes in the next 10 years: {_dm_range(r)} ({band}).**",
             f"This is a screening score of {r['score_min']}" + ("" if r["score_min"] == r["score_max"] else f" to {r['score_max']}") + ", not a diagnosis and not a prediction about you.",
             "**What feeds it (points each):**"] + [f"- {d['label']}: {d['text']} ({d['points']} points)" for d in r["drivers"]]
    watch = {w["key"]: w for w in p.get("outlook", {}).get("watch", {}).get("items", [])}
    for k in ("hba1c", "fasting_glucose"):
        w = watch.get(k)
        if w:
            paras.append(f"Your {w['label']}: {w['value_text']} {w['unit']} ({w['category'].lower()}). {w['change']}.")
    paras += ["**What this does not include:** " + " ".join(r["assumptions"]), r["bands"], f"Method: {r['method']}.", r["caveat"]]
    return _reply("risk", paras, src, _suggest(p, "diabetes"), keys=["diabetes"])


TREND_KEYS = {"bp": ["bp"], "kidney": ["egfr"], "cholesterol": ["ldl_cholesterol", "total_cholesterol", "hdl_cholesterol", "triglycerides"], "weight": ["bmi"]}


def h_trend_condition(p, text, state, cond):
    """Where one condition's measures are heading: status, direction, and a projection only when the trend is strong."""
    names = {"bp": "Blood pressure", "kidney": "Kidney function", "cholesterol": "Cholesterol", "weight": "Weight"}
    watch = {w["key"]: w for w in p.get("outlook", {}).get("watch", {}).get("items", [])}
    ref = {i["key"]: i for i in p.get("reference", {}).get("items", [])}
    paras = [f"**{names[cond]}: where it stands and where it is heading.**"]
    for k in TREND_KEYS[cond]:
        w, it = watch.get(k), ref.get(k)
        if w:
            line = f"- **{w['label']}** {w['value_text']} {w['unit']}, {w['category'].lower()}. {w['change']}."
            line += (f" In about 3 months it may be around {_fmt(w['projection']['value'])} (likely {_fmt(w['projection']['low'])} to {_fmt(w['projection']['high'])})." if w["projection"]
                     else " No strong trend, so I can’t project a change.")
            paras.append(line)
        elif it:
            paras.append(f"- **{trim(it['label'])}** {it['value_text']} {it['unit']}, {it['category'].lower()}." + (" Nothing about it needs watching right now." if it["flag"] == "within" else " Worth raising with your care team."))
    if len(paras) == 1:
        return _reply("predict", [f"I don’t have {names[cond].lower()} measurements in this record."], suggestions=_suggest(p, cond))
    if cond == "bp":
        h = p.get("outlook", {}).get("risk", {})
        if h.get("available"):
            paras.append(f"Blood pressure is one input to your 10-year heart risk, which is {h['per100']} in 100 ({h['band']}). Ask me “What is my chance of a heart attack?” for the breakdown.")
    paras.append("A trend is a description of the recent past, not a prediction of illness.")
    return _reply("predict", paras, [{"label": "Where your numbers are heading", "link": "#/outlook"}], _suggest(p, cond), keys=TREND_KEYS[cond])


def h_risk_overview(p, text, state):
    o = p.get("outlook", {})
    h, d, w = o.get("risk", {}), o.get("diabetes", {}), o.get("watch", {}).get("items", [])
    paras = ["**Your health risks at a glance.** These are estimates from published scores, not diagnoses."]
    paras.append(f"- **Heart attack or stroke (10 years):** {h['per100']} in 100, {h['band']} band." if h.get("available") else f"- **Heart attack or stroke:** not scored. {h.get('reason', '')}")
    paras.append(f"- **Type 2 diabetes (10 years):** {_dm_range(d)}, {d['band_min'] if d['band_min'] == d['band_max'] else d['band_min'] + ' to ' + d['band_max']}." if d.get("available") else f"- **Type 2 diabetes:** not scored. {d.get('reason', '')}")
    if w:
        paras.append("**Measures to keep an eye on:** " + ", ".join(x["label"].lower() for x in w[:4]) + ".")
    paras += ["I can’t estimate other conditions such as cancer or dementia. Ask me about the heart, diabetes, blood pressure, cholesterol, kidneys or weight for the details.", "Ask “What is my chance of a heart attack?” or “What is my chance of developing diabetes?” for the full breakdown."]
    return _reply("risk", paras, [{"label": "Your health risks", "link": "#/outlook"}], _suggest(p, "risks"), keys=["risk"])


def h_unsupported(p, text, state):
    return _reply("predict", ["I can’t estimate that. I can score the 10-year chance of a heart attack or stroke and of type 2 diabetes, and show where your blood pressure, cholesterol, kidney function and weight are heading.",
                              "For anything else, a clinician is the right person to ask. I can help you prepare questions."], suggestions=_suggest(p, "unsupported"))


CANONICAL = ["Give me a summary", "What is my chance of a heart attack?", "What is my chance of developing diabetes?", "What are my health risks?", "Will my blood pressure change?",
             "Will my weight change?", "Will my cholesterol change?", "What should I ask my doctor?", "Did anything change for me?", "Which medicines am I taking?", "What is missing from my record?"]


CANONICAL_HINTS = {
    "Give me a summary": "overall summary, how am I doing",
    "What is my chance of a heart attack?": "heart attack, stroke, heart risk",
    "What is my chance of developing diabetes?": "diabetes, blood sugar, glucose, HbA1c",
    "What are my health risks?": "all health risks",
    "Will my blood pressure change?": "blood pressure",
    "Will my weight change?": "weight, BMI",
    "Will my cholesterol change?": "cholesterol, LDL, lipids",
    "What should I ask my doctor?": "doctor visit, questions to ask, appointment",
    "Did anything change for me?": "what changed, anything new, trends",
    "Which medicines am I taking?": "medicines, tablets, pills, prescriptions",
    "What is missing from my record?": "missing data, more tests, what else is needed",
}


def h_fallback(p, text, state):
    return _reply("fallback", ["I’m not sure I understood that. I can answer questions about your measurements, usual ranges, patterns, medicines, what’s missing, projections, and what to ask your care team.",
                               "I can’t diagnose, advise on medicines, or assess urgent symptoms."], suggestions=_suggest(p, "fallback"))


ROUTES = [
    (re.compile(r"did anything change|what (has )?changed|any changes|changed for me|what('s| is) new|anything new"), h_changes),
    (re.compile(r"^(hi|hello|hey|help|what can you (do|answer)|how do i use|start)\b"), h_help),
    (re.compile(r"^(thanks|thank you|ok thanks|great thanks|cheers)\b"), h_thanks),
    (re.compile(r"appointment|visit|ask (my|the) (doctor|clinician|gp|care team)|questions? (for|to ask)|prepare|bring to|talk to my doctor"), h_visit),
    (re.compile(r"\b(will|going to|predict|forecast|projection|projected|heading|future|next (month|few|weeks|year)|get worse|go up|go down|keep (rising|falling)|trend)\b"), h_forecast),
    (re.compile(r"what should i do|\brecommend|advice|next steps?|what can i do|\btips?\b|suggest|improve|help me"), h_recommend),
    (re.compile(r"medicine|medication|\bmeds\b|pills?|tablets?|prescri|adherence|missed doses?|taking"), h_meds),
    (re.compile(r"missing|what data|what tests?|incomplete|what else do you need|what (information|info)"), h_missing),
    (re.compile(r"\bhistory\b|diagnos(is|es)|symptoms?|\bnotes?\b|on my record"), h_history),
    (re.compile(r"data quality|how complete|blank|impossible values|how good is my data"), h_quality),
    (re.compile(r"who can see|is my data (safe|private|secure)|privacy|confidential"), h_privacy),
    (re.compile(r"how (do|does) (you|this|it) work|how accurate|can i trust|is this (a )?diagnos|how reliable|who built|how do you know|what is pranasync"), h_method),
]


def answer(message: str, payload: dict, state: dict | None = None) -> dict:
    """Answer one question about this patient's own package. Returns {intent, answer[], sources[], suggestions[], state}."""
    text = _norm(message)[:500]
    state = state or {}
    if not text:
        return h_help(payload, text, state)
    t = triage(text, payload)
    cond = next((k for k, rx in CONDITIONS if re.search(rx, text)), None)
    predictive = bool(PRED_WORDS.search(text)) and (cond is not None or OVERVIEW.search(text) or UNSUPPORTED.search(text))
    if t == "diagnosis" and predictive:   # "what are my chances of..." asks for a risk estimate, not a diagnosis
        t = None
    if t is None and predictive:
        if UNSUPPORTED.search(text) and cond is None:
            return h_unsupported(payload, text, state)
        if OVERVIEW.search(text) and cond is None:
            return h_risk_overview(payload, text, state)
        if cond == "heart" or RISK.search(text):
            return h_risk(payload, text, state)
        if cond == "diabetes":
            return h_risk_diabetes(payload, text, state)
        if cond in TREND_KEYS:
            return h_trend_condition(payload, text, state, cond)
    if t:
        return _reply("safety_" + t, SAFETY_REPLY[t], suggestions=_suggest(payload, "safety") if t != "emergency" else [])
    keys = measure_keys(text)
    for rx, fn in ROUTES:
        if rx.search(text):
            return fn(payload, text, state)
    if keys:
        return h_measure(payload, text, state, keys)
    for area, rx in AREA_WORDS:
        if re.search(rx, text):
            return h_area(payload, text, state, area)
    if re.search(r"summary|overall|how am i doing|what('s| is) (going on|new|happening)|what changed|tell me about my (health|record)|anything (wrong|to worry)", text):
        return h_summary(payload, text, state)
    if re.search(r"\bwhy\b|tell me more|explain|more detail|what does that mean", text) and state.get("last"):
        return h_why(payload, text, state)
    return h_fallback(payload, text, state)
