"""The document store: a database of its own, apart from the portal's main database, holding one JSON document per uploaded file.

Each JSON document records the uploaded file (name, size, type, fingerprint), when it was uploaded and when its text was extracted, the extracted text,
every value read from it (with the original reading and any correction the person made), and the history of those corrections.

It is locked in two ways, so a person's documents can only be seen by that person when signed in, or by an administrator:

  1. Encryption. The JSON is sealed with AES-256-GCM under a key made for that one person (HKDF from a server key and the person's ID). The document id and the
     owner are bound into the seal, so a sealed document cannot be moved to another person's row and still open. Someone who copies the database file sees
     only ids, times and a status.
  2. Access rules in the code that reads it. Every read and write names who is asking (`Actor`). A person is only ever given their own documents; an
     administrator may read anyone's (never change them), and every administrator read is written to the audit log by the routes. Anyone else is refused,
     and a refusal looks exactly like "no such document", so it does not even confirm that someone else's document exists.

The server key lives in `data/.docstore_key` (or the PRANA_DOCSTORE_KEY setting). Losing it makes the stored documents unreadable, so back it up with the database.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, timezone

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlalchemy import Column, MetaData, String, Table, Text, create_engine, delete, select
from sqlalchemy.engine import Engine

from prana.config import DATA_DIR, setting

KEY_FILE = DATA_DIR / ".docstore_key"
metadata = MetaData()
store = Table(
    "document_store", metadata,
    Column("doc_id", String(36), primary_key=True), Column("patient_id", String(32), nullable=False, index=True),
    Column("uploaded_at", String(32), nullable=False), Column("updated_at", String(32), nullable=False), Column("status", String(16), nullable=False),
    Column("sealed", Text, nullable=False))      # the JSON document, encrypted

_engine: Engine | None = None
_lock = threading.Lock()


class AccessDenied(Exception):
    """Raised when someone asks for a document that is not theirs. Routes show it as 'not found'."""


@dataclass(frozen=True)
class Actor:
    """Who is asking. Always built from the signed session, never from anything the caller typed."""
    patient_id: str
    admin: bool = False


def is_admin(patient_id: str) -> bool:
    """Administrators are the IDs listed in the PRANA_ADMIN_IDS setting (comma separated). They sign in like anyone else; nothing about a request can make someone an administrator."""
    ids = {x.strip().upper() for x in (setting("PRANA_ADMIN_IDS") or "").split(",") if x.strip()}
    return patient_id.upper() in ids


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ------------------------------------------------------------------ engine
def database_url() -> str:
    return setting("DOCSTORE_URL") or f"sqlite:///{DATA_DIR / 'documents.db'}"


def engine() -> Engine:
    global _engine
    with _lock:
        if _engine is None:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            _engine = create_engine(database_url(), future=True)
            metadata.create_all(_engine)
        return _engine


def use_engine(e: Engine) -> None:
    """Point the store at another database (tests use a throw-away one)."""
    global _engine
    _engine = e
    metadata.create_all(e)


# ------------------------------------------------------------------ keys and sealing
def _master() -> bytes:
    env = setting("PRANA_DOCSTORE_KEY")
    if env:
        return hashlib.sha256(env.encode()).digest()          # any string works as the server key
    KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not KEY_FILE.exists():
        KEY_FILE.write_bytes(secrets.token_bytes(32))
        try:
            os.chmod(KEY_FILE, 0o600)
        except OSError:
            pass
    return KEY_FILE.read_bytes()


def _key(patient_id: str) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=b"pranasync-docstore-v1", info=patient_id.encode()).derive(_master())


def seal_bytes(patient_id: str, doc_id: str, data: bytes) -> bytes:
    """Encrypt bytes for one person and one document. Also used for the uploaded file itself."""
    nonce = secrets.token_bytes(12)
    return b"PSv1" + nonce + AESGCM(_key(patient_id)).encrypt(nonce, data, f"{patient_id}:{doc_id}".encode())


def open_bytes(patient_id: str, doc_id: str, blob: bytes) -> bytes:
    if not blob.startswith(b"PSv1"):
        return blob                      # a file saved before sealing existed
    nonce, ct = blob[4:16], blob[16:]
    return AESGCM(_key(patient_id)).decrypt(nonce, ct, f"{patient_id}:{doc_id}".encode())


def _seal(doc: dict) -> str:
    return base64.b64encode(seal_bytes(doc["patient_id"], doc["doc_id"], json.dumps(doc, ensure_ascii=False, default=str).encode("utf-8"))).decode()


def _open(row) -> dict:
    return json.loads(open_bytes(row["patient_id"], row["doc_id"], base64.b64decode(row["sealed"])).decode("utf-8"))


# ------------------------------------------------------------------ the rule
def _allowed(actor: Actor, owner: str, write: bool) -> None:
    if actor.patient_id == owner:
        return
    if actor.admin and not write:
        return
    raise AccessDenied()


# ------------------------------------------------------------------ reads and writes
def put(actor: Actor, doc: dict) -> None:
    """Create or replace a document. Only the owner may write: not even an administrator changes someone's document."""
    _allowed(actor, doc["patient_id"], write=True)
    t = now()
    doc["updated_at"] = t
    row = {"doc_id": doc["doc_id"], "patient_id": doc["patient_id"], "uploaded_at": doc["uploaded_at"], "updated_at": t, "status": doc.get("status", "needs_review"), "sealed": _seal(doc)}
    with engine().begin() as con:
        owner = con.execute(select(store.c.patient_id).where(store.c.doc_id == doc["doc_id"])).scalar()
        if owner is not None and owner != doc["patient_id"]:
            raise AccessDenied()
        if owner is None:
            con.execute(store.insert().values(**row))
        else:
            con.execute(store.update().where(store.c.doc_id == doc["doc_id"]).values(**{k: v for k, v in row.items() if k != "doc_id"}))


