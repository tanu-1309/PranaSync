"""Insight-layer tests (Uday)."""
from prana.config import scenarios_config
from prana.data.loader import load_workbook
from prana.insight.pipeline import analyze_record, analyze_workbook

G = scenarios_config()["guardrails"]


def _scen(result, key):
    return next(s for s in result["scenarios"] if s["scenario"] == key)


def test_pattern_is_linked_to_history(workbooks):
    r, _, _ = analyze_workbook(workbooks["t2d"])
    t2d = _scen(r, "t2d")
    assert t2d["status"] == "pattern_with_context"
    assert any("glycemic" in c["text"].lower() for c in t2d["context"])
    assert t2d["evidence"], "evidence must list the signals"


def test_every_explanation_has_disclaimer_and_no_banned_words(workbooks):
    for p in workbooks.values():
        r, _, _ = analyze_workbook(p)
        for s in r["scenarios"]:
            if s["status"] == "not_applicable":
                continue
            text = s["explanation"]["text"]
            assert G["required_disclaimer"] in text
            body = text.replace(G["required_disclaimer"], "").lower()
            assert not any(b in body for b in G["banned_phrases"])


def test_missing_hba1c_is_requested(workbooks):
    rec = load_workbook(workbooks["t2d_missing"])
    r = analyze_record(rec)
    assert "hba1c" in {m["key"] for m in _scen(r, "t2d")["missing_data"]}


def test_hormone_labs_requested_for_pcos(workbooks):
    r, _, _ = analyze_workbook(workbooks["pcos_nohormones"])
    asked = {m["key"] for m in _scen(r, "pcos")["missing_data"]}
    assert {"testosterone", "lh_fsh_ratio"} <= asked
