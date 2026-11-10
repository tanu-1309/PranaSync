"""Patient accounts: scrypt-hashed passwords, stored in the database `users` table, and login throttling.

Rows are {patient_id, "scrypt$n$r$p$salt$hash"}. They are created by `scripts/create_users.py`, which also writes the
one-time credentials sheet for the care team to hand out. (Older installs kept the hashes in data/users.json;
`scripts/init_db.py` imports that file once.)

This is a prototype scheme (ID + issued password, signed cookie session). A production deployment would sit
behind the platform's real identity provider with MFA; the API shape (`/api/login`, `/api/me`) would not change.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

from prana.config import DATA_DIR
from prana.data import db

USERS_FILE = Path(os.getenv("PRANA_USERS_FILE", DATA_DIR / "users.json"))
SECRET_FILE = DATA_DIR / ".session_secret"
N, R, P = 2**14, 8, 1

MAX_FAILS = 5
LOCK_SECONDS = 300


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=N, r=R, p=P, dklen=32)
    return "$".join(["scrypt", str(N), str(R), str(P), base64.b64encode(salt).decode(), base64.b64encode(dk).decode()])


def _verify(password: str, stored: str) -> bool:
    try:
        _, n, r, p, salt, dk = stored.split("$")
        got = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p), dklen=32)
        return hmac.compare_digest(got, base64.b64decode(dk))
    except Exception:
        return False


_DUMMY = hash_password("not-a-real-password")  # so unknown IDs cost the same time as wrong passwords


def legacy_users() -> dict[str, str]:
    """Hashes from the old data/users.json, used only by the one-time import."""
    return json.loads(USERS_FILE.read_text(encoding="utf-8")) if USERS_FILE.exists() else {}


def password_version(pid: str) -> str | None:
    """Changes whenever the patient's password is reset, so old sessions stop working."""
    stored = db.get_user_hash(pid)
    return hashlib.sha256(stored.encode()).hexdigest()[:16] if stored else None


def session_secret() -> str:
    env = os.getenv("PRANA_SECRET_KEY")
    if env:
        return env
    SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not SECRET_FILE.exists():
        SECRET_FILE.write_text(secrets.token_urlsafe(48), encoding="utf-8")
    return SECRET_FILE.read_text(encoding="utf-8").strip()


_fails: dict[str, tuple[int, float]] = {}


def locked_for(key: str) -> int:
    n, until = _fails.get(key, (0, 0.0))
    return max(0, int(until - time.time())) if n >= MAX_FAILS else 0


def check(pid: str, password: str, client: str) -> tuple[bool, int]:
    """Return (ok, seconds_locked). Throttles per patient ID and per client address."""
    keys = (f"id:{pid}", f"ip:{client}")
    wait = max(locked_for(k) for k in keys)
    if wait:
        return False, wait
    stored = db.get_user_hash(pid)
    ok = _verify(password, stored or _DUMMY) and stored is not None
    for k in keys:
        if ok:
            _fails.pop(k, None)
        else:
            n, _ = _fails.get(k, (0, 0.0))
            _fails[k] = (n + 1, time.time() + LOCK_SECONDS)
    return ok, 0
