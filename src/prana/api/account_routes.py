"""Account page: the person's own details (view and edit), a download of everything held about them, and the facts the "How it works" page shows about the models.

The person always comes from the signed session cookie, never from the URL. Guest mode is read-only. Every edit is written to the audit log (which fields, never the values).
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from prana.config import RESULTS_DIR, setting
from prana.data import db, docstore
from prana.risk import service
from prana.risk.model import _value_text
from prana.risk.params import PARAMS
from prana.risk.params import label as param_label
from prana.risk.review import CHOICES as CATEGORICAL

MODEL_FILE = service.model.MODEL_DIR / "risk_model.json"

# field -> (label, kind, max length). `kind` drives the form and the checks.
FIELDS = {
    "name": ("Name", "text", 80), "age": ("Age", "int", 3), "sex": ("Sex", "choice", 20), "blood": ("Blood group", "choice", 4), "height": ("Height (cm)", "int", 3),
    "allergies": ("Allergies", "text", 300), "family": ("Family history", "text", 300),
    "email": ("Email", "email", 120), "phone": ("Phone", "phone", 30), "emergency": ("Emergency contact", "text", 160),
}
CHOICES = {"sex": ["Female", "Male", "Other", "Prefer not to say"], "blood": ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "Unknown"]}
RANGE = {"age": (0, 120), "height": (50, 250)}
CTRL = re.compile(r"[\x00-\x1f\x7f<>]")          # control characters and angle brackets are never part of a name, address or note
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE = re.compile(r"^[0-9+()\-.\s]{5,30}$")


class ProfileIn(BaseModel):
    values: dict[str, str | int | None]


def clean(values: dict) -> dict:
    """Checked, trimmed values for the known fields only. Raises 422 with a sentence a person can act on."""
    out = {}
    for k, v in values.items():
        if k not in FIELDS:
            continue
        label, kind, n = FIELDS[k]
        v = "" if v is None else str(v).strip()
        if not v:
            out[k] = ""
            continue
        if len(v) > n or CTRL.search(v):
            raise HTTPException(422, f"{label}: please use up to {n} plain characters.")
        if kind == "int":
            if not v.isdigit() or not (RANGE[k][0] <= int(v) <= RANGE[k][1]):
                raise HTTPException(422, f"{label}: please enter a whole number from {RANGE[k][0]} to {RANGE[k][1]}.")
            v = int(v)
        elif kind == "choice" and v not in CHOICES[k]:
            raise HTTPException(422, f"{label}: please choose one of the listed options.")
        elif kind == "email" and not EMAIL.match(v):
            raise HTTPException(422, "Email: that doesn’t look like an email address.")
        elif kind == "phone" and not PHONE.match(v):
            raise HTTPException(422, "Phone: use digits, spaces, + ( ) - only.")
        out[k] = v
    return out


def record_profile(pid: str, payload: dict) -> dict:
    """What the record itself says about the person, in the same fields (before any edits)."""
    p = payload.get("profile", {}) or {}
    return {"name": db.get_display_name(pid) or "", "age": None if p.get("age") is None else round(p["age"]), "sex": p.get("sex") or "", "blood": p.get("blood") or "",
            "height": p.get("height") or "", "allergies": p.get("allergies") or "", "family": p.get("family") or ""}


def merged(pid: str, payload: dict) -> dict:
    """The record's values, with whatever the person has edited on top, and for each field where it came from."""
    base, mine = record_profile(pid, payload), db.get_profile(pid)
    out, source = {}, {}
    for k in FIELDS:
        edited = k in mine and mine[k] not in ("", None)
        out[k] = mine[k] if edited else base.get(k, "")
        source[k] = "you" if edited or (k == "name" and base.get(k)) else ("record" if base.get(k) not in ("", None) else "empty")     # a name on file was typed by the person when they signed up
    return {"values": out, "source": source, "fields": {k: {"label": v[0], "kind": v[1], "max": v[2], "choices": CHOICES.get(k)} for k, v in FIELDS.items()}}


def apply_profile(pid: str, payload: dict) -> dict:
    """The patient package with the person's own edits on top, for /api/me. The stored record itself is never changed."""
    mine = db.get_profile(pid)
    if not mine:
        return payload
    prof = dict(payload.get("profile", {}) or {})
    for k in ("age", "sex", "blood", "height", "allergies", "family"):
        if mine.get(k) not in ("", None):
            prof[k] = mine[k] if k not in ("age",) else float(mine[k])
    return {**payload, "profile": prof, "contact": {k: mine.get(k, "") for k in ("name", "email", "phone", "emergency")}}


