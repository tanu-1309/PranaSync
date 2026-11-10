"""Database layer (owner: Sneha).

PostgreSQL when DATABASE_URL is set (environment or .env), SQLite otherwise so the demo and CI need no server.
The same code runs on both; PostgreSQL gets JSONB columns and COPY bulk loading.

Tables
  patients   one row per patient (profile + data-quality summary)
  timeline   unified long timeline (patient_id, date, source, signal, value, unit, text)
  findings   analysis output, one row per patient x scenario (JSON evidence pack)
  users      one login per patient: salted scrypt hash only, never the password
  records    the portal's ready-made package for each patient (JSON), rebuilt when PAYLOAD_VERSION changes
  audit_log  security events (sign-in ok / failed, sign-out, chat intent). Never passwords, never message text.
"""
from __future__ import annotations

import io
import json
import logging

import pandas as pd
from sqlalchemy import (JSON, BigInteger, Boolean, Column, Date, DateTime, Float, ForeignKey, Index, Integer, MetaData, String, Table, Text,
                        create_engine, delete, func, inspect, select, text)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from prana.config import database_url

log = logging.getLogger("prana.db")

PAYLOAD_VERSION = 4   # bump whenever the shape of the portal package changes: stale records are rebuilt on demand

metadata = MetaData()
JSONT = JSON().with_variant(JSONB(), "postgresql")
TS = DateTime(timezone=True)

patients = Table(
    "patients", metadata,
    Column("patient_id", String(32), primary_key=True),
    Column("age", Integer), Column("sex", String(16)), Column("family_history", Text),
    Column("quality", JSONT), Column("updated_at", TS, server_default=func.now()))

timeline = Table(
    "timeline", metadata,
    Column("patient_id", String(32), ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False),
    Column("date", Date, nullable=False), Column("source", String(24), nullable=False), Column("signal", String(48), nullable=False),
    Column("value", Float), Column("unit", String(24)), Column("text", Text),
    Index("ix_timeline_patient_date", "patient_id", "date"), Index("ix_timeline_patient_signal", "patient_id", "signal"))

findings = Table(
    "findings", metadata,
    Column("patient_id", String(32), ForeignKey("patients.patient_id", ondelete="CASCADE"), primary_key=True),
    Column("scenario", String(8), primary_key=True),
    Column("surfaced", Boolean, nullable=False), Column("linked_context", Boolean, nullable=False),
    Column("n_signals", Integer, nullable=False), Column("evidence", JSONT, nullable=False))

users = Table(
    "users", metadata,
    Column("patient_id", String(32), primary_key=True), Column("pw_hash", Text, nullable=False),
    Column("created_at", TS, server_default=func.now()), Column("updated_at", TS, server_default=func.now()))

records = Table(
    "records", metadata,
    Column("patient_id", String(32), primary_key=True), Column("payload", JSONT, nullable=False),
    Column("version", Integer, nullable=False), Column("built_at", TS, server_default=func.now()))

audit_log = Table(
    "audit_log", metadata,
    Column("id", BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True),
    Column("ts", TS, server_default=func.now(), nullable=False), Column("patient_id", String(32)),
    Column("event", String(32), nullable=False), Column("detail", JSONT),
    Index("ix_audit_patient_ts", "patient_id", "ts"))

_engine = None


def _dumps(obj) -> str:
    return json.dumps(obj, allow_nan=False, default=str)  # strict JSON: NaN would corrupt a JSONB column


def engine():
    global _engine
    if _engine is None:
        _engine = create_engine(database_url(), future=True, pool_pre_ping=True, json_serializer=_dumps)
    return _engine


def use_engine(eng) -> None:
    """Swap the engine (tests use a temporary SQLite file)."""
    global _engine
    _engine = eng


def dialect() -> str:
    return engine().dialect.name


def _insert(table):
    return (pg_insert if dialect() == "postgresql" else sqlite_insert)(table)


def init_db(reset: bool = False) -> None:
    """Create any missing tables. reset=True drops everything first (destroys data)."""
    if reset:
        metadata.drop_all(engine())
    metadata.create_all(engine())


