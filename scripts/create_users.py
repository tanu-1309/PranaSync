"""Create one login per patient workbook.

    python scripts/create_users.py                  # accounts for every workbook that has none yet
    python scripts/create_users.py --reset PC0042   # issue a new password for one patient
    python scripts/create_users.py --reset-all      # new random passwords for everyone

Writes
  data/users.json                 patient ID -> scrypt hash        (what the server checks)
  data/credentials_ISSUE_ONCE.csv patient ID, temporary password   (hand out, then delete)

Both files are git-ignored. Passwords are 12 random characters in three groups (for example Kq7m-Xw3R-b9Zp), drawn from
letters and digits without look-alikes (no 0/O, 1/l/I). They come from `secrets`, Python's cryptographically secure random
generator; the plain `random` module is predictable and must not be used for passwords.
"""
from __future__ import annotations

import argparse
import csv
import json
import secrets
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from prana.api.auth import USERS_FILE, hash_password, load_users  # noqa: E402
from prana.config import DATA_DIR, RAW_DIR, SYNTHETIC_DIR  # noqa: E402
from prana.data.loader import list_workbooks  # noqa: E402

ALPHABET = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # 54 symbols, no look-alikes


def new_password(groups: int = 3, size: int = 4) -> str:
    return "-".join("".join(secrets.choice(ALPHABET) for _ in range(size)) for _ in range(groups))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", nargs="*", default=[], help="patient IDs to issue a fresh password")
    ap.add_argument("--reset-all", action="store_true", help="issue a fresh password to every patient (replaces the credentials sheet)")
    a = ap.parse_args()

    ids = [p.stem for p in (list_workbooks(RAW_DIR) or list_workbooks(SYNTHETIC_DIR))]
    users = load_users()
    todo = ids if a.reset_all else [i for i in ids if i not in users or i in a.reset]
    if not todo:
        print("Everyone already has an account.")
        raise SystemExit(0)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    sheet = DATA_DIR / "credentials_ISSUE_ONCE.csv"
    # --reset-all replaces the sheet (old temporary passwords stop working, so the old list must not linger)
    new_file = a.reset_all or not sheet.exists()
    try:
        fh = open(sheet, "w" if new_file else "a", newline="", encoding="utf-8")
    except PermissionError:  # the old sheet is open in another program (Excel, a viewer)
        sheet = DATA_DIR / f"credentials_{datetime.now():%Y%m%d-%H%M%S}_ISSUE_ONCE.csv"
        fh, new_file = open(sheet, "w", newline="", encoding="utf-8"), True
        print("NOTE: credentials_ISSUE_ONCE.csv is open elsewhere, so the new list is in a new file. "
              "Close and delete the old one: its passwords no longer work.")
    with fh:
        w = csv.writer(fh)
        if new_file:
            w.writerow(["patient_id", "temporary_password"])
        for pid in todo:
            pw = new_password()
            users[pid] = hash_password(pw)
            w.writerow([pid, pw])
    USERS_FILE.write_text(json.dumps(users, indent=0), encoding="utf-8")
    print(f"Created {len(todo)} account(s). Hashes: {USERS_FILE}\nCredentials to hand out: {sheet}")
