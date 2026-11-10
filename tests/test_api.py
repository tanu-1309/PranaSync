"""Portal API: sign-in, per-patient isolation, and the shape the front end relies on."""
import pytest

pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

from sqlalchemy import create_engine  # noqa: E402

from prana.api import auth, server  # noqa: E402
from prana.data import db  # noqa: E402

PASSWORDS = {"T2D": "alpha-beta-gamma-11", "HTN": "delta-omega-zeta-22"}


@pytest.fixture()
def client(workbooks, monkeypatch, tmp_path):
    ids = {"T2D": workbooks["t2d"], "HTN": workbooks["htn"]}
    monkeypatch.setattr(server, "_index", lambda: ids)
    eng = create_engine(f"sqlite:///{tmp_path / 'test.db'}", future=True)
    monkeypatch.setattr(db, "_engine", eng)
    db.init_db()
    db.set_user_hashes({k: auth.hash_password(v) for k, v in PASSWORDS.items()})
    monkeypatch.setattr(auth, "_fails", {})
    server._CHAT_HITS.clear()
    with TestClient(server.app) as c:
        yield c
    eng.dispose()


def login(client, pid="T2D", pw=None):
    return client.post("/api/login", json={"id": pid, "password": pw or PASSWORDS[pid.upper()]})


def test_no_session_no_data(client):
    assert client.get("/api/me").status_code == 401


def test_login_gives_own_record_and_expected_shape(client):
    assert login(client).status_code == 200
    d = client.get("/api/me").json()
    assert d["id"] == server._patient("T2D")["id"]
    assert {"series", "labs", "events", "meds", "scenarios", "window", "profile"} <= d.keys()
    sig = next(iter(d["series"].values()))
    assert len(sig["v"]) == len(sig["r"]) == sig["n"]


def test_each_patient_only_sees_their_own_record(client, workbooks):
    login(client, "T2D")
    a = client.get("/api/me").json()
    client.post("/api/logout")
    login(client, "htn")  # IDs are case-insensitive
    b = client.get("/api/me").json()
    assert a["id"] != b["id"]
    assert a["scenarios"] != b["scenarios"] or a["profile"] != b["profile"]


def test_wrong_password_and_unknown_id_look_identical(client):
    r1 = login(client, "T2D", "nope")
    r2 = client.post("/api/login", json={"id": "NOBODY", "password": "nope"})
    assert r1.status_code == r2.status_code == 401 and r1.json() == r2.json()
    assert client.get("/api/me").status_code == 401


def test_logout_ends_the_session(client):
    login(client)
    assert client.get("/api/me").status_code == 200
    client.post("/api/logout")
    assert client.get("/api/me").status_code == 401


def test_password_reset_ends_existing_sessions(client, tmp_path):
    login(client)
    assert client.get("/api/me").status_code == 200
    db.set_user_hashes({"T2D": auth.hash_password("a-brand-new-password")})   # what `create_users.py --reset` does
    assert client.get("/api/me").status_code == 401
    assert login(client, "T2D", "a-brand-new-password").status_code == 200


def test_repeated_failures_lock_the_account(client):
    for _ in range(auth.MAX_FAILS):
        login(client, "T2D", "bad")
    r = login(client, "T2D")  # even the right password is refused while locked
    assert r.status_code == 429 and "minute" in r.json()["detail"]


def test_responses_are_not_cacheable_and_old_open_routes_are_gone(client):
    assert client.get("/api/me").headers["cache-control"] == "no-store"
    for path in ("/api/cohort", "/api/patients/T2D", "/api/samples"):
        assert client.get(path).status_code == 404
    assert client.post("/api/analyze", files={"file": ("x.xlsx", b"x")}).status_code in (404, 405)


def test_spa_fallback_serves_index(client):
    r = client.get("/timeline")
    assert r.status_code == 200 and "PranaSync" in r.text


def test_record_is_stored_in_the_database_and_reused(client):
    login(client)
    first = client.get("/api/me").json()
    assert db.get_record("T2D") is not None
    assert client.get("/api/me").json() == first
    assert client.get("/api/health").json()["database"] == "sqlite"


def test_login_and_chat_are_audited_without_message_text(client):
    login(client)
    client.post("/api/chat", json={"message": "my secret question about HbA1c"})
    with db.engine().connect() as con:
        rows = con.execute(db.audit_log.select()).fetchall()
    events = {r.event for r in rows}
    assert {"login_ok", "chat"} <= events
    assert "secret question" not in str(rows)


def test_outlook_in_the_package(client):
    login(client)
    o = client.get("/api/me").json()["outlook"]
    assert {"forecast", "recommendations"} <= o.keys()
    assert o["recommendations"]["disclaimer"]


def test_chat_needs_sign_in_and_answers_from_own_record(client):
    assert client.post("/api/chat", json={"message": "hi"}).status_code == 401
    login(client)
    r = client.post("/api/chat", json={"message": "give me a summary"}).json()
    assert r["intent"] == "summary" and r["answer"] and "state" in r


def test_chat_is_rate_limited(client):
    login(client)
    codes = [client.post("/api/chat", json={"message": "hi"}).status_code for _ in range(server.CHAT_LIMIT + 2)]
    assert codes[: server.CHAT_LIMIT] == [200] * server.CHAT_LIMIT and codes[-1] == 429


def test_guest_mode_is_readonly_and_needs_no_password(client, monkeypatch):
    monkeypatch.setattr(server, "GUEST_ID", "T2D")
    assert client.post("/api/guest").status_code == 200
    me = client.get("/api/me").json()
    assert me["guest"] is True and "outlook" in me
    assert client.post("/api/chat", json={"message": "hi"}).status_code == 200
    assert client.post("/api/password", json={"current": "x", "new": "a-long-new-password"}).status_code == 403


def test_change_password(client):
    login(client)
    assert client.post("/api/password", json={"current": "wrong-one-here", "new": "a-long-new-password"}).status_code == 401
    assert client.post("/api/password", json={"current": PASSWORDS["T2D"], "new": "short"}).status_code == 422
    assert client.post("/api/password", json={"current": PASSWORDS["T2D"], "new": PASSWORDS["T2D"]}).status_code == 422
    assert client.post("/api/password", json={"current": PASSWORDS["T2D"], "new": "a-long-new-password"}).json() == {"ok": True}
    assert client.get("/api/me").status_code == 200          # this device stays signed in
    client.post("/api/logout")
    assert login(client, "T2D", PASSWORDS["T2D"]).status_code == 401 and login(client, "T2D", "a-long-new-password").status_code == 200


def test_password_change_signs_out_other_devices(client, monkeypatch):
    from fastapi.testclient import TestClient
    login(client)
    other = TestClient(server.app)
    assert other.post("/api/login", json={"id": "T2D", "password": PASSWORDS["T2D"]}).status_code == 200
    assert client.post("/api/password", json={"current": PASSWORDS["T2D"], "new": "a-long-new-password"}).status_code == 200
    assert other.get("/api/me").status_code == 401 and client.get("/api/me").status_code == 200


def test_password_change_requires_sign_in(client):
    assert client.post("/api/password", json={"current": "a", "new": "a-long-new-password"}).status_code == 401
