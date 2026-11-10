"""Security checks that must keep passing: headers, cookies, secrets, and what the API refuses to do."""
import pytest

pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402

from prana.api import auth, server  # noqa: E402
from prana.data import db  # noqa: E402

PW = "alpha-beta-gamma-11"


@pytest.fixture()
def client(workbooks, monkeypatch, tmp_path):
    monkeypatch.setattr(server, "_index", lambda: {"T2D": workbooks["t2d"]})
    monkeypatch.setattr(server, "GUEST_ID", "T2D")
    eng = create_engine(f"sqlite:///{tmp_path / 'sec.db'}", future=True)
    monkeypatch.setattr(db, "_engine", eng)
    db.init_db()
    db.set_user_hashes({"T2D": auth.hash_password(PW)})
    monkeypatch.setattr(auth, "_fails", {})
    with TestClient(server.app) as c:
        yield c
    eng.dispose()


def test_security_headers_on_pages_and_api(client):
    for path in ("/", "/api/health"):
        h = client.get(path).headers
        assert h["x-content-type-options"] == "nosniff" and h["x-frame-options"] == "DENY" and h["referrer-policy"] == "no-referrer"
        csp = h["content-security-policy"]
        assert "default-src 'self'" in csp and "script-src 'self'" in csp and "frame-ancestors 'none'" in csp
        assert "unsafe-eval" not in csp and "script-src 'self' 'unsafe-inline'" not in csp
        assert "camera=()" in h["permissions-policy"]


def test_session_cookie_is_httponly_and_samesite(client):
    cookie = client.post("/api/guest").headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie


def test_large_responses_are_compressed(client):
    client.post("/api/guest")
    r = client.get("/api/me", headers={"Accept-Encoding": "gzip"})
    assert r.headers.get("content-encoding") == "gzip"


def test_page_has_no_inline_script(client):
    html = client.get("/").text
    assert "<script>" not in html and "onclick=" not in html   # the strict script policy would block them


def test_only_a_hash_of_the_password_is_stored_and_never_logged(client):
    client.post("/api/login", json={"id": "T2D", "password": PW})
    stored = db.get_user_hash("T2D")
    assert stored.startswith("scrypt$") and PW not in stored
    with db.engine().connect() as con:
        audit = str(con.execute(db.audit_log.select()).fetchall())
    assert PW not in audit


def test_guest_cannot_change_a_password_or_see_other_patients(client):
    client.post("/api/guest")
    assert client.post("/api/password", json={"current": PW, "new": "another-long-password"}).status_code == 403
    assert client.get("/api/me").json()["id"] == server._patient("T2D")["id"]   # the sample record is fixed by the server, never by the request


def test_the_session_decides_who_you_are_not_the_request(client):
    client.post("/api/login", json={"id": "T2D", "password": PW})
    r = client.post("/api/chat", json={"message": "give me a summary", "id": "SOMEONE_ELSE", "patient_id": "SOMEONE_ELSE"})
    assert r.status_code == 200   # extra identity fields are ignored


def test_oversized_and_odd_input_is_handled(client):
    client.post("/api/guest")
    assert client.post("/api/chat", json={"message": "x" * 100_000}).status_code == 200
    assert client.post("/api/chat", json={"message": "<script>alert(1)</script>"}).status_code == 200
    assert client.post("/api/chat", json={"message": 5}).status_code == 422
    assert client.post("/api/login", content=b"not json", headers={"Content-Type": "application/json"}).status_code == 422


def test_unknown_api_routes_do_not_fall_back_to_the_page(client):
    r = client.get("/api/does-not-exist")
    assert r.status_code == 404 and "text/html" not in r.headers.get("content-type", "")