# ----------------------------------------------------------------------------- patients, timeline, findings
def save_patient(rec, tl: pd.DataFrame) -> None:
    age = pd.to_numeric(rec.profile.get("Age"), errors="coerce")
    row = {"patient_id": rec.patient_id, "age": None if pd.isna(age) else int(age), "sex": rec.profile.get("Sex"),
           "family_history": rec.profile.get("Family History"), "quality": json.loads(_dumps(rec.quality))}
    df = tl[["patient_id", "date", "source", "signal", "value", "unit", "text"]].dropna(subset=["date"]).copy()  # undated notes ("no active prescriptions") have no place on a timeline
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    with engine().begin() as con:
        con.execute(delete(timeline).where(timeline.c.patient_id == rec.patient_id))
        stmt = _insert(patients).values(**row)
        con.execute(stmt.on_conflict_do_update(index_elements=["patient_id"], set_={k: stmt.excluded[k] for k in row if k != "patient_id"} | {"updated_at": func.now()}))
        if dialect() == "postgresql":  # COPY is far faster than INSERT for thousands of rows
            buf = io.StringIO()
            df.to_csv(buf, index=False, header=False)
            buf.seek(0)
            cur = con.connection.cursor()
            cur.copy_expert("COPY timeline (patient_id, date, source, signal, value, unit, text) FROM STDIN WITH (FORMAT csv)", buf)
        else:
            from datetime import date as _d
            recs = df.where(df.notna(), None).to_dict("records")
            for r in recs:
                r["date"] = _d.fromisoformat(r["date"])
            for i in range(0, len(recs), 2000):
                con.execute(timeline.insert(), recs[i:i + 2000])


def save_findings(patient_id: str, scenario_results: list[dict]) -> None:
    rows = [{"patient_id": patient_id, "scenario": r["scenario"], "surfaced": bool(r["surfaced"]), "linked_context": bool(r["context"]),
             "n_signals": len(r["changed_signals"]), "evidence": json.loads(_dumps(r))} for r in scenario_results]
    with engine().begin() as con:
        con.execute(delete(findings).where(findings.c.patient_id == patient_id))
        if rows:
            con.execute(findings.insert(), rows)


def read_timeline(patient_id: str) -> pd.DataFrame:
    return pd.read_sql(select(timeline).where(timeline.c.patient_id == patient_id).order_by(timeline.c.date), engine())


# ----------------------------------------------------------------------------- portal records
def save_record(patient_id: str, payload: dict) -> None:
    clean = json.loads(_dumps(payload))
    with engine().begin() as con:
        stmt = _insert(records).values(patient_id=patient_id, payload=clean, version=PAYLOAD_VERSION)
        con.execute(stmt.on_conflict_do_update(index_elements=["patient_id"], set_={"payload": stmt.excluded.payload, "version": stmt.excluded.version, "built_at": func.now()}))


def get_record(patient_id: str) -> dict | None:
    """The stored package, or None when missing or built by an older version of the code."""
    with engine().connect() as con:
        row = con.execute(select(records.c.payload, records.c.version).where(records.c.patient_id == patient_id)).first()
    if not row or row.version != PAYLOAD_VERSION:
        return None
    return row.payload if isinstance(row.payload, dict) else json.loads(row.payload)


# ----------------------------------------------------------------------------- accounts
def get_user_hash(patient_id: str) -> str | None:
    with engine().connect() as con:
        return con.execute(select(users.c.pw_hash).where(users.c.patient_id == patient_id)).scalar()


def set_user_hashes(hashes: dict[str, str]) -> None:
    if not hashes:
        return
    with engine().begin() as con:
        for pid, h in hashes.items():
            stmt = _insert(users).values(patient_id=pid, pw_hash=h)
            con.execute(stmt.on_conflict_do_update(index_elements=["patient_id"], set_={"pw_hash": stmt.excluded.pw_hash, "updated_at": func.now()}))


def user_ids() -> set[str]:
    with engine().connect() as con:
        return {r[0] for r in con.execute(select(users.c.patient_id))}


# ----------------------------------------------------------------------------- audit and housekeeping
def audit(event: str, patient_id: str | None = None, **detail) -> None:
    """Record a security event. A failure here is logged but never blocks the request."""
    try:
        with engine().begin() as con:
            con.execute(audit_log.insert().values(event=event, patient_id=(patient_id or None) and patient_id[:32], detail=detail or None))
    except Exception:  # pragma: no cover
        log.exception("could not write audit event %s", event)


def counts() -> dict[str, int]:
    out = {}
    with engine().connect() as con:
        for t in metadata.sorted_tables:
            out[t.name] = con.execute(select(func.count()).select_from(t)).scalar() if inspect(con).has_table(t.name) else 0
    return out


def ping() -> str:
    with engine().connect() as con:
        con.execute(text("SELECT 1"))
    return dialect()
