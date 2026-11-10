"""10-year heart and stroke risk estimate with the factors behind it (owner: Uday, to be checked by Sindhu).

The number comes from a published, validated formula, never from a language model: the 2013 ACC/AHA Pooled Cohort Equations
(Goff et al., Circulation 2014), the equations behind the ACC/AHA 2018 cholesterol guideline. They estimate the chance of a first
heart attack, fatal coronary event or stroke within 10 years, for people aged 40 to 79.

What we do NOT have in the workbooks: smoking status and race. The tool assumes "non-smoker" and uses the equations for "white or
other" patients, and says so in every answer. A smoker's real risk would be higher.

Explaining the number: each factor's share is found by "what if" arithmetic. We recompute the risk with that one factor set to a
healthy value and report how many percentage points the risk would drop. Age and sex cannot be changed and are listed as fixed.
"""
from __future__ import annotations

import math

import pandas as pd

from prana.data.timeline import daily_series, lab_series

BANDS = [(5.0, "low"), (7.5, "borderline"), (20.0, "intermediate"), (101.0, "high")]  # ACC/AHA 2018 risk bands, % over 10 years
HEALTHY = {"sbp": 115.0, "tc": 170.0, "hdl": 60.0}
SOURCE = "2013 ACC/AHA Pooled Cohort Equations (Goff et al., Circulation 2014)"
BP_WORDS = ("blood pressure", "hypertens", "cardiovascular")


def pce(sex: str, age: float, tc: float, hdl: float, sbp: float, treated: bool, smoker: bool, diabetes: bool) -> float:
    """10-year ASCVD risk in percent (white or other patients)."""
    la, lt, lh, ls = math.log(age), math.log(tc), math.log(hdl), math.log(sbp)
    if sex == "F":
        s = (-29.799 * la + 4.884 * la ** 2 + 13.540 * lt - 3.114 * la * lt - 13.578 * lh + 3.149 * la * lh
             + (2.019 if treated else 1.957) * ls + ((7.574 - 1.665 * la) if smoker else 0) + (0.661 if diabetes else 0))
        return 100 * (1 - 0.9665 ** math.exp(s + 29.18))
    s = (12.344 * la + 11.853 * lt - 2.664 * la * lt - 7.990 * lh + 1.769 * la * lh
         + (1.797 if treated else 1.764) * ls + ((7.837 - 1.795 * la) if smoker else 0) + (0.658 if diabetes else 0))
    return 100 * (1 - 0.9144 ** math.exp(s - 61.18))


def _band(pct: float) -> str:
    return next(name for cap, name in BANDS if pct < cap)


def _last(series: pd.Series, n: int = 30):
    s = series.dropna()
    return float(s.tail(n).mean()) if len(s) else None


def gather(rec) -> dict:
    """Pull the formula's inputs out of the patient's record."""
    sex = "F" if str(rec.profile.get("Sex", "")).strip().lower().startswith("f") else "M"
    age = pd.to_numeric(rec.profile.get("Age"), errors="coerce")
    labs = {k: lab_series(rec, k) for k in ("total_cholesterol", "hdl_cholesterol", "hba1c")}
    last = {k: (float(v.dropna().iloc[-1]) if len(v.dropna()) else None) for k, v in labs.items()}
    meds, hist = rec.get("medications"), rec.get("history")
    active = meds[meds["end_date"].isna()] if not meds.empty and "end_date" in meds else meds
    ind = " ".join(active["indication"].astype(str).str.lower()) if not active.empty and "indication" in active else ""
    notes = " ".join(hist["finding"].astype(str).str.lower()) if not hist.empty and "finding" in hist else ""
    return {"sex": sex, "age": None if pd.isna(age) else float(age), "sbp": _last(daily_series(rec, "sbp")),
            "tc": last["total_cholesterol"], "hdl": last["hdl_cholesterol"],
            "treated": any(w in ind for w in BP_WORDS),
            "diabetes": (last["hba1c"] or 0) >= 6.5 or "type 2 diabetes" in notes or "diabetes mellitus" in notes}


