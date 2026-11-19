"""The routes behind the Analytics & Intelligence page.

The statistics come first and are fast (no AI). Each AI result is fetched separately, so the page can show numbers while a model is still writing, and no model
runs just because a page was opened: the page asks for stored results first (`cached_only=1`) and only calls a model when the person presses a button.
Like every route that returns health data, the patient comes from the signed session cookie, never from the URL or a parameter.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from prana.ai import analytics_ai, llm, medical_explain, model_router
from prana.ai.facts import build_facts
from prana.ai.narrative import facts_hash
from prana.api.analytics import architecture, build_analytics, build_report, models_status
from prana.data import db

LIMIT, WINDOW = 6, 60.0


class Ask(BaseModel):
    question: str


def _built_at(pid: str) -> str | None:
    try:
        with db.engine().connect() as con:
            v = con.execute(select(db.records.c.built_at).where(db.records.c.patient_id == pid)).scalar()
        return v.isoformat() if v else None
    except Exception:  # noqa: BLE001
        return None


def _nemotron_view(n: dict | None) -> dict:
    """The existing portal text, shown as Nemotron's result. Its generation time was not recorded, so it is reported as not recorded."""
    if not n:
        return {"provider": "nemotron", "status": "not_generated", "message": "Nothing has been generated for this record yet."}
    if not n.get("available"):
        return {"provider": "nemotron", "status": "disabled" if not llm.enabled() else "failed", "validation": "failed", "message": n.get("reason")}
    name = (n.get("model") or "").split(":", 1)[-1]
    return {"provider": "nemotron", "status": "ok", "model_name": name, "model_version": "not reported", "generated_at": n.get("generated_at"), "latency_ms": None, "latency_note": "not recorded",
            "validation": "passed: every number came from the record and no banned phrase was used", "headline": n.get("headline"), "overview": n.get("overview"), "levels": n.get("levels"),
            "outlook": n.get("outlook"), "findings": n.get("findings", []), "analytical_findings_referenced": [f.get("title") for f in n.get("findings", []) if f.get("title")]}


def make_router(current, patient) -> APIRouter:
    router = APIRouter()
    hits: dict[str, deque] = defaultdict(deque)
    router.hits = hits                         # exposed so tests can reset the limiter

    def limited(pid: str, what: str) -> None:
        now, q = time.monotonic(), hits[f"{pid}:{what}"]
        while q and now - q[0] > WINDOW:
            q.popleft()
        if len(q) >= LIMIT:
            raise HTTPException(429, "Please wait a moment before asking again.")
        q.append(now)

    @router.get("/api/analytics")
    def analytics(request: Request):
        pid = current(request)
        models = models_status()
        out = {**build_analytics(patient(pid), _built_at(pid)), "models": models, "architecture": architecture(models)}
        db.audit("analytics", pid, part="statistics")
        return out

    def stored_nemotron(pid: str, payload: dict) -> dict | None:
        got = db.get_narrative(pid, facts_hash(build_facts(payload)))
        return {"available": True, **got} if got else None

    @router.get("/api/analytics/summary")
    def summary(request: Request, cached_only: int = 0):
        """Nemotron's plain-language summary and one explanation per graph. `cached_only=1` returns only a stored result and never calls a model."""
        pid = current(request)
        payload = patient(pid)
        if not cached_only:
            limited(pid, "summary")
            db.audit("analytics", pid, part="summary")
        return analytics_ai.summarize(pid, build_analytics(payload, _built_at(pid)), cached_only=bool(cached_only))

    @router.get("/api/analytics/insights")
    def insights(request: Request, cached_only: int = 0, fallback: int = 0):
        """MedGemma's insights with the evidence, reasoning, confidence and medical context behind each. `fallback=1` lets Nemotron answer, labelled as Nemotron, if MedGemma is not connected."""
        pid = current(request)
        payload = patient(pid)
        if not cached_only:
            limited(pid, "insights")
            db.audit("analytics", pid, part="insights")
        return analytics_ai.insights(pid, payload, build_analytics(payload, _built_at(pid)), cached_only=bool(cached_only), allow_fallback=bool(fallback))

    @router.post("/api/analytics/ask")
    def ask(body: Ask, request: Request):
        """A medical-context question about the signed-in patient's own record. The fixed safety gate runs first; the audit log records the topic only, never the question."""
        pid = current(request)
        limited(pid, "ask")
        db.audit("analytics", pid, part="ask")
        return medical_explain.assess_question(pid, patient(pid), body.question[:500])

    @router.get("/api/analytics/compare")
    def compare(request: Request):
        pid = current(request)
        if not model_router.comparison_enabled():
            return {"status": "disabled", "message": "Model comparison is switched off."}
        limited(pid, "compare")
        db.audit("analytics", pid, part="compare")
        return medical_explain.compare_analytics(pid, patient(pid))

    @router.get("/api/analytics/report")
    def report(request: Request):
        """The consolidated report. It uses only results already stored, so opening it never triggers a model."""
        pid = current(request)
        payload = patient(pid)
        stats = build_analytics(payload, _built_at(pid))
        n = stored_nemotron(pid, payload)
        nv = _nemotron_view(n) if n else None
        mv = medical_explain.cached_explanation(pid, payload) if model_router.routes()["medgemma_enabled"] else None
        db.audit("analytics", pid, part="report")
        return build_report(stats, nv, mv, payload.get("outlook", {}).get("recommendations"))

    return router
