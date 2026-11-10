"""Projections, recommendations and the chatbot: honest, grounded, and never a diagnosis or a medicine instruction."""
import numpy as np
import pandas as pd
import pytest

from prana.ai import chat
from prana.ai.forecast import forecast_daily
from prana.ai.recommend import banned_hits
from prana.api.payload import build_payload
from prana.insight.pipeline import analyze_workbook


@pytest.fixture(scope="module")
def packages(workbooks):
    return {k: build_payload(*analyze_workbook(workbooks[k])) for k in ("t2d", "htn", "control", "pcos")}


def _series(slope, n=160, noise=0.2, seed=1):
    rng = np.random.default_rng(seed)
    return pd.Series(100 + slope * np.arange(n) + rng.normal(0, noise, n), index=pd.date_range("2026-01-01", periods=n))


def test_flat_series_is_not_projected():
    f = forecast_daily(_series(0.0, noise=1.0), "sbp")
    assert f is None or not f["reliable"]


def test_strong_trend_is_projected_with_a_range_that_widens():
    f = forecast_daily(_series(0.3), "sbp")
    assert f and f["reliable"] and f["trend"] == "rising"
    p30, p90 = f["projection"]
    assert p90["value"] > p30["value"] > f["now"] - 1
    assert p90["high"] - p90["low"] > p30["high"] - p30["low"]


def test_damping_projects_less_than_a_straight_line():
    f = forecast_daily(_series(0.3), "sbp")
    straight = f["now"] + f["slope_per_week"] * 90 / 7
    assert f["projection"][1]["value"] < straight


def test_recommendations_are_complete_and_never_banned(packages):
    for p in packages.values():
        r = p["outlook"]["recommendations"]
        assert r["summary"] and r["disclaimer"]
        for g in r["groups"]:
            for i in g["items"]:
                text = " ".join([i["title"], *i["why"], i["ask"] or ""])
                assert banned_hits(text) == [], text
                assert i["title"] and i["why"]


def test_pattern_patient_gets_a_pattern_suggestion(packages):
    ids = [i["id"] for g in packages["t2d"]["outlook"]["recommendations"]["groups"] for i in g["items"]]
    assert any(i.startswith("pattern_") for i in ids)


def test_numbers_in_chat_come_from_the_record(packages):
    p = packages["t2d"]
    r = chat.answer("Is my HbA1c normal?", p)
    item = next(i for i in p["reference"]["items"] if i["key"] == "hba1c")
    assert r["intent"] == "measure" and item["value_text"] in " ".join(r["answer"])


@pytest.mark.parametrize("q,intent", [
    ("I have chest pain", "safety_emergency"), ("I can't breathe", "safety_emergency"),
    ("Should I stop my metformin?", "safety_medicine"), ("how much should I take", "safety_medicine"),
    ("Do I have diabetes?", "safety_diagnosis"), ("what is wrong with me", "safety_diagnosis"),
])
def test_safety_questions_never_reach_the_analysis(packages, q, intent):
    r = chat.answer(q, packages["t2d"])
    assert r["intent"] == intent
    assert "\n".join(r["answer"]).count("mg") == 0


def test_chat_never_uses_banned_wording_for_any_question(packages):
    qs = ["hi", "summary", "blood pressure", "will my weight go up", "what should I do", "medicines", "what is missing", "history", "sleep",
          "metabolic", "how does this work", "what should I ask my doctor", "how is my data quality", "asdfgh"]
    for p in packages.values():
        state = {}
        for q in qs:
            r = chat.answer(q, p, state)
            state = r["state"]
            assert r["answer"] and isinstance(r["suggestions"], list)
            for line in r["answer"]:
                # "diagnosis" appears only in negations ("not a diagnosis"); every other banned phrase must never appear
                assert not [b for b in banned_hits(line) if b != "diagnos"], line


def test_unknown_question_is_honest(packages):
    r = chat.answer("what is the capital of france", packages["control"])
    assert r["intent"] == "fallback" and "not sure" in r["answer"][0]


def test_empty_message_shows_help(packages):
    assert chat.answer("   ", packages["control"])["intent"] == "help"


# ---- heart-risk estimate and the questions around it
def test_pooled_cohort_equations_match_the_published_example():
    from prana.ai.risk import pce
    # Goff et al. 2014 worked example: white woman, 55, TC 213, HDL 50, SBP 120 untreated, non-smoker, no diabetes -> 2.1%
    assert round(pce("F", 55, 213, 50, 120, False, False, False), 1) == 2.1
    assert pce("F", 55, 213, 50, 160, False, False, False) > pce("F", 55, 213, 50, 120, False, False, False)   # higher BP, higher risk
    assert pce("F", 55, 213, 50, 120, False, True, False) > pce("F", 55, 213, 50, 120, False, False, False)    # smoking raises it


