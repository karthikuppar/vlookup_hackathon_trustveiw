import io, sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.__main__ import bootstrap  # noqa: E402

PW = "Test-Password-123"


class World:
    def __init__(self, tmp_path):
        self.settings = Settings(data_dir=tmp_path / "data", secret=b"test-secret-test-secret", pbkdf2_iterations=1000, checkpoint_every=3)
        bootstrap(self.settings, "root@p.test", PW)
        self.app = create_app(self.settings)
        self.c = TestClient(self.app)
        self.root = self.login("root@p.test")
        self.t = {}

    def login(self, email, password=PW):
        r = self.c.post("/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['token']}"}

    def tenant(self, name):
        tid = self.c.post("/admin/tenants", json={"name": name}, headers=self.root).json()["id"]
        self.t[name] = tid
        return tid

    def user(self, email, tid, role="employee"):
        r = self.c.post("/admin/users", json={"email": email, "name": email, "password": PW, "tenant_id": tid, "role": role}, headers=self.root)
        assert r.status_code == 201, r.text
        return r.json()["id"]

    def upload(self, hdr, tid, name, data, title=None, expect=201):
        files = {"file": (name, io.BytesIO(data if isinstance(data, bytes) else data.encode()))}
        r = self.c.post(f"/tenants/{tid}/documents", files=files, data={"title": title} if title else None, headers=hdr)
        assert r.status_code == expect, r.text
        return r.json()

    def version(self, hdr, tid, did, name, data, expect=201):
        r = self.c.post(f"/tenants/{tid}/documents/{did}/versions", files={"file": (name, io.BytesIO(data.encode()))}, headers=hdr)
        assert r.status_code == expect, r.text
        return r.json()

    def ask(self, hdr, tid, q, expect=200, **kw):
        r = self.c.post(f"/tenants/{tid}/chat", json={"question": q, **kw}, headers=hdr)
        assert r.status_code == expect, r.text
        return r.json()


@pytest.fixture
def w(tmp_path):
    return World(tmp_path)


@pytest.fixture
def two(w):
    """Two tenants, each with an admin and an employee, and one distinct document each."""
    a, b = w.tenant("Alpha"), w.tenant("Beta")
    w.user("admin@alpha.test", a, "client_admin"); w.user("emp@alpha.test", a)
    w.user("admin@beta.test", b, "client_admin"); w.user("emp@beta.test", b)
    w.ha, w.ea = w.login("admin@alpha.test"), w.login("emp@alpha.test")
    w.hb, w.eb = w.login("admin@beta.test"), w.login("emp@beta.test")
    w.a, w.b = a, b
    w.da = w.upload(w.ha, a, "alpha.md", "# Alpha Refunds\n\nAlpha customers may request a refund within 30 days of purchase.\n\n# Alpha Codename\n\nThe Alpha secret project codename is Bluebird.\n")
    w.db = w.upload(w.hb, b, "beta.md", "# Beta Hours\n\nBeta support desk is open from 9am to 6pm on business days.\n\n# Beta Codename\n\nThe Beta confidential project codename is Redwood.\n")
    return w