def _profile_fallback(result: dict) -> list[dict]:
    """When the formula does not apply (age), still show the heart-related factors that sit outside their usual ranges."""
    keys = ("bp", "ldl_cholesterol", "hdl_cholesterol", "total_cholesterol", "triglycerides", "fasting_glucose", "hba1c", "bmi")
    out = []
    for it in result["reference"]["items"]:
        if it["key"] in keys and it["flag"] != "within":
            out.append({"label": it["label"].split(" (")[0], "text": f"{it['value_text']} {it['unit']}: {it['category'].lower()}", "points": None, "fixed": False})
    return out


def build_risk(result: dict, rec) -> dict:
    x = gather(rec)
    base = {"method": SOURCE, "applies_to": "ages 40 to 79",
            "caveat": "An estimate for groups of people like you, not a prediction about you. It is not a diagnosis. Your clinician can include things this tool cannot see."}
    if x["age"] is None or not 40 <= x["age"] <= 79:
        age = "unknown" if x["age"] is None else f"{x['age']:.0f}"
        return {**base, "available": False, "reason": f"The validated formula is only for ages 40 to 79 and this record is age {age}, so no percentage is given.",
                "drivers": _profile_fallback(result)}
    missing = [k for k in ("sbp", "tc", "hdl") if not x[k]]
    if missing:
        names = {"sbp": "a recent blood pressure", "tc": "a total cholesterol result", "hdl": "an HDL cholesterol result"}
        return {**base, "available": False, "reason": "To estimate this we also need " + ", ".join(names[m] for m in missing) + ".", "drivers": _profile_fallback(result)}

    args = dict(sex=x["sex"], age=x["age"], tc=x["tc"], hdl=x["hdl"], sbp=x["sbp"], treated=x["treated"], smoker=False, diabetes=x["diabetes"])
    pct = pce(**args)
    drivers = []

    def what_if(label, text, **change):
        drop = pct - pce(**{**args, **change})
        drivers.append({"label": label, "text": text, "points": round(drop, 1), "fixed": False})

    if x["sbp"] > HEALTHY["sbp"]:
        what_if("Blood pressure", f"Recent average {x['sbp']:.0f} mmHg{', on treatment' if x['treated'] else ''}", sbp=HEALTHY["sbp"])
    if x["tc"] > HEALTHY["tc"]:
        what_if("Total cholesterol", f"{x['tc']:.0f} mg/dL", tc=HEALTHY["tc"])
    if x["hdl"] < HEALTHY["hdl"]:
        what_if("HDL (protective) cholesterol", f"{x['hdl']:.0f} mg/dL, lower than the protective level", hdl=HEALTHY["hdl"])
    if x["diabetes"]:
        what_if("Diabetes", "Recorded in this patient's data", diabetes=False)
    drivers = sorted(drivers, key=lambda d: -d["points"])
    drivers.append({"label": "Age", "text": f"{x['age']:.0f} years. Risk rises with age and this cannot be changed.", "points": None, "fixed": True})
    drivers.append({"label": "Sex", "text": "Female" if x["sex"] == "F" else "Male", "points": None, "fixed": True})

    inputs = [{"label": "Age", "value": f"{x['age']:.0f}", "source": "your record"}, {"label": "Sex", "value": "Female" if x["sex"] == "F" else "Male", "source": "your record"},
              {"label": "Systolic blood pressure", "value": f"{x['sbp']:.0f} mmHg", "source": "your record (last 30-day average)"},
              {"label": "Total cholesterol", "value": f"{x['tc']:.0f} mg/dL", "source": "your record (latest lab)"}, {"label": "HDL cholesterol", "value": f"{x['hdl']:.0f} mg/dL", "source": "your record (latest lab)"},
              {"label": "On blood-pressure treatment", "value": "Yes" if x["treated"] else "No", "source": "your medicines list"},
              {"label": "Diabetes", "value": "Yes" if x["diabetes"] else "No", "source": "your record (HbA1c and history)"},
              {"label": "Smoking", "value": "Not recorded, assumed non-smoker", "source": "assumed"}]
    return {**base, "available": True, "percent": round(pct, 1), "band": _band(pct), "per100": round(pct), "inputs": inputs, "drivers": drivers,
            "assumptions": ["Smoking status is not in the workbook, so a non-smoker is assumed. Smoking would raise the figure.",
                            "The equations used are for white or other patients. Race is not in the workbook."],
            "bands": "Under 5% low, 5 to 7.4% borderline, 7.5 to 19.9% intermediate, 20% or more high (ACC/AHA 2018)."}