def get(actor: Actor, patient_id: str, doc_id: str) -> dict | None:
    """The document, or None when there is none. Raises AccessDenied when it belongs to someone else and the actor is not an administrator."""
    _allowed(actor, patient_id, write=False)
    with engine().connect() as con:
        row = con.execute(select(store).where(store.c.doc_id == doc_id, store.c.patient_id == patient_id)).mappings().first()
    return _open(row) if row else None


def statuses(actor: Actor, patient_id: str) -> dict[str, dict]:
    """doc_id -> {status, uploaded_at, updated_at}, without opening anything."""
    _allowed(actor, patient_id, write=False)
    with engine().connect() as con:
        rows = con.execute(select(store.c.doc_id, store.c.status, store.c.uploaded_at, store.c.updated_at).where(store.c.patient_id == patient_id)).mappings().all()
    return {r["doc_id"]: {"status": r["status"], "uploaded_at": r["uploaded_at"], "updated_at": r["updated_at"]} for r in rows}


def all_for(actor: Actor, patient_id: str) -> list[dict]:
    _allowed(actor, patient_id, write=False)
    with engine().connect() as con:
        rows = con.execute(select(store).where(store.c.patient_id == patient_id).order_by(store.c.uploaded_at.desc())).mappings().all()
    return [_open(r) for r in rows]


def remove(actor: Actor, patient_id: str, doc_id: str) -> bool:
    _allowed(actor, patient_id, write=True)
    with engine().begin() as con:
        return con.execute(delete(store).where(store.c.doc_id == doc_id, store.c.patient_id == patient_id)).rowcount > 0


def owners(actor: Actor) -> list[dict]:
    """For administrators only: who has documents, and how many."""
    if not actor.admin:
        raise AccessDenied()
    with engine().connect() as con:
        rows = con.execute(select(store.c.patient_id, store.c.doc_id, store.c.uploaded_at)).mappings().all()
    out: dict[str, dict] = {}
    for r in rows:
        o = out.setdefault(r["patient_id"], {"patient_id": r["patient_id"], "documents": 0, "last_upload": ""})
        o["documents"] += 1
        o["last_upload"] = max(o["last_upload"], r["uploaded_at"])
    return sorted(out.values(), key=lambda o: o["last_upload"], reverse=True)
