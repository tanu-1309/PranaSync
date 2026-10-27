"""Data profiling across many workbooks (owner: Sneha).

    python -m prana.data.profiling --data data/raw --limit 100

Writes results/data_profile.csv (one row per workbook) and prints a summary:
rows per sheet, blank cells, impossible values, duplicate days, unit fixes,
missing sheets. This is the evidence for the "data quality" part of the demo.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from prana.config import RESULTS_DIR
from prana.data.loader import list_workbooks, load_workbook


def profile_folder(folder: Path, limit: int | None = None) -> pd.DataFrame:
    rows = []
    for p in list_workbooks(folder)[:limit]:
        rec = load_workbook(p)
        q = dict(rec.quality)
        q["patient_id"] = rec.patient_id
        q["sex"] = rec.profile.get("Sex")
        q["age"] = rec.profile.get("Age")
        q["missing_sheets"] = ";".join(q.get("missing_sheets", []))
        q["history_findings"] = "; ".join(rec.get("history").get("finding", pd.Series(dtype=str)).astype(str))
        rows.append(q)
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=Path("data/raw"))
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    df = profile_folder(a.data, a.limit)
    RESULTS_DIR.mkdir(exist_ok=True)
    df.to_csv(RESULTS_DIR / "data_profile.csv", index=False)
    num = df.select_dtypes("number")
    print(f"profiled {len(df)} workbooks")
    print(num.describe().T[["mean", "min", "max"]].round(2).to_string())


if __name__ == "__main__":
    main()
