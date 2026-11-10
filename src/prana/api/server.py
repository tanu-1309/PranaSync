"""Patient portal API + static host.

    python scripts/serve.py                         (needs accounts: python scripts/create_users.py)

Every route that returns health data takes the patient from the signed session cookie, never from the URL,
so one patient cannot ask for another's record. Accounts, the patient packages and the audit log live in the
database (PostgreSQL when DATABASE_URL is set, SQLite otherwise). The analysis itself is untouched.
"""
from __future__ import annotations

import json
import math
import time
from collections import defaultdict, deque
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.sessions import SessionMiddleware

from prana.ai import chat as chatbot
from prana.ai import llm
from prana.api import auth
from prana.api.payload import build_payload
from prana.config import RAW_DIR, RESULTS_DIR, ROOT, SYNTHETIC_DIR, setting
from prana.data import db
from prana.data.loader import list_workbooks
from prana.insight.pipeline import analyze_workbook

WEB_DIR = ROOT / "web"

app = FastAPI(title="PranaSync API", version="0.7", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(SessionMiddleware, secret_key=auth.session_secret(), session_cookie="prana_session",
                   max_age=60 * 60 * 8, same_site="lax", https_only=setting("PRANA_HTTPS") == "1")  # PRANA_HTTPS=1 behind TLS
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.on_event("startup")
def _startup() -> None:
    db.init_db()  # creates any missing tables; never drops data


@lru_cache(maxsize=1)
def _index() -> dict[str, Path]:
    files = list_workbooks(RAW_DIR) or list_workbooks(SYNTHETIC_DIR)
    return {p.stem: p for p in files}


@app.get("/api/validation")
def validation():
    p = RESULTS_DIR / "metrics.json"
    if not p.exists():
        raise HTTPException(404, "Run scripts/validate.py to create results/metrics.json")
    return json.loads(p.read_text(encoding="utf-8"))


def _patient(pid: str) -> dict:
    """The patient's package from the database; built from the workbook (and stored) when missing or out of date."""
    stored = db.get_record(pid)
    if stored is not None:
        return stored
    path = _index().get(pid)
    if path is None:
        raise HTTPException(404, "No record found for this account.")
    payload = build_payload(*analyze_workbook(path))
    try:
        db.save_record(pid, payload)
    except Exception:  # a database hiccup must not stop the patient seeing their record
        pass
    return payload


class Login(BaseModel):
    id: str
    password: str


@app.post("/api/login")
def login(body: Login, request: Request):
    pid = body.id.strip().upper()[:32]
    ok, wait = auth.check(pid, body.password[:200], request.client.host if request.client else "?")
    if wait:
        db.audit("login_locked", pid)
        raise HTTPException(429, f"Too many attempts. Please try again in {math.ceil(wait / 60)} minute(s).")
    if not ok or (pid not in _index() and db.get_record(pid) is None):
        db.audit("login_failed", pid)
        raise HTTPException(401, "That ID and password don’t match.")
    request.session.clear()
    request.session["pid"] = pid
    request.session["pv"] = auth.password_version(pid)
    db.audit("login_ok", pid)
    return {"id": pid}


@app.post("/api/logout")
def logout(request: Request):
    pid = request.session.get("pid")
    request.session.clear()
    if pid:
        db.audit("logout", pid)
    return {"ok": True}


GUEST_ID = setting("GUEST_ID", "PC0159")   # the sample record shown in guest mode


def _current(request: Request) -> str:
    pid = request.session.get("pid")
    if pid and request.session.get("guest"):
        return pid
    if not pid or request.session.get("pv") != auth.password_version(pid):  # signed out, or password was reset
        request.session.clear()
        raise HTTPException(401, "Please sign in.")
    return pid


@app.post("/api/guest")
def guest(request: Request):
    """Guest mode: look around a sample record without an account. Read-only: no password, nothing personal."""
    if GUEST_ID not in _index() and db.get_record(GUEST_ID) is None:
        raise HTTPException(404, "The sample record is not available.")
    request.session.clear()
    request.session["pid"] = GUEST_ID
    request.session["guest"] = True
    db.audit("guest_start", None)
    return {"id": GUEST_ID, "guest": True}


@app.get("/api/me")
def me(request: Request):
    """The signed-in patient's own record and analysis."""
    pid = _current(request)
    return {**_patient(pid), "guest": bool(request.session.get("guest"))}


class PasswordChange(BaseModel):
    current: str
    new: str


@app.post("/api/password")
def change_password(body: PasswordChange, request: Request):
    pid = _current(request)
    if request.session.get("guest"):
        raise HTTPException(403, "Guest mode has no password. Sign in with your own ID to change it.")
    new = body.new[:200]
    if len(new) < 10:
        raise HTTPException(422, "Please choose a password of at least 10 characters.")
    if new == body.current or pid.lower() in new.lower() or new.lower() in ("password123", "1234567890", "qwertyuiop"):
        raise HTTPException(422, "Please choose a different password, not your ID or your old password.")
    ok, wait = auth.check(pid, body.current[:200], request.client.host if request.client else "?")
    if wait:
        raise HTTPException(429, f"Too many attempts. Please try again in {math.ceil(wait / 60)} minute(s).")
    if not ok:
        db.audit("password_change_failed", pid)
        raise HTTPException(401, "Your current password isn’t right.")
    db.set_user_hashes({pid: auth.hash_password(new)})
    request.session["pv"] = auth.password_version(pid)   # this device stays signed in; every other session is ended
    db.audit("password_changed", pid)
    return {"ok": True}


_CHAT_HITS: dict[str, deque] = defaultdict(deque)
CHAT_LIMIT, CHAT_WINDOW = 20, 60  # messages per minute per patient


class Chat(BaseModel):
    message: str
    state: dict | None = None


@app.post("/api/chat")
def chat(body: Chat, request: Request):
    """Answer a question about the signed-in patient's own record. The patient comes from the session, never from the request."""
    pid = _current(request)
    key = f"guest:{request.client.host if request.client else '?'}" if request.session.get("guest") else pid
    now, hits = time.monotonic(), _CHAT_HITS[key]
    while hits and now - hits[0] > CHAT_WINDOW:
        hits.popleft()
    if len(hits) >= CHAT_LIMIT:
        raise HTTPException(429, "That's a lot of questions at once. Please wait a moment.")
    hits.append(now)
    state = body.state if isinstance(body.state, dict) and len(json.dumps(body.state, default=str)) < 2000 else {}
    out = chatbot.answer(body.message[:500], _patient(pid), state)
    if out["intent"] == "fallback" and llm.enabled():   # the model may only pick one of our fixed questions; the answer still comes from the record
        routed = llm.route(body.message, chatbot.CANONICAL, chatbot.CANONICAL_HINTS)
        if routed:
            out = chatbot.answer(routed, _patient(pid), state)
            out["answer"] = [f"_I read your question as: “{routed}”_"] + out["answer"]   # so a wrong guess is visible and the patient can rephrase
    if not out["intent"].startswith("safety") and llm.enabled():
        out["answer"] = llm.polish(out["answer"])   # reworded only if every number and safety check still holds
    db.audit("chat", pid, intent=out["intent"])  # the topic only, never the message
    return out


@app.middleware("http")
async def _headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Content-Security-Policy"] = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; "
                                               "img-src 'self' data:; media-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
    resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if setting("PRANA_HTTPS") == "1":
        resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if request.url.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


@app.get("/api/health")
def health():
    try:
        return {"ok": True, "database": db.ping(), "workbooks": len(_index()), "llm": llm.status()}
    except Exception:
        raise HTTPException(503, "Database unavailable")


class _NoCacheStatic(StaticFiles):
    """Revalidate on every load so edits to the interface show up without a hard refresh."""

    async def get_response(self, path, scope):
        resp = await super().get_response(path, scope)
        resp.headers["Cache-Control"] = "no-cache"
        return resp


app.mount("/assets", _NoCacheStatic(directory=WEB_DIR), name="assets")


@app.get("/{path:path}")
def spa(path: str):
    if path.startswith("api/"):
        raise HTTPException(404, "Not found")
    return FileResponse(WEB_DIR / "index.html")
