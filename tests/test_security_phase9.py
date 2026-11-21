# ruff: noqa: E702, F401, F811
"""Security checks for the MedGemma, knowledge and Analytics additions: no secrets in files, none in logs, nothing sent without approval, patients kept apart."""
import logging
import re
from pathlib import Path

import pytest
from sqlalchemy import create_engine

from prana.ai import medgemma, medical_explain as M
from prana.api import analytics as A, auth
from prana.data import db
from test_medical_workflows import GOOD, good_with, package, world  # noqa: E402  (the same stand-in model world)

ROOT = Path(__file__).resolve().parents[1]
PW = "alpha-beta-gamma-11"
SECRET_PATTERNS = [r"sk-or-v1-[A-Za-z0-9]{20,}", r"AQ\.[A-Za-z0-9_-]{30,}", r"AIza[0-9A-Za-z_-]{30,}", r"hf_[A-Za-z0-9]{20,}", r"sk-ant-[A-Za-z0-9_-]{20,}", r"sk-[A-Za-z0-9]{32,}",
                   r"postgres(ql)?(\+\w+)?://[^:\s/]+:(?!secret@|pass@|password@|user@|\*+@|<)[^@\s{}]{6,}@", r"Bearer [A-Za-z0-9._-]{30,}"]


# ---------------------------------------------------------------- no secrets in any file that is shared
def test_no_key_or_password_is_written_in_any_shared_file():
    hits = []
    for top in ("web", "src", "config", "docs", "scripts", "tests"):
        for f in (ROOT / top).rglob("*"):
            if f.is_file() and f.suffix in (".js", ".py", ".md", ".yaml", ".yml", ".html", ".css", ".json", ".txt", ".example") and "__pycache__" not in f.parts:
                text = f.read_text(encoding="utf-8", errors="ignore")
                hits += [f"{f.relative_to(ROOT)}: {p}" for p in SECRET_PATTERNS if re.search(p, text)]
    for f in (ROOT / ".env.example", ROOT / "README.md", ROOT / "requirements.txt"):
        text = f.read_text(encoding="utf-8", errors="ignore")
        hits += [f"{f.name}: {p}" for p in SECRET_PATTERNS if re.search(p, text)]
    assert hits == []


def test_the_browser_code_never_names_a_model_key_setting():
    for f in (ROOT / "web").rglob("*.js"):
        text = f.read_text(encoding="utf-8")
        assert not re.search(r"PRANA_(LLM|MEDGEMMA|RERANK|EMBED)_KEY|ANTHROPIC_API_KEY|Authorization", text), f.name


def test_the_env_file_is_ignored_by_git():
    assert re.search(r"^\.env$", (ROOT / ".gitignore").read_text(encoding="utf-8"), re.M)


# ---------------------------------------------------------------- nothing sensitive in the logs
def test_logs_never_contain_the_question_the_key_the_address_or_patient_numbers(world, package, caplog):
    cfg, state, _ = world
    cfg["PRANA_MEDGEMMA_KEY"] = "secret-token-9f8e7d"
    cfg["PRANA_MEDGEMMA_URL"] = "https://secret-host.example/v1"
    caplog.set_level(logging.DEBUG)
    question = "My name is Alex Morgan, my phone is 555-0100 and my HbA1c is 6.99. How is my blood pressure?"
    for reply in (medgemma.MedGemmaError("auth"), "not json at all", good_with(medical_interpretations=["You have diabetes."]), good_with()):
        state["reply"] = lambda s, u, r=reply: r
        M._FAILED_UNTIL.clear()
        M.assess_question("P1", package, question)
        M._FAILED_UNTIL.clear()
        M.explain_analytics("P1", package, force=True)
    logs = "\n".join(r.getMessage() for r in caplog.records)
    for secret in ("secret-token-9f8e7d", "secret-host", "Alex Morgan", "555-0100", "6.99", "How is my blood pressure"):
        assert secret not in logs, secret
    facts_numbers = {str(m["recent"]).split()[0] for m in M.build_facts(package)["measures"] if m.get("recent")}
    assert not any(n in logs for n in facts_numbers if len(n) > 3)               # no patient value from the record either


