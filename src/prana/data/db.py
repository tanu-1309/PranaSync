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

narratives = Table(   # the AI-written text for each patient, kept until the facts it was written from change
    "narratives", metadata,
    Column("patient_id", String(32), primary_key=True), Column("facts_hash", String(40), nullable=False),
    Column("model", String(80)), Column("payload", JSONT, nullable=False), Column("created_at", TS, server_default=func.now()))

# ---- a record built up one document at a time (people who register and upload their own documents)
accounts = Table(   # one row per person who registered themselves; the password hash itself lives in `users`
    "accounts", metadata,
    Column("patient_id", String(32), primary_key=True), Column("display_name", String(80)), Column("created_at", TS, server_default=func.now()))

profiles = Table(   # personal details a person has entered or corrected themselves (name, age, sex, contact…). No foreign key: people from the training workbooks have no `accounts` row
    "profiles", metadata,
    Column("patient_id", String(32), primary_key=True), Column("data", JSONT, nullable=False), Column("updated_at", TS, server_default=func.now()))

documents = Table(  # one row per uploaded file. The file itself is kept on disk; here only what we need to list, de-duplicate and delete it
    "documents", metadata,
    Column("doc_id", String(36), primary_key=True), Column("patient_id", String(32), ForeignKey("accounts.patient_id", ondelete="CASCADE"), nullable=False),
    Column("filename", String(200), nullable=False), Column("sha256", String(64), nullable=False), Column("size", Integer), Column("kind", String(32)),
    Column("status", String(16), nullable=False), Column("message", Text), Column("n_values", Integer, server_default="0"),
    Column("uploaded_at", TS, server_default=func.now()),
    Index("ix_documents_patient", "patient_id", "uploaded_at"), Index("ux_documents_patient_hash", "patient_id", "sha256", unique=True))

observations = Table(   # every value read from a document, with where it came from, so any number can be traced and removed with its document
    "observations", metadata,
    Column("id", BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True),
    Column("patient_id", String(32), nullable=False), Column("doc_id", String(36), ForeignKey("documents.doc_id", ondelete="CASCADE"), nullable=False),
    Column("param", String(32), nullable=False), Column("value", Float, nullable=False), Column("unit", String(24)), Column("observed_on", Date),
    Column("source_text", Text), Column("created_at", TS, server_default=func.now()),
    Index("ix_obs_patient_param", "patient_id", "param", "observed_on"))

risk_snapshots = Table(   # the risk result after each document was added, so the page can show how the picture grew
    "risk_snapshots", metadata,
    Column("id", BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True),
    Column("patient_id", String(32), nullable=False), Column("doc_id", String(36)), Column("result", JSONT, nullable=False),
    Column("created_at", TS, server_default=func.now()), Index("ix_snap_patient", "patient_id", "created_at"))

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


# ----------------------------------------------------------------------------- AI-written text
def get_narrative(patient_id: str, facts_hash: str) -> dict | None:
    """The stored AI text, only if it was written from exactly these facts."""
    with engine().connect() as con:
        row = con.execute(select(narratives.c.payload, narratives.c.facts_hash).where(narratives.c.patient_id == patient_id)).first()
    if not row or row.facts_hash != facts_hash:
        return None
    return row.payload if isinstance(row.payload, dict) else json.loads(row.payload)


def save_narrative(patient_id: str, facts_hash: str, model: str, payload: dict) -> None:
    clean = json.loads(_dumps(payload))
    with engine().begin() as con:
        stmt = _insert(narratives).values(patient_id=patient_id, facts_hash=facts_hash, model=model[:80], payload=clean)
        con.execute(stmt.on_conflict_do_update(index_elements=["patient_id"], set_={"facts_hash": stmt.excluded.facts_hash, "model": stmt.excluded.model, "payload": stmt.excluded.payload, "created_at": func.now()}))


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


# ----------------------------------------------------------------------------- registered people, documents, observations
def is_registered(patient_id: str) -> bool:
    with engine().connect() as con:
        return con.execute(select(accounts.c.patient_id).where(accounts.c.patient_id == patient_id)).first() is not None


def create_account(patient_id: str, display_name: str, pw_hash: str) -> bool:
    """False when the ID is already taken."""
    with engine().begin() as con:
        if con.execute(select(accounts.c.patient_id).where(accounts.c.patient_id == patient_id)).first() or \
                con.execute(select(users.c.patient_id).where(users.c.patient_id == patient_id)).first():
            return False
        con.execute(accounts.insert().values(patient_id=patient_id, display_name=display_name[:80]))
        con.execute(users.insert().values(patient_id=patient_id, pw_hash=pw_hash))
    return True


def get_display_name(patient_id: str) -> str | None:
    with engine().connect() as con:
        return con.execute(select(accounts.c.display_name).where(accounts.c.patient_id == patient_id)).scalar()


