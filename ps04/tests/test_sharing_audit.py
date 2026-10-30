"""Knowledge-base sharing, audit ledger, TEE honesty, offline operation."""
import json, sqlite3, socket

import pytest

from app.audit import Ledger
from app.db import connect


# --------------------------------------------------------------------- sharing
def share(two, **kw):
    r = two.c.post(f"/tenants/{two.b}/shares", json={"grantee_tenant_id": two.a, "document_id": two.db["document_id"], **kw}, headers=two.hb)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_no_access_without_grant_then_access_with_grant(two):
    q = "Beta support desk open hours"
    assert two.ask(two.ea, two.a, q)["outcome"] == "insufficient_evidence"
    share(two)
    r = two.ask(two.ea, two.a, q)
    assert r["outcome"] == "grounded" and r["citations"][0]["shared_from"] == "Beta"


def test_grant_is_scoped_to_the_named_document(two):
    share(two)
    assert two.ask(two.ea, two.a, "Beta support desk open hours")["outcome"] == "grounded"
    other = two.upload(two.hb, two.b, "beta2.md", "# Beta Finance\n\nBeta quarterly budget is approved by the board.\n")
    assert two.ask(two.ea, two.a, "Beta quarterly budget approved")["outcome"] == "insufficient_evidence"


def test_whole_kb_grant_covers_future_documents(two):
    r = two.c.post(f"/tenants/{two.b}/shares", json={"grantee_tenant_id": two.a}, headers=two.hb)
    assert r.status_code == 201
    two.upload(two.hb, two.b, "beta3.md", "# Beta Travel\n\nBeta travel must be booked fourteen days ahead.\n")
    assert two.ask(two.ea, two.a, "Beta travel booked ahead")["outcome"] == "grounded"


def test_revocation_blocks_retrieval_and_source_access_immediately(two):
    sid = share(two)
    r = two.ask(two.ea, two.a, "Beta support desk open hours")
    chunk, doc = r["citations"][0]["chunk_id"], two.db["document_id"]
    assert two.c.get(f"/tenants/{two.a}/citations/{chunk}", headers=two.ea).status_code == 200
    assert two.c.get(f"/tenants/{two.a}/documents/{doc}", headers=two.ea).status_code == 200
    assert two.c.delete(f"/tenants/{two.b}/shares/{sid}", headers=two.hb).status_code == 200
    assert two.ask(two.ea, two.a, "Beta support desk open hours")["outcome"] == "insufficient_evidence"
    assert two.c.get(f"/tenants/{two.a}/citations/{chunk}", headers=two.ea).status_code == 404
    assert two.c.get(f"/tenants/{two.a}/documents/{doc}", headers=two.ea).status_code == 404
    assert two.c.get(f"/tenants/{two.a}/documents/{doc}", headers=two.ha).status_code == 404


def test_expired_grant_is_ignored(two):
    two.c.post(f"/tenants/{two.b}/shares", json={"grantee_tenant_id": two.a, "expires_at": "2999-01-01T00:00:00"}, headers=two.hb)
    conn = connect(two.settings.data_dir / "ps04.sqlite3")
    conn.execute("UPDATE shares SET expires_at='2000-01-01T00:00:00'")
    assert two.ask(two.ea, two.a, "Beta support desk open hours")["outcome"] == "insufficient_evidence"


def test_sharing_is_one_directional(two):
    share(two)
    assert two.ask(two.eb, two.b, "Alpha secret project codename Bluebird")["outcome"] == "insufficient_evidence"


def test_only_owner_admin_can_grant_or_revoke(two):
    body = {"grantee_tenant_id": two.b, "document_id": two.da["document_id"]}
    assert two.c.post(f"/tenants/{two.a}/shares", json=body, headers=two.ea).status_code == 404
    assert two.c.post(f"/tenants/{two.a}/shares", json=body, headers=two.hb).status_code == 404
    assert two.c.post(f"/tenants/{two.b}/shares", json={**body, "grantee_tenant_id": two.a}, headers=two.hb).status_code == 404  # not Beta's document
    sid = share(two)
    assert two.c.delete(f"/tenants/{two.b}/shares/{sid}", headers=two.ha).status_code == 404


def test_share_history_and_usage_are_audited_for_both_sides(two):
    sid = share(two)
    two.ask(two.ea, two.a, "Beta support desk open hours")
    two.c.delete(f"/tenants/{two.b}/shares/{sid}", headers=two.hb)
    owner = [e["action"] for e in two.c.get(f"/tenants/{two.b}/audit", headers=two.hb).json()]
    grantee = [e["action"] for e in two.c.get(f"/tenants/{two.a}/audit", headers=two.ha).json()]
    assert {"share.grant", "share.revoke", "share.used"} <= set(owner)
    assert {"share.grant", "share.revoke"} <= set(grantee)


def test_suspended_owner_stops_sharing(two):
    share(two)
    two.c.patch(f"/admin/tenants/{two.b}", json={"status": "suspended"}, headers=two.root)
    assert two.ask(two.ea, two.a, "Beta support desk open hours")["outcome"] == "insufficient_evidence"


# ---------------------------------------------------------------- audit ledger
def test_audit_covers_required_events(two):
    two.ask(two.ea, two.a, "refund window")
    actions = {e["action"] for e in two.c.get("/admin/audit?limit=500", headers=two.root).json()}
    assert {"auth.login", "tenant.create", "user.create", "document.upload", "document.activate", "chat.query"} <= actions


