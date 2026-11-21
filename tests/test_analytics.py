# ruff: noqa: E702
"""The Analytics & Intelligence page's backend: every number is one the analysis already computed (or recomputed with the same function), nothing is made up."""
import json

import pytest
from sqlalchemy import create_engine

from prana.api import analytics as A
from prana.api.payload import build_payload
from prana.data import db
from prana.insight.pipeline import analyze_workbook


@pytest.fixture(scope="module")
def package(workbooks):
    return build_payload(*analyze_workbook(workbooks["t2d"]))


@pytest.fixture(scope="module")
def stats(package):
    return A.build_analytics(package, "2026-11-15T10:00:00")


# ---------------------------------------------------------------- the numbers are the analysis's own
def test_baseline_and_trend_values_are_the_stored_analysis_values(package, stats):
    stored = {(sc["scenario"], k): a for sc in package["scenarios"] if sc["status"] != "not_applicable" for k, a in sc["signals"].items()}
    assert len(stats["baseline"]) == len(stored)
    changed = [r for r in stats["baseline"] if r["status"] == "changed" and r["kind"] == "daily"]
    assert changed, "the planted pattern should give at least one changed daily signal"
    for r in changed:
        a = next(a for (_, k), a in stored.items() if k == r["key"])
        assert (r["baseline_mean"], r["recent_mean"], r["effect_size"], r["change"], r["min_change"]) == (a["baseline_mean"], a["recent_mean"], a["effect_size"], a["change"], a["min_change"])
        assert r["baseline_period"][0] == package["series"][r["key"]]["start"] and r["recent_period"][1] == package["window"][1]
    for t in stats["trend"]:
        if t["statistic_z"] is not None:
            assert abs(t["recomputed_p"] - t["p_value"]) < 0.01            # the same Mann-Kendall function on the stored series agrees with the stored p-value
            assert (t["trend"] == "rising") == (t["statistic_z"] > 0 and t["p_value"] < 0.05) or t["trend"] != "rising"


def test_change_points_are_only_for_changed_signals_with_before_and_after_values(stats):
    cps = stats["change_points"]
    assert cps["ruptures_available"] is True and "Binseg" in cps["algorithm"] and cps["rows"] and "not a finding of no change point" in cps["note"]
    for r in cps["rows"]:
        assert r["breakpoint"] and r["before"]["n"] > 0 and r["after"]["n"] > 0 and r["before"]["mean"] != r["after"]["mean"]
    assert cps["signals_not_run"] >= 0


def test_multi_signal_reference_risk_forecast_and_missing_data_come_from_the_package(package, stats):
    surfaced = [m for m in stats["multi_signal"] if m["surfaced"]]
    assert len(surfaced) == sum(1 for sc in package["scenarios"] if sc.get("surfaced")) and all(m["n_signals"] >= 3 for m in surfaced)
    assert stats["reference"]["counts"] == package["reference"]["counts"] and len(stats["reference"]["items"]) == len(package["reference"]["items"])
    assert isinstance(stats["risk"]["areas"], list) and "No clinical validation" in stats["risk"]["validation"]
    assert stats["missing"]["rules_triggered"] == [{"area": sc["title"], "item": m["item"], "reason": m["reason"]} for sc in package["scenarios"] if sc["status"] != "not_applicable" for m in sc["missing_data"]]
    assert all(c["projection"] for c in stats["forecast"]["charts"]) and "p below 0.001" in stats["forecast"]["gate"]


def test_the_overview_counts_are_consistent_and_a_blank_is_never_zero(package, stats):
    o = stats["overview"]
    assert o["signals_analysed"] + o["signals_insufficient_data"] == o["signals_in_scope"] and o["record_to"] == package["window"][1] and o["analysis_built_at"] == "2026-11-15T10:00:00"
    assert 0 < o["data_completeness"] <= 1
    for s in stats["missing"]["series"]:
        assert s["with_reading"] == sum(1 for v in package["series"][s["key"]]["v"] if v is not None) and s["with_reading"] <= s["days"]


def test_no_correlation_is_claimed_and_the_whole_result_is_json_safe(stats):
    assert stats["correlation"]["available"] is False and "co-occurrence" in stats["correlation"]["note"]
    json.dumps(stats, allow_nan=False)                                          # no NaN or infinity reaches the browser


