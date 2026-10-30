"""Tenant isolation and access control (spec §11: Tenant isolation)."""


def test_employee_gets_grounded_answer_with_citation(two):
    r = two.ask(two.ea, two.a, "What is the refund window for customers?")
    assert r["outcome"] == "grounded"
    c = r["citations"][0]
    assert "30 days" in r["answer"] and c["version_no"] == 1 and c["title"] and c["section"] == "Alpha Refunds"
    assert c["document_id"] == two.da["document_id"]


def test_cross_tenant_query_never_returns_other_tenant_content(two):
    r = two.ask(two.ea, two.a, "What is the Beta confidential project codename?")
    assert r["outcome"] == "insufficient_evidence" and r["citations"] == []
    assert "Redwood" not in str(r)


def test_cannot_use_other_tenant_context(two):
    # Alpha employee names Beta's tenant id in the path: uniform 404, not 403, and nothing leaks.
    assert two.c.post(f"/tenants/{two.b}/chat", json={"question": "codename"}, headers=two.ea).status_code == 404
    assert two.c.get(f"/tenants/{two.b}/documents", headers=two.ea).status_code == 404


def test_document_and_citation_endpoints_enforce_same_policy(two):
    beta_doc = two.db["document_id"]
    for url in (f"/tenants/{two.a}/documents/{beta_doc}",):
        assert two.c.get(url, headers=two.ea).status_code == 404
    chunk = two.ask(two.eb, two.b, "Beta confidential project codename")["citations"][0]["chunk_id"]
    assert two.c.get(f"/tenants/{two.a}/citations/{chunk}", headers=two.ea).status_code == 404
    assert two.c.get(f"/tenants/{two.a}/citations/{chunk}", headers=two.ha).status_code == 404
    assert two.c.get(f"/tenants/{two.b}/citations/{chunk}", headers=two.eb).status_code == 200


def test_unknown_and_forbidden_documents_are_indistinguishable(two):
    a = two.c.get(f"/tenants/{two.a}/documents/{two.db['document_id']}", headers=two.ea)
    b = two.c.get(f"/tenants/{two.a}/documents/doc_doesnotexist", headers=two.ea)
    assert (a.status_code, a.json()) == (b.status_code, b.json())


def test_employee_cannot_administer(two):
    f = {"file": ("x.txt", b"hello world")}
    assert two.c.post(f"/tenants/{two.a}/documents", files=f, headers=two.ea).status_code == 404
    assert two.c.get(f"/tenants/{two.a}/members", headers=two.ea).status_code == 404
    assert two.c.get(f"/tenants/{two.a}/audit", headers=two.ea).status_code == 404
    assert two.c.post("/admin/tenants", json={"name": "Evil"}, headers=two.ea).status_code == 403


def test_client_admin_cannot_touch_other_tenant(two):
    f = {"file": ("x.txt", b"hello world")}
    assert two.c.post(f"/tenants/{two.b}/documents", files=f, headers=two.ha).status_code == 404
    assert two.c.post(f"/tenants/{two.a}/documents/{two.db['document_id']}/versions", files=f, headers=two.ha).status_code == 404
    assert two.c.get(f"/tenants/{two.b}/audit", headers=two.ha).status_code == 404


def test_sysadmin_has_no_implicit_document_access(two):
    assert two.c.post(f"/tenants/{two.a}/chat", json={"question": "refund"}, headers=two.root).status_code == 404
    assert two.c.get(f"/tenants/{two.a}/documents", headers=two.root).status_code == 404


def test_no_token_or_bad_token_denied(two):
    assert two.c.get(f"/tenants/{two.a}/documents").status_code == 401
    assert two.c.get(f"/tenants/{two.a}/documents", headers={"Authorization": "Bearer x.y"}).status_code == 401
    tok = two.ea["Authorization"][7:]
    tampered = tok[:-2] + ("aa" if not tok.endswith("aa") else "bb")
    assert two.c.get("/auth/me", headers={"Authorization": f"Bearer {tampered}"}).status_code == 401


def test_conversations_are_private_to_their_user(two):
    cid = two.ask(two.ea, two.a, "refund window")["conversation_id"]
    two.w = two
    two.user("emp2@alpha.test", two.a)
    other = two.login("emp2@alpha.test")
    assert two.c.get(f"/tenants/{two.a}/conversations/{cid}", headers=other).status_code == 404
    assert two.c.post(f"/tenants/{two.a}/chat", json={"question": "x y", "conversation_id": cid}, headers=other).status_code == 404
    assert two.c.get(f"/tenants/{two.a}/conversations/{cid}", headers=two.ea).status_code == 200


def test_offboarding_revokes_access_immediately(two):
    me = two.c.get("/auth/me", headers=two.ea).json()
    assert two.c.post(f"/admin/users/{me['id']}/offboard", headers=two.root).status_code == 200
    assert two.c.get("/auth/me", headers=two.ea).status_code == 401
    assert two.c.post("/auth/login", json={"email": "emp@alpha.test", "password": "Test-Password-123"}).status_code == 401


def test_removed_member_loses_tenant_access_but_keeps_session(two):
    uid = two.c.get("/auth/me", headers=two.ea).json()["id"]
    assert two.c.delete(f"/tenants/{two.a}/members/{uid}", headers=two.ha).status_code == 200
    assert two.c.post(f"/tenants/{two.a}/chat", json={"question": "refund"}, headers=two.ea).status_code == 404


def test_suspended_tenant_fails_closed(two):
    two.c.patch(f"/admin/tenants/{two.a}", json={"status": "suspended"}, headers=two.root)
    assert two.c.post(f"/tenants/{two.a}/chat", json={"question": "refund"}, headers=two.ea).status_code == 404


def test_login_lockout_and_no_user_enumeration(two):
    r1 = two.c.post("/auth/login", json={"email": "nobody@x.test", "password": "wrong-password-1"})
    r2 = two.c.post("/auth/login", json={"email": "emp@alpha.test", "password": "wrong-password-1"})
    assert r1.status_code == r2.status_code == 401 and r1.json() == r2.json()
    for _ in range(6):
        two.c.post("/auth/login", json={"email": "emp@alpha.test", "password": "wrong-password-1"})
    assert two.c.post("/auth/login", json={"email": "emp@alpha.test", "password": "Test-Password-123"}).status_code == 429


def test_denials_are_audited(two):
    two.c.get(f"/tenants/{two.b}/documents", headers=two.ea)
    events = two.c.get("/admin/audit", headers=two.root).json()
    assert any(e["action"] == "access.denied" for e in events)
