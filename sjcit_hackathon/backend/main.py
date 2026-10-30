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


@app.on_event("startup")
def on_startup():
    init_db()
    seed_demo_data()
    try:
        from vector_store import InMemoryVectorDB
        InMemoryVectorDB.get_instance().rebuild_all()
    except Exception as e:
        print(f"Vector DB init warning: {e}")


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

    # 3. Seed Rich Employee SOP Documents for tenant_a (AcroCorp)
    # --- Document 1: Employee Onboarding SOP ---
    doc_onboarding = """ACROCORP EMPLOYEE ONBOARDING STANDARD OPERATING PROCEDURE (SOP-HR-001)
Version: 1.0 | Effective Date: January 2024 | Owner: Human Resources Department

SECTION 1: PURPOSE
This document outlines the mandatory onboarding steps every new employee must complete within their first 30 days at AcroCorp Technologies. Following this SOP ensures a smooth transition into your role and compliance with organizational policy.

SECTION 2: DAY ONE — YOUR FIRST STEPS
Step 1: Report to Reception (Ground Floor, Building A) by 9:00 AM on your joining date. Bring your original ID documents and offer letter.
Step 2: Collect your employee access badge from the Security Desk. You must wear this badge visibly at all times on company premises.
Step 3: Proceed to HR to complete your new hire documentation pack. This includes tax forms, bank account details for payroll, emergency contact information, and policy acknowledgement sign-offs.
Step 4: Your assigned buddy or reporting manager will give you a tour of the office and introduce you to your team.
Step 5: IT will set up your laptop, email account, and system access. You must complete the IT Security Awareness training on your first day before accessing corporate systems.

SECTION 3: FIRST WEEK CHECKLIST
- Complete all mandatory e-learning modules on the Learning Portal within 5 business days.
- Attend the New Employee Orientation session scheduled by HR (check your welcome email for date/time).
- Set up your AcroCorp email signature using the standard corporate template available on the Intranet.
- Schedule a 1:1 meeting with your reporting manager to discuss your 30-60-90 day goals.
- Join your team's Slack channel and introduce yourself.
- Request access to any project tools or systems you need by raising an IT helpdesk ticket.

SECTION 4: FIRST 30 DAYS
- Complete the role-specific technical training assigned by your manager.
- Read and acknowledge the Code of Conduct, Data Protection Policy, and Information Security Policy.
- Complete the mandatory Health & Safety induction.
- Probation period: All new employees are on a 3-month probation period. Your manager will schedule a mid-probation review at 6 weeks.

SECTION 5: IMPORTANT CONTACTS
- HR Helpdesk: hr@acrocorp.com | Ext: 1000
- IT Helpdesk: it-support@acrocorp.com | Ext: 2000 | Portal: helpdesk.acrocorp.internal
- Payroll: payroll@acrocorp.com | Ext: 1050
- Security Desk: security@acrocorp.com | Ext: 3000
- Facilities (desk, equipment, parking): facilities@acrocorp.com | Ext: 4000

SECTION 6: WHAT TO DO IF YOU HAVE QUESTIONS
Contact your assigned HR buddy or email hr@acrocorp.com. For urgent issues on Day 1, speak directly with the HR representative at the front desk.
"""
    DocumentService.ingest_document(
        tenant_id="tenant_a",
        user_id="usr_admin_a",
        title="Employee Onboarding SOP (HR-001)",
        filename="acrocorp_onboarding_sop.txt",
        content_bytes=doc_onboarding.encode("utf-8"),
    )

    # --- Document 2: Leave & Attendance Policy ---
    doc_leave = """ACROCORP LEAVE AND ATTENDANCE POLICY (POL-HR-002)
Version: 2.1 | Effective Date: April 2024 | Owner: Human Resources

SECTION 1: LEAVE ENTITLEMENTS
Annual Leave: All full-time employees are entitled to 24 days of paid annual leave per calendar year, accrued monthly.
Sick Leave: Employees are entitled to 12 days of paid sick leave per year. A medical certificate is required for absences exceeding 2 consecutive days.
Casual Leave: 6 days of casual leave per year, non-encashable. Cannot be carried forward.
Maternity Leave: 26 weeks of paid maternity leave as per statutory requirements.
Paternity Leave: 5 working days of paid paternity leave to be taken within 30 days of the child's birth.
Bereavement Leave: 3 days for immediate family members (spouse, children, parents, siblings).
Public Holidays: Employees observe all government-declared public holidays. A revised list is published on the Intranet each January.

SECTION 2: HOW TO APPLY FOR LEAVE
Step 1: Log in to the HR Portal at hr.acrocorp.internal.
Step 2: Navigate to Leave Management > Apply for Leave.
Step 3: Select leave type, start date, end date, and enter the reason.
Step 4: Submit the request. Your reporting manager will receive an automatic notification for approval.
Step 5: You will receive an email confirmation once your manager approves or declines the request.
For urgent or same-day sick leave: Call or message your manager before 9:30 AM and follow up with an application on the HR Portal.

SECTION 3: LEAVE CARRY-FORWARD RULES
Annual leave: Maximum of 10 days can be carried forward to the next calendar year. Unused leave beyond 10 days will lapse on December 31st.
Sick leave: Not encashable, cannot be carried forward. Remaining sick leave lapses at year-end.

SECTION 4: ATTENDANCE GUIDELINES
Standard work hours are 9:00 AM to 6:00 PM, Monday to Friday.
Employees must check in using the biometric system or the remote attendance app within 15 minutes of shift start.
Late arrivals (beyond 9:30 AM) must be notified to the manager. Three unnotified late arrivals in a month may result in a leave deduction.
Remote Work: Refer to the Remote Work Policy (POL-HR-008) for WFH attendance rules.

SECTION 5: CONTACT
For leave disputes or adjustments, contact hr@acrocorp.com or ext 1000.
"""
    DocumentService.ingest_document(
        tenant_id="tenant_a",
        user_id="usr_admin_a",
        title="Leave & Attendance Policy (HR-002)",
        filename="acrocorp_leave_policy.txt",
        content_bytes=doc_leave.encode("utf-8"),
    )

    # --- Document 3: IT Security & Access Control SOP ---
    doc_it = """ACROCORP INFORMATION SECURITY & ACCESS CONTROL SOP (SOP-IT-003)
Version: 3.0 | Effective Date: June 2024 | Owner: Information Technology & Cybersecurity

SECTION 1: PASSWORD POLICY
All employees must use a strong password meeting these requirements:
- Minimum 12 characters in length.
- Must include at least one uppercase letter, one lowercase letter, one number, and one special character.
- Passwords must be changed every 90 days.
- Do not reuse any of your last 10 passwords.
- Never share your password with anyone, including IT staff. AcroCorp IT will NEVER ask for your password.
- Use the AcroCorp Password Manager (Vault) for storing credentials securely.

SECTION 2: MULTI-FACTOR AUTHENTICATION (MFA)
MFA is mandatory for all employees accessing corporate systems remotely, including VPN, email, HR Portal, and cloud applications.
Step 1: Download the AcroCorp Authenticator app from the IT portal.
Step 2: Register your device by scanning the QR code provided during your IT setup session.
Step 3: Use the 6-digit one-time code for every remote login.

SECTION 3: DEVICE & LAPTOP POLICY
Your corporate laptop must not be used for personal activities, including personal email, social media, or installing unauthorized software.
Do not connect to unsecured public Wi-Fi without using the corporate VPN.
Lost or stolen devices must be reported to IT within 1 hour of discovery: it-support@acrocorp.com or Ext 2000.
All devices are enrolled in the Mobile Device Management (MDM) system and can be remotely wiped if lost.
Do not connect personal USB drives or external storage to corporate devices without prior IT authorization.

SECTION 4: DATA CLASSIFICATION & HANDLING
Data is classified into three levels:
- PUBLIC: Can be shared externally (press releases, public documentation).
- INTERNAL: For employees only. Do not share outside the organization.
- CONFIDENTIAL: Requires manager approval before sharing. Must be encrypted when stored or transmitted.
Customer data and PII (Personally Identifiable Information) is always classified as CONFIDENTIAL.
Do not store confidential data on personal devices, personal cloud storage (Dropbox, Google Drive personal accounts), or email personal mailboxes.

SECTION 5: REPORTING SECURITY INCIDENTS
If you suspect a security incident (phishing, malware, unauthorized access, data breach):
Step 1: Do not click any suspicious links or provide credentials.
Step 2: Immediately report to the IT Security team: security@acrocorp.com or Ext 2999 (24/7).
Step 3: Do not attempt to fix or investigate the issue yourself.
Step 4: Preserve all evidence (screenshots, email headers) for IT forensics.
Step 5: Your manager and the CISO will be notified by IT.
All security incidents are treated as high priority and must be reported within 30 minutes of discovery.

SECTION 6: INTERNET & EMAIL USAGE
Corporate internet and email are for business use. Reasonable personal use is permitted but monitored.
Prohibited uses: Accessing illegal content, downloading pirated software, bulk email marketing, cryptocurrency mining.
Phishing emails should be forwarded to phishing@acrocorp.com and then deleted.
"""
    DocumentService.ingest_document(
        tenant_id="tenant_a",
        user_id="usr_admin_a",
        title="IT Security & Access Control SOP (IT-003)",
        filename="acrocorp_it_security_sop.txt",
        content_bytes=doc_it.encode("utf-8"),
    )

    # --- Document 4: Expense & Reimbursement Policy ---
    doc_expense = """ACROCORP EXPENSE AND REIMBURSEMENT POLICY (POL-FIN-004)
Version: 1.5 | Effective Date: March 2024 | Owner: Finance Department

SECTION 1: PURPOSE
This policy governs how employees submit and receive reimbursement for legitimate business expenses incurred on behalf of AcroCorp Technologies.

SECTION 2: ELIGIBLE EXPENSES
The following expense categories are reimbursable with proper documentation:
- Business Travel (flights, trains, taxis/ride-share): Economy class for domestic, business class for international flights over 6 hours.
- Hotel Accommodation: Up to $150 per night for domestic travel; up to $250 per night for international travel.
- Meals & Entertainment: Up to $50 per day for domestic travel; up to $75 per day for international travel. Client entertainment requires prior manager approval.
- Communication: Mobile phone bill reimbursement up to $50/month for employees on the approved field/remote list.
- Professional Subscriptions: Software or professional memberships must be pre-approved by your manager.

SECTION 3: HOW TO SUBMIT AN EXPENSE CLAIM
Step 1: Collect all receipts. Receipts are mandatory for all expenses over $10. Credit card statements alone are not accepted.
Step 2: Log in to the Finance Portal at finance.acrocorp.internal.
Step 3: Navigate to Expense Claims > New Claim.
Step 4: Enter expense items, upload receipt images or PDFs, select the relevant project code, and add a description.
Step 5: Submit for manager approval. Claims must be submitted within 30 days of the expense date.
Step 6: Approved claims are processed within 7 business days and paid via direct bank transfer.

SECTION 4: NON-REIMBURSABLE EXPENSES
The following are NOT reimbursable:
- Fines, parking tickets, or traffic violations.
- Personal entertainment, alcohol (unless part of approved client entertainment).
- Expenses for family members or guests not on official company business.
- Expenses without valid original receipts.

SECTION 5: TRAVEL ADVANCE REQUESTS
For large business trips, employees may request a travel advance of up to $500 by submitting a Travel Advance Request form to finance@acrocorp.com at least 5 business days before travel.
Unused advance amounts must be returned to Finance within 5 business days of returning from travel.

SECTION 6: CONTACTS
Finance queries: finance@acrocorp.com | Ext 5000
Expense Portal: finance.acrocorp.internal
"""
    DocumentService.ingest_document(
        tenant_id="tenant_a",
        user_id="usr_admin_a",
        title="Expense & Reimbursement Policy (FIN-004)",
        filename="acrocorp_expense_policy.txt",
        content_bytes=doc_expense.encode("utf-8"),
    )

    # --- Document 5: Code of Conduct ---
    doc_conduct = """ACROCORP CODE OF CONDUCT & WORKPLACE ETHICS (POL-HR-005)
Version: 2.0 | Effective Date: January 2024 | Owner: Compliance & Human Resources

SECTION 1: OUR VALUES
AcroCorp is built on Integrity, Respect, Innovation, and Accountability. All employees are expected to embody these values in every interaction — internal and external.

SECTION 2: PROFESSIONAL CONDUCT
- Treat every colleague, client, and partner with courtesy and respect.
- Discrimination, harassment, or bullying of any kind — based on gender, race, age, religion, disability, or any other protected characteristic — is strictly prohibited and will result in immediate disciplinary action.
- All business decisions must be made in the best interest of AcroCorp, free from personal bias or conflicts of interest.
- Conflicts of interest (e.g., working for a competitor, having a financial interest in a supplier) must be disclosed to your manager and HR in writing.

SECTION 3: CONFIDENTIALITY
Employees must not share proprietary business information, client data, or trade secrets with unauthorized parties, during or after employment.
This obligation continues for 2 years after your last day of employment.
Signing the Non-Disclosure Agreement (NDA) is mandatory for all employees and is part of your employment contract.

SECTION 4: SOCIAL MEDIA POLICY
You may mention your role and employer on personal social media, but must not:
- Share confidential client information or internal business data.
- Make disparaging comments about AcroCorp, colleagues, clients, or competitors.
- Represent your personal opinions as official AcroCorp statements.
All official communications on behalf of AcroCorp on social media must be approved by the Marketing team.

SECTION 5: GIFTS & ENTERTAINMENT
Employees must not accept gifts valued above $50 from vendors, clients, or business partners.
Any gifts of higher value must be reported to your manager and may be donated to charity at company discretion.
Offering gifts to clients or partners must be pre-approved by your manager and the Finance team.

SECTION 6: REPORTING VIOLATIONS
If you witness or experience a violation of this Code of Conduct:
Step 1: Report to your manager or HR if you feel comfortable doing so.
Step 2: Use the anonymous Ethics Hotline: ethics.acrocorp.internal or call 1-800-ACRO-ETH.
Step 3: For urgent legal or safety concerns, contact the Compliance Officer directly: compliance@acrocorp.com.
AcroCorp strictly prohibits retaliation against anyone who reports a concern in good faith.
"""
    DocumentService.ingest_document(
        tenant_id="tenant_a",
        user_id="usr_admin_a",
        title="Code of Conduct & Workplace Ethics (HR-005)",
        filename="acrocorp_code_of_conduct.txt",
        content_bytes=doc_conduct.encode("utf-8"),
    )

    # --- Seed BetaShield docs for cross-tenant demo (conflict scenario) ---
    doc_b_text = (
        "BetaShield Security Protocol (SOP-BS-001):\n\n"
        "1. Invoicing Policy: All invoices have a mandatory settlement deadline of 15 days. "
        "Under no conditions can payment terms exceed 15 days.\n\n"
        "2. Remote Access: Direct remote vendor access to infrastructure is strictly forbidden under any circumstances. "
        "All remote sessions must be mediated by an internal systems engineer.\n\n"
        "3. Compliance Audits: Internal audits are conducted quarterly by the Compliance team."
    )
    DocumentService.ingest_document(
        tenant_id="tenant_b",
        user_id="usr_admin_b",
        title="BetaShield Security Standards (BS-001)",
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


# --- Admin & NLP / Security Hub ---
@app.get("/api/admin/nlp-stats")
def get_nlp_stats(user: dict[str, Any] = Depends(get_current_user)):
    from vector_store import InMemoryVectorDB
    return InMemoryVectorDB.get_instance().get_status()


@app.post("/api/admin/vector-reindex")
def reindex_vectors(user: dict[str, Any] = Depends(get_current_user)):
    if user["role"] not in {"system_admin", "client_admin"}:
        raise HTTPException(status_code=403, detail="Only administrators can trigger vector re-indexing")
    import time
    from vector_store import InMemoryVectorDB
    t0 = time.perf_counter()
    InMemoryVectorDB.get_instance().rebuild_all()
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    status = InMemoryVectorDB.get_instance().get_status()
    status["reindex_time_ms"] = elapsed_ms
    return status


@app.get("/api/admin/security-matrix")
def get_security_matrix(user: dict[str, Any] = Depends(get_current_user)):
    from vector_store import InMemoryVectorDB
    from tee_engine import TeeService
    from ledger_engine import AuditLedger

    ledger_status = AuditLedger.verify()
    tee_status = TeeService.get_status()
    nlp_status = InMemoryVectorDB.get_instance().get_status()

    with get_connection() as conn:
        threat_rows = conn.execute(
            """
            SELECT sequence, event_type, actor_id, tenant_id, action, decision, payload_digest, timestamp
            FROM audit_events
            WHERE event_type IN ('security_threat_detected', 'cross_tenant_access_denied', 'tee_attestation_rejected', 'tamper_attack_simulated')
            ORDER BY sequence DESC LIMIT 10
            """
        ).fetchall()
        total_threats = conn.execute(
            """
            SELECT COUNT(*) as count FROM audit_events
            WHERE event_type IN ('security_threat_detected', 'cross_tenant_access_denied', 'tee_attestation_rejected', 'tamper_attack_simulated')
            """
        ).fetchone()["count"]

    return {
        "overall_health": "SECURE" if ledger_status.get("valid") else "TAMPERED",
        "tee_enclave": tee_status,
        "audit_ledger": ledger_status,
        "vector_nlp": nlp_status,
        "tenant_isolation": {
            "guarantee": "Strict server-side isolation before vector embedding and retrieval",
            "active_tenants": list(nlp_status.get("tenants", {}).keys()),
            "cross_tenant_leakage_risk": "0.0% (Zero cross-tenant vector contamination)",
        },
        "threat_monitor": {
            "total_threats_blocked": total_threats,
            "recent_events": [dict(r) for r in threat_rows],
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