# ---------------------------------------------------------------- architecture
def test_the_architecture_lists_only_parts_that_exist_with_their_running_state():
    off = {"routes": {"general": "nemotron", "medical": "medgemma"}, "nemotron": {"enabled": True, "model": "nvidia/test"}, "medgemma": {"enabled": False, "configured": False},
           "comparison_enabled": False, "knowledge": {"sources": 0, "passages": 0, "mode": "none"}}
    arch = A.architecture(off)
    by = {n["id"]: n for n in arch["nodes"]}
    assert len(arch["nodes"]) == 10 and all(n["implemented"] for n in arch["nodes"]) and all(all(n["files_found"].values()) for n in arch["nodes"])
    assert by["medgemma"]["state"].startswith("off") and by["nemotron"]["state"] == "on (nvidia/test)" and "empty" in by["knowledge"]["state"] and "Comparison off" in by["router"]["state"]
    assert set(by["router"]["to"]) == {"nemotron", "medgemma"} and by["safety"]["to"] == ["dashboard"]
    on = {**off, "medgemma": {"enabled": True, "configured": True}, "knowledge": {"sources": 2, "passages": 9, "mode": "keyword"}}
    by = {n["id"]: n for n in A.architecture(on)["nodes"]}
    assert by["medgemma"]["state"] == "on" and "9 passages" in by["knowledge"]["state"]


# ---------------------------------------------------------------- the report
def test_the_report_labels_every_line_by_who_produced_it_and_says_when_ai_is_missing(package, stats):
    r = A.build_report(stats, None, None, package["outlook"]["recommendations"])
    assert [s["title"] for s in r["sections"]][:3] == ["Overall analytical summary", "Statistical findings", "Important trends"] and len(r["sections"]) == 12
    kinds = {i["kind"] for s in r["sections"] for i in s["items"]}
    assert kinds <= {"statistical", "rule_based", "fixed", "unavailable"} and "ai" not in kinds and r["models"] == {"nemotron": False, "medgemma": False}
    assert "No part of this report has been clinically validated" in json.dumps(r)


def test_ai_lines_appear_only_from_stored_results_and_are_tagged_ai(package, stats):
    nem = {"status": "ok", "headline": "A steady record.", "model_name": "nvidia/test"}
    med = {"status": "ok", "model": {"model_name": "google/medgemma-1.5-4b-it"}, "assessment": {"medical_interpretations": ["An interpretation."], "supporting_evidence": ["Evidence."], "missing_information": ["Waist"],
           "recommended_next_steps": ["Talk to your care team."], "limitations": ["Not a diagnosis."], "uncertainty": ["Cause unknown."]}, "references": [{"title": "T", "source": "S", "published": "2024", "url": "https://www.who.int/x", "use": "clinical_guidance"}]}
    r = A.build_report(stats, nem, med, package["outlook"]["recommendations"])
    ai = [i["text"] for s in r["sections"] for i in s["items"] if i["kind"] == "ai"]
    assert {"A steady record.", "An interpretation.", "Evidence.", "Waist", "Talk to your care team.", "Not a diagnosis.", "Cause unknown.", "T (S, 2024)"} <= set(ai) and r["models"] == {"nemotron": True, "medgemma": True}


# ---------------------------------------------------------------- the routes
@pytest.fixture()
def site(workbooks, monkeypatch, tmp_path):
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from prana.api import auth, server
    eng = create_engine(f"sqlite:///{tmp_path / 'a.db'}", future=True, connect_args={"check_same_thread": False})
    monkeypatch.setattr(db, "_engine", eng)
    db.init_db()
    monkeypatch.setattr(server, "_index", lambda: {"T2D": workbooks["t2d"], "HTN": workbooks["htn"]})
    monkeypatch.setattr(server, "GUEST_ID", "T2D")
    monkeypatch.setattr(auth, "_fails", {})
    server._analytics.hits.clear()
    with TestClient(server.app) as c:
        yield c, server
    eng.dispose()


def test_every_analytics_route_needs_sign_in(site):
    c, _ = site
    for path in ("/api/analytics", "/api/analytics/summary", "/api/analytics/insights", "/api/analytics/compare", "/api/analytics/report"):
        assert c.get(path).status_code == 401, path


