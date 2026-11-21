"""The separate document store (one JSON document per upload), the review of what was read, and the lock: owner when signed in, or an administrator."""
import base64
import datetime

import pytest
from cryptography.exceptions import InvalidTag
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select

from prana.api import risk_routes
from prana.api.server import _risk, app
from prana.data import db, docstore
from prana.risk import model

LAB = (b"Patient: Jane Roe   Sex: Female   Age: 58 years\nReport date: 14 March 2026\nFasting glucose   148 mg/dL\nHbA1c: 7.1 %\nLDL cholesterol 162 mg/dL\n"
       b"Blood pressure: 152/94 mmHg\nHeight 165 cm  Weight 82 kg\nSmoking: former\n")
needs_model = pytest.mark.skipif(model.load() is None, reason="risk model not trained")


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db.use_engine(create_engine(f"sqlite:///{tmp_path / 'main.db'}", future=True))
    db.init_db()
    docstore.use_engine(create_engine(f"sqlite:///{tmp_path / 'documents.db'}", future=True))
    monkeypatch.setattr(risk_routes, "UPLOAD_DIR", tmp_path / "uploads")
    monkeypatch.setattr(docstore, "KEY_FILE", tmp_path / "key")
    _risk.hits.clear()
    return TestClient(app)


def person(c, name="Jane"):
    r = c.post("/api/register", json={"name": name, "password": "a-long-password-1"})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def upload(c, data=LAB, name="lab.txt"):
    r = c.post("/api/documents", files={"file": (name, data)})
    assert r.status_code == 200, r.text
    return r.json()["document"]["id"]


def test_each_upload_becomes_a_json_document_in_a_separate_database_with_times_and_text(client):
    pid = person(client)
    doc_id = upload(client)
    assert str(docstore.engine().url) != str(db.engine().url)                                  # a database of its own
    d = docstore.get(docstore.Actor(pid), pid, doc_id)
    assert d["source"]["filename"] == "lab.txt" and d["source"]["type"] == "txt" and len(d["source"]["sha256"]) == 64
    assert d["uploaded_at"].endswith("+00:00") and d["extracted_at"] and d["status"] == "needs_review" and d["reviewed_at"] is None
    assert "Fasting glucose" in d["extracted_text"]
    v = {x["param"]: x for x in d["values"]}
    assert v["hba1c"]["value"] == 7.1 and v["hba1c"]["original_value"] == 7.1 and v["hba1c"]["source_text"] and v["sbp"]["value"] == 152


def test_what_is_stored_is_sealed_so_the_database_file_alone_shows_nothing(client, tmp_path):
    pid = person(client)
    doc_id = upload(client)
    with docstore.engine().connect() as con:
        row = con.execute(select(docstore.store)).mappings().one()
    raw = base64.b64decode(row["sealed"])
    assert raw.startswith(b"PSv1") and b"Fasting glucose" not in raw and b"lab.txt" not in raw and b"Jane" not in raw
    saved = next((tmp_path / "uploads" / pid).glob(f"{doc_id}.*")).read_bytes()
    assert saved.startswith(b"PSv1") and b"Fasting glucose" not in saved                       # the uploaded file itself is sealed too
    with pytest.raises(InvalidTag):                                                            # a sealed document moved to another person's row will not open
        docstore.open_bytes("PS000000", doc_id, raw)


def test_review_lets_only_the_values_be_changed_and_keeps_the_history(client):
    pid = person(client)
    doc_id = upload(client)
    r = client.get(f"/api/documents/{doc_id}").json()
    assert r["can_edit"] and r["document"]["values"][0]["original_value"] is not None
    before = {o["param"]: o["value"] for o in db.read_observations(pid)}
    out = client.put(f"/api/documents/{doc_id}/values", json={"edits": {"sbp": {"value": 128}, "hba1c": {"ignore": True}, "smoking": {"value": 0}}})
    assert out.status_code == 200, out.text
    d = out.json()["document"]
    assert d["status"] == "confirmed" and d["reviewed_at"]
    v = {x["param"]: x for x in d["values"]}
    assert v["sbp"]["value"] == 128 and v["sbp"]["edited"] and v["sbp"]["original_value"] == 152 and v["hba1c"]["ignored"] and v["smoking"]["text"] == "never"
    assert {h["param"] for h in d["edit_history"]} >= {"sbp", "hba1c", "smoking"}
    after = {o["param"]: o["value"] for o in db.read_observations(pid)}
    assert after["sbp"] == 128 and "hba1c" not in after and before["hba1c"] == 7.1            # the risk picture now uses the corrected values
    assert "Fasting glucose" in docstore.get(docstore.Actor(pid), pid, doc_id)["extracted_text"]   # the text is never changed
    back = client.put(f"/api/documents/{doc_id}/values", json={"edits": {"hba1c": {"ignore": False}}}).json()["document"]
    assert not {x["param"]: x for x in back["values"]}["hba1c"]["ignored"] and "hba1c" in {o["param"] for o in db.read_observations(pid)}


