"""Patient portal API + static host.

    python scripts/serve.py                         (needs accounts: python scripts/create_users.py)

Every route that returns health data takes the patient from the signed session cookie, never from the URL,
so one patient cannot ask for another's record. The analysis itself is untouched: `analyze_workbook`.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

from prana.analysis.baseline import rolling_view
from prana.api import auth
from prana.config import RAW_DIR, RESULTS_DIR, ROOT, SYNTHETIC_DIR
from prana.data.loader import list_workbooks
from prana.data.timeline import daily_series
from prana.insight.evidence import LABELS
from prana.insight.pipeline import analyze_workbook

WEB_DIR = ROOT / "web"

# (key, label, unit, group) for every daily line the patient page can draw
DAILY = [
    ("sbp", "Systolic BP", "mmHg", "Heart"), ("dbp", "Diastolic BP", "mmHg", "Heart"),
    ("resting_hr", "Resting heart rate", "bpm", "Heart"), ("hrv_ms", "Heart-rate variability", "ms", "Heart"),
    ("weight_kg", "Weight", "kg", "Body"), ("spo2", "Blood oxygen", "%", "Body"),
    ("steps", "Daily steps", "steps", "Movement"), ("active_minutes", "Active minutes", "min", "Movement"),
    ("sedentary_hours", "Sedentary time", "h", "Movement"), ("sleep_hours", "Sleep", "h", "Rest"),
    ("stress_score", "Stress score", "pts", "Rest"),
]
LAB_KEYS = ["hba1c", "fasting_glucose", "ldl_cholesterol", "hdl_cholesterol", "triglycerides", "total_cholesterol",
            "testosterone", "lh_fsh_ratio", "fasting_insulin", "tsh", "vitamin_d", "egfr"]

app = FastAPI(title="Prana Chain API", version="0.6", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(SessionMiddleware, secret_key=auth.session_secret(), session_cookie="prana_session",
                   max_age=60 * 60 * 8, same_site="lax", https_only=False)  # set https_only=True behind TLS


def _num(x, nd=2):
    if x is None:
        return None
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) or math.isinf(f) else round(f, nd)


def _d(x) -> str | None:
    return None if x is None or pd.isna(x) else pd.Timestamp(x).strftime("%Y-%m-%d")


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


def _payload(result: dict, rec, tl) -> dict:
    start = rec.window[0] if rec.window else None

    series = {}
    for key, label, unit, group in DAILY:
        s = daily_series(rec, key)
        if s.empty or s.dropna().empty:
            continue
        rv = rolling_view(s)
        series[key] = {"label": label, "unit": unit, "group": group,
                       "start": _d(s.index[0]), "n": len(s),
                       "v": [_num(x) for x in rv["value"]], "r": [_num(x) for x in rv["rolling"]],
                       "base": {"mean": _num(rv["baseline_mean"].iloc[0]), "lo": _num(rv["baseline_low"].iloc[0]),
                                "hi": _num(rv["baseline_high"].iloc[0])}}

    labs = {}
    L = rec.get("labs")
    if not L.empty:
        for key in LAB_KEYS:
            d = L[L.test_key == key].sort_values("date")
            if d.empty:
                continue
            labs[key] = {"label": LABELS.get(key, d.test.iloc[0]), "unit": d.unit.iloc[0], "ref": str(d.ref_range.iloc[0]),
                         "points": [{"d": _d(r.date), "v": _num(r.value)} for r in d.itertuples()]}

    events = []
    for r in tl[tl.source.isin(["history", "medications", "symptoms", "notes"])].itertuples():
        events.append({"d": _d(r.date), "t": r.source, "text": r.text})
    meds = [{"id": r.med_id, "name": r.medication, "dose": r.dose, "freq": r.frequency, "start": _d(r.start_date), "end": _d(r.end_date),
             "status": r.status, "for": r.indication, "tolerance": r.tolerance, "why": r.change_rationale}
            for r in rec.get("medications").itertuples()] if not rec.get("medications").empty else []
    adherence = [{"d": _d(r.date), "med": r.med_id, "pct": _num(r.adherence_pct, 0), "missed": _num(r.missed_doses, 0), "src": r.source}
                 for r in rec.get("adherence").itertuples()] if not rec.get("adherence").empty else []
    cycles = [{"d": _d(r.date), "len": _num(r.cycle_length, 0), "bleed": _num(r.bleeding_days, 0)}
              for r in rec.get("women").itertuples()] if not rec.get("women").empty else []

    scenarios = json.loads(json.dumps(result["scenarios"], default=str))
    for s in scenarios:
        s["signals"] = {k: {kk: vv for kk, vv in a.items() if kk != "values"} for k, a in s.get("signals", {}).items()}
        for e in s["evidence"]:
            e.pop("values", None)

    prof = result["profile"]
    return {"id": result["patient_id"], "window": result["window"], "start": _d(start),
            "profile": {"age": _num(prof.get("Age"), 0), "sex": prof.get("Sex"), "height": prof.get("Height (cm)"),
                        "blood": prof.get("Blood Group"), "allergies": prof.get("Allergies"),
                        "family": prof.get("Family History")},
            "quality": result["quality"], "scenarios": scenarios, "labels": LABELS, "series": series, "labs": labs,
            "events": events, "meds": meds, "adherence": adherence, "cycles": cycles,
            "reference": result["reference"]}


@lru_cache(maxsize=64)
def _patient(pid: str) -> dict:
    path = _index().get(pid)
    if path is None:
        raise HTTPException(404, "No record found for this account.")
    return _payload(*analyze_workbook(path))


class Login(BaseModel):
    id: str
    password: str


@app.post("/api/login")
def login(body: Login, request: Request):
    pid = body.id.strip().upper()[:32]
    ok, wait = auth.check(pid, body.password[:200], request.client.host if request.client else "?")
    if wait:
        raise HTTPException(429, f"Too many attempts. Please try again in {math.ceil(wait / 60)} minute(s).")
    if not ok or pid not in _index():
        raise HTTPException(401, "That ID and password don’t match.")
    request.session.clear()
    request.session["pid"] = pid
    request.session["pv"] = auth.password_version(pid)
    return {"id": pid}


@app.post("/api/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}


def _current(request: Request) -> str:
    pid = request.session.get("pid")
    if not pid or request.session.get("pv") != auth.password_version(pid):  # signed out, or password was reset
        request.session.clear()
        raise HTTPException(401, "Please sign in.")
    return pid


@app.get("/api/me")
def me(request: Request):
    """The signed-in patient's own record and analysis."""
    return _patient(_current(request))


@app.middleware("http")
async def _headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


@app.get("/api/health")
def health():
    return {"ok": True, "workbooks": len(_index())}


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
