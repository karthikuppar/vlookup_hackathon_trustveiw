"""TrustView API: tenant-bound authentication and secured operations routes."""
from __future__ import annotations
import os, re, sqlite3, uuid
from contextlib import contextmanager
from pathlib import Path
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, Field
from auth_security import create_access_token, decode_access_token, hash_password, verify_password
from vico import VicoStore, create_router

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
VALID_ROLES = {"employee", "manager", "admin", "hod"}
TENANT = re.compile(r"T\d{4}")

class UserStore:
    def __init__(self, path=None):
        self.path = path or os.getenv("TRUSTVIEW_AUTH_DB", str(Path(__file__).with_name("trustview_auth.sqlite3")))
        with self.connection() as c: c.execute("CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY,name TEXT NOT NULL,email TEXT NOT NULL UNIQUE,password_hash TEXT NOT NULL,role TEXT NOT NULL,tenant_id TEXT NOT NULL)")
    @contextmanager
    def connection(self):
        c = sqlite3.connect(self.path); c.row_factory = sqlite3.Row
        try: yield c; c.commit()
        finally: c.close()
    def by_email(self, email):
        with self.connection() as c: row = c.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        return dict(row) if row else None
    def by_id(self, ident):
        with self.connection() as c: row = c.execute("SELECT * FROM users WHERE id=?", (ident,)).fetchone()
        return dict(row) if row else None
    def create(self, name, email, password, role, tenant_id):
        user = {"id": f"usr_{uuid.uuid4().hex}", "name": name.strip(), "email": email, "password_hash": hash_password(password), "role": role, "tenant_id": tenant_id}
        with self.connection() as c: c.execute("INSERT INTO users VALUES (:id,:name,:email,:password_hash,:role,:tenant_id)", user)
        return user

class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120); email: EmailStr; password: str = Field(min_length=10, max_length=72); role: str = "employee"; tenant_id: str
class LoginRequest(BaseModel):
    email: EmailStr; password: str

def role(value):
    value = value.lower().strip()
    if value not in VALID_ROLES: raise HTTPException(422, "role must be employee, manager, admin, or hod")
    return value
def tenant(value):
    value = value.upper().strip()
    if not TENANT.fullmatch(value): raise HTTPException(422, "tenant_id must use the form T1234")
    return value
def public(user): return {k: user[k] for k in ("id", "name", "email", "role", "tenant_id")}
def session(user):
    token = create_access_token({"user_id": user["id"], "role": user["role"], "tenant_id": user["tenant_id"]})
    return {"access_token": token, "token": token, "user": public(user), "role": user["role"], "tenant_id": user["tenant_id"]}

users = UserStore()
app = FastAPI(title="TrustView", version="1.0.0", description="Tenant-isolated knowledge and case operations.")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("TRUSTVIEW_CORS_ORIGINS", "http://localhost:5173").split(","), allow_credentials=False, allow_methods=["*"], allow_headers=["*"])
@app.get("/health")
async def health(): return {"status": "ok", "service": "TrustView"}
@app.post("/auth/register", status_code=201)
async def register(request: RegisterRequest):
    email = str(request.email).lower()
    if users.by_email(email): raise HTTPException(409, "An account with this email already exists")
    user = users.create(request.name, email, request.password, role(request.role), tenant(request.tenant_id))
    return {"success": True, "message": "Account created", "data": session(user)}
@app.post("/auth/login")
async def login(request: LoginRequest):
    user = users.by_email(str(request.email).lower())
    if not user or not verify_password(request.password, user["password_hash"]): raise HTTPException(401, "Invalid email or password")
    return {"success": True, "message": "Authenticated", "data": session(user)}
async def current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if not payload or not payload.get("user_id"): raise HTTPException(401, "Invalid or expired access token")
    user = users.by_id(payload["user_id"])
    if not user: raise HTTPException(401, "User no longer exists")
    return public(user)
@app.get("/auth/me")
async def me(user: dict = Depends(current_user)): return {"success": True, "data": user}

audit_key = os.getenv("VICO_AUDIT_HMAC_KEY")
if audit_key: app.include_router(create_router(VicoStore(audit_key=audit_key)))
else:
    @app.get("/vico/health", status_code=503)
    async def vico_unavailable(): return {"detail": "TrustView operations are unavailable: VICO_AUDIT_HMAC_KEY is not configured"}
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
