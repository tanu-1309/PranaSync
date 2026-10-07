"""Database layer (owner: Sneha).

SQLite file by default (zero setup for the demo). Set DATABASE_URL to use
PostgreSQL as planned in the setup report, e.g.
    export DATABASE_URL=postgresql+psycopg2://prana:secret@localhost:5432/prana

Tables
  patients  : one row per patient (profile + data-quality summary)
  timeline  : unified long timeline (patient_id, date, source, signal, value, unit, text)
  findings  : analysis output, one row per patient x scenario (JSON evidence pack)
"""
from __future__ import annotations

import json

import pandas as pd
from sqlalchemy import create_engine, text

from prana.config import database_url

_engine = None


def engine():
    global _engine
    if _engine is None:
        _engine = create_engine(database_url(), future=True)
    return _engine


def init_db():
    with engine().begin() as con:
        for t in ("findings", "timeline", "patients"):
            con.execute(text(f"DROP TABLE IF EXISTS {t}"))


def save_patient(rec, timeline: pd.DataFrame):
    row = {"patient_id": rec.patient_id, "age": rec.profile.get("Age"), "sex": rec.profile.get("Sex"),
           "family_history": rec.profile.get("Family History"), "quality": json.dumps(rec.quality, default=str)}
    with engine().begin() as con:
        for table in ("timeline", "patients"):
            if _has(con, table):
                con.execute(text(f"DELETE FROM {table} WHERE patient_id = :p"), {"p": rec.patient_id})
    pd.DataFrame([row]).to_sql("patients", engine(), if_exists="append", index=False)
    tl = timeline.copy()
    tl["date"] = pd.to_datetime(tl["date"]).dt.date
    tl.to_sql("timeline", engine(), if_exists="append", index=False, chunksize=5000)


def save_findings(patient_id: str, scenario_results: list[dict]):
    rows = [{"patient_id": patient_id, "scenario": r["scenario"], "surfaced": bool(r["surfaced"]),
             "linked_context": bool(r["context"]), "n_signals": len(r["changed_signals"]),
             "evidence": json.dumps(r, default=str)} for r in scenario_results]
    with engine().begin() as con:
        if _has(con, "findings"):
            con.execute(text("DELETE FROM findings WHERE patient_id = :p"), {"p": patient_id})
    if rows:
        pd.DataFrame(rows).to_sql("findings", engine(), if_exists="append", index=False)


def read_timeline(patient_id: str) -> pd.DataFrame:
    return pd.read_sql(text("SELECT * FROM timeline WHERE patient_id = :p ORDER BY date"), engine(), params={"p": patient_id})


def _has(con, table: str) -> bool:
    from sqlalchemy import inspect
    return inspect(con).has_table(table)
