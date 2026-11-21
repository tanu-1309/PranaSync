"""Document-by-document risk: reading values from uploads, the explainable model with parts missing, registering, and the rules around it."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from prana.api import risk_routes
from prana.api.server import _risk, app
from prana.data import db, docstore
from prana.risk import model
from prana.risk.extract import extract, find_date

LAB = (b"Patient: Jane Roe   Date of birth: 1971-04-02   Sex: Female\nReport date: 14 March 2026\nFasting glucose   112 mg/dL   (70-99)\nHbA1c: 6.1 %\n"
       b"LDL cholesterol  4.1 mmol/L\nHDL-C 1.1 mmol/L\nTotal Cholesterol: 210 mg/dL\nTriglycerides 180\nBlood pressure: 138/88 mmHg\nHeight 165 cm  Weight 82 kg\nSmoking: former\n")
needs_model = pytest.mark.skipif(model.load() is None, reason="risk model not trained (python scripts/train_risk_model.py)")


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db.use_engine(create_engine(f"sqlite:///{tmp_path / 't.db'}", future=True))
    db.init_db()
    docstore.use_engine(create_engine(f"sqlite:///{tmp_path / 'documents.db'}", future=True))      # the document store is a database of its own: never touch the real one
    monkeypatch.setattr(docstore, "KEY_FILE", tmp_path / "key")
    monkeypatch.setattr(risk_routes, "UPLOAD_DIR", tmp_path / "uploads")
    _risk.hits.clear()                                  # the sign-up limit is per device; every test starts with a clean slate
    return TestClient(app)


def register(c, name="Jane"):
    r = c.post("/api/register", json={"name": name, "password": "a-long-password-1"})
    assert r.status_code == 200, r.text
    return r.json()["id"]


# ------------------------------------------------------------------ reading documents
def test_values_units_and_dates_are_read_correctly_and_the_birth_date_is_not_the_report_date():
    ex = extract("lab.txt", LAB)
    got = {o["param"]: o for o in ex.observations}
    assert got["fasting_glucose"]["value"] == 112 and got["hba1c"]["value"] == 6.1 and got["sbp"]["value"] == 138 and got["dbp"]["value"] == 88
    assert abs(got["ldl"]["value"] - 158.5) < 0.2 and abs(got["hdl"]["value"] - 42.5) < 0.2          # mmol/L converted to mg/dL
    assert got["bmi"]["value"] == pytest.approx(30.1, abs=0.1) and got["smoking"]["value"] == 1 and got["sex_male"]["value"] == 0
    assert str(got["hba1c"]["observed_on"]) == "2026-03-14"
    assert all(o["source_text"] for o in ex.observations)           # every value says where it came from


def test_implausible_values_unsupported_types_and_unreadable_files_are_refused_with_a_reason():
    ex = extract("x.txt", b"HbA1c: 61 %\nSystolic only here\nBlood pressure 400/30\n")
    assert not any(o["param"] == "hba1c" for o in ex.observations) and ex.notes
    assert "not supported" in extract("program.exe", b"x" * 100).error and "image" in extract("scan.png", b"x" * 100).error          # a damaged picture is refused with a reason
    assert "10 MB" in extract("big.txt", b"x" * (10 * 1024 * 1024 + 1)).error
    assert "could not find" in extract("none.txt", b"Hello, this note has no health values in it at all.").error
    assert "not a real PDF" in extract("fake.pdf", b"this is not a pdf at all, just text").error
    assert find_date("born 1990-01-01") is not None


def test_a_csv_table_and_wide_daily_columns_are_read():
    ex = extract("labs.csv", b"Test,Result,Unit\nFasting glucose,5.8,mmol/L\nHbA1c,39,mmol/mol\nLDL cholesterol,120,mg/dL\n")
    got = {o["param"]: o["value"] for o in ex.observations}
    assert got["fasting_glucose"] == pytest.approx(104.5, abs=0.2) and got["hba1c"] == pytest.approx(5.7, abs=0.1) and got["ldl"] == 120
    wide = extract("v.csv", b"Date,Systolic BP,Diastolic BP\n2026-01-01,120,80\n2026-01-02,130,84\n")
    assert {o["param"]: o["value"] for o in wide.observations} == {"sbp": 125, "dbp": 82}


# ------------------------------------------------------------------ the model
@needs_model
def test_a_single_document_gives_an_answer_and_says_what_is_missing_without_any_percentage():
    r = model.public(model.predict({"age": 55, "sex_male": 0, "fasting_glucose": 112, "hba1c": 6.1}))
    by = {a["area"]: a for a in r["areas"]}
    assert by["diabetes"]["level"] in ("moderate", "higher") and by["diabetes"]["evidence"] >= 25
    assert by["diabetes"]["drivers"] and by["diabetes"]["missing"] and by["diabetes"]["ask_for"]
    assert by["heart"]["level"] == "unknown" and "Not enough" in by["heart"]["level_text"] and not by["heart"]["drivers"]     # too little to say anything about the heart
    text = repr(r)
    assert "_score" not in text and "probab" not in text.lower() and "percent" not in text.lower()


@needs_model
def test_more_documents_raise_evidence_strength_and_directions_never_point_the_wrong_way():
    few = model.predict({"age": 50, "sex_male": 1, "sbp": 150, "dbp": 95})
    many = model.predict({"age": 50, "sex_male": 1, "sbp": 150, "dbp": 95, "bmi": 31, "ldl": 170, "hdl": 38, "hba1c": 6.8, "fasting_glucose": 130, "triglycerides": 220, "steps": 3000, "smoking": 2})
    assert all(m["evidence"] >= f["evidence"] for f, m in zip(few["areas"], many["areas"])) and any(m["evidence"] > f["evidence"] for f, m in zip(few["areas"], many["areas"]))
    base = {"age": 50, "sex_male": 1, "sbp": 120, "dbp": 78, "bmi": 24, "ldl": 100, "hdl": 55, "hba1c": 5.2, "fasting_glucose": 90, "triglycerides": 110, "steps": 9000, "smoking": 0, "total_chol": 180}
    risky = dict(base, ldl=190, hba1c=6.9, fasting_glucose=140, sbp=160, dbp=100, bmi=35, smoking=2, steps=2000)
    for a, b in zip(model.predict(base)["areas"], model.predict(risky)["areas"]):
        rank = {"lower": 0, "moderate": 1, "higher": 2}
        assert rank[b["level"]] >= rank[a["level"]]
    assert all(d["direction"] in ("raises", "lowers") for a in many["areas"] for d in a["drivers"])


# ------------------------------------------------------------------ the API
@needs_model
def test_register_upload_read_risk_delete_and_duplicates(client):
    pid = register(client)
    assert pid.startswith("PS") and client.get("/api/me").json()["mode"] == "uploads"
    r = client.post("/api/documents", files={"file": ("lab.txt", LAB)})
    assert r.status_code == 200
    body = r.json()
    assert len(body["read"]) >= 10 and body["risk"]["areas"] and "percent" not in repr(body["risk"]).lower()
    assert client.post("/api/documents", files={"file": ("again.txt", LAB)}).status_code == 409               # same content twice
    assert client.post("/api/documents", files={"file": ("pic.png", b"x" * 100)}).status_code == 422
    docs = client.get("/api/documents").json()["documents"]
    assert len(docs) == 1 and docs[0]["n_values"] == len(body["read"])
    before = client.get("/api/risk").json()
    assert client.delete(f"/api/documents/{docs[0]['id']}").status_code == 200
    after = client.get("/api/risk").json()
    assert after["documents"] == 0 and all(a["level"] == "unknown" for a in after["areas"]) and before["areas"] != after["areas"]
    assert db.read_observations(pid) == []                                                                       # the values go with the document


@needs_model
def test_each_person_sees_only_their_own_documents_and_guests_cannot_upload(client):
    a = register(client, "A")
    client.post("/api/documents", files={"file": ("lab.txt", LAB)})
    doc_id = client.get("/api/documents").json()["documents"][0]["id"]
    other = TestClient(app)
    b = other.post("/api/register", json={"name": "B", "password": "another-long-pass-2"}).json()["id"]
    assert b != a and other.get("/api/documents").json()["documents"] == []
    assert other.delete(f"/api/documents/{doc_id}").status_code == 404                                           # cannot delete someone else's
    assert TestClient(app).get("/api/risk").status_code == 401
    guest = TestClient(app)
    guest.post("/api/guest")
    assert guest.post("/api/documents", files={"file": ("lab.txt", LAB)}).status_code == 403


def test_registration_rules(client):
    assert client.post("/api/register", json={"name": "x", "password": "short"}).status_code == 422
    assert client.post("/api/register", json={"name": "x", "password": "password123"}).status_code == 422
    pid = register(client)
    c2 = TestClient(app)
    assert c2.post("/api/login", json={"id": pid, "password": "a-long-password-1"}).status_code == 200        # the new account can sign in again
    assert c2.post("/api/login", json={"id": pid, "password": "wrong-password-xx"}).status_code == 401


def test_pdf_tables_that_come_out_one_cell_per_line_are_read():
    cells = b"Test\nResult\nUnit\nFasting glucose\n148\nmg/dL\n70 - 99\nHbA1c\n7.1\n%\n4.0 - 5.6\nLDL cholesterol\n3.8\nmmol/L\nBlood pressure: 152/94 mmHg\nExercise: 1 session per week\nExercise: 30 minutes daily\n"
    got = {o["param"]: o["value"] for o in extract("cells.txt", cells).observations}
    assert got["fasting_glucose"] == 148 and got["hba1c"] == 7.1 and abs(got["ldl"] - 146.9) < 0.2 and got["sbp"] == 152
    assert got["exercise_sessions"] == 1                               # the "30 minutes daily" line is not a count of sessions


@needs_model
def test_a_person_from_the_training_workbooks_can_upload_too(client):
    """People like PC0001 sign in with a `users` row but have no `accounts` row; their first upload must still work (it used to fail with a foreign-key error)."""
    pid = register(client)
    with db.engine().begin() as con:
        con.execute(db.documents.delete())
        con.execute(db.accounts.delete().where(db.accounts.c.patient_id == pid))
    r = client.post("/api/documents", files={"file": ("lab.txt", LAB)})
    assert r.status_code == 200, r.text
    assert len(client.get("/api/documents").json()["documents"]) == 1


def test_an_age_the_document_states_beats_one_worked_out_from_a_birth_date_on_an_earlier_line():
    ex = extract("v.txt", b"Patient: Jo Smith  DOB 1969-05-05\nVisit 3 June 2026. Age 58. Sex: Male.\nFasting glucose 148 mg/dL\n")
    assert {o["param"]: o["value"] for o in ex.observations}["age"] == 58
    only_dob = extract("v.txt", b"Date of birth: 1969-05-05\nFasting glucose 148 mg/dL\n")
    assert {o["param"]: o["value"] for o in only_dob.observations}["age"] >= 55          # with no stated age, the birth date is used


def test_a_usual_range_printed_before_the_result_is_not_taken_as_the_result():
    doc = (b"Lab report 12 October 2026   Patient age 54   Sex: Female\nFasting glucose (70-99 mg/dL)    131 mg/dL\nHbA1c (4.0-5.6 %)    6.6 %\n"
           b"LDL cholesterol (< 100 mg/dL)    171 mg/dL\nTriglycerides (target < 150)    205 mg/dL\nGlucose (112 mg/dL) after fasting\n")
    got = {o["param"]: o["value"] for o in extract("r.txt", doc).observations}
    assert got["fasting_glucose"] == 131 and got["hba1c"] == 6.6 and got["ldl"] == 171 and got["triglycerides"] == 205
    only = {o["param"]: o["value"] for o in extract("r.txt", b"Fasting glucose (112 mg/dL) taken at 8 am\nHbA1c: 6.1 %\n").observations}
    assert only["fasting_glucose"] == 112                       # a result that is itself in brackets is still read
