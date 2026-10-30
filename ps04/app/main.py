"""PS-04 API. Authorisation is enforced here and in retrieval SQL -- never by the language model.

Roles
  system administrator : platform operator. Creates tenants/users, suspends tenants, offboards users, reads all audit
                          metadata and verifies the ledger. Has NO implicit access to tenant documents or chat.
  client administrator  : within their own tenant only: manage members, documents/versions, sharing grants, tenant audit.
  client employee       : within their own tenant only: ask questions, open citations, read current documents.
Every tenant-scoped route requires an active membership; anything else is a uniform 404 (existence is not revealed).
"""
from __future__ import annotations
import hashlib, json, time, uuid
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import security
from .answer import answer_question, is_injection
from .audit import Ledger, now
from .guard import RateLimiter
from .config import Settings
from .db import connect, init_db, tx
from .ingest import IngestRejected, ingest_version
from .retrieval import VISIBLE
from .tee import SimulatedTee

STATIC = Path(__file__).resolve().parent.parent / "static"
NOT_FOUND = HTTPException(404, "Not found")


class LoginIn(BaseModel):
    email: str
    password: str


class TenantIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)


class UserIn(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=10, max_length=200)
    is_sysadmin: bool = False
    tenant_id: str | None = None
    role: str = Field(default="employee", pattern="^(client_admin|employee)$")


class MembershipIn(BaseModel):
    user_id: str
    tenant_id: str
    role: str = Field(pattern="^(client_admin|employee)$")


class MemberIn(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=10, max_length=200)
    role: str = Field(default="employee", pattern="^(client_admin|employee)$")


class RoleIn(BaseModel):
    role: str = Field(pattern="^(client_admin|employee)$")


class StatusIn(BaseModel):
    status: str = Field(pattern="^(active|suspended)$")


