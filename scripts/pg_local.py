"""A private PostgreSQL server for development, inside the project folder (no admin rights, no system install).

    python scripts/pg_local.py start      # first run creates the cluster, an app role and the database, writes .env
    python scripts/pg_local.py status
    python scripts/pg_local.py stop
    python scripts/pg_local.py url        # prints the DATABASE_URL (it contains the generated password)

It uses the PostgreSQL binaries that ship inside the `pgserver` pip package. Data lives in data/pgdata and the
passwords in data/.pg_* (both git-ignored). The app connects as a plain role that owns only its own database.

For a real deployment, skip this script: install PostgreSQL (or use a managed one) and set
    DATABASE_URL=postgresql+psycopg2://user:password@host:5432/pranasync
"""
from __future__ import annotations

import secrets
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PGDATA = ROOT / "data" / "pgdata"
SUPER_PW = ROOT / "data" / ".pg_superpw"
APP_PW = ROOT / "data" / ".pg_apppw"
ENV_FILE = ROOT / ".env"
PORT, DBNAME, ROLE = 5433, "pranasync", "pranasync"


def bin_dir() -> Path:
    try:
        from pgserver._commands import POSTGRES_BIN_PATH
    except ImportError:
        sys.exit("The embedded PostgreSQL is missing. Run:  python -m pip install pgserver psycopg2-binary")
    return Path(POSTGRES_BIN_PATH)


def tool(name: str) -> Path:
    return bin_dir() / (name + (".exe" if sys.platform == "win32" else ""))


def run(*args, check=True, **kw):
    return subprocess.run([str(a) for a in args], check=check, capture_output=True, text=True, **kw)


def secret(path: Path) -> str:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(secrets.token_urlsafe(24), encoding="utf-8")
    return path.read_text(encoding="utf-8").strip()


def url() -> str:
    return f"postgresql+psycopg2://{ROLE}:{secret(APP_PW)}@127.0.0.1:{PORT}/{DBNAME}"


def running() -> bool:
    return run(tool("pg_ctl"), "-D", PGDATA, "status", check=False).returncode == 0


def init_cluster():
    if (PGDATA / "PG_VERSION").exists():
        return
    print("creating the cluster in", PGDATA)
    PGDATA.parent.mkdir(parents=True, exist_ok=True)
    secret(SUPER_PW)  # make sure the superuser password file exists before initdb reads it
    run(tool("initdb"), "-D", PGDATA, "-U", "postgres", "-E", "UTF8", "--auth=scram-sha-256", f"--pwfile={SUPER_PW}")


def start():
    init_cluster()
    if not running():
        # send the server's output to a file, not a pipe: on Windows the server inherits a pipe and the call never returns
        with open(PGDATA / "pg_ctl.log", "ab") as log:
            r = subprocess.run([str(tool("pg_ctl")), "-D", str(PGDATA), "-l", str(PGDATA / "server.log"), "-o", f"-p {PORT} -c listen_addresses=127.0.0.1", "-w", "start"],
                               stdout=log, stderr=log, check=False, timeout=120)
        if r.returncode:
            sys.exit(f"could not start PostgreSQL, see {PGDATA / 'server.log'}")
    import psycopg2
    con = psycopg2.connect(host="127.0.0.1", port=PORT, user="postgres", password=secret(SUPER_PW), dbname="postgres")
    con.autocommit = True
    cur = con.cursor()
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (ROLE,))
    if not cur.fetchone():
        cur.execute(f"CREATE ROLE {ROLE} LOGIN PASSWORD %s", (secret(APP_PW),))
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DBNAME,))
    if not cur.fetchone():
        cur.execute(f"CREATE DATABASE {DBNAME} OWNER {ROLE}")
    con.close()
    lines = [ln for ln in (ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.exists() else []) if not ln.startswith("DATABASE_URL=")]
    ENV_FILE.write_text("\n".join(lines + [f"DATABASE_URL={url()}"]) + "\n", encoding="utf-8")
    print(f"PostgreSQL is running on 127.0.0.1:{PORT}, database '{DBNAME}'. DATABASE_URL was written to .env (git-ignored).")


def stop():
    if running():
        with open(PGDATA / "pg_ctl.log", "ab") as log:
            subprocess.run([str(tool("pg_ctl")), "-D", str(PGDATA), "stop", "-m", "fast", "-w"], stdout=log, stderr=log, check=False, timeout=120)
        print("stopped")
    else:
        print("not running")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "start":
        start()
    elif cmd == "stop":
        stop()
    elif cmd == "url":
        print(url())
    else:
        print("running" if running() else "stopped")