def test_the_audit_log_records_topics_not_questions(workbooks, monkeypatch, tmp_path):
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from prana.api import server
    eng = create_engine(f"sqlite:///{tmp_path / 'a.db'}", future=True, connect_args={"check_same_thread": False})
    monkeypatch.setattr(db, "_engine", eng); db.init_db()
    monkeypatch.setattr(server, "_index", lambda: {"T2D": workbooks["t2d"]}); monkeypatch.setattr(server, "GUEST_ID", "T2D"); monkeypatch.setattr(auth, "_fails", {})
    server._analytics.hits.clear()
    with TestClient(server.app) as c:
        c.post("/api/guest")
        c.post("/api/analytics/ask", json={"question": "I have chest pain, my name is Alex Morgan"})
    from sqlalchemy import text
    with eng.connect() as con:
        rows = " ".join(str(r) for r in con.execute(text("select * from audit_log")).all())
    assert "ask" in rows and "Alex" not in rows and "chest" not in rows
    eng.dispose()


# ---------------------------------------------------------------- nothing leaves without approval
def test_a_record_that_is_not_approved_makes_no_network_call_at_all(world, package, monkeypatch):
    cfg, _, _ = world
    cfg["PRANA_CLOUD_AI_PATIENTS"] = "SOMEONE_ELSE"
    monkeypatch.setattr(medgemma, "_request", lambda *a, **k: pytest.fail("a request was made for a record that is not approved"))
    from prana.ai import knowledge
    monkeypatch.setattr(knowledge, "embed", lambda *a, **k: pytest.fail("an embeddings request was made"))
    assert M.explain_analytics("P1", package)["status"] == "blocked" and M.assess_question("P1", package, "How is my blood pressure?")["status"] == "blocked"
    assert M.compare_analytics("P1", package)["status"] in ("blocked", "disabled")


# ---------------------------------------------------------------- patients stay apart
def test_two_signed_in_patients_each_get_only_their_own_analytics(workbooks, monkeypatch, tmp_path):
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from prana.api import server
    eng = create_engine(f"sqlite:///{tmp_path / 'iso.db'}", future=True, connect_args={"check_same_thread": False})
    monkeypatch.setattr(db, "_engine", eng); db.init_db()
    monkeypatch.setattr(server, "_index", lambda: {"T2D": workbooks["t2d"], "HTN": workbooks["htn"]}); monkeypatch.setattr(server, "GUEST_ID", "T2D"); monkeypatch.setattr(auth, "_fails", {})
    db.set_user_hashes({"T2D": auth.hash_password(PW), "HTN": auth.hash_password(PW)})
    server._analytics.hits.clear()
    with TestClient(server.app) as a, TestClient(server.app) as b:
        assert a.post("/api/login", json={"id": "T2D", "password": PW}).status_code == 200 and b.post("/api/login", json={"id": "HTN", "password": PW}).status_code == 200
        da, db_ = a.get("/api/analytics").json(), b.get("/api/analytics").json()
        assert da["baseline"] != db_["baseline"] or da["overview"] != db_["overview"]
        for who, client, other in (("T2D", a, "HTN"), ("HTN", b, "T2D")):
            own = A.build_analytics(server._patient(who))
            got = client.get(f"/api/analytics?pid={other}&patient_id={other}").json()
            assert got["baseline"] == own["baseline"] and got["trend"] == own["trend"] and got["reference"]["items"] == own["reference"]["items"]
            assert client.get(f"/api/analytics/report?pid={other}").json()["sections"][0]["items"][0]["text"] == A.build_report(own, None, None, server._patient(who)["outlook"]["recommendations"])["sections"][0]["items"][0]["text"]
    eng.dispose()
