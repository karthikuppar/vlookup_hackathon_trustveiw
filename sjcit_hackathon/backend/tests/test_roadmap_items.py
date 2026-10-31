"""Unit tests verifying Roadmap items:
- 1.1 Tenant-scoped admin metrics (/api/admin/nlp-stats, /api/graph/stats, /api/admin/interaction-metrics)
- 1.4 Strict password policy (length >= 12, common password blacklist, email rejection)
"""
import unittest
from fastapi.testclient import TestClient

from main import app, init_db, seed_demo_data
from auth_security import validate_password_policy

class TestRoadmapItems(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        seed_demo_data()
        cls.client = TestClient(app)

        # Login Alice Admin (Tenant A)
        res_a = cls.client.post("/api/auth/login", json={"email": "admin@acrocorp.com", "password": "Password123!"})
        cls.token_a = res_a.json()["access_token"]
        cls.headers_a = {"Authorization": f"Bearer {cls.token_a}"}

        # Login System SuperAdmin (System global)
        res_sys = cls.client.post("/api/auth/login", json={"email": "sysadmin@ps04platform.com", "password": "Password123!"})
        cls.token_sys = res_sys.json()["access_token"]
        cls.headers_sys = {"Authorization": f"Bearer {cls.token_sys}"}

    # -------------------------------------------------------------------------
    # ROADMAP 1.1: Tenant-Scoped Admin Metrics
    # -------------------------------------------------------------------------
    def test_01_tenant_scoped_nlp_stats(self):
        # Client Admin A should get tenant-scoped numbers
        res = self.client.get("/api/admin/nlp-stats", headers=self.headers_a)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("is_tenant_scoped"))
        self.assertEqual(data.get("scoped_tenant_id"), "tenant_a")

        # System SuperAdmin gets global metrics
        res_sys = self.client.get("/api/admin/nlp-stats", headers=self.headers_sys)
        self.assertEqual(res_sys.status_code, 200)
        data_sys = res_sys.json()
        self.assertFalse(data_sys.get("is_tenant_scoped", False))

    def test_02_tenant_scoped_graph_stats(self):
        # Client Admin A
        res = self.client.get("/api/graph/stats", headers=self.headers_a)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("scoped_tenant_id"), "tenant_a")

        # System SuperAdmin
        res_sys = self.client.get("/api/graph/stats", headers=self.headers_sys)
        self.assertEqual(res_sys.status_code, 200)
        data_sys = res_sys.json()
        self.assertIsNone(data_sys.get("scoped_tenant_id"))

    def test_03_tenant_scoped_interaction_metrics(self):
        # Client Admin A
        res = self.client.get("/api/admin/interaction-metrics", headers=self.headers_a)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("scoped_tenant_id"), "tenant_a")

        # System SuperAdmin
        res_sys = self.client.get("/api/admin/interaction-metrics", headers=self.headers_sys)
        self.assertEqual(res_sys.status_code, 200)
        data_sys = res_sys.json()
        self.assertIsNone(data_sys.get("scoped_tenant_id"))

    # -------------------------------------------------------------------------
    # ROADMAP 1.4: Password Policy
    # -------------------------------------------------------------------------
    def test_04_password_policy_short_rejected(self):
        with self.assertRaises(ValueError):
            validate_password_policy("short", email="user@acrocorp.com")
        with self.assertRaises(ValueError):
            validate_password_policy("only11chars", email="user@acrocorp.com")

    def test_05_password_policy_common_rejected(self):
        with self.assertRaises(ValueError):
            validate_password_policy("password12345", email="user@acrocorp.com")
        with self.assertRaises(ValueError):
            validate_password_policy("123456789012", email="user@acrocorp.com")

    def test_06_password_policy_email_match_rejected(self):
        with self.assertRaises(ValueError):
            validate_password_policy("alice@acrocorp.com", email="alice@acrocorp.com")
        with self.assertRaises(ValueError):
            validate_password_policy("myalicepassword", email="alice@acrocorp.com")

    def test_07_password_policy_strong_accepted(self):
        try:
            validate_password_policy("CorrectHorseBatteryStaple!", email="charlie@acrocorp.com")
        except ValueError:
            self.fail("Strong password was unexpectedly rejected!")

    # -------------------------------------------------------------------------
    # ROADMAP 1.2: Token Lifecycle & Revocation
    # -------------------------------------------------------------------------
    def test_08_token_logout_revocation(self):
        # Create a fresh login token
        res_login = self.client.post("/api/auth/login", json={"email": "employee@acrocorp.com", "password": "Password123!"})
        self.assertEqual(res_login.status_code, 200)
        emp_token = res_login.json()["access_token"]
        emp_headers = {"Authorization": f"Bearer {emp_token}"}

        # Token works initially
        res_me = self.client.get("/api/auth/me", headers=emp_headers)
        self.assertEqual(res_me.status_code, 200)

        # Logout
        res_logout = self.client.post("/api/auth/logout", headers=emp_headers)
        self.assertEqual(res_logout.status_code, 200)

        # Next request with this token must be rejected (401)
        res_after = self.client.get("/api/auth/me", headers=emp_headers)
        self.assertEqual(res_after.status_code, 401)
        self.assertIn("revoked", res_after.json()["detail"].lower())

    def test_09_logout_all_sessions(self):
        # Login and obtain token
        res_login = self.client.post("/api/auth/login", json={"email": "employee@betashield.com", "password": "Password123!"})
        self.assertEqual(res_login.status_code, 200)
        tok = res_login.json()["access_token"]
        headers = {"Authorization": f"Bearer {tok}"}

        # Verify works
        self.assertEqual(self.client.get("/api/auth/me", headers=headers).status_code, 200)

        # Invalidate all sessions
        res_rev = self.client.post("/api/auth/logout-all", headers=headers)
        self.assertEqual(res_rev.status_code, 200)

        # Prior token is immediately rejected
        res_after = self.client.get("/api/auth/me", headers=headers)
        self.assertEqual(res_after.status_code, 401)

    def test_10_change_password_revokes_tokens(self):
        # Add a temporary test user
        import uuid
        uid = uuid.uuid4().hex[:6]
        test_email = f"temptest_{uid}@acrocorp.com"
        new_pwd = "InitPassw0rd1234!"
        add_res = self.client.post(
            "/api/clients/tenant_a/members",
            headers=self.headers_a,
            json={"name": "Temp Test", "email": test_email, "password": new_pwd, "role": "client_employee"},
        )
        self.assertEqual(add_res.status_code, 201)

        # Login as temp user
        log_res = self.client.post("/api/auth/login", json={"email": test_email, "password": new_pwd})
        old_token = log_res.json()["access_token"]
        temp_headers = {"Authorization": f"Bearer {old_token}"}

        # Change password
        changed_pwd = "BrandNewSuperSecurePass2026!"
        chg_res = self.client.post(
            "/api/auth/change-password",
            headers=temp_headers,
            json={"old_password": new_pwd, "new_password": changed_pwd},
        )
        self.assertEqual(chg_res.status_code, 200)
        new_token = chg_res.json()["access_token"]

        # Old token is now invalid
        self.assertEqual(self.client.get("/api/auth/me", headers=temp_headers).status_code, 401)

        # New token works
        me_res = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {new_token}"})
        self.assertEqual(me_res.status_code, 200)

    # -------------------------------------------------------------------------
    # ROADMAP 1.3: User Management (Add, Disable, Remove, Reset Password)
    # -------------------------------------------------------------------------
    def test_11_user_removal_invalidates_token_immediately(self):
        # 1. Add user
        import uuid
        test_email = f"deleteme_{uuid.uuid4().hex[:6]}@acrocorp.com"
        pwd = "TestUserPass1234!"
        add_res = self.client.post(
            "/api/clients/tenant_a/members",
            headers=self.headers_a,
            json={"name": "Delete Me", "email": test_email, "password": pwd, "role": "client_employee"},
        )
        self.assertEqual(add_res.status_code, 201)
        user_id = add_res.json()["id"]

        # 2. Login as user and get token
        login_res = self.client.post("/api/auth/login", json={"email": test_email, "password": pwd})
        del_user_tok = login_res.json()["access_token"]
        del_headers = {"Authorization": f"Bearer {del_user_tok}"}
        self.assertEqual(self.client.get("/api/auth/me", headers=del_headers).status_code, 200)

        # 3. Admin removes user
        del_res = self.client.delete(f"/api/clients/tenant_a/members/{user_id}", headers=self.headers_a)
        self.assertEqual(del_res.status_code, 200)

        # 4. User's token is immediately invalid (Roadmap 1.2 "Done when: Removing a user invalidates their token immediately")
        res_after = self.client.get("/api/auth/me", headers=del_headers)
        self.assertEqual(res_after.status_code, 401)

    def test_12_user_disable_invalidates_token(self):
        # 1. Add user
        import uuid
        test_email = f"disableme_{uuid.uuid4().hex[:6]}@acrocorp.com"
        pwd = "DisableTestPass1234!"
        add_res = self.client.post(
            "/api/clients/tenant_a/members",
            headers=self.headers_a,
            json={"name": "Disable Me", "email": test_email, "password": pwd, "role": "client_employee"},
        )
        self.assertEqual(add_res.status_code, 201)
        user_id = add_res.json()["id"]

        # 2. Login
        login_res = self.client.post("/api/auth/login", json={"email": test_email, "password": pwd})
        tok = login_res.json()["access_token"]
        user_headers = {"Authorization": f"Bearer {tok}"}
        self.assertEqual(self.client.get("/api/auth/me", headers=user_headers).status_code, 200)

        # 3. Admin deactivates account
        patch_res = self.client.patch(
            f"/api/clients/tenant_a/members/{user_id}",
            headers=self.headers_a,
            json={"is_active": False},
        )
        self.assertEqual(patch_res.status_code, 200)
        self.assertEqual(patch_res.json()["member"]["is_active"], 0)

        # 4. Token immediately invalid
        res_after = self.client.get("/api/auth/me", headers=user_headers)
        self.assertEqual(res_after.status_code, 401)
        self.assertIn("deactivated", res_after.json()["detail"].lower())

    def test_13_admin_reset_member_password(self):
        # 1. Add user
        import uuid
        test_email = f"resetme_{uuid.uuid4().hex[:6]}@acrocorp.com"
        init_pwd = "InitialSetupPass1234!"
        add_res = self.client.post(
            "/api/clients/tenant_a/members",
            headers=self.headers_a,
            json={"name": "Reset Me", "email": test_email, "password": init_pwd, "role": "client_employee"},
        )
        self.assertEqual(add_res.status_code, 201)
        user_id = add_res.json()["id"]

        # 2. Admin resets password
        reset_pwd = "AdminIssuedTempPass1234!"
        res_rst = self.client.post(
            f"/api/clients/tenant_a/members/{user_id}/reset-password",
            headers=self.headers_a,
            json={"new_password": reset_pwd},
        )
        self.assertEqual(res_rst.status_code, 200)

        # 3. Old password fails
        fail_login = self.client.post("/api/auth/login", json={"email": test_email, "password": init_pwd})
        self.assertEqual(fail_login.status_code, 401)

        # 4. New password succeeds
        succ_login = self.client.post("/api/auth/login", json={"email": test_email, "password": reset_pwd})
        self.assertEqual(succ_login.status_code, 200)




if __name__ == "__main__":
    unittest.main()

