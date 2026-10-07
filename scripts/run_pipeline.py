"""Run the full pipeline on a folder of workbooks.

    python scripts/run_pipeline.py --data data/raw --limit 1000        # real Prana Chain data
    python scripts/run_pipeline.py --data data/synthetic               # generated test data

Outputs
  results/insights/<patient>.json   evidence pack + explanation per scenario
  results/summary.csv               one row per patient x scenario
  database (SQLite data/prana.db or DATABASE_URL): patients, timeline, findings
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from prana.config import RESULTS_DIR  # noqa: E402
from prana.data import db  # noqa: E402
from prana.data.loader import list_workbooks  # noqa: E402
from prana.insight.pipeline import analyze_workbook  # noqa: E402


def run(folder: Path, limit: int | None, save_db: bool, out_dir: Path = RESULTS_DIR) -> pd.DataFrame:
    files = list_workbooks(folder)[:limit]
    (out_dir / "insights").mkdir(parents=True, exist_ok=True)
    if save_db:
        db.init_db()
    rows, t0, errors = [], time.time(), []
    for i, p in enumerate(files, 1):
        try:
            result, rec, tl = analyze_workbook(p)
        except Exception as exc:  # keep going; report at the end
            errors.append((p.name, repr(exc)))
            continue
        slim = json.loads(json.dumps(result, default=str))
        for s in slim["scenarios"]:
            s.pop("signals", None)  # full per-signal stats stay in the DB
        (out_dir / "insights" / f"{rec.patient_id}.json").write_text(json.dumps(slim, indent=2))
        if save_db:
            db.save_patient(rec, tl)
            db.save_findings(rec.patient_id, result["scenarios"])
        for s in result["scenarios"]:
            rows.append({"patient_id": rec.patient_id, "sex": rec.profile.get("Sex"), "age": rec.profile.get("Age"),
                         "scenario": s["scenario"], "status": s["status"], "surfaced": s["surfaced"],
                         "pattern_signals": ";".join(s["pattern_signals"]), "pattern_start": s.get("pattern_start"),
                         "context": "; ".join(c["text"] for c in s["context"] if c["type"] != "symptoms"),
                         "missing_data": "; ".join(m["key"] for m in s["missing_data"])})
        if i % 25 == 0:
            print(f"  {i}/{len(files)} done ({time.time() - t0:.0f}s)")
    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "summary.csv", index=False)
    print(f"analysed {len(files) - len(errors)} workbooks in {time.time() - t0:.0f}s; errors: {len(errors)}")
    for e in errors[:10]:
        print("  ERROR", e)
    if not df.empty:
        print(df.groupby(["scenario", "status"]).size().unstack(fill_value=0).to_string())
    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=Path("data/synthetic"))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--no-db", action="store_true")
    a = ap.parse_args()
    run(a.data, a.limit, not a.no_db)