def test_risk_only_for_ages_40_to_79_and_explains_itself(packages):
    for p in packages.values():
        r = p["outlook"]["risk"]
        age = p["profile"]["age"]
        assert r["available"] == (40 <= age <= 79 and bool(r.get("inputs")))
        if r["available"]:
            assert 0 < r["percent"] < 100 and r["drivers"] and r["assumptions"]
            assert all(d["points"] >= 0 for d in r["drivers"] if not d["fixed"])
        else:
            assert r["reason"]


def test_heart_attack_chance_is_answered_with_its_factors_but_chest_pain_is_not(packages):
    p = next(x for x in packages.values() if x["outlook"]["risk"]["available"])
    r = chat.answer("What are the chances of me getting a heart attack?", p)
    text = " ".join(r["answer"])
    assert r["intent"] == "risk" and "in 100" in text and "What is pushing it up" in text and "assumed" in text
    assert chat.answer("I have chest pain", p)["intent"] == "safety_emergency"
    assert chat.answer("I think I'm having a heart attack", p)["intent"] == "safety_emergency"
    assert chat.answer("what is my stroke risk", p)["intent"] == "risk"


def test_risk_not_scored_for_young_patients_says_why(packages):
    young = next((x for x in packages.values() if not x["outlook"]["risk"]["available"]), None)
    if young:
        r = chat.answer("what is my risk of heart attack", young)
        assert r["intent"] == "risk" and "can’t give a percentage" in " ".join(r["answer"])


def test_language_model_rewording_is_rejected_when_it_changes_numbers():
    from prana.ai.llm import acceptable
    assert acceptable("Your HbA1c is 5.8 %.", "Your HbA1c is 5.8 %, a little high.")
    assert not acceptable("Your HbA1c is 5.8 %.", "Your HbA1c is 6.8 %.")
    assert not acceptable("Your level is 5.8.", "Your level is 5.8. You should stop taking it.")


# ---- every predictive question gets an answer; diagnosis and emergencies still do not
def test_diabetes_risk_is_a_range_from_a_published_score(packages):
    for p in packages.values():
        d = p["outlook"]["diabetes"]
        if d["available"]:
            assert d["score_min"] <= d["score_max"] and d["per100_min"] <= d["per100_max"] and d["assumptions"] and d["method"].startswith("FINDRISC")
        else:
            assert d["reason"]


def test_watchlist_covers_each_measure_outside_its_range_with_its_own_trend(packages):
    for p in packages.values():
        outside = [i for i in p["reference"]["items"] if i["flag"] != "within" and not i["soft"]]
        w = p["outlook"]["watch"]
        assert len(w["items"]) + len(w["more"]) <= len(outside)
        for item in w["items"]:
            assert item["points"] and item["direction"] in ("rising", "falling", "steady")
            assert item["projection"] is not None or item["note"]   # no projection is ever silent about why


@pytest.mark.parametrize("q,intent", [
    ("will I develop diabetes", "risk"), ("what are the chances I get diabetes", "risk"), ("what is the likelihood of me having a stroke", "risk"),
    ("what are my health risks", "risk"), ("will my blood pressure get worse", "predict"), ("will my cholesterol go up", "predict"),
    ("will my kidney function decline", "predict"), ("am I at risk of cancer", "predict"),
])
def test_predictive_questions_are_answered(packages, q, intent):
    r = chat.answer(q, packages["t2d"])
    assert r["intent"] == intent and r["answer"]


def test_unsupported_prediction_says_what_it_can_do(packages):
    text = " ".join(chat.answer("what is my chance of getting cancer", packages["t2d"])["answer"])
    assert "can’t estimate" in text and "heart" in text


def test_language_model_router_only_returns_one_of_our_questions():
    from prana.ai import llm
    assert llm.route("anything", chat.CANONICAL) is None   # off unless PRANA_LLM=1 and a key is set


def test_what_changed_question_is_answered_for_every_kind_of_patient(packages):
    for p in packages.values():
        r = chat.answer("did anything change for me?", p)
        assert r["intent"] == "changes" and r["answer"]
        assert ("Yes, something changed" in r["answer"][0]) == any(sc["surfaced"] for sc in p["scenarios"])
