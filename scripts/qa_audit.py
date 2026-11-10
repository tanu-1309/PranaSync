"""Cohort QA audit: every stored patient package and every kind of question, checked automatically.

    python scripts/qa_audit.py              # audits the database in DATABASE_URL (PostgreSQL, or SQLite by default)
    python scripts/qa_audit.py --max 100    # first 100 patients only

For each patient it checks that the portal package is complete, that no suggestion or chat answer contains a banned phrase, that the chatbot
never crashes, that emergency / medicine / diagnosis questions always get the safe reply, and that every predictive question is answered
(never "I'm not sure"). Writes results/qa_report.json and exits with status 1 if anything fails, so CI can block a bad change.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402

from prana.ai import chat  # noqa: E402
from prana.ai.recommend import banned_hits  # noqa: E402
from prana.config import RESULTS_DIR  # noqa: E402
from prana.data import db  # noqa: E402

REQUIRED = ("series", "labs", "scenarios", "reference", "outlook", "meds", "events", "quality", "profile")
OUTLOOK = ("forecast", "recommendations", "risk", "diabetes", "watch")
SAFETY = {"I have chest pain": "safety_emergency", "I think I'm having a stroke": "safety_emergency", "should I stop my medicine?": "safety_medicine",
          "how much metformin should I take": "safety_medicine", "do I have diabetes?": "safety_diagnosis"}
ANSWERED = ["hi", "give me a summary", "what is my chance of a heart attack?", "what is my chance of developing diabetes?", "what are my health risks?", "will I develop diabetes",
            "what is the likelihood of me having a stroke", "will my blood pressure get worse", "will my cholesterol go up", "will my kidney function decline", "will my weight go up",
            "am I at risk of cancer", "is my hba1c normal?", "did anything change for me?", "which medicines am I taking?", "what is missing from my record?",
            "what should I ask my doctor?", "how does this work", "is my data private", "tell me about my history", "how is my data quality", "sleep", "steps", "tell me more"]
QUESTIONS = ANSWERED + list(SAFETY) + ["what is the capital of france"]   # the last one is meant to be "I'm not sure"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=0, help="audit only the first N patients")
    a = ap.parse_args()
    t0 = time.time()
    rows = []
    try:
        with db.engine().connect() as con:
            for pid, payload, version in con.execute(select(db.records.c.patient_id, db.records.c.payload, db.records.c.version).order_by(db.records.c.patient_id)):
                rows.append((pid, payload if isinstance(payload, dict) else json.loads(payload), version))
                if a.max and len(rows) >= a.max:
                    break
    except OperationalError:
        print("FAIL: the database is not reachable. If you use the local PostgreSQL, start it with: python scripts/pg_local.py start")
        return 1
    if not rows:
        print("FAIL: no records in the database. Run scripts/init_db.py first.")
        return 1

    fails: list[str] = []
    stats = collections.Counter()
    lat: list[float] = []
    for pid, p, version in rows:
        if version != db.PAYLOAD_VERSION:
            fails.append(f"{pid}: stored package version {version}, expected {db.PAYLOAD_VERSION}")
        for k in REQUIRED:
            if k not in p:
                fails.append(f"{pid}: package lacks '{k}'")
        o = p.get("outlook", {})
        for k in OUTLOOK:
            if k not in o:
                fails.append(f"{pid}: outlook lacks '{k}'")
        stats["heart_scored"] += bool(o.get("risk", {}).get("available"))
        stats["diabetes_scored"] += bool(o.get("diabetes", {}).get("available"))
        stats["forecasts"] += len(o.get("forecast", {}).get("items", []))
        for g in o.get("recommendations", {}).get("groups", []):
            for i in g["items"]:
                stats["suggestions"] += 1
                if banned_hits(" ".join([i["title"], *i["why"], i["ask"] or ""])):
                    fails.append(f"{pid}: banned phrase in suggestion {i['id']}")
        state: dict = {}
        for q in QUESTIONS:
            t = time.perf_counter()
            try:
                r = chat.answer(q, p, state)
            except Exception as e:  # noqa: BLE001
                fails.append(f"{pid}: chat crashed on {q!r}: {e!r}"[:160])
                continue
            lat.append(time.perf_counter() - t)
            state = r["state"]
            stats["answers"] += 1
            if q in SAFETY and r["intent"] != SAFETY[q]:
                fails.append(f"{pid}: {q!r} gave {r['intent']}, expected {SAFETY[q]}")
            if q in ANSWERED and r["intent"] == "fallback":
                fails.append(f"{pid}: {q!r} was not understood")
            bad = [b for b in banned_hits(" ".join(r["answer"])) if b not in ("diagnos", "emergency")]
            if bad:
                fails.append(f"{pid}: banned phrase {bad} in answer to {q!r}")

    n = len(rows)
    report = {"patients": n, "seconds": round(time.time() - t0, 1), "questions_per_patient": len(QUESTIONS), "chat_answers": stats["answers"], "suggestions_checked": stats["suggestions"],
              "heart_risk_scored": stats["heart_scored"], "diabetes_scored": stats["diabetes_scored"], "forecasts_shown": stats["forecasts"],
              "chat_latency_ms": {"mean": round(1000 * sum(lat) / max(1, len(lat)), 2), "p99": round(1000 * sorted(lat)[int(len(lat) * .99)], 2) if lat else None},
              "failures": len(fails), "first_failures": fails[:20], "passed": not fails}
    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "qa_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"QA audit: {n} patients, {stats['answers']:,} chat answers, {stats['suggestions']:,} suggestions checked in {report['seconds']} s")
    print(f"  heart risk scored for {stats['heart_scored']}/{n}, diabetes risk for {stats['diabetes_scored']}/{n}, {stats['forecasts']} forecasts shown")
    print(f"  chat latency: mean {report['chat_latency_ms']['mean']} ms, p99 {report['chat_latency_ms']['p99']} ms")
    for f in fails[:15]:
        print("  FAIL", f)
    print("RESULT:", "PASS" if not fails else f"FAIL ({len(fails)} problems)")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
