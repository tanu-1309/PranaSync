"""One command for demo day: start everything the demo needs, check that it all works, and open the browser.

    python scripts/start_demo.py            # starts PostgreSQL if it is stopped, finds a free port, starts the portal, runs a smoke test, opens the browser
    python scripts/start_demo.py --check    # only check, start nothing (use this the night before)
    python scripts/start_demo.py --port 8010 --no-browser

What it checks, and says plainly if something is wrong: the database is reachable and has records, the portal answers, the sample record
loads, the chatbot gives a safe reply to an emergency and an answer to a risk question, and (if PRANA_LLM=1) that the model server is up.
If it finds a PranaSync portal already running on one of the usual ports it reuses it instead of starting a second one.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from http.cookiejar import CookieJar
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from prana.config import database_url, setting  # noqa: E402

PORTS = (8000, 8010, 8020, 8030)
OK, BAD, WARN = "  [ok]  ", " [FAIL] ", " [warn] "


def say(tag: str, text: str) -> None:
    print(f"{tag}{text}", flush=True)


def get(url: str, timeout: float = 3):
    with urllib.request.urlopen(url, timeout=timeout) as r:  # noqa: S310  (local addresses only)
        return json.loads(r.read())


def port_free(port: int) -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def pranasync_on(port: int) -> dict | None:
    """The health answer if a PranaSync portal is listening on this port, else None."""
    try:
        h = get(f"http://127.0.0.1:{port}/api/health", 2)
        return h if h.get("ok") and "workbooks" in h else None
    except (OSError, ValueError, urllib.error.URLError):
        return None


def database_ready() -> bool:
    url = database_url()
    if not url.startswith("postgresql"):
        say(OK, "database: SQLite file (no server to start)")
        return True
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import OperationalError

    def can_connect() -> bool:
        try:
            with create_engine(url, pool_pre_ping=True).connect() as c:
                c.execute(text("select 1"))
            return True
        except OperationalError:
            return False

    if can_connect():
        say(OK, "database: PostgreSQL is running")
        return True
    if "127.0.0.1:5433" in url and (ROOT / "scripts" / "pg_local.py").exists():
        say(WARN, "PostgreSQL is stopped; starting it (this can take up to a minute)")
        subprocess.run([sys.executable, str(ROOT / "scripts" / "pg_local.py"), "start"], cwd=ROOT, timeout=180, capture_output=True)
        if can_connect():
            say(OK, "database: PostgreSQL started")
            return True
    say(BAD, "database: cannot connect. Start PostgreSQL, or remove DATABASE_URL from .env to use the SQLite file")
    return False


def llm_ready() -> None:
    if setting("PRANA_LLM") != "1":
        say(OK, "language model: off (Prana uses its rules only)")
        return
    url = (setting("PRANA_LLM_URL") or "").rstrip("/")
    if "localhost" in url or "127.0.0.1" in url:
        try:
            v = get(url.rsplit("/v1", 1)[0] + "/api/version")
            say(OK, f"language model: Ollama {v.get('version', '')} is running (model {setting('PRANA_LLM_MODEL')})")
        except (OSError, ValueError, urllib.error.URLError):
            say(WARN, "language model: Ollama is NOT running. Prana still works, but oddly worded questions get 'I'm not sure'. Start the Ollama app")
    else:
        say(OK, "language model: hosted provider configured (not tested here)")


def smoke(base: str) -> bool:
    """A guest session, the record, a risk answer and an emergency reply, exactly as a visitor would use them."""
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))

    def post(path: str, body: dict | None = None) -> dict:
        req = urllib.request.Request(base + path, data=json.dumps(body or {}).encode(), headers={"Content-Type": "application/json"}, method="POST")
        return json.loads(op.open(req, timeout=60).read())

    ok = True
    try:
        post("/api/guest")
        me = json.loads(op.open(base + "/api/me", timeout=20).read())
        good = "outlook" in me and me.get("guest") is True
        say(OK if good else BAD, f"sample record opens (patient {me.get('id')}, {len(me.get('series', {}))} daily signals)")
        ok &= good
        r = post("/api/chat", {"message": "what is my chance of a heart attack?"})
        good = r["intent"] == "risk"
        say(OK if good else BAD, f"chatbot answers a risk question ({r['intent']})")
        ok &= good
        r = post("/api/chat", {"message": "I have chest pain"})
        good = r["intent"] == "safety_emergency"
        say(OK if good else BAD, f"chatbot gives the safe reply to 'I have chest pain' ({r['intent']})")
        ok &= good
    except Exception as e:  # noqa: BLE001
        say(BAD, f"smoke test failed: {e}")
        return False
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--check", action="store_true", help="check only, start nothing")
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    print("PranaSync demo check\n")
    ok = database_ready()
    llm_ready()
    if not ok:
        return 1

    running = next(((p, pranasync_on(p)) for p in ([a.port] if a.port else PORTS) if pranasync_on(p)), None)
    proc = None
    if running:
        port, h = running
        say(OK, f"portal already running on port {port} (database {h['database']}, {h['workbooks']} workbooks, model {h.get('llm', 'off')})")
    elif a.check:
        say(WARN, "portal is not running (check-only mode: not starting it)")
        return 0
    else:
        port = a.port or next((p for p in PORTS if port_free(p)), 0)
        if not port:
            say(BAD, "no free port among " + ", ".join(map(str, PORTS)))
            return 1
        env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
        proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "prana.api.server:app", "--port", str(port), "--log-level", "warning"], cwd=ROOT, env=env)
        for _ in range(60):
            if pranasync_on(port):
                break
            time.sleep(0.5)
        else:
            say(BAD, "the portal did not start within 30 seconds")
            proc.terminate()
            return 1
        say(OK, f"portal started on port {port}")

    base = f"http://127.0.0.1:{port}"
    good = smoke(base)
    print("\n" + ("READY. Open " + base.replace("127.0.0.1", "localhost") if good else "NOT READY: fix the lines marked [FAIL] above before the demo."), flush=True)
    if not good:
        if proc:
            proc.terminate()
        return 1
    if proc is None:
        return 0
    if not a.no_browser:
        webbrowser.open(base.replace("127.0.0.1", "localhost"))
    print("Leave this window open during the demo. Press Ctrl+C to stop the portal.", flush=True)
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
    return 0


if __name__ == "__main__":
    sys.exit(main())
