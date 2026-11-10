"""Database layer on a throwaway SQLite file (the same code runs on PostgreSQL)."""
import pytest
from sqlalchemy import create_engine

from prana.api.payload import build_payload
from prana.data import db
from prana.insight.pipeline import analyze_workbook


@pytest.fixture()
def eng(tmp_path):
    e = create_engine(f"sqlite:///{tmp_path / 't.db'}", future=True)
    old = db._engine
    db.use_engine(e)
    db.init_db()
    yield e
    db.use_engine(old)
    e.dispose()


def test_record_roundtrip_and_version_gate(eng, workbooks, monkeypatch):
    payload = build_payload(*analyze_workbook(workbooks["t2d"]))
    db.save_record("P1", payload)
    assert db.get_record("P1")["id"] == payload["id"]
    monkeypatch.setattr(db, "PAYLOAD_VERSION", db.PAYLOAD_VERSION + 1)
    assert db.get_record("P1") is None   # built by older code, so rebuilt on demand


def test_users_and_audit(eng):
    db.set_user_hashes({"A": "h1"})
    db.set_user_hashes({"A": "h2", "B": "h3"})
    assert db.get_user_hash("A") == "h2" and db.user_ids() == {"A", "B"}
    db.audit("login_ok", "A", ip="x")
    assert db.counts()["audit_log"] == 1


def test_nan_is_never_stored(eng):
    with pytest.raises(ValueError):
        db._dumps({"a": float("nan")})
