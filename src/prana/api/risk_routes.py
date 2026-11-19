"""Routes for registering, uploading documents one at a time, and reading the risk result.

As everywhere in this portal, the person comes from the signed session cookie, never from the URL. Guest mode is read-only.
Files are checked (size, type, content), read in memory, and kept under data/uploads/<person>/ with a generated name. Only values the extractor
found in plausible ranges are stored, each with the line it came from.
"""
from __future__ import annotations

import hashlib
import secrets
import time
import uuid
from collections import defaultdict, deque
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from prana.api import auth
from prana.config import DATA_DIR
from prana.data import db, docstore
from prana.risk import review, service
from prana.risk.extract import MAX_BYTES, SUPPORTED, extract
from prana.risk.model import _value_text as value_text
from prana.risk.params import label

UPLOAD_DIR = DATA_DIR / "uploads"
LIMIT, WINDOW = 15, 60.0


class Edits(BaseModel):
    edits: dict[str, dict]


class Register(BaseModel):
    name: str = ""
    password: str


def _new_id() -> str:
    return "PS" + "".join(secrets.choice("0123456789") for _ in range(6))


def make_router(current) -> APIRouter:
    router = APIRouter()
    hits: dict[str, deque] = defaultdict(deque)
    router.hits = hits

    def limited(pid: str) -> None:
        now, q = time.monotonic(), hits[pid]
        while q and now - q[0] > WINDOW:
            q.popleft()
        if len(q) >= LIMIT:
            raise HTTPException(429, "Please wait a moment before uploading again.")
        q.append(now)

    def writer(request: Request) -> str:
        pid = current(request)
        if request.session.get("guest"):
            raise HTTPException(403, "Guest mode is read-only. Create an account to upload your own documents.")
        return pid

    def admin_actor(request: Request) -> docstore.Actor:
        pid = current(request)
        if request.session.get("guest") or not docstore.is_admin(pid):
            db.audit("admin_denied", pid, path=request.url.path[:60])
            raise HTTPException(403, "This page is for administrators.")
        return docstore.Actor(pid, admin=True)

    def load_doc(pid: str, doc_id: str) -> dict:
        """The person's own document from the document store. One uploaded before the store existed is rebuilt from the main database (and its saved file)."""
        me = docstore.Actor(pid)
        doc = docstore.get(me, pid, doc_id)
        if doc is None:
            main = db.get_document(pid, doc_id)
            if main is None:
                raise HTTPException(404, "That document was not found.")
            text = ""
            for f in (UPLOAD_DIR / pid).glob(f"{doc_id}.*"):
                try:
                    text = extract(main["filename"], docstore.open_bytes(pid, doc_id, f.read_bytes())).text
                except Exception:      # an unreadable old file just means no text is shown
                    text = ""
            doc = review.rebuild_legacy(pid, main, db.document_observations(pid, doc_id), text)
            if main.get("status") == "confirmed":
                doc["status"] = "confirmed"
            docstore.put(me, doc)
        return doc

    @router.post("/api/register")
    def register(body: Register, request: Request):
        pw = body.password[:200]
        if len(pw) < 10:
            raise HTTPException(422, "Please choose a password of at least 10 characters.")
        if pw.lower() in ("password123", "1234567890", "qwertyuiop"):
            raise HTTPException(422, "That password is too easy to guess. Please choose another.")
        ip = request.client.host if request.client else "?"
        q = hits[f"register:{ip}"]
        now = time.monotonic()
        while q and now - q[0] > 600:
            q.popleft()
        if len(q) >= 5:
            raise HTTPException(429, "Too many new accounts from this device. Please try again later.")
        q.append(now)
        for _ in range(20):
            pid = _new_id()
            if db.create_account(pid, body.name.strip()[:80] or "New patient", auth.hash_password(pw)):
                break
        else:
            raise HTTPException(503, "Could not create an account right now. Please try again.")
        request.session.clear()
        request.session["pid"] = pid
        request.session["pv"] = auth.password_version(pid)
        db.audit("register", pid)
        return {"id": pid}

    @router.get("/api/risk")
    def risk(request: Request):
        return service.risk_for(current(request))

    @router.get("/api/documents")
    def documents(request: Request):
        pid = current(request)
        st = docstore.statuses(docstore.Actor(pid), pid)
        return {"documents": [{"id": d["doc_id"], "filename": d["filename"], "kind": d["kind"], "n_values": d["n_values"], "uploaded_at": d["uploaded_at"].isoformat() if d["uploaded_at"] else None,
                               "status": st.get(d["doc_id"], {}).get("status", "confirmed" if d.get("status") == "confirmed" else "needs_review")}
                              for d in db.list_documents(pid)], "supported": list(SUPPORTED), "max_mb": MAX_BYTES // (1024 * 1024), "can_upload": not request.session.get("guest")}

    @router.post("/api/documents")
    async def upload(request: Request, file: UploadFile = File(...)):
        pid = writer(request)
        limited(pid)
        data = await file.read(MAX_BYTES + 1)
        name = Path(file.filename or "document").name[:120]
        digest = hashlib.sha256(data).hexdigest()
        if db.find_document(pid, digest):
            raise HTTPException(409, "You already uploaded this document.")
        ex = await run_in_threadpool(extract, name, data)          # reading can wait on the optional AI second reader: do not block other requests
        if ex.error:
            db.audit("upload_rejected", pid, reason=ex.error[:60])
            raise HTTPException(422, ex.error)
        doc_id = str(uuid.uuid4())
        db.add_document({"doc_id": doc_id, "patient_id": pid, "filename": name, "sha256": digest, "size": len(data), "kind": ex.kind, "status": "read",
                         "message": " ".join(ex.notes)[:500] or None, "n_values": len(ex.observations)}, ex.observations)
        folder = UPLOAD_DIR / pid
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{doc_id}{Path(name).suffix.lower()}").write_bytes(docstore.seal_bytes(pid, doc_id, data))
        docstore.put(docstore.Actor(pid), review.new_document(pid, doc_id, name, len(data), digest, Path(name).suffix.lower(), ex.kind, ex.observations, ex.notes, ex.text))
        result = service.risk_for(pid)
        db.save_snapshot(pid, doc_id, result)
        db.audit("upload_ok", pid, values=len(ex.observations))
        return {"document": {"id": doc_id, "filename": name, "kind": ex.kind, "review": f"#/review/{doc_id}"}, "read": [{"key": o["param"], "label": label(o["param"]), "text": value_text(o["param"], o["value"]), "from": o["source_text"]} for o in ex.observations],
                "notes": ex.notes, "risk": result}

    @router.delete("/api/documents/{doc_id}")
    def remove(doc_id: str, request: Request):
        pid = writer(request)
        if not db.delete_document(pid, doc_id):
            raise HTTPException(404, "That document was not found.")
        docstore.remove(docstore.Actor(pid), pid, doc_id)
        for f in (UPLOAD_DIR / pid).glob(f"{doc_id}.*"):
            f.unlink(missing_ok=True)
        result = service.risk_for(pid)
        db.save_snapshot(pid, None, result)
        db.audit("document_deleted", pid)
        return {"ok": True, "risk": result}

    @router.get("/api/documents/{doc_id}")
    def one_document(doc_id: str, request: Request):
        """The review page's data: the whole JSON document (times, extracted text, values with their original readings). Only the signed-in owner gets it."""
        pid = current(request)
        return {"document": load_doc(pid, doc_id), "can_edit": not request.session.get("guest")}

    @router.put("/api/documents/{doc_id}/values")
    def correct_values(doc_id: str, body: Edits, request: Request):
        """Change values that were read wrongly (or set one aside). Only values already read from this document can be changed, and each is checked."""
        pid = writer(request)
        limited(pid)
        doc = load_doc(pid, doc_id)
        problems = review.apply_edits(doc, body.edits)
        if problems:
            raise HTTPException(422, " ".join(problems))
        db.replace_observations(pid, doc_id, review.active_observations(doc))
        docstore.put(docstore.Actor(pid), doc)
        result = service.risk_for(pid)
        db.save_snapshot(pid, doc_id, result)
        db.audit("document_values_reviewed", pid, changes=len(doc["edit_history"]))
        return {"document": doc, "risk": result}

    # ---- administrators: read-only, and every look is written to the audit log
    @router.get("/api/admin/people")
    def admin_people(request: Request):
        who = admin_actor(request)
        db.audit("admin_document_list", who.patient_id)
        return {"people": docstore.owners(who)}

    @router.get("/api/admin/people/{pid}/documents")
    def admin_documents(pid: str, request: Request):
        who = admin_actor(request)
        db.audit("admin_document_list", who.patient_id, target=pid[:32])
        return {"patient_id": pid, "documents": [{"doc_id": d["doc_id"], "filename": d["source"]["filename"], "status": d["status"], "uploaded_at": d["uploaded_at"], "values": len(d["values"])}
                                                 for d in docstore.all_for(who, pid)]}

    @router.get("/api/admin/people/{pid}/documents/{doc_id}")
    def admin_document(pid: str, doc_id: str, request: Request):
        who = admin_actor(request)
        doc = docstore.get(who, pid, doc_id)
        if doc is None:
            raise HTTPException(404, "That document was not found.")
        db.audit("admin_document_view", who.patient_id, target=pid[:32], doc=doc_id[:36])
        return {"document": doc, "can_edit": False}

    return router
