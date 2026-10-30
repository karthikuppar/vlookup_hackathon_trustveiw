"""PS-04 Secure Multi-Client Knowledge Chatbot - Main FastAPI Server."""
from __future__ import annotations
import os
import uuid
from typing import Any
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, Field

from auth_security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from crypto_utils import now_utc_iso
from database import get_connection, init_db
from document_processor import DocumentService
from ledger_engine import AuditLedger
from retrieval_engine import RetrievalEngine
from sharing_service import SharingService
from tee_engine import TeeService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

app = FastAPI(
    title="PS-04: Secure Multi-Client Knowledge Chatbot",
    version="1.0.0",
    description="Offline-capable, tenant-isolated document-grounded chatbot with blockchain-lite audit and TEE simulation.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Pydantic Request Models ---
class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=64)
    role: str = "client_employee"  # system_admin, client_admin, client_employee
    tenant_id: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class CreateClientRequest(BaseModel):
    client_id: str = Field(min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=120)


class AddMemberRequest(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=8)
    role: str = "client_employee"


class DirectDocUploadRequest(BaseModel):
    title: str
    filename: str
    content: str


class DirectVersionUploadRequest(BaseModel):
    filename: str
    content: str


class CreateShareRequest(BaseModel):
    recipient_tenant_id: str
    reason: str | None = None
    permission: str = "read"


class ChatQueryRequest(BaseModel):
    question: str = Field(min_length=2)
    session_id: str | None = None


class TamperTestRequest(BaseModel):
    sequence: int | None = None


class TeeVerifyRequest(BaseModel):
    simulate_invalid: bool = False
    quote_signature: str | None = None


# --- Authentication & Current User Dependency ---
async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict[str, Any]:
    payload = decode_access_token(token)
    if not payload or not payload.get("user_id"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired authentication token")

    with get_connection() as conn:
        user = conn.execute("SELECT id, name, email, role, tenant_id FROM users WHERE id = ?", (payload["user_id"],)).fetchone()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account not found")

    return dict(user)


# --- Startup & Seeding ---
@app.on_event("startup")
def on_startup():
    init_db()
    seed_demo_data()


def seed_demo_data():
    """Seed initial sample clients and conflicting documents for Section 12 demo scenarios."""
    with get_connection() as conn:
        # Check if tenants exist
        if conn.execute("SELECT id FROM tenants WHERE id = 'tenant_a'").fetchone():
            return

        now = now_utc_iso()
        # 1. Seed Tenants
        conn.execute("INSERT OR IGNORE INTO tenants VALUES ('system', 'Platform Administration', ?)", (now,))
        conn.execute("INSERT OR IGNORE INTO tenants VALUES ('tenant_a', 'AcroCorp Technologies', ?)", (now,))
        conn.execute("INSERT OR IGNORE INTO tenants VALUES ('tenant_b', 'BetaShield Security', ?)", (now,))

        # 2. Seed Users
        pwd_hash = hash_password("Password123!")
        conn.execute("INSERT OR IGNORE INTO users VALUES ('usr_sysadmin', 'System SuperAdmin', 'sysadmin@ps04platform.com', ?, 'system_admin', 'system', ?)", (pwd_hash, now))
        conn.execute("INSERT OR IGNORE INTO users VALUES ('usr_admin_a', 'Alice Admin', 'admin@acrocorp.com', ?, 'client_admin', 'tenant_a', ?)", (pwd_hash, now))
        conn.execute("INSERT OR IGNORE INTO users VALUES ('usr_emp_a', 'Edward Employee', 'employee@acrocorp.com', ?, 'client_employee', 'tenant_a', ?)", (pwd_hash, now))
        conn.execute("INSERT OR IGNORE INTO users VALUES ('usr_admin_b', 'Bob Admin', 'admin@betashield.com', ?, 'client_admin', 'tenant_b', ?)", (pwd_hash, now))
        conn.execute("INSERT OR IGNORE INTO users VALUES ('usr_emp_b', 'Betty Employee', 'employee@betashield.com', ?, 'client_employee', 'tenant_b', ?)", (pwd_hash, now))

    # 3. Seed Conflicting SOP Documents (Demo Scenarios 2 & 3)
    doc_a_text = (
        "AcroCorp Standard Operating Procedure (SOP):\n\n"
        "1. Invoicing Policy: All vendor and customer service invoices have a mandatory settlement deadline of 30 days.\n"
        "Payments issued after 30 days incur standard interest.\n\n"
        "2. Infrastructure Access: Direct remote vendor access is permitted with written manager sign-off.\n\n"
        "3. Travel Reimbursements: Standard meal allowance is capped at $75 per day."
    )
    DocumentService.ingest_document(
        tenant_id="tenant_a",
        user_id="usr_admin_a",
        title="AcroCorp Operational Guidelines",
        filename="acrocorp_sop_v1.txt",
        content_bytes=doc_a_text.encode("utf-8"),
    )

    doc_b_text = (
        "BetaShield Security and Financial Protocol:\n\n"
        "1. Invoicing Policy: All vendor and customer service invoices have a mandatory settlement deadline of 15 days.\n"
        "Under no conditions can payment terms exceed 15 days.\n\n"
        "2. Infrastructure Access: Direct remote vendor access is strictly forbidden under any circumstances.\n\n"
        "3. Compliance Audits: Internal audits are conducted quarterly."
    )
    DocumentService.ingest_document(
        tenant_id="tenant_b",
        user_id="usr_admin_b",
        title="BetaShield Security Standards",
        filename="betashield_standards_v1.txt",
        content_bytes=doc_b_text.encode("utf-8"),
    )


# --- Health & Status ---
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "PS-04 Secure Multi-Client Knowledge Chatbot",
        "offline_runtime": True,
    }