def test_bad_corrections_are_refused_and_nothing_changes(client):
    pid = person(client)
    doc_id = upload(client)
    for edits, word in (({"sbp": {"value": 999}}, "outside"), ({"sbp": {"value": "abc"}}, "number"), ({"smoking": {"value": 7}}, "listed options"),
                        ({"made_up": {"value": 1}}, "not read from the document")):
        r = client.put(f"/api/documents/{doc_id}/values", json={"edits": edits})
        assert r.status_code == 422 and word in r.json()["detail"], (edits, r.text)
    assert docstore.get(docstore.Actor(pid), pid, doc_id)["status"] == "needs_review"
    assert {o["param"]: o["value"] for o in db.read_observations(pid)}["sbp"] == 152


def test_only_the_owner_can_open_or_change_a_document_and_a_stranger_gets_not_found(client):
    a = person(client, "A")
    doc_id = upload(client)
    other = TestClient(app)
    b = other.post("/api/register", json={"name": "B", "password": "another-long-pass-2"}).json()["id"]
    assert b != a
    assert other.get(f"/api/documents/{doc_id}").status_code == 404
    assert other.put(f"/api/documents/{doc_id}/values", json={"edits": {"sbp": {"value": 100}}}).status_code == 404
    assert other.get("/api/admin/people").status_code == 403
    assert TestClient(app).get(f"/api/documents/{doc_id}").status_code == 401
    with pytest.raises(docstore.AccessDenied):
        docstore.get(docstore.Actor(b), a, doc_id)
    with pytest.raises(docstore.AccessDenied):
        docstore.all_for(docstore.Actor(b), a)
    assert docstore.get(docstore.Actor(a), a, doc_id)["doc_id"] == doc_id
    guest = TestClient(app)
    guest.post("/api/guest")
    assert guest.put(f"/api/documents/{doc_id}/values", json={"edits": {}}).status_code == 403


def test_an_administrator_can_read_any_document_but_not_change_it_and_every_look_is_logged(client, monkeypatch):
    a = person(client, "A")
    doc_id = upload(client)
    admin = TestClient(app)
    adm = admin.post("/api/register", json={"name": "Admin", "password": "an-admin-password-3"}).json()["id"]
    assert admin.get("/api/admin/people").status_code == 403                                  # not an administrator yet
    monkeypatch.setenv("PRANA_ADMIN_IDS", adm)
    assert admin.get("/api/me").json()["admin"] is True and client.get("/api/me").json()["admin"] is False
    people = admin.get("/api/admin/people").json()["people"]
    assert [p["patient_id"] for p in people] == [a] and people[0]["documents"] == 1
    docs = admin.get(f"/api/admin/people/{a}/documents").json()["documents"]
    assert docs[0]["filename"] == "lab.txt"
    one = admin.get(f"/api/admin/people/{a}/documents/{doc_id}").json()
    assert one["can_edit"] is False and "Fasting glucose" in one["document"]["extracted_text"]
    with pytest.raises(docstore.AccessDenied):
        docstore.put(docstore.Actor(adm, admin=True), docstore.get(docstore.Actor(a), a, doc_id))     # read-only for administrators
    assert admin.put(f"/api/documents/{doc_id}/values", json={"edits": {"sbp": {"value": 100}}}).status_code == 404   # the normal route only opens your own
    other = TestClient(app)
    other.post("/api/register", json={"name": "C", "password": "third-long-pass-4"})
    assert other.get("/api/admin/people").status_code == 403
    with db.engine().connect() as con:
        events = [r[0] for r in con.execute(select(db.audit_log.c.event).where(db.audit_log.c.patient_id == adm))]
    assert "admin_document_view" in events and "admin_denied" in events


def test_deleting_removes_the_stored_document_and_a_document_from_before_the_store_is_rebuilt(client):
    pid = person(client)
    doc_id = upload(client)
    assert client.delete(f"/api/documents/{doc_id}").status_code == 200
    assert docstore.get(docstore.Actor(pid), pid, doc_id) is None and client.get(f"/api/documents/{doc_id}").status_code == 404
    old = "11111111-1111-1111-1111-111111111111"             # uploaded when there was no document store: only the main database knows it
    db.add_document({"doc_id": old, "patient_id": pid, "filename": "old.txt", "sha256": "a" * 64, "size": 10, "kind": "vitals", "status": "read", "message": None, "n_values": 1},
                    [{"param": "sbp", "value": 140.0, "unit": "mmHg", "observed_on": datetime.date(2026, 1, 2), "source_text": "BP 140/90"}])
    r = client.get(f"/api/documents/{old}").json()["document"]
    assert r["source"]["filename"] == "old.txt" and r["values"][0]["param"] == "sbp" and docstore.get(docstore.Actor(pid), pid, old) is not None


def test_the_export_includes_the_json_documents(client):
    pid = person(client)
    upload(client)
    ex = client.get("/api/export").json()
    assert ex["document_records"][0]["source"]["filename"] == "lab.txt" and ex["document_records"][0]["patient_id"] == pid