def test_the_statistics_route_returns_the_page_data_for_the_signed_in_patient_only(site):
    c, _ = site
    c.post("/api/guest")
    r = c.get("/api/analytics").json()
    assert {"overview", "baseline", "trend", "change_points", "multi_signal", "reference", "risk", "forecast", "missing", "charts", "architecture", "models"} <= r.keys()
    assert r["overview"]["record_from"] and r["overview"]["analysis_built_at"] is not None
    other = c.get("/api/analytics?pid=HTN&patient_id=HTN").json()            # the patient comes from the session, never from a parameter
    assert other["overview"] == r["overview"]
    assert len(json.dumps(r)) < 600_000                                       # aggregated results, not the timeline


def test_model_panels_report_unavailable_states_honestly_and_never_leak_settings(site, monkeypatch):
    from prana.ai import medgemma, model_router
    c, _ = site
    c.post("/api/guest")
    assert c.get("/api/analytics/model/nemotron").status_code == 404                   # the old per-model route is gone: the page uses /summary and /insights
    assert c.get("/api/analytics/summary?cached_only=1").json()["status"] == "not_generated"
    assert c.get("/api/analytics/insights?cached_only=1").json()["status"] == "not_generated"
    assert c.get("/api/analytics/insights").json()["status"] == "blocked"             # this record is not approved for an external model, so nothing is sent
    assert c.get("/api/analytics/compare").json()["status"] == "disabled"
    cfg = {"PRANA_MEDGEMMA_ENABLED": "1", "PRANA_MEDGEMMA_URL": "https://secret-host.example/v1", "PRANA_MEDGEMMA_KEY": "secret-token"}
    for mod in (medgemma, model_router):
        monkeypatch.setattr(mod, "setting", lambda n, d=None: cfg.get(n, d))
    assert c.get("/api/analytics/insights?cached_only=1").json()["status"] == "not_generated"
    body = json.dumps([c.get(p).json() for p in ("/api/analytics", "/api/analytics/report", "/api/analytics/insights?cached_only=1", "/api/analytics/summary?cached_only=1")])
    assert "secret-token" not in body and "secret-host" not in body


def test_the_model_routes_are_rate_limited_and_the_report_never_triggers_a_model(site):
    c, server = site
    c.post("/api/guest")
    codes = [c.get("/api/analytics/summary").status_code for _ in range(8)]
    assert codes[:6] == [200] * 6 and codes[6:] == [429, 429]
    r = c.get("/api/analytics/report").json()
    assert r["models"] == {"nemotron": False, "medgemma": False} and len(r["sections"]) == 12


# ---------------------------------------------------------------- the question route and the cost of a page view
def test_the_question_route_needs_sign_in_and_the_safety_gate_runs_first(site):
    c, _ = site
    assert c.post("/api/analytics/ask", json={"question": "hello"}).status_code == 401
    c.post("/api/guest")
    for q, key in (("I have chest pain", "safety_emergency"), ("Should I stop my medicine?", "safety_medicine"), ("Do I have diabetes?", "safety_diagnosis")):
        r = c.post("/api/analytics/ask", json={"question": q}).json()
        assert r["status"] == "safety_reply" and r["safety"]["deterministic"] == [key] and r["assessment"] is None
    blocked = c.post("/api/analytics/ask", json={"question": "How is my blood pressure?"}).json()
    assert blocked["status"] == "blocked"                                      # this record is not approved for an external model, so nothing is sent


def test_the_question_route_is_rate_limited(site):
    c, _ = site
    c.post("/api/guest")
    codes = [c.post("/api/analytics/ask", json={"question": "I have chest pain"}).status_code for _ in range(8)]
    assert codes[:6] == [200] * 6 and codes[6:] == [429, 429]


def test_a_page_view_never_reads_the_timeline_table_and_uses_few_queries(site):
    from sqlalchemy import event
    c, _ = site
    c.post("/api/guest")
    c.get("/api/analytics")                                                    # the first call may build and store the record
    seen = []
    event.listen(db.engine(), "before_cursor_execute", lambda conn, cur, stmt, *a: seen.append(stmt))
    for path in ("/api/analytics", "/api/analytics/report", "/api/analytics/summary?cached_only=1", "/api/analytics/insights?cached_only=1"):
        assert c.get(path).status_code == 200
    reads = [q for q in seen if q.lstrip().upper().startswith("SELECT")]
    assert reads and not any("timeline" in q.lower() for q in seen)           # the 5 million timeline rows are never fetched for the dashboard
    assert len(reads) < 40                                                    # still a handful per request: the risk classes read three small tables (uploaded values, documents, profile)
