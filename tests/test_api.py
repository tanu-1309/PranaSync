"""Portal API: sign-in, per-patient isolation, and the shape the front end relies on."""
import json

import pytest

pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

from prana.api import auth, server  # noqa: E402

PASSWORDS = {"T2D": "alpha-beta-gamma-11", "HTN": "delta-omega-zeta-22"}


@pytest.fixture()
def client(workbooks, monkeypatch, tmp_path):
    ids = {"T2D": workbooks["t2d"], "HTN": workbooks["htn"]}
    monkeypatch.setattr(server, "_index", lambda: ids)
    users = tmp_path / "users.json"
    users.write_text(json.dumps({k: auth.hash_password(v) for k, v in PASSWORDS.items()}))
    monkeypatch.setattr(auth, "USERS_FILE", users)
    monkeypatch.setattr(auth, "_fails", {})
    server._patient.cache_clear()
    return TestClient(server.app)


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
    users = json.loads(auth.USERS_FILE.read_text())
    users["T2D"] = auth.hash_password("a-brand-new-password")   # what `create_users.py --reset` does
    auth.USERS_FILE.write_text(json.dumps(users))
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
    assert r.status_code == 200 and "PranaChain Insight" in r.text