# ----------------------------------------------------------------------------- type 2 diabetes
DM_SOURCE = "FINDRISC, the Finnish Diabetes Risk Score (Lindström & Tuomilehto, Diabetes Care 2003)"
DM_BANDS = [(7, "low", 1), (12, "slightly raised", 4), (15, "moderate", 17), (21, "high", 33), (99, "very high", 50)]   # (score below, name, about % over 10 years)


def _dm_band(score: int) -> tuple[str, int]:
    return next((n, p) for cap, n, p in DM_BANDS if score < cap)


def build_diabetes_risk(result: dict, rec) -> dict:
    """10-year type 2 diabetes risk from the FINDRISC questionnaire, using what the record holds.

    Not in the workbooks: waist size and daily vegetable intake. The score is therefore a RANGE, from "best case" to "worst case"
    for those two answers, and the answer says so.
    """
    base = {"method": DM_SOURCE, "caveat": "A screening score, not a diagnosis. It estimates the chance of developing type 2 diabetes over 10 years for people with the same answers."}
    x = gather(rec)
    ref = {i["key"]: i for i in result["reference"]["items"]}
    hist = rec.get("history")
    notes = " ".join(hist["finding"].astype(str).str.lower()) if not hist.empty and "finding" in hist else ""
    hba1c = lab_series(rec, "hba1c").dropna()
    glu = lab_series(rec, "fasting_glucose").dropna()
    if x["diabetes"]:
        return {**base, "available": False, "reason": "Diabetes is already part of this record, so a risk of developing it does not apply."}
    if x["age"] is None or x["age"] < 18:
        return {**base, "available": False, "reason": "This score is for adults."}
    bmi = ref.get("bmi", {}).get("value")
    if bmi is None:
        return {**base, "available": False, "reason": "A body mass index is needed for this score and is not in the record."}
    high_glucose = ((float(hba1c.iloc[-1]) >= 5.7) if len(hba1c) else False) or ((float(glu.iloc[-1]) >= 100) if len(glu) else False) or "glycemic" in notes or "prediabet" in notes or "glucose" in notes
    fam = str(rec.profile.get("Family History", "")).lower()
    family = 5 if "diabetes" in fam and ("first" in fam or "parent" in fam or "sibling" in fam) else 3 if "diabetes" in fam else 0
    active = daily_series(rec, "active_minutes").dropna().tail(30)
    moves = float(active.mean()) >= 30 if len(active) else None
    pts = [("Age", 0 if x["age"] < 45 else 2 if x["age"] < 55 else 3 if x["age"] < 65 else 4, f"{x['age']:.0f} years"),
           ("Body mass index", 0 if bmi < 25 else 1 if bmi < 30 else 3, f"{bmi:.1f} kg/m²"),
           ("Daily physical activity", 2 if moves is False else 0, "about 30 or more active minutes a day" if moves else "under 30 active minutes a day" if moves is False else "not recorded"),
           ("Taking blood-pressure medicine", 2 if x["treated"] else 0, "yes" if x["treated"] else "no"),
           ("Past high blood sugar", 5 if high_glucose else 0, "yes, borderline or raised results on record" if high_glucose else "none on record"),
           ("Diabetes in the family", family, "close relative" if family == 5 else "other relative" if family == 3 else "none recorded")]
    known = sum(p for _, p, _ in pts)
    lo, hi = known, known + 4 + 1          # waist adds 0 to 4 points, vegetables 0 or 1
    (b_lo, p_lo), (b_hi, p_hi) = _dm_band(lo), _dm_band(hi)
    drivers = sorted([{"label": n, "text": t, "points": p, "fixed": n == "Age"} for n, p, t in pts if p > 0], key=lambda d: -d["points"])
    return {**base, "available": True, "score_min": lo, "score_max": hi, "band_min": b_lo, "band_max": b_hi, "per100_min": p_lo, "per100_max": p_hi,
            "drivers": drivers, "inputs": [{"label": n, "value": t, "points": p} for n, p, t in pts],
            "assumptions": ["Waist size and daily vegetable intake are not in the record, so the score is shown as a range that allows for them."],
            "bands": "Score under 7: low (about 1 in 100). 7 to 11: slightly raised (about 4 in 100). 12 to 14: moderate (about 17 in 100). 15 to 20: high (about 33 in 100). Over 20: very high (about 50 in 100)."}