# --- Auth Routes ---
@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
def register_user(req: RegisterRequest):
    email = str(req.email).lower()
    with get_connection() as conn:
        tenant = conn.execute("SELECT id FROM tenants WHERE id = ?", (req.tenant_id,)).fetchone()
        if not tenant:
            raise HTTPException(status_code=400, detail=f"Tenant '{req.tenant_id}' does not exist")

        existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="An account with this email already exists")

        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        now = now_utc_iso()
        pwd_hash = hash_password(req.password)
        conn.execute(
            "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, req.name.strip(), email, pwd_hash, req.role, req.tenant_id, now),
        )

    AuditLedger.append_event(
        event_type="user_registered",
        actor_id=user_id,
        tenant_id=req.tenant_id,
        resource_id=user_id,
        action="register_account",
        decision="permitted",
        details={"email": email, "role": req.role},
    )

    token = create_access_token({"user_id": user_id, "role": req.role, "tenant_id": req.tenant_id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user_id, "name": req.name, "email": email, "role": req.role, "tenant_id": req.tenant_id},
    }


@app.post("/api/auth/login")
def login_user(req: LoginRequest):
    email = str(req.email).lower()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

    if not row or not verify_password(req.password, row["password_hash"]):
        AuditLedger.append_event(
            event_type="user_login_failed",
            actor_id=email,
            tenant_id="auth",
            resource_id=email,
            action="login",
            decision="denied",
            details={"reason": "Invalid credentials"},
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    user = dict(row)
    token = create_access_token({"user_id": user["id"], "role": user["role"], "tenant_id": user["tenant_id"]})

    AuditLedger.append_event(
        event_type="user_logged_in",
        actor_id=user["id"],
        tenant_id=user["tenant_id"],
        resource_id=user["id"],
        action="login",
        decision="permitted",
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user["id"], "name": user["name"], "email": user["email"], "role": user["role"], "tenant_id": user["tenant_id"]},
    }


@app.get("/api/auth/me")
def get_me(user: dict[str, Any] = Depends(get_current_user)):
    return {"user": user}


# --- Client / Tenant Management ---
@app.post("/api/clients", status_code=status.HTTP_201_CREATED)
def create_client(req: CreateClientRequest, user: dict[str, Any] = Depends(get_current_user)):
    if user["role"] not in {"system_admin", "client_admin"}:
        raise HTTPException(status_code=403, detail="Only administrators can onboard new client tenants")

    client_id = req.client_id.strip().lower()
    now = now_utc_iso()
    with get_connection() as conn:
        existing = conn.execute("SELECT id FROM tenants WHERE id = ?", (client_id,)).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail=f"Client '{client_id}' already exists")
        conn.execute("INSERT INTO tenants VALUES (?, ?, ?)", (client_id, req.name.strip(), now))

    AuditLedger.append_event(
        event_type="client_tenant_created",
        actor_id=user["id"],
        tenant_id=client_id,
        resource_id=client_id,
        action="create_client",
        decision="permitted",
        details={"name": req.name},
    )

    return {"client_id": client_id, "name": req.name, "created_at": now}