def set_display_name(patient_id: str, name: str) -> None:
    with engine().begin() as con:
        con.execute(accounts.update().where(accounts.c.patient_id == patient_id).values(display_name=name[:80]))


def get_profile(patient_id: str) -> dict:
    with engine().connect() as con:
        row = con.execute(select(profiles.c.data).where(profiles.c.patient_id == patient_id)).scalar()
    return dict(row or {})


def save_profile(patient_id: str, data: dict) -> None:
    with engine().begin() as con:
        if con.execute(select(profiles.c.patient_id).where(profiles.c.patient_id == patient_id)).first():
            con.execute(profiles.update().where(profiles.c.patient_id == patient_id).values(data=data, updated_at=func.now()))
        else:
            con.execute(profiles.insert().values(patient_id=patient_id, data=data))


def find_document(patient_id: str, sha256: str) -> dict | None:
    with engine().connect() as con:
        r = con.execute(select(documents).where(documents.c.patient_id == patient_id, documents.c.sha256 == sha256)).mappings().first()
    return dict(r) if r else None


def add_document(doc: dict, obs: list[dict]) -> None:
    with engine().begin() as con:
        # People from the training workbooks (PC0001…) sign in with an existing user row but have no `accounts` row; the first upload gives them one.
        if not con.execute(select(accounts.c.patient_id).where(accounts.c.patient_id == doc["patient_id"])).first():
            con.execute(accounts.insert().values(patient_id=doc["patient_id"], display_name=doc["patient_id"]))
        con.execute(documents.insert().values(**doc))
        if obs:
            con.execute(observations.insert(), [{**o, "patient_id": doc["patient_id"], "doc_id": doc["doc_id"]} for o in obs])


def list_documents(patient_id: str) -> list[dict]:
    with engine().connect() as con:
        rows = con.execute(select(documents).where(documents.c.patient_id == patient_id).order_by(documents.c.uploaded_at.desc())).mappings().all()
    return [dict(r) for r in rows]


def delete_document(patient_id: str, doc_id: str) -> bool:
    """Removes the document and every value read from it (done explicitly so SQLite, which skips foreign-key cascades by default, behaves like PostgreSQL)."""
    with engine().begin() as con:
        if not con.execute(select(documents.c.doc_id).where(documents.c.doc_id == doc_id, documents.c.patient_id == patient_id)).first():
            return False
        con.execute(delete(observations).where(observations.c.doc_id == doc_id))
        con.execute(delete(documents).where(documents.c.doc_id == doc_id))
    return True


def document_observations(patient_id: str, doc_id: str) -> list[dict]:
    with engine().connect() as con:
        rows = con.execute(select(observations.c.param, observations.c.value, observations.c.unit, observations.c.observed_on, observations.c.source_text)
                           .where(observations.c.patient_id == patient_id, observations.c.doc_id == doc_id).order_by(observations.c.id.asc())).mappings().all()
    return [dict(r) for r in rows]


def get_document(patient_id: str, doc_id: str) -> dict | None:
    with engine().connect() as con:
        r = con.execute(select(documents).where(documents.c.doc_id == doc_id, documents.c.patient_id == patient_id)).mappings().first()
    return dict(r) if r else None


def replace_observations(patient_id: str, doc_id: str, obs: list[dict], status: str = "confirmed") -> None:
    """After a person corrects the values read from one document: swap that document's values for the corrected ones."""
    with engine().begin() as con:
        con.execute(delete(observations).where(observations.c.doc_id == doc_id, observations.c.patient_id == patient_id))
        if obs:
            con.execute(observations.insert(), [{**o, "patient_id": patient_id, "doc_id": doc_id} for o in obs])
        con.execute(documents.update().where(documents.c.doc_id == doc_id, documents.c.patient_id == patient_id).values(n_values=len(obs), status=status))


def read_observations(patient_id: str) -> list[dict]:
    """Every stored value, oldest first. The caller keeps the latest value of each parameter."""
    with engine().connect() as con:
        rows = con.execute(select(observations.c.param, observations.c.value, observations.c.unit, observations.c.observed_on, observations.c.doc_id,
                                  observations.c.created_at).where(observations.c.patient_id == patient_id)
                           .order_by(observations.c.observed_on.asc().nulls_first(), observations.c.created_at.asc(), observations.c.id.asc())).mappings().all()
    return [dict(r) for r in rows]


def save_snapshot(patient_id: str, doc_id: str | None, result: dict) -> None:
    with engine().begin() as con:
        con.execute(risk_snapshots.insert().values(patient_id=patient_id, doc_id=doc_id, result=json.loads(_dumps(result))))


def read_snapshots(patient_id: str, limit: int = 20) -> list[dict]:
    with engine().connect() as con:
        rows = con.execute(select(risk_snapshots).where(risk_snapshots.c.patient_id == patient_id).order_by(risk_snapshots.c.created_at.desc()).limit(limit)).mappings().all()
    return [dict(r) for r in rows]


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