def test_ledger_never_stores_question_text_or_document_text(two):
    two.ask(two.ea, two.a, "What is the Alpha secret project codename Bluebird?")
    dump = json.dumps(two.c.get("/admin/audit?limit=1000", headers=two.root).json())
    assert "Bluebird" not in dump and "What is the Alpha" not in dump
    assert "question_sha256" in dump


def test_clean_ledger_verifies(two):
    two.ask(two.ea, two.a, "refund window")
    r = two.c.get("/audit/verify", headers=two.root).json()
    assert r["ok"] is True and r["events"] > 10
    assert two.c.get("/audit/verify", headers=two.ha).json() == {"ok": True}
    assert two.c.get("/audit/verify", headers=two.ea).status_code == 403


@pytest.fixture
def db(two):
    return connect(two.settings.data_dir / "ps04.sqlite3")


def verify(two):
    return two.c.get("/audit/verify", headers=two.root).json()


def test_detects_modified_event(two, db):
    db.execute("UPDATE audit_events SET details='{\"outcome\":\"forged\"}' WHERE seq=5")
    r = verify(two)
    assert r["ok"] is False and r["broken_at"] == 5 and r["reason"] == "hash_mismatch"


def test_detects_deleted_middle_event(two, db):
    db.execute("DELETE FROM audit_events WHERE seq=6")
    r = verify(two)
    assert r["ok"] is False and r["broken_at"] == 6


def test_detects_reordered_events(two, db):
    db.execute("UPDATE audit_events SET seq=-1 WHERE seq=4")
    db.execute("UPDATE audit_events SET seq=4 WHERE seq=5")
    db.execute("UPDATE audit_events SET seq=5 WHERE seq=-1")
    assert verify(two)["ok"] is False


def test_detects_tail_truncation_via_checkpoint(two, db):
    two.c.post("/audit/checkpoint", headers=two.root)
    head = db.execute("SELECT MAX(seq) FROM audit_events").fetchone()[0]
    db.execute("DELETE FROM audit_events WHERE seq>?", (head - 3,))
    r = verify(two)
    assert r["ok"] is False and r["reason"] == "truncated_after_checkpoint"


def test_detects_full_rehash_rewrite_via_checkpoint(two, db):
    """An attacker who rewrites an event and recomputes the whole chain is still caught by the signed checkpoint."""
    from app.audit import canonical, event_hash, GENESIS
    two.c.post("/audit/checkpoint", headers=two.root)
    rows = db.execute("SELECT * FROM audit_events ORDER BY seq").fetchall()
    prev = GENESIS
    for r in rows:
        det = '{"forged":true}' if r["seq"] == 2 else r["details"]
        h = event_hash(prev, canonical(r["seq"], r["ts"], r["tenant_id"], r["counterparty_tenant_id"], r["actor"], r["action"], json.loads(det)))
        db.execute("UPDATE audit_events SET details=?, prev_hash=?, hash=? WHERE seq=?", (det, prev, h, r["seq"]))
        prev = h
    r = verify(two)
    assert r["ok"] is False and r["reason"] == "checkpoint_hash_mismatch"


def test_forged_checkpoint_rejected(two):
    two.c.post("/audit/checkpoint", headers=two.root)
    p = two.settings.data_dir / "audit_checkpoints.jsonl"
    lines = [json.loads(l) for l in p.read_text().splitlines()]
    lines[-1]["hash"] = "f" * 64
    p.write_text("\n".join(json.dumps(l) for l in lines) + "\n")
    assert verify(two)["reason"] == "checkpoint_signature_invalid"


def test_ledger_event_is_atomic_with_action(two):
    """A failed action must leave neither the change nor its audit record."""
    before = two.c.get("/admin/audit?limit=1", headers=two.root).json()[0]["seq"]
    assert two.c.post("/admin/tenants", json={"name": "Alpha"}, headers=two.root).status_code == 409
    assert two.c.get("/admin/audit?limit=1", headers=two.root).json()[0]["seq"] == before
    assert verify(two)["ok"] is True


# ----------------------------------------------------------- TEE + offline
def test_security_status_is_honest_about_tee(two):
    s = two.c.get("/security/status", headers=two.ea).json()
    assert s["tee"]["mode"] == "simulated" and s["tee"]["hardware_backed"] is False and s["tee"]["enabled"] is False


def test_simulated_key_release_requires_matching_measurement(two):
    tee = two.app.state.tee
    rep = tee.attest()
    assert tee.release_key("x", rep, tee.measurement()) is not None
    assert tee.release_key("x", rep, "0" * 64) is None
    assert tee.release_key("x", {**rep, "measurement": "0" * 64}, tee.measurement()) is None


def test_full_flow_works_with_network_blocked(two, monkeypatch):
    real_connect = socket.socket.connect

    def blocked(*a, **k):
        raise AssertionError("outbound network access attempted")

    def loopback_only(self, addr, *a, **k):  # asyncio on Windows needs a loopback socketpair
        if isinstance(addr, tuple) and addr[0] in ("127.0.0.1", "::1"):
            return real_connect(self, addr, *a, **k)
        blocked()
    monkeypatch.setattr(socket.socket, "connect", loopback_only)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)
    two.upload(two.ha, two.a, "offline.md", "# Offline\n\nThe offline check passes without any network access.\n")
    assert two.ask(two.ea, two.a, "offline check network access")["outcome"] == "grounded"
    assert verify(two)["ok"] is True