@app.get("/api/clients")
def list_clients(user: dict[str, Any] = Depends(get_current_user)):
    with get_connection() as conn:
        if user["role"] == "system_admin":
            rows = conn.execute("SELECT * FROM tenants ORDER BY created_at DESC").fetchall()
        else:
            rows = conn.execute("SELECT * FROM tenants WHERE id = ?", (user["tenant_id"],)).fetchall()
    return {"clients": [dict(r) for r in rows]}


@app.post("/api/clients/{client_id}/members", status_code=status.HTTP_201_CREATED)
def add_client_member(client_id: str, req: AddMemberRequest, user: dict[str, Any] = Depends(get_current_user)):
    if user["role"] not in {"system_admin", "client_admin"}:
        raise HTTPException(status_code=403, detail="Forbidden: Admin privilege required")
    if user["role"] == "client_admin" and user["tenant_id"] != client_id:
        raise HTTPException(status_code=403, detail="Cannot manage members of another tenant")

    email = str(req.email).lower()
    with get_connection() as conn:
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="User with this email already exists")

        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        now = now_utc_iso()
        pwd_hash = hash_password(req.password)
        conn.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)", (user_id, req.name, email, pwd_hash, req.role, client_id, now))

    AuditLedger.append_event(
        event_type="client_member_added",
        actor_id=user["id"],
        tenant_id=client_id,
        resource_id=user_id,
        action="add_member",
        decision="permitted",
        details={"email": email, "role": req.role},
    )

    return {"id": user_id, "name": req.name, "email": email, "role": req.role, "tenant_id": client_id}


@app.get("/api/clients/{client_id}/members")
def list_client_members(client_id: str, user: dict[str, Any] = Depends(get_current_user)):
    if user["tenant_id"] != client_id and user["role"] != "system_admin":
        raise HTTPException(status_code=403, detail="Access to other tenant member lists is prohibited")
    with get_connection() as conn:
        rows = conn.execute("SELECT id, name, email, role, tenant_id, created_at FROM users WHERE tenant_id = ?", (client_id,)).fetchall()
    return {"members": [dict(r) for r in rows]}


@app.post("/api/clients/{client_id}/documents", status_code=status.HTTP_201_CREATED)
async def upload_document(
    client_id: str,
    request: Request,
    user: dict[str, Any] = Depends(get_current_user),
):
    if user["tenant_id"] != client_id and user["role"] != "system_admin":
        raise HTTPException(status_code=403, detail="Cannot upload documents to another tenant's repository")

    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        form = await request.form()
        title = form.get("title")
        file = form.get("file")
        if not file:
            raise HTTPException(status_code=400, detail="File must be uploaded in form-data")
        content_bytes = await file.read()
        filename = getattr(file, "filename", "uploaded_doc.txt")
        doc_title = str(title) if title else filename
    else:
        body = await request.json()
        doc_title = body.get("title", "Untitled Document")
        filename = body.get("filename", "document.txt")
        content = body.get("content", "")
        content_bytes = content.encode("utf-8") if isinstance(content, str) else b""

    result = DocumentService.ingest_document(
        tenant_id=client_id,
        user_id=user["id"],
        title=doc_title,
        filename=filename,
        content_bytes=content_bytes,
    )
    return result


@app.get("/api/clients/{client_id}/documents")
def list_documents(client_id: str, user: dict[str, Any] = Depends(get_current_user)):
    # Server-side authorization check
    if user["tenant_id"] != client_id and user["role"] != "system_admin":
        AuditLedger.append_event(
            event_type="document_list_denied",
            actor_id=user["id"],
            tenant_id=user["tenant_id"],
            resource_id=client_id,
            action="list_documents",
            decision="denied",
            details={"attempted_tenant": client_id},
        )
        raise HTTPException(status_code=403, detail="Access denied: Cannot list another client's documents")

    docs = DocumentService.list_documents(client_id)
    return {"documents": docs}