class ChatIn(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = None


class ShareIn(BaseModel):
    grantee_tenant_id: str
    document_id: str | None = None
    expires_at: str | None = None  # ISO-8601 UTC


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    db_path = settings.data_dir / "ps04.sqlite3"
    boot = connect(db_path)
    init_db(boot)
    boot.close()
    tee = SimulatedTee(settings.secret)
    # Ledger checkpoint key is released by the (simulated) TEE only for a verified measurement.
    report = tee.attest()
    ledger_key = tee.release_key("ledger-checkpoint", report, tee.measurement())
    ledger = Ledger(settings.data_dir / "audit_checkpoints.jsonl", ledger_key, settings.checkpoint_every)
    # Same PBKDF2 cost as real accounts, so an unknown email takes as long as a wrong password.
    dummy_hash = security.hash_password("dummy-password", settings.pbkdf2_iterations)
    limiter = RateLimiter({"chat": (30, 60), "upload": (20, 60)})

    app = FastAPI(title="PS-04 Secure Multi-Client Knowledge Chatbot")
    app.state.settings, app.state.ledger, app.state.db_path, app.state.tee = settings, ledger, db_path, tee
    app.state.dummy_hash, app.state.limiter = dummy_hash, limiter

    @app.middleware("http")
    async def headers(request: Request, call_next):
        resp = await call_next(request)
        resp.headers["Content-Security-Policy"] = "default-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
        resp.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        resp.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        return resp

    def get_conn():
        conn = connect(db_path)
        try:
            yield conn
        finally:
            conn.close()

    def current_user(request: Request, conn=Depends(get_conn)) -> dict:
        auth = request.headers.get("authorization", "")
        sid = security.read_token(settings.secret, auth[7:]) if auth.lower().startswith("bearer ") else None
        if not sid:
            raise HTTPException(401, "Not authenticated")
        row = conn.execute("SELECT u.*, s.id AS sid FROM sessions s JOIN users u ON u.id = s.user_id "
                           "WHERE s.id=? AND s.revoked=0 AND s.expires_at>? AND u.status='active'", (sid, time.time())).fetchone()
        if not row:
            raise HTTPException(401, "Not authenticated")
        return dict(row)

    def deny(conn, user, what, tid=None):
        with tx(conn):
            # counterparty = the tenant that was targeted, so its administrators can see probing against it
            ledger.append(conn, "access.denied", actor=user["id"], counterparty=tid, resource=what, attempted_tenant=tid)
        raise HTTPException(404, "Not found")

    def role_in(conn, user, tid) -> str | None:
        r = conn.execute("SELECT m.role FROM memberships m JOIN tenants t ON t.id=m.tenant_id "
                         "WHERE m.user_id=? AND m.tenant_id=? AND m.status='active' AND t.status='active'", (user["id"], tid)).fetchone()
        return r["role"] if r else None

    def member(conn, user, tid, admin=False) -> str:
        role = role_in(conn, user, tid)
        if role is None or (admin and role != "client_admin"):
            deny(conn, user, "tenant", tid)
        return role

    def throttle(bucket, user):
        if not limiter.allow(bucket, user["id"]):
            raise HTTPException(429, "Rate limit exceeded; slow down and retry shortly")

    def sysadmin(user):
        if not user["is_sysadmin"]:
            raise HTTPException(403, "System administrator required")

    # ---------------------------------------------------------------- auth
    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    @app.post("/auth/login")
    def login(body: LoginIn, request: Request, conn=Depends(get_conn)):
        # Lockout is per (account, client address): a stranger cannot lock a victim out by guessing wrong
        # passwords from elsewhere. A wider per-address cap bounds password spraying across many accounts.
        # The address is the socket peer; X-Forwarded-For is deliberately not trusted (it is client-controlled).
        email = body.email.strip().lower()
        ip = request.client.host if request.client else "unknown"
        key, ipkey = f"{email}|{ip}", f"ip|{ip}"
        t = time.time()
        recent = conn.execute("SELECT COUNT(*) FROM login_failures WHERE email=? AND at>?", (key, t - settings.lockout_seconds)).fetchone()[0]
        ip_recent = conn.execute("SELECT COUNT(*) FROM login_failures WHERE email=? AND at>?", (ipkey, t - settings.lockout_seconds)).fetchone()[0]
        locked = recent >= settings.max_failed_logins or ip_recent >= settings.max_failed_logins * 4
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        ok = security.verify_password(body.password, user["password_hash"] if user else dummy_hash)
        who = hashlib.sha256(email.encode()).hexdigest()[:16]
        if locked or not (user and ok and user["status"] == "active"):
            with tx(conn):
                if not locked:
                    conn.execute("INSERT INTO login_failures VALUES(?,?)", (key, t))
                    conn.execute("INSERT INTO login_failures VALUES(?,?)", (ipkey, t))
                ledger.append(conn, "auth.login_failed", actor=None, email_sha256=who, locked=locked)
            raise HTTPException(429 if locked else 401, "Too many attempts; try later" if locked else "Invalid credentials")
        sid = uuid.uuid4().hex
        with tx(conn):
            conn.execute("DELETE FROM login_failures WHERE email=?", (key,))
            conn.execute("INSERT INTO sessions VALUES(?,?,?,0)", (sid, user["id"], t + settings.token_ttl))
            ledger.append(conn, "auth.login", actor=user["id"])
        return {"token": security.issue_token(settings.secret, sid, settings.token_ttl), "expires_in": settings.token_ttl}

    @app.post("/auth/logout")
    def logout(user=Depends(current_user), conn=Depends(get_conn)):
        with tx(conn):
            conn.execute("UPDATE sessions SET revoked=1 WHERE id=?", (user["sid"],))
            ledger.append(conn, "auth.logout", actor=user["id"])
        return {"ok": True}

    @app.get("/auth/me")
    def me(user=Depends(current_user), conn=Depends(get_conn)):
        ms = conn.execute("SELECT m.tenant_id, t.name, m.role FROM memberships m JOIN tenants t ON t.id=m.tenant_id "
                          "WHERE m.user_id=? AND m.status='active' AND t.status='active'", (user["id"],)).fetchall()
        return {"id": user["id"], "email": user["email"], "name": user["name"], "is_sysadmin": bool(user["is_sysadmin"]),
                "memberships": [dict(m) for m in ms]}

    # ------------------------------------------------- platform administration
    @app.post("/admin/tenants", status_code=201)
    def create_tenant(body: TenantIn, user=Depends(current_user), conn=Depends(get_conn)):
        sysadmin(user)
        tid = f"ten_{uuid.uuid4().hex[:12]}"
        try:
            with tx(conn):
                conn.execute("INSERT INTO tenants VALUES(?,?,'active',?)", (tid, body.name.strip(), now()))
                ledger.append(conn, "tenant.create", actor=user["id"], tenant_id=tid, name=body.name.strip())
        except Exception as e:
            if "UNIQUE" in str(e):
                raise HTTPException(409, "Tenant name already exists")
            raise
        return {"id": tid, "name": body.name.strip()}

    @app.get("/admin/tenants")
    def list_tenants(user=Depends(current_user), conn=Depends(get_conn)):
        sysadmin(user)
        return [dict(r) for r in conn.execute("SELECT id, name, status, created_at FROM tenants ORDER BY created_at")]

    @app.patch("/admin/tenants/{tid}")
    def set_tenant_status(tid: str, body: StatusIn, user=Depends(current_user), conn=Depends(get_conn)):
        sysadmin(user)
        with tx(conn):
            if not conn.execute("UPDATE tenants SET status=? WHERE id=?", (body.status, tid)).rowcount:
                raise NOT_FOUND
            ledger.append(conn, "tenant.status", actor=user["id"], tenant_id=tid, status=body.status)
        return {"id": tid, "status": body.status}

    @app.post("/admin/users", status_code=201)
    def create_user(body: UserIn, user=Depends(current_user), conn=Depends(get_conn)):
        sysadmin(user)
        uid = f"usr_{uuid.uuid4().hex[:12]}"
        with tx(conn):
            if conn.execute("SELECT 1 FROM users WHERE email=?", (body.email.lower(),)).fetchone():
                raise HTTPException(409, "Email already registered")
            if body.tenant_id and not conn.execute("SELECT 1 FROM tenants WHERE id=?", (body.tenant_id,)).fetchone():
                raise HTTPException(404, "Tenant not found")
            conn.execute("INSERT INTO users VALUES(?,?,?,?,?, 'active', ?)",
                         (uid, body.email.lower(), body.name, security.hash_password(body.password, settings.pbkdf2_iterations), int(body.is_sysadmin), now()))
            ledger.append(conn, "user.create", actor=user["id"], user_id=uid, is_sysadmin=body.is_sysadmin)
            if body.tenant_id:
                conn.execute("INSERT INTO memberships VALUES(?,?,?,'active',?)", (uid, body.tenant_id, body.role, now()))
                ledger.append(conn, "membership.add", actor=user["id"], tenant_id=body.tenant_id, user_id=uid, role=body.role)
        return {"id": uid}

    @app.post("/admin/memberships", status_code=201)
    def add_membership(body: MembershipIn, user=Depends(current_user), conn=Depends(get_conn)):
        sysadmin(user)
        with tx(conn):
            if not conn.execute("SELECT 1 FROM users WHERE id=?", (body.user_id,)).fetchone() or \
               not conn.execute("SELECT 1 FROM tenants WHERE id=?", (body.tenant_id,)).fetchone():
                raise NOT_FOUND
            conn.execute("INSERT INTO memberships VALUES(?,?,?,'active',?) ON CONFLICT(user_id,tenant_id) DO UPDATE SET role=excluded.role, status='active'",
                         (body.user_id, body.tenant_id, body.role, now()))
            ledger.append(conn, "membership.add", actor=user["id"], tenant_id=body.tenant_id, user_id=body.user_id, role=body.role)
        return {"ok": True}

    @app.post("/admin/users/{uid}/offboard")
    def offboard(uid: str, user=Depends(current_user), conn=Depends(get_conn)):
        """Disable the account, revoke every session and deactivate every membership in one transaction."""
        sysadmin(user)
        with tx(conn):
            if not conn.execute("UPDATE users SET status='disabled' WHERE id=?", (uid,)).rowcount:
                raise NOT_FOUND
            conn.execute("UPDATE sessions SET revoked=1 WHERE user_id=?", (uid,))
            conn.execute("UPDATE memberships SET status='removed' WHERE user_id=?", (uid,))
            ledger.append(conn, "user.offboard", actor=user["id"], user_id=uid)
        return {"ok": True}

    @app.get("/admin/audit")
    def admin_audit(limit: int = 200, user=Depends(current_user), conn=Depends(get_conn)):
        sysadmin(user)
        return [dict(r) for r in conn.execute("SELECT * FROM audit_events ORDER BY seq DESC LIMIT ?", (min(limit, 1000),))]

    # ---------------------------------------------------- tenant member management
    @app.get("/tenants/{tid}/members")
    def members(tid: str, user=Depends(current_user), conn=Depends(get_conn)):
        member(conn, user, tid, admin=True)
        rows = conn.execute("SELECT u.id, u.email, u.name, m.role, m.status FROM memberships m JOIN users u ON u.id=m.user_id WHERE m.tenant_id=?", (tid,))
        return [dict(r) for r in rows]

    @app.post("/tenants/{tid}/members", status_code=201)
    def add_member(tid: str, body: MemberIn, user=Depends(current_user), conn=Depends(get_conn)):
        member(conn, user, tid, admin=True)
        uid = f"usr_{uuid.uuid4().hex[:12]}"
        with tx(conn):
            if conn.execute("SELECT 1 FROM users WHERE email=?", (body.email.lower(),)).fetchone():
                raise HTTPException(409, "Unable to add this email address")
            conn.execute("INSERT INTO users VALUES(?,?,?,?,0,'active',?)",
                         (uid, body.email.lower(), body.name, security.hash_password(body.password, settings.pbkdf2_iterations), now()))
            conn.execute("INSERT INTO memberships VALUES(?,?,?,'active',?)", (uid, tid, body.role, now()))
            ledger.append(conn, "membership.add", actor=user["id"], tenant_id=tid, user_id=uid, role=body.role)
        return {"id": uid}

    @app.patch("/tenants/{tid}/members/{uid}")
    def set_role(tid: str, uid: str, body: RoleIn, user=Depends(current_user), conn=Depends(get_conn)):
        member(conn, user, tid, admin=True)
        with tx(conn):
            if not conn.execute("UPDATE memberships SET role=? WHERE tenant_id=? AND user_id=? AND status='active'", (body.role, tid, uid)).rowcount:
                raise NOT_FOUND
            ledger.append(conn, "membership.role_change", actor=user["id"], tenant_id=tid, user_id=uid, role=body.role)
        return {"ok": True}

    @app.delete("/tenants/{tid}/members/{uid}")
    def remove_member(tid: str, uid: str, user=Depends(current_user), conn=Depends(get_conn)):
        member(conn, user, tid, admin=True)
        with tx(conn):
            if not conn.execute("UPDATE memberships SET status='removed' WHERE tenant_id=? AND user_id=? AND status='active'", (tid, uid)).rowcount:
                raise NOT_FOUND
            ledger.append(conn, "membership.remove", actor=user["id"], tenant_id=tid, user_id=uid)
        return {"ok": True}

    # ----------------------------------------------------------------- documents
    def read_upload(file: UploadFile) -> bytes:
        data = file.file.read(settings.max_upload_bytes + 1)
        return data

    def do_ingest(conn, user, tid, file, title=None, document_id=None):
        throttle("upload", user)
        data = read_upload(file)
        try:
            res = ingest_version(conn, ledger, settings, tenant_id=tid, user_id=user["id"], filename=file.filename or "", data=data, title=title, document_id=document_id)
        except IngestRejected as e:
            with tx(conn):
                ledger.append(conn, "document.upload_rejected", actor=user["id"], tenant_id=tid, filename=Path(file.filename or "").name[:100], reason=str(e))
            raise HTTPException(400, str(e))
        return JSONResponse(res, status_code=201 if res["status"] == "ready" else 422)

    @app.post("/tenants/{tid}/documents")
    def upload_document(tid: str, file: UploadFile = File(...), title: str | None = Form(None), user=Depends(current_user), conn=Depends(get_conn)):
        member(conn, user, tid, admin=True)
        return do_ingest(conn, user, tid, file, title=title)

    @app.post("/tenants/{tid}/documents/{did}/versions")
    def upload_version(tid: str, did: str, file: UploadFile = File(...), user=Depends(current_user), conn=Depends(get_conn)):
        member(conn, user, tid, admin=True)
        if not conn.execute("SELECT 1 FROM documents WHERE id=? AND tenant_id=?", (did, tid)).fetchone():
            deny(conn, user, "document", tid)
        return do_ingest(conn, user, tid, file, document_id=did)

    @app.get("/tenants/{tid}/documents")
    def list_documents(tid: str, user=Depends(current_user), conn=Depends(get_conn)):
        role = member(conn, user, tid)
        rows = conn.execute(f"""SELECT d.id, d.title, d.tenant_id AS owner_tenant_id, t.name AS owner_name, v.version_no, v.id AS version_id,
                                       v.uploaded_at, v.sha256, v.status
                                FROM documents d JOIN tenants t ON t.id=d.tenant_id
                                JOIN document_versions v ON v.document_id=d.id AND v.is_current=1 AND v.status='ready'
                                WHERE {VISIBLE} ORDER BY d.title""", {"tid": tid, "now": now()}).fetchall()
        out = [dict(r) | {"shared_from": r["owner_name"] if r["owner_tenant_id"] != tid else None} for r in rows]
        if role == "client_admin":  # admins also see documents with no current version (e.g. failed first upload)
            have = {r["id"] for r in rows}
            for r in conn.execute("SELECT d.id, d.title, d.tenant_id AS owner_tenant_id, v.status, v.version_no, v.error FROM documents d JOIN document_versions v "
                                  "ON v.document_id=d.id AND v.version_no=(SELECT MAX(version_no) FROM document_versions WHERE document_id=d.id) WHERE d.tenant_id=?", (tid,)):
                if r["id"] not in have:
                    out.append(dict(r) | {"shared_from": None})
        return out

    @app.get("/tenants/{tid}/documents/{did}")
    def get_document(tid: str, did: str, user=Depends(current_user), conn=Depends(get_conn)):
        role = member(conn, user, tid)
        d = conn.execute(f"""SELECT d.id, d.title, d.tenant_id AS owner_tenant_id FROM documents d
                             JOIN document_versions v ON v.document_id=d.id AND v.is_current=1 AND v.status='ready'
                             WHERE d.id=:did AND {VISIBLE}""", {"did": did, "tid": tid, "now": now()}).fetchone()
        own_admin = role == "client_admin" and conn.execute("SELECT 1 FROM documents WHERE id=? AND tenant_id=?", (did, tid)).fetchone()
        if not d and not own_admin:
            deny(conn, user, "document", tid)
        cols = "id, version_no, filename, media_type, uploaded_by, uploaded_at, sha256, size, status, error, is_current, superseded_at, superseded_by_version"
        if own_admin:
            versions = conn.execute(f"SELECT {cols} FROM document_versions WHERE document_id=? ORDER BY version_no DESC", (did,)).fetchall()
        else:
            versions = conn.execute(f"SELECT id, version_no, filename, media_type, uploaded_at, sha256 FROM document_versions WHERE document_id=? AND is_current=1", (did,)).fetchall()
        with tx(conn):
            ledger.append(conn, "document.read", actor=user["id"], tenant_id=tid, document_id=did)
        return {"id": did, "title": (d or conn.execute("SELECT title FROM documents WHERE id=?", (did,)).fetchone())["title"], "versions": [dict(v) for v in versions]}

    @app.get("/tenants/{tid}/citations/{chunk_id}")
    def open_citation(tid: str, chunk_id: str, user=Depends(current_user), conn=Depends(get_conn)):
        """Same policy as retrieval. Superseded versions are readable only by the owning tenant's administrators (audit)."""
        role = member(conn, user, tid)
        base = """SELECT c.id, c.document_id, c.version_id, c.page, c.section, c.char_start, c.char_end, c.text, d.title, d.tenant_id AS owner_tenant_id,
                         v.version_no, v.sha256, v.is_current, v.status FROM chunks c JOIN document_versions v ON v.id=c.version_id
                  JOIN documents d ON d.id=c.document_id WHERE c.id=:cid AND """
        row = conn.execute(base + "v.is_current=1 AND v.status='ready' AND " + VISIBLE, {"cid": chunk_id, "tid": tid, "now": now()}).fetchone()
        if not row and role == "client_admin":
            row = conn.execute(base + "d.tenant_id=:tid", {"cid": chunk_id, "tid": tid}).fetchone()
        if not row:
            deny(conn, user, "citation", tid)
        with tx(conn):
            ledger.append(conn, "citation.open", actor=user["id"], tenant_id=tid, chunk_id=chunk_id, version_id=row["version_id"],
                          counterparty=row["owner_tenant_id"] if row["owner_tenant_id"] != tid else None)
        return dict(row) | {"superseded": not row["is_current"]}

    # ---------------------------------------------------------------------- chat
    @app.post("/tenants/{tid}/chat")
    def chat(tid: str, body: ChatIn, user=Depends(current_user), conn=Depends(get_conn)):
        member(conn, user, tid)
        throttle("chat", user)
        cid = body.conversation_id
        if cid and not conn.execute("SELECT 1 FROM conversations WHERE id=? AND tenant_id=? AND user_id=?", (cid, tid, user["id"])).fetchone():
            deny(conn, user, "conversation", tid)
        res = answer_question(conn, tid, body.question)
        retrieved = res.pop("retrieved", [])
        qhash = hashlib.sha256(body.question.encode()).hexdigest()
        with tx(conn):
            if not cid:
                cid = f"cnv_{uuid.uuid4().hex[:12]}"
                conn.execute("INSERT INTO conversations VALUES(?,?,?,?)", (cid, tid, user["id"], now()))
            conn.execute("INSERT INTO messages VALUES(?,?,'user',?,NULL,NULL,?)", (f"msg_{uuid.uuid4().hex[:12]}", cid, body.question, now()))
            conn.execute("INSERT INTO messages VALUES(?,?,'assistant',?,?,?,?)",
                         (f"msg_{uuid.uuid4().hex[:12]}", cid, res["answer"], res["outcome"], json.dumps(res["citations"]), now()))
            ledger.append(conn, "chat.query", actor=user["id"], tenant_id=tid, conversation_id=cid, question_sha256=qhash,
                          outcome=res["outcome"], retrieved_chunks=retrieved,
                          cited=[{"chunk": c["chunk_id"], "version": c["version_id"]} for c in res["citations"]])
            if res["question_flagged"] or res["flagged_document_sentences"]:
                ledger.append(conn, "security.injection_suspected", actor=user["id"], tenant_id=tid, conversation_id=cid,
                              in_question=res["question_flagged"], in_documents=res["flagged_document_sentences"])
            owners = {}
            for c in res["citations"]:
                if c["shared_from"]:
                    owners.setdefault(c["document_id"], c["shared_from"])
            for doc_id in owners:  # let the owning tenant see that its shared knowledge was used
                owner = conn.execute("SELECT tenant_id FROM documents WHERE id=?", (doc_id,)).fetchone()["tenant_id"]
                ledger.append(conn, "share.used", actor=user["id"], tenant_id=owner, counterparty=tid, document_id=doc_id)
        return res | {"conversation_id": cid}

    @app.get("/tenants/{tid}/conversations")
    def conversations(tid: str, user=Depends(current_user), conn=Depends(get_conn)):
        member(conn, user, tid)
        return [dict(r) for r in conn.execute("SELECT id, created_at FROM conversations WHERE tenant_id=? AND user_id=? ORDER BY created_at DESC", (tid, user["id"]))]

    @app.get("/tenants/{tid}/conversations/{cid}")
    def conversation(tid: str, cid: str, user=Depends(current_user), conn=Depends(get_conn)):
        member(conn, user, tid)
        if not conn.execute("SELECT 1 FROM conversations WHERE id=? AND tenant_id=? AND user_id=?", (cid, tid, user["id"])).fetchone():
            deny(conn, user, "conversation", tid)
        out = []
        for r in conn.execute("SELECT role, content, outcome, citations, created_at FROM messages WHERE conversation_id=? ORDER BY created_at", (cid,)):
            m = dict(r) | {"citations": json.loads(r["citations"] or "[]")}
            # History must not outlive access: if a shared source was revoked, expired or its owner suspended,
            # the stored answer and quotes derived from it are withheld.
            if any(c.get("shared_from") and not still_visible(conn, tid, c["document_id"]) for c in m["citations"]):
                m.update(content="[Content withheld: access to a shared source has been revoked or has expired.]", citations=[], outcome="redacted")
            out.append(m)
        return out

    def still_visible(conn, tid, did) -> bool:
        return bool(conn.execute(f"""SELECT 1 FROM documents d JOIN document_versions v ON v.document_id=d.id AND v.is_current=1 AND v.status='ready'
                                     WHERE d.id=:did AND {VISIBLE}""", {"did": did, "tid": tid, "now": now()}).fetchone())

    # ------------------------------------------------------------------- sharing
    @app.post("/tenants/{tid}/shares", status_code=201)
    def create_share(tid: str, body: ShareIn, user=Depends(current_user), conn=Depends(get_conn)):
        member(conn, user, tid, admin=True)
        if body.grantee_tenant_id == tid:
            raise HTTPException(400, "Cannot share with your own tenant")
        if body.expires_at and body.expires_at <= now():
            raise HTTPException(400, "expires_at must be in the future (ISO-8601 UTC)")
        sid = f"shr_{uuid.uuid4().hex[:12]}"
        with tx(conn):
            if not conn.execute("SELECT 1 FROM tenants WHERE id=? AND status='active'", (body.grantee_tenant_id,)).fetchone():
                raise HTTPException(404, "Grantee tenant not found")
            if body.document_id and not conn.execute("SELECT 1 FROM documents WHERE id=? AND tenant_id=?", (body.document_id, tid)).fetchone():
                raise HTTPException(404, "Document not found")
            conn.execute("INSERT INTO shares VALUES(?,?,?,?,?,?,?,NULL,NULL)", (sid, tid, body.grantee_tenant_id, body.document_id, user["id"], now(), body.expires_at))
            ledger.append(conn, "share.grant", actor=user["id"], tenant_id=tid, counterparty=body.grantee_tenant_id, share_id=sid,
                          document_id=body.document_id, expires_at=body.expires_at)
        return {"id": sid}

    @app.get("/tenants/{tid}/shares")
    def list_shares(tid: str, user=Depends(current_user), conn=Depends(get_conn)):
        member(conn, user, tid, admin=True)
        cols = "id, owner_tenant_id, grantee_tenant_id, document_id, granted_at, expires_at, revoked_at"
        return {"outgoing": [dict(r) for r in conn.execute(f"SELECT {cols} FROM shares WHERE owner_tenant_id=?", (tid,))],
                "incoming": [dict(r) for r in conn.execute(f"SELECT {cols} FROM shares WHERE grantee_tenant_id=? AND revoked_at IS NULL", (tid,))]}

    @app.delete("/tenants/{tid}/shares/{sid}")
    def revoke_share(tid: str, sid: str, user=Depends(current_user), conn=Depends(get_conn)):
        member(conn, user, tid, admin=True)
        with tx(conn):
            sh = conn.execute("SELECT grantee_tenant_id FROM shares WHERE id=? AND owner_tenant_id=? AND revoked_at IS NULL", (sid, tid)).fetchone()
            if not sh:
                raise NOT_FOUND
            conn.execute("UPDATE shares SET revoked_at=?, revoked_by=? WHERE id=?", (now(), user["id"], sid))
            ledger.append(conn, "share.revoke", actor=user["id"], tenant_id=tid, counterparty=sh["grantee_tenant_id"], share_id=sid)
        return {"ok": True}

    # --------------------------------------------------------------------- audit
    @app.get("/tenants/{tid}/audit")
    def tenant_audit(tid: str, limit: int = 200, user=Depends(current_user), conn=Depends(get_conn)):
        member(conn, user, tid, admin=True)
        rows = conn.execute("SELECT seq, ts, tenant_id, counterparty_tenant_id, actor, action, details, hash FROM audit_events "
                            "WHERE tenant_id=? OR counterparty_tenant_id=? ORDER BY seq DESC LIMIT ?", (tid, tid, min(limit, 1000)))
        return [dict(r) | {"details": json.loads(r["details"])} for r in rows]

    @app.get("/audit/verify")
    def verify(user=Depends(current_user), conn=Depends(get_conn)):
        is_admin = conn.execute("SELECT 1 FROM memberships WHERE user_id=? AND role='client_admin' AND status='active'", (user["id"],)).fetchone()
        if not (user["is_sysadmin"] or is_admin):
            raise HTTPException(403, "Administrator required")
        res = ledger.verify(conn)
        return res if user["is_sysadmin"] else {"ok": res["ok"]}

    @app.post("/audit/checkpoint")
    def checkpoint(user=Depends(current_user), conn=Depends(get_conn)):
        sysadmin(user)
        with tx(conn):
            ledger.append(conn, "audit.checkpoint", actor=user["id"])
            cp = ledger.checkpoint(conn)
        return cp

    @app.get("/security/status")
    def security_status(user=Depends(current_user)):
        return tee.status() | {"audit_ledger": {"type": "sha256-hash-chain", "anchoring": "local HMAC-signed checkpoint file; not a distributed ledger"},
                               "egress": "no outbound network calls are made by the application; run with egress blocked at the host/container",
                               "model": "extractive answers from authorised passages; no generative model is trusted for access control"}

    if STATIC.exists():
        app.mount("/static", StaticFiles(directory=STATIC), name="static")

        @app.get("/", include_in_schema=False)
        def index():
            return FileResponse(STATIC / "index.html")

    return app
