"""Account page: view and edit your own details, download your data, and the model facts for the How it works page."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from prana.api import risk_routes
from prana.api.server import _risk, app
from prana.data import db, docstore
from prana.risk import model

needs_model = pytest.mark.skipif(model.load() is None, reason="risk model not trained")


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db.use_engine(create_engine(f"sqlite:///{tmp_path / 't.db'}", future=True))
    db.init_db()
    docstore.use_engine(create_engine(f"sqlite:///{tmp_path / 'documents.db'}", future=True))      # the document store is a database of its own: never touch the real one
    monkeypatch.setattr(docstore, "KEY_FILE", tmp_path / "key")
    monkeypatch.setattr(risk_routes, "UPLOAD_DIR", tmp_path / "uploads")
    _risk.hits.clear()                                  # the sign-up limit is per device and per minute; each test starts fresh
    return TestClient(app)


def signup(c, name="Jane Roe"):
    r = c.post("/api/register", json={"name": name, "password": "a-long-password-1"})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_edit_your_details_and_see_where_each_value_came_from(client):
    pid = signup(client)
    first = client.get("/api/profile").json()
    assert first["id"] == pid and first["values"]["name"] == "Jane Roe" and first["can_edit"] and first["fields"]["sex"]["choices"]
    r = client.put("/api/profile", json={"values": {"age": "52", "sex": "Female", "email": "jane@example.com", "phone": "+1 (519) 555-0100", "allergies": "Penicillin"}})
    assert r.status_code == 200, r.text
    got = r.json()
    assert got["values"]["age"] == 52 and got["source"]["age"] == "you" and got["values"]["email"] == "jane@example.com"
    me = client.get("/api/me").json()
    assert me["profile"]["age"] == 52 and me["profile"]["sex"] == "Female" and me["contact"]["email"] == "jane@example.com"
    r = client.put("/api/profile", json={"values": {"name": "Jane R"}})
    assert client.get("/api/profile").json()["values"]["name"] == "Jane R" and client.get("/api/profile").json()["values"]["age"] == 52     # an edit does not erase the others


def test_bad_values_are_refused_with_a_reason_and_nothing_is_saved(client):
    signup(client)
    for bad, word in (({"age": "200"}, "Age"), ({"age": "abc"}, "Age"), ({"email": "not-an-email"}, "Email"), ({"phone": "call me"}, "Phone"), ({"sex": "Robot"}, "Sex"),
                      ({"name": "<script>alert(1)</script>"}, "Name"), ({"allergies": "x" * 301}, "Allergies"), ({"height": "30"}, "Height")):
        r = client.put("/api/profile", json={"values": bad})
        assert r.status_code == 422 and word in r.json()["detail"], (bad, r.text)
    assert client.get("/api/profile").json()["source"]["email"] == "empty"
    r = client.put("/api/profile", json={"values": {"secret_field": "x"}})            # unknown fields are ignored, not stored
    assert r.status_code == 200 and "secret_field" not in db.get_profile(client.get("/api/profile").json()["id"])


def test_guests_can_look_but_not_edit_or_export_and_strangers_are_turned_away(client):
    assert TestClient(app).get("/api/profile").status_code == 401
    g = TestClient(app)
    g.post("/api/guest")
    assert g.get("/api/profile").json()["can_edit"] is False
    assert g.put("/api/profile", json={"values": {"age": "40"}}).status_code == 403 and g.get("/api/export").status_code == 403


def test_each_person_edits_only_their_own_details(client):
    a = signup(client, "A")
    client.put("/api/profile", json={"values": {"phone": "5195550100"}})
    other = TestClient(app)
    b = other.post("/api/register", json={"name": "B", "password": "another-long-pass-2"}).json()["id"]
    assert a != b and other.get("/api/profile").json()["values"]["phone"] == ""


@needs_model
def test_edited_age_and_sex_feed_the_risk_estimate_and_export_lists_everything(client):
    signup(client)
    client.put("/api/profile", json={"values": {"age": "70", "sex": "Male"}})
    risk = client.get("/api/risk").json()
    known = {k["key"]: k for k in risk["known"]}
    assert known["age"]["text"].startswith("70") and known["sex_male"]["from"] == "your profile"
    ex = client.get("/api/export").json()
    assert ex["details"]["age"] == 70 and "documents" in ex and "values_read_from_documents" in ex and ex["risk_classes"]


def test_models_page_facts_are_real_numbers_or_say_nothing(client):
    signup(client)
    m = client.get("/api/models").json()
    assert set(m) >= {"risk", "pattern", "forecast", "language_models"}
    if m["risk"]:
        assert m["risk"]["development_check"]["heart"]["complete"] > 0.5 and m["risk"]["top_parameters"]["diabetes"][0]["share"] > 0
    assert "text" in m["language_models"] and "insights" in m["language_models"]


@needs_model
def test_clinical_risk_detail_shows_every_value_and_its_share_but_never_a_probability(client):
    signup(client)
    client.post("/api/documents", files={"file": ("lab.txt", b"Age: 58\nSex: Male\nFasting glucose 148 mg/dL\nHbA1c: 7.1 %\nBlood pressure: 152/94 mmHg\nHeight 172 cm Weight 96 kg\nLDL cholesterol 162 mg/dL\n")})
    d = client.get("/api/clinical/risk").json()
    assert d["available"] and {a["area"] for a in d["areas"]} == {"heart", "diabetes", "blood_pressure"}
    dia = next(a for a in d["areas"] if a["area"] == "diabetes")
    assert dia["available"] and dia["rows"] and all(r["from"] == "lab.txt" for r in dia["rows"] if r["key"] in ("hba1c", "fasting_glucose"))
    assert 99 <= sum(r["share"] for r in dia["rows"]) <= 101 and all("attention" in r and r["monotone"] for r in dia["rows"])
    text = repr(d).lower()
    assert "_score" not in text and "probab" not in text.replace("not a probability", "")
    docs = client.get("/api/clinical/documents").json()["documents"]
    assert docs and docs[0]["values"][0]["original_value"] is not None and "extracted_text" not in docs[0] and docs[0]["text_characters"] > 20
    assert TestClient(app).get("/api/clinical/risk").status_code == 401


def test_values_history_follows_each_value_across_uploaded_documents(client):
    signup(client)
    old = b"Report date: 12 September 2026\nAge: 58\nSex: Male\nFasting glucose 148 mg/dL\nHbA1c: 7.1 %\nBlood pressure: 152/94 mmHg\n"
    new = b"Report date: 12 November 2026\nFasting glucose 132 mg/dL\nHbA1c: 6.7 %\nLDL cholesterol 141 mg/dL\n"
    assert client.post("/api/documents", files={"file": ("a.txt", old)}).status_code == 200
    assert client.post("/api/documents", files={"file": ("b.txt", new)}).status_code == 200
    rows = {r["param"]: r for r in client.get("/api/values/history").json()["values"]}
    h = rows["hba1c"]
    assert [p["value"] for p in h["points"]] == [7.1, 6.7] and [p["date"] for p in h["points"]] == ["2026-09-12", "2026-11-12"] and h["change_pct"] == -5.6
    assert [p["document"] for p in h["points"]] == ["a.txt", "b.txt"] and len(rows["ldl"]["points"]) == 1 and rows["ldl"]["change_pct"] is None
    assert "sex_male" not in rows and "smoking" not in rows                               # categories have no trend
    assert TestClient(app).get("/api/values/history").status_code == 401