@app.post("/api/documents/{document_id}/versions", status_code=status.HTTP_201_CREATED)
async def replace_document_version(
    document_id: str,
    request: Request,
    user: dict[str, Any] = Depends(get_current_user),
):
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        form = await request.form()
        file = form.get("file")
        if not file:
            raise HTTPException(status_code=400, detail="File must be provided")
        content_bytes = await file.read()
        filename = getattr(file, "filename", "updated_version.txt")
    else:
        body = await request.json()
        filename = body.get("filename", "updated_version.txt")
        content = body.get("content", "")
        content_bytes = content.encode("utf-8") if isinstance(content, str) else b""

    try:
        result = DocumentService.replace_version(
            doc_id=document_id,
            tenant_id=user["tenant_id"],
            user_id=user["id"],
            content_bytes=content_bytes,
            filename=filename,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- Explicit Knowledge Sharing (Section 4) ---
@app.post("/api/knowledge-bases/{kb_id}/shares", status_code=status.HTTP_201_CREATED)
def create_share_grant(kb_id: str, req: CreateShareRequest, user: dict[str, Any] = Depends(get_current_user)):
    # Only client_admin or system_admin can share their knowledge base
    if user["role"] not in {"system_admin", "client_admin"}:
        raise HTTPException(status_code=403, detail="Only administrators can configure knowledge base sharing")

    # If kb_id is a tenant ID or alias, use user's tenant
    source_tenant = user["tenant_id"] if kb_id in {"default", user["tenant_id"]} else kb_id
    if source_tenant != user["tenant_id"] and user["role"] != "system_admin":
        raise HTTPException(status_code=403, detail="Cannot share another tenant's knowledge base")

    try:
        grant = SharingService.create_share_grant(
            source_tenant_id=source_tenant,
            recipient_tenant_id=req.recipient_tenant_id,
            granted_by=user["id"],
            reason=req.reason,
            permission=req.permission,
        )
        return grant
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/knowledge-bases/{kb_id}/shares/{share_id}")
def revoke_share_grant(kb_id: str, share_id: str, user: dict[str, Any] = Depends(get_current_user)):
    if user["role"] not in {"system_admin", "client_admin"}:
        raise HTTPException(status_code=403, detail="Only administrators can revoke knowledge base sharing")

    try:
        res = SharingService.revoke_share_grant(
            share_id=share_id,
            actor_id=user["id"],
            actor_tenant_id=user["tenant_id"],
        )
        return res
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/knowledge-bases/shares")
def list_knowledge_shares(user: dict[str, Any] = Depends(get_current_user)):
    return SharingService.list_shares(user["tenant_id"])


# --- Chat & Grounded Querying (Section 3.4) ---
@app.post("/api/chat/query")
def chat_query(req: ChatQueryRequest, user: dict[str, Any] = Depends(get_current_user)):
    """
    Non-negotiable server-side boundary:
    Derives user tenant strictly from verified session.
    Retrieval filters chunks before returning response.
    """
    res = RetrievalEngine.query_knowledge_base(
        user_id=user["id"],
        user_tenant_id=user["tenant_id"],
        question=req.question,
        session_id=req.session_id,
    )
    return res


# --- Audit Ledger & Tamper Verification (Section 5) ---
@app.get("/api/audit/events")
def get_audit_events(limit: int = 100, user: dict[str, Any] = Depends(get_current_user)):
    return {"events": AuditLedger.get_events(limit=limit)}


@app.post("/api/audit/verify")
def verify_audit_ledger(user: dict[str, Any] = Depends(get_current_user)):
    result = AuditLedger.verify()
    return result


@app.post("/api/audit/tamper-test")
def simulate_tamper_attack(req: TamperTestRequest, user: dict[str, Any] = Depends(get_current_user)):
    """Simulate a tamper attack on the audit ledger to demonstrate detection."""
    result = AuditLedger.tamper_for_demo(sequence=req.sequence)
    return result


# --- TEE Simulation (Section 6) ---
@app.get("/api/security/tee-status")
def get_tee_status():
    return TeeService.get_status()


@app.post("/api/security/tee-verify")
def verify_tee_attestation(req: TeeVerifyRequest, user: dict[str, Any] = Depends(get_current_user)):
    return TeeService.verify_attestation(
        quote_signature=req.quote_signature,
        simulate_invalid=req.simulate_invalid,
        actor_id=user["id"],
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