def make_router(current, patient) -> APIRouter:
    router = APIRouter()

    def writer(request: Request) -> str:
        pid = current(request)
        if request.session.get("guest"):
            raise HTTPException(403, "Guest mode is read-only. Sign in with your own ID to edit your details.")
        return pid

    @router.get("/api/profile")
    def get_profile(request: Request):
        pid = current(request)
        return {**merged(pid, patient(pid)), "id": pid, "can_edit": not request.session.get("guest")}

    @router.put("/api/profile")
    def put_profile(body: ProfileIn, request: Request):
        pid = writer(request)
        new = clean(body.values)
        mine = {**db.get_profile(pid), **new}
        db.save_profile(pid, {k: v for k, v in mine.items() if v not in ("", None)})
        if "name" in new and db.is_registered(pid):
            db.set_display_name(pid, new["name"] or pid)
        db.audit("profile_edit", pid, fields=sorted(new))
        return {**merged(pid, patient(pid)), "id": pid, "can_edit": True}

    @router.get("/api/export")
    def export(request: Request):
        """Everything held about the person, as one JSON file they can keep."""
        pid = writer(request)
        payload = patient(pid)
        docs = [{k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in d.items() if k != "patient_id"} for d in db.list_documents(pid)]
        obs = [{k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in o.items()} for o in db.read_observations(pid)]
        db.audit("export", pid)
        return {"exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "id": pid, "details": merged(pid, payload)["values"],
                "documents": docs, "document_records": docstore.all_for(docstore.Actor(pid), pid), "values_read_from_documents": obs, "risk_classes": service.brief(pid),
                "note": "Your uploaded files and these values are kept only for your account. Delete a document on the Upload page and its values go with it."}

    @router.get("/api/values/history")
    def values_history(request: Request):
        """Each measured value across the person's uploaded documents, oldest to newest, so a newer report shows what changed. Categories (sex, smoking…) are left out."""
        pid = current(request)
        docs = {d["doc_id"]: d["filename"] for d in db.list_documents(pid)}
        series: dict[str, list[dict]] = {}
        for o in db.read_observations(pid):
            if o["param"] in CATEGORICAL or o["param"] not in PARAMS:
                continue
            on = o["observed_on"]
            series.setdefault(o["param"], []).append({"date": on.isoformat() if on else None, "value": float(o["value"]), "text": _value_text(o["param"], float(o["value"])), "document": docs.get(o["doc_id"], "")})
        rows = []
        for p, pts in series.items():
            first, last = pts[0], pts[-1]
            change = round(100 * (last["value"] - first["value"]) / first["value"], 1) if len(pts) > 1 and first["value"] else None
            rows.append({"param": p, "label": param_label(p), "unit": PARAMS[p][1], "points": pts, "change_pct": change})
        rows.sort(key=lambda r: (-len(r["points"]), r["label"]))
        return {"values": rows, "documents": len(docs)}

    @router.get("/api/clinical/risk")
    def clinical_risk(request: Request):
        """Deep view of the three risk areas for a clinician: every value used, where it came from, and each one's share of the push."""
        return service.risk_detail(current(request))

    @router.get("/api/clinical/documents")
    def clinical_documents(request: Request):
        """The person's own stored documents without the extracted text: times, status, every value with its original reading, and the correction history."""
        pid = current(request)
        out = []
        for d in docstore.all_for(docstore.Actor(pid), pid):
            out.append({**{k: v for k, v in d.items() if k not in ("extracted_text", "patient_id")}, "text_characters": len(d.get("extracted_text", ""))})
        return {"documents": out}

    @router.get("/api/models")
    def models(request: Request):
        """What each model does and how it was checked, for the How it works page. Real numbers only: none are made up, and where nothing was measured it says so."""
        current(request)
        risk = json.loads(MODEL_FILE.read_text(encoding="utf-8")) if MODEL_FILE.exists() else None
        out: dict = {"risk": None, "pattern": None, "forecast": None, "extraction": None, "redteam": None}
        if risk:
            top = {}
            for area, a in risk["areas"].items():
                imp = a["importance"]
                tot = sum(imp.values()) or 1
                top[area] = [{"key": k, "label": param_label(k), "share": round(v / tot, 3)} for k, v in sorted(imp.items(), key=lambda kv: -kv[1])[:6] if v > 0]
            out["risk"] = {"n_patients": risk["n_patients"], "development_check": risk["development_check"], "top_parameters": top,
                           "definitions": {a: x["label_definition"] for a, x in risk["areas"].items()}, "prevalence": {a: x["prevalence"] for a, x in risk["areas"].items()}}
        for name, f in (("pattern", "metrics.json"), ("forecast", "forecast_backtest.json"), ("extraction", "extraction_eval.json"), ("redteam", "redteam.json")):
            p = RESULTS_DIR / f
            if p.exists():
                out[name] = json.loads(p.read_text(encoding="utf-8"))
        from prana.ai import guardrails, llm, medgemma
        out["rails"] = [{"id": r[0], "name": r[1], "plain": r[2], "when": r[3]} for r in guardrails.RAILS]
        if out.get("redteam"):
            out["redteam"] = {k: out["redteam"].get(k) for k in ("model", "passed", "failed", "not_tested", "tested", "total", "chat_prompts", "booby_trapped_documents", "by_category", "note", "rescored")}
        out["language_models"] = {"text": {"name": setting("PRANA_LLM_MODEL") or llm.status(), "on": llm.status() != "off"}, "insights": medgemma.status()}
        return out

    return router
