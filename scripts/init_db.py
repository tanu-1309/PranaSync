"""Create the database schema and load every patient into it.

    python scripts/pg_local.py start          # development only: a private PostgreSQL (writes DATABASE_URL to .env)
    python scripts/init_db.py                 # schema + all workbooks + portal packages + import of the old users.json
    python scripts/init_db.py --limit 20      # quick trial on 20 workbooks
    python scripts/init_db.py --reset         # drop everything first (destroys data)

For each workbook it runs the analysis once, then stores: the profile, the unified timeline, the findings and the
ready-made portal package. After this the web server reads from the database and does not touch the Excel files.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from prana.api import auth  # noqa: E402
from prana.api.payload import build_payload  # noqa: E402
from prana.config import RAW_DIR, SYNTHETIC_DIR  # noqa: E402
from prana.data import db  # noqa: E402
from prana.data.loader import list_workbooks  # noqa: E402
from prana.insight.pipeline import analyze_workbook  # noqa: E402


def load_one(path: str) -> tuple[str, str | None]:
    """Analyse one workbook and store everything about it. Returns (file name, error or None)."""
    try:
        result, rec, tl = analyze_workbook(path)
        db.save_patient(rec, tl)
        db.save_findings(rec.patient_id, result["scenarios"])
        db.save_record(rec.patient_id, build_payload(result, rec, tl))
        return Path(path).name, None
    except Exception as exc:  # report and carry on with the others
        return Path(path).name, repr(exc)[:200]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--reset", action="store_true", help="drop all tables first")
    ap.add_argument("--workers", type=int, default=min(4, os.cpu_count() or 2))
    a = ap.parse_args()

    print(f"database: {db.dialect()}")
    db.init_db(reset=a.reset)
    files = (list_workbooks(RAW_DIR) or list_workbooks(SYNTHETIC_DIR))[: a.limit]
    t0, errors = time.time(), []
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        futs = [pool.submit(load_one, str(p)) for p in files]
        for i, f in enumerate(as_completed(futs), 1):
            name, err = f.result()
            if err:
                errors.append((name, err))
            if i % 50 == 0 or i == len(files):
                print(f"  {i}/{len(files)} loaded ({time.time() - t0:.0f}s)", flush=True)

    legacy = auth.legacy_users()
    todo = {k: v for k, v in legacy.items() if k not in db.user_ids()}
    if todo:
        db.set_user_hashes(todo)
        print(f"imported {len(todo)} account hashes from the old users.json")

    print("row counts:", db.counts())
    for name, err in errors[:10]:
        print("  ERROR", name, err)
    print(f"done in {time.time() - t0:.0f}s, {len(errors)} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
