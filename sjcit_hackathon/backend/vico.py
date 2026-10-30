"""TrustView MVP module: tenant-scoped retrieval, audit chain, and CRM cases.

This deliberately uses no model provider.  Answers are extractive from retrieved
documents, so the chatbot has no outbound model/network path and cannot make an
uncited claim.  It is mounted in the existing FastAPI process by ``main.py``.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field


REFUSAL = "I cannot answer that from the active documents available to your tenant."
CATEGORIES = {"General", "Incident", "Request", "Question"}
STATUSES = {"Active", "Completed", "Closed"}
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def crm_cases_from_service(token: str, overdue: bool) -> list[dict] | None:
    """Use the Mongo/Express CRM when configured; local storage remains demo fallback."""
    base_url = os.getenv("CRM_API_URL", "").rstrip("/")
    if not base_url:
        return None
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base_url}/cases", params={"overdue": str(overdue).lower()}, headers={"Authorization": f"Bearer {token}"})
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


class VicoStore:
    # ASSUMPTION(D-3): no configured Monstack API was found, so this adapter uses
    # a local SQLite development store in the existing Python service.
    def __init__(self, path: str | None = None, audit_key: str | None = None):
        self.path = path or os.getenv("VICO_DB_PATH", str(Path(__file__).with_name("vico.sqlite3")))
        self.audit_key = (audit_key or os.getenv("VICO_AUDIT_HMAC_KEY", "")).encode()
        if not self.audit_key:
            raise RuntimeError("VICO_AUDIT_HMAC_KEY must be configured; no audit key is stored in the repository")
        self.init()

    @contextmanager
    def connection(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init(self) -> None:
        with self.connection() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS documents (tenant_id TEXT NOT NULL, doc_id TEXT NOT NULL, version TEXT NOT NULL, status TEXT NOT NULL, source TEXT, failure_reason TEXT, PRIMARY KEY(tenant_id, doc_id, version));
            CREATE TABLE IF NOT EXISTS chunks (id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, doc_id TEXT NOT NULL, version TEXT NOT NULL, page INTEGER NOT NULL, status TEXT NOT NULL, text TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS chunks_tenant_active ON chunks(tenant_id, status);
            CREATE TABLE IF NOT EXISTS routing_log (id TEXT PRIMARY KEY, ts TEXT NOT NULL, user_hmac TEXT NOT NULL, tenant_id TEXT NOT NULL, route TEXT NOT NULL, query_hash TEXT NOT NULL, returned_doc_ids TEXT NOT NULL, llm_called INTEGER NOT NULL, session_anon_id TEXT);
            CREATE TABLE IF NOT EXISTS ai_usage (id TEXT PRIMARY KEY, ts TEXT NOT NULL, user_hmac TEXT NOT NULL, tenant_id TEXT NOT NULL, route TEXT NOT NULL, llm_called INTEGER NOT NULL, model TEXT, tokens_in INTEGER NOT NULL, tokens_out INTEGER NOT NULL, latency_ms INTEGER NOT NULL, est_cost REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS audit_events (id TEXT PRIMARY KEY, ts TEXT NOT NULL, actor_hmac TEXT NOT NULL, tenant_id TEXT NOT NULL, action TEXT NOT NULL, resource TEXT NOT NULL, decision TEXT NOT NULL, details TEXT NOT NULL, prev_hash TEXT NOT NULL, event_hash TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS anchors (id TEXT PRIMARY KEY, ts TEXT NOT NULL, chain_head TEXT NOT NULL, mode TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS cases (case_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, creator TEXT NOT NULL, assignee TEXT NOT NULL, category TEXT NOT NULL, description TEXT NOT NULL, status TEXT NOT NULL, required_action TEXT, due_date TEXT, next_action_date TEXT, closure_date TEXT, resolution_note TEXT, citations TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS case_actions (id TEXT PRIMARY KEY, case_id TEXT NOT NULL, actor TEXT NOT NULL, ts TEXT NOT NULL, type TEXT NOT NULL, note TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS query_sessions (anon_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, actor_hmac TEXT NOT NULL, created_at TEXT NOT NULL, state TEXT NOT NULL);
            """)
            # Forward-compatible with databases created by the first MVP build.
            try:
                c.execute("ALTER TABLE routing_log ADD COLUMN session_anon_id TEXT")
            except sqlite3.OperationalError:
                pass

    def actor(self, user_id: str) -> str:
        return hmac.new(self.audit_key, user_id.encode(), hashlib.sha256).hexdigest()

    def _private_hash(self, value: str) -> str:
        """HMAC-SHA-256, not a plain/salted SHA-256 password scheme."""
        return hmac.new(self.audit_key, value.encode(), hashlib.sha256).hexdigest()

    def audit(self, user_id: str, tenant: str, action: str, resource: str, decision: str, details: dict | None = None) -> str:
        with self.connection() as c:
            prior = c.execute("SELECT event_hash FROM audit_events ORDER BY rowid DESC LIMIT 1").fetchone()
            prev = prior["event_hash"] if prior else "0" * 64
            event = {"ts": _now(), "actor_hmac": self.actor(user_id), "tenant_id": tenant, "action": action, "resource": resource, "decision": decision, "details": details or {}}
            digest = hashlib.sha256((prev + _canonical(event)).encode()).hexdigest()
            ident = str(uuid.uuid4())
            c.execute("INSERT INTO audit_events VALUES (?,?,?,?,?,?,?,?,?,?)", (ident, event["ts"], event["actor_hmac"], tenant, action, resource, decision, _canonical(event["details"]), prev, digest))
            return digest

    def anchor(self) -> dict:
        with self.connection() as c:
            row = c.execute("SELECT event_hash FROM audit_events ORDER BY rowid DESC LIMIT 1").fetchone()
            head = row["event_hash"] if row else "0" * 64
            c.execute("INSERT INTO anchors VALUES (?,?,?,?)", (str(uuid.uuid4()), _now(), head, "simulated"))
        return {"chain_head": head, "mode": "simulated"}

    def verify(self) -> dict:
        with self.connection() as c:
            rows = c.execute("SELECT * FROM audit_events ORDER BY rowid").fetchall()
            prev = "0" * 64
            for row in rows:
                event = {"ts": row["ts"], "actor_hmac": row["actor_hmac"], "tenant_id": row["tenant_id"], "action": row["action"], "resource": row["resource"], "decision": row["decision"], "details": json.loads(row["details"])}
                actual = hashlib.sha256((prev + _canonical(event)).encode()).hexdigest()
                if row["prev_hash"] != prev or row["event_hash"] != actual:
                    return {"ok": False, "invalid_event_id": row["id"]}
                prev = actual
            anchor = c.execute("SELECT chain_head, mode FROM anchors ORDER BY rowid DESC LIMIT 1").fetchone()
            return {"ok": True, "chain_head": prev, "anchor_matches": not anchor or anchor["chain_head"] == prev, "anchor_mode": anchor["mode"] if anchor else "off"}

    def ingest(self, tenant: str, doc_id: str, version: str, text: str, user: str) -> dict:
        if not text.strip():
            with self.connection() as c:
                c.execute("INSERT OR REPLACE INTO documents VALUES (?,?,?,?,?,?)", (tenant, doc_id, version, "failed", None, "empty document"))
            self.audit(user, tenant, "ingest", doc_id, "failed", {"reason": "empty document"})
            raise HTTPException(422, "Document text is empty")
        pages = text.split("\f")
        with self.connection() as c:
            c.execute("UPDATE documents SET status='superseded' WHERE tenant_id=? AND doc_id=? AND status='active'", (tenant, doc_id))
            c.execute("UPDATE chunks SET status='superseded' WHERE tenant_id=? AND doc_id=? AND status='active'", (tenant, doc_id))
            c.execute("INSERT OR REPLACE INTO documents VALUES (?,?,?,?,?,?)", (tenant, doc_id, version, "active", "request-body", None))
            count = 0
            for page, page_text in enumerate(pages, 1):
                words = page_text.split()
                for start in range(0, len(words), 500):
                    chunk = " ".join(words[start:start + 500])
                    if chunk:
                        c.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?)", (str(uuid.uuid4()), tenant, doc_id, version, page, "active", chunk))
                        count += 1
        self.audit(user, tenant, "ingest", doc_id, "allowed", {"version": version, "chunks": count})
        return {"doc_id": doc_id, "version": version, "chunks": count, "status": "active"}

    def retrieve(self, tenant: str, query: str) -> list[dict]:
        # tenant is accepted only from authenticated claims; callers never supply it.
        terms = set(re.findall(r"[a-zA-Z0-9]{3,}", query.lower()))
        with self.connection() as c:
            rows = c.execute("SELECT * FROM chunks WHERE tenant_id=? AND status='active'", (tenant,)).fetchall()
        scored = []
        for row in rows:
            text_terms = set(re.findall(r"[a-zA-Z0-9]{3,}", row["text"].lower()))
            score = len(terms & text_terms) / max(1, len(terms))
            if score >= 0.20:
                scored.append((score, dict(row)))
        return [row for _, row in sorted(scored, reverse=True, key=lambda x: x[0])[:3]]

    def create_query_session(self, tenant: str, user: str) -> dict:
        """Create a pseudonymous session record; neither a raw token nor user ID is logged."""
        nonce = secrets.token_bytes(32)
        # Nested privacy identifiers: actor HMAC -> anonymous session HMAC.
        # The random nonce is intentionally never persisted or logged.
        actor_hmac = self.actor(user)
        anon_id = "qs_" + hmac.new(self.audit_key, actor_hmac.encode() + tenant.encode() + nonce, hashlib.sha256).hexdigest()[:32]
        with self.connection() as c:
            c.execute("INSERT INTO query_sessions VALUES (?,?,?,?,?)", (anon_id, tenant, actor_hmac, _now(), "active"))
        self.audit(user, tenant, "query_session_create", anon_id, "allowed", {"privacy_boundary": "tee-simulated"})
        return {"anonymous_session_id": anon_id, "protection": "TEE simulated; no attestation configured"}

    def validate_session(self, tenant: str, anon_id: str | None) -> None:
        if not anon_id:
            return
        with self.connection() as c:
            row = c.execute("SELECT 1 FROM query_sessions WHERE anon_id=? AND tenant_id=? AND state='active'", (anon_id, tenant)).fetchone()
        if not row:
            raise HTTPException(403, "Unknown or cross-tenant query session")

    def log_usage(self, user: str, tenant: str, route: str, query: str, docs: list[str], llm_called: bool, latency: int, session_anon_id: str | None = None, model: str = "extractive-local") -> None:
        actor = self.actor(user); ident = str(uuid.uuid4()); ts = _now()
        # Query HMAC is nested under the anonymous session where supplied. No
        # raw prompt, tenant string, or employee identity is written to logs.
        qhash = self._private_hash((session_anon_id or actor) + query)
        with self.connection() as c:
            c.execute("INSERT INTO routing_log VALUES (?,?,?,?,?,?,?,?,?)", (ident, ts, actor, tenant, route, qhash, _canonical(docs), int(llm_called), session_anon_id))
            c.execute("INSERT INTO ai_usage VALUES (?,?,?,?,?,?,?,?,?,?,?)", (ident, ts, actor, tenant, route, int(llm_called), model, len(query.split()), 0, latency, 0.0))

    def create_case(self, tenant: str, actor: str, data: dict) -> dict:
        if data["category"] not in CATEGORIES: raise HTTPException(422, "Invalid case category")
        ident = "CASE-" + uuid.uuid4().hex[:10].upper(); now = _now()
        with self.connection() as c:
            c.execute("INSERT INTO cases VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (ident, tenant, actor, data.get("assignee") or actor, data["category"], data["description"], "Active", data.get("required_action"), data.get("due_date"), data.get("next_action_date"), None, None, _canonical(data.get("citations", [])), now))
        self.audit(actor, tenant, "case_create", ident, "allowed")
        return self.get_case(tenant, actor, ident, manager=True)

    def get_case(self, tenant: str, actor: str, case_id: str, manager: bool) -> dict:
        with self.connection() as c:
            row = c.execute("SELECT * FROM cases WHERE case_id=? AND tenant_id=?", (case_id, tenant)).fetchone()
            if not row: raise HTTPException(404, "Case not found")
            if not manager and row["assignee"] != actor and row["creator"] != actor: raise HTTPException(403, "Case is outside your scope")
            actions = c.execute("SELECT actor,ts,type,note FROM case_actions WHERE case_id=? ORDER BY rowid", (case_id,)).fetchall()
        output = dict(row); output["overdue"] = bool(row["due_date"] and row["due_date"] < date.today().isoformat() and row["status"] == "Active"); output["actions"] = [dict(x) for x in actions]; output["citations"] = json.loads(output.pop("citations")); return output

    def update_case(self, tenant: str, actor: str, case_id: str, patch: dict, manager: bool) -> dict:
        before = self.get_case(tenant, actor, case_id, manager)
        if "status" in patch and patch["status"] not in STATUSES: raise HTTPException(422, "Invalid case status")
        if patch.get("status") == "Completed" and not patch.get("resolution_note") and not before.get("resolution_note"): raise HTTPException(422, "Completion requires a resolution note")
        allowed = {"assignee", "status", "due_date", "next_action_date", "required_action", "resolution_note"}; changes = {k:v for k,v in patch.items() if k in allowed}
        if not changes: raise HTTPException(422, "No editable fields")
        if patch.get("status") in {"Completed", "Closed"}: changes["closure_date"] = _now()
        with self.connection() as c:
            c.execute("UPDATE cases SET " + ",".join(f"{k}=?" for k in changes) + " WHERE case_id=? AND tenant_id=?", (*changes.values(), case_id, tenant))
        self.audit(actor, tenant, "case_update", case_id, "allowed", {"fields": sorted(changes)})
        return self.get_case(tenant, actor, case_id, manager)

    def add_action(self, tenant: str, actor: str, case_id: str, action_type: str, note: str, manager: bool) -> dict:
        self.get_case(tenant, actor, case_id, manager)
        if not note.strip(): raise HTTPException(422, "Action note is required")
        with self.connection() as c: c.execute("INSERT INTO case_actions VALUES (?,?,?,?,?,?)", (str(uuid.uuid4()), case_id, actor, _now(), action_type, note))
        self.audit(actor, tenant, "case_action", case_id, "allowed")
        return self.get_case(tenant, actor, case_id, manager)

    def list_cases(self, tenant: str, actor: str, manager: bool, overdue: bool | None = None) -> list[dict]:
        with self.connection() as c: ids = c.execute("SELECT case_id FROM cases WHERE tenant_id=?" + ("" if manager else " AND (creator=? OR assignee=?)"), (tenant,) if manager else (tenant, actor, actor)).fetchall()
        cases = [self.get_case(tenant, actor, x["case_id"], manager) for x in ids]
        return [x for x in cases if overdue is None or x["overdue"] == overdue]

    def dashboards(self, tenant: str, actor: str, manager: bool) -> dict:
        cases = self.list_cases(tenant, actor, manager); counts = {"total":len(cases), "active":sum(x["status"]=="Active" for x in cases), "overdue":sum(x["overdue"] for x in cases), "completed":sum(x["status"]=="Completed" for x in cases)}
        with self.connection() as c: usage = c.execute("SELECT route,llm_called,tokens_in,tokens_out,latency_ms,est_cost FROM ai_usage WHERE tenant_id=?", (tenant,)).fetchall()
        resolved: dict[str, int] = {}
        for case in cases:
            if case["status"] == "Completed":
                resolved[case["assignee"]] = resolved.get(case["assignee"], 0) + 1
        total = len(usage); return {"cases": counts, "case_list": cases, "employee_progress": [{"employee_id": employee, "cases_solved": count} for employee, count in sorted(resolved.items())], "ai_usage": {"calls": total, "by_route": {r:sum(x["route"]==r for x in usage) for r in {x["route"] for x in usage}}, "answered_without_llm_pct": (100 * sum(not x["llm_called"] for x in usage) / total) if total else 0, "tokens": sum(x["tokens_in"] + x["tokens_out"] for x in usage), "average_latency_ms": (sum(x["latency_ms"] for x in usage) / total) if total else 0, "estimated_cost": sum(x["est_cost"] for x in usage), "avoidable_llm_calls": 0}}


class IngestRequest(BaseModel): doc_id: str; version: str; text: str
class ChatRequest(BaseModel): message: str; session_anon_id: str | None = None
class CaseRequest(BaseModel): category: str; description: str; assignee: str | None = None; required_action: str | None = None; due_date: str | None = None; next_action_date: str | None = None; citations: list[dict] = Field(default_factory=list)
class CasePatch(BaseModel): assignee: str | None = None; status: str | None = None; due_date: str | None = None; next_action_date: str | None = None; required_action: str | None = None; resolution_note: str | None = None
class ActionRequest(BaseModel): type: str = "note"; note: str


def create_router(store: VicoStore) -> APIRouter:
    router = APIRouter(prefix="/vico", tags=["TrustView"])
    async def claims(token: str = Depends(oauth2_scheme)) -> dict:
        # Keep this module testable when optional legacy auth dependencies are
        # not installed; production always resolves the existing auth helper.
        from auth_security import decode_access_token
        payload = decode_access_token(token)
        tenant = payload.get("tenant_id") if payload else None
        if not payload or not isinstance(tenant, str) or not re.fullmatch(r"T\d{4}", tenant) or not payload.get("user_id"):
            raise HTTPException(401, "TrustView requires a tenant_id claim in the form T1234")
        payload["_crm_bearer"] = token
        return payload
    def manager(c: dict) -> bool: return c.get("role") in {"manager", "admin", "hod"}
    def redact_for_external_ai(query: str) -> str:
        """Remove obvious identifiers before the opt-in hosted-model pathway."""
        query = re.sub(r"[\w.+-]+@[\w.-]+", "[redacted-email]", query)
        return re.sub(r"\b(?:T\d{4}|\+?\d[\d -]{7,}\d)\b", "[redacted-id]", query)
    async def gemini_fallback(query: str) -> str | None:
        if os.getenv("VICO_GEMINI_FALLBACK_ENABLED", "").lower() != "true" or not os.getenv("GEMINI_API_KEY"):
            return None
        try:
            import google.generativeai as genai
            genai.configure(api_key=os.environ["GEMINI_API_KEY"])
            model = genai.GenerativeModel(os.getenv("VICO_GEMINI_MODEL", "gemini-1.5-flash"))
            response = await __import__("asyncio").to_thread(model.generate_content, redact_for_external_ai(query))
            return (getattr(response, "text", "") or "").strip() or None
        except Exception:
            return None
    @router.post("/ingest")
    async def ingest(req: IngestRequest, c: dict = Depends(claims)):
        if not manager(c):
            store.audit(c["user_id"], c["tenant_id"], "ingest", req.doc_id, "denied")
            raise HTTPException(403, "Only a tenant manager or admin can ingest documents")
        return store.ingest(c["tenant_id"], req.doc_id, req.version, req.text, c["user_id"])
    @router.post("/sessions")
    async def create_session(c: dict = Depends(claims)): return store.create_query_session(c["tenant_id"], c["user_id"])
    @router.post("/chat")
    async def chat(req: ChatRequest, c: dict = Depends(claims)):
        started=time.monotonic(); query=req.message; lower=query.lower(); tenant=c["tenant_id"]; store.validate_session(tenant, req.session_anon_id)
        if re.search(r"\b(my )?overdue cases\b", lower):
            result=await crm_cases_from_service(c["_crm_bearer"], True)
            if result is None: result=store.list_cases(tenant,c["user_id"],manager(c),True)
            store.log_usage(c["user_id"],tenant,"crm",query,[],False,int((time.monotonic()-started)*1000),req.session_anon_id); store.audit(c["user_id"],tenant,"crm_query","overdue", "allowed"); return {"answer":result,"citations":[],"route":"crm","llm_called":False}
        if re.search(r"\bstatus of case\s+([A-Za-z0-9-]+)", lower):
            case_id=re.search(r"\bstatus of case\s+([A-Za-z0-9-]+)", query, re.I).group(1); result=store.get_case(tenant,c["user_id"],case_id,manager(c)); store.log_usage(c["user_id"],tenant,"crm",query,[],False,int((time.monotonic()-started)*1000),req.session_anon_id); return {"answer":result,"citations":[],"route":"crm","llm_called":False}
        chunks=store.retrieve(tenant,query); docs=sorted({x["doc_id"] for x in chunks})
        if not chunks:
            # AI decider: first deterministic CRM, then tenant RAG; only an
            # authorized manager/admin can opt into an anonymized Gemini assist.
            if manager(c):
                assisted = await gemini_fallback(query)
                if assisted:
                    store.log_usage(c["user_id"],tenant,"ai_assist",query,[],True,int((time.monotonic()-started)*1000),req.session_anon_id,"gemini-hosted-anonymized")
                    store.audit(c["user_id"],tenant,"ai_fallback",store._private_hash(query),"allowed",{"external_pathway":"gemini", "anonymous_session":bool(req.session_anon_id)})
                    return {"answer":assisted,"citations":[],"route":"ai_assist","llm_called":True,"ai_decision":"role-authorized fallback"}
                decision = "fallback eligible but Gemini is not enabled"
            else:
                decision = "fallback denied by role"
            store.log_usage(c["user_id"],tenant,"rag",query,[],False,int((time.monotonic()-started)*1000),req.session_anon_id)
            store.audit(c["user_id"],tenant,"retrieval",store._private_hash(query),"refused",{"returned_doc_ids":[],"ai_decision":decision}); return {"answer":REFUSAL,"citations":[],"route":"rag","llm_called":False,"ai_decision":decision}
        citations=[{"doc_id":x["doc_id"],"version":x["version"],"page":x["page"]} for x in chunks]
        answer="\n\n".join(x["text"] for x in chunks); store.log_usage(c["user_id"],tenant,"rag",query,docs,False,int((time.monotonic()-started)*1000),req.session_anon_id); store.audit(c["user_id"],tenant,"retrieval",store._private_hash(query),"allowed",{"returned_doc_ids":docs}); return {"answer":answer,"citations":citations,"route":"rag","llm_called":False,"ai_decision":"tenant RAG"}
    def request_data(request: BaseModel, **kwargs) -> dict:
        return request.model_dump(**kwargs) if hasattr(request, "model_dump") else request.dict(**kwargs)
    @router.post("/cases")
    async def create_case(req: CaseRequest,c:dict=Depends(claims)): return store.create_case(c["tenant_id"],c["user_id"],request_data(req))
    @router.get("/cases")
    async def cases(overdue:bool|None=None,c:dict=Depends(claims)): return store.list_cases(c["tenant_id"],c["user_id"],manager(c),overdue)
    @router.patch("/cases/{case_id}")
    async def patch_case(case_id:str,req:CasePatch,c:dict=Depends(claims)): return store.update_case(c["tenant_id"],c["user_id"],case_id,request_data(req, exclude_none=True),manager(c))
    @router.post("/cases/{case_id}/actions")
    async def action(case_id:str,req:ActionRequest,c:dict=Depends(claims)): return store.add_action(c["tenant_id"],c["user_id"],case_id,req.type,req.note,manager(c))
    @router.get("/dashboards")
    async def dashboard(c:dict=Depends(claims)): return store.dashboards(c["tenant_id"],c["user_id"],manager(c))
    @router.post("/audit/anchor")
    async def anchor(c:dict=Depends(claims)): return store.anchor()
    @router.get("/audit/verify")
    async def verify(c:dict=Depends(claims)): return store.verify()
    @router.get("/security/status")
    async def security_status(c:dict=Depends(claims)): return {"tee":"not enabled","tee_detail":"design only; no attestation was found", "chain":"simulated", "trustbeam":"not integrated"}
    return router
