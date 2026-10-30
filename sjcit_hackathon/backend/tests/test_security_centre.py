"""
Automated Test Suite for PS-04 Security Testing, Vulnerability Assessment & Automated Remediation Centre.

Uses Python standard unittest framework to execute without external dependencies.
Tests all security endpoints, scan triggers, finding models, automated remediations, verification, and rollback.
"""
from __future__ import annotations

import unittest
from fastapi.testclient import TestClient

from main import app, init_db, seed_demo_data
from security.config import SECURITY_CATEGORIES


class TestSecurityCentre(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        seed_demo_data()
        cls.client = TestClient(app)

    def _login(self, email: str, password: str = "Password123!") -> str:
        res = self.client.post("/api/auth/login", json={"email": email, "password": password})
        self.assertEqual(res.status_code, 200, f"Login failed for {email}: {res.text}")
        return res.json()["access_token"]

    def test_01_security_categories_accessible_to_admin(self):
        admin_token = self._login("admin@acrocorp.com")
        res = self.client.get(
            "/api/admin/security/categories",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(res.status_code, 200)
        categories = res.json()
        self.assertEqual(len(categories), 20)
        keys = [c["key"] for c in categories]
        self.assertIn("prompt_injection", keys)
        self.assertIn("sql_injection", keys)
        self.assertIn("tenant_isolation", keys)
        self.assertIn("secrets_exposure", keys)

    def test_02_security_categories_forbidden_to_employee(self):
        employee_token = self._login("employee@acrocorp.com")
        res = self.client.get(
            "/api/admin/security/categories",
            headers={"Authorization": f"Bearer {employee_token}"},
        )
        self.assertEqual(res.status_code, 403)

    def test_03_trigger_targeted_security_scan(self):
        admin_token = self._login("admin@acrocorp.com")
        # Run scan for 4 fast categories: security_config, audit_integrity, cryptographic_config, rate_limiting
        target_scope = ["security_config", "audit_integrity", "cryptographic_config", "rate_limiting"]
        res = self.client.post(
            "/api/admin/security/scans",
            json={"scope": target_scope},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertIn("id", data)
        self.assertEqual(data["status"], "COMPLETED")
        self.assertEqual(data["total_tests"], 4)
        self.assertEqual(data["scope"], "TARGETED_SCAN")
        self.assertIn("duration_seconds", data)

    def test_04_list_scans_and_get_details(self):
        admin_token = self._login("admin@acrocorp.com")
        # List scans
        res = self.client.get(
            "/api/admin/security/scans",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(res.status_code, 200)
        scans = res.json()
        self.assertGreater(len(scans), 0)
        latest_scan_id = scans[0]["id"]

        # Get details
        res_detail = self.client.get(
            f"/api/admin/security/scans/{latest_scan_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(res_detail.status_code, 200)
        scan_detail = res_detail.json()
        self.assertEqual(scan_detail["id"], latest_scan_id)
        self.assertIn("findings", scan_detail)
        self.assertIn("execution_log", scan_detail)

    def test_05_list_and_inspect_findings(self):
        admin_token = self._login("admin@acrocorp.com")
        res = self.client.get(
            "/api/admin/security/findings",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(res.status_code, 200)
        findings = res.json()
        self.assertIsInstance(findings, list)

        if len(findings) > 0:
            first = findings[0]
            self.assertIn("id", first)
            self.assertIn("title", first)
            self.assertIn("severity", first)
            self.assertIn("root_cause", first)
            self.assertIn("status", first)

            # Detail endpoint
            res_single = self.client.get(
                f"/api/admin/security/findings/{first['id']}",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            self.assertEqual(res_single.status_code, 200)
            self.assertEqual(res_single.json()["id"], first["id"])

    def test_06_remediation_lifecycle_apply_verify_rollback(self):
        admin_token = self._login("admin@acrocorp.com")
        res = self.client.post(
            "/api/admin/security/scans",
            json={"scope": ["security_config", "dependencies"]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(res.status_code, 200)
        scan_id = res.json()["id"]

        # Get findings for this scan
        res_f = self.client.get(
            f"/api/admin/security/findings?scan_id={scan_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(res_f.status_code, 200)
        findings = res_f.json()

        if len(findings) > 0:
            target_finding = findings[0]
            finding_id = target_finding["id"]

            # 1. Apply remediation
            res_apply = self.client.post(
                f"/api/admin/security/findings/{finding_id}/remediate",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            self.assertEqual(res_apply.status_code, 200)
            apply_data = res_apply.json()
            self.assertTrue(apply_data["success"])
            self.assertEqual(apply_data["status"], "APPLIED")
            rem_id = apply_data["remediation_id"]

            # 2. Verify remediation
            res_verify = self.client.post(
                f"/api/admin/security/remediations/{rem_id}/verify",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            self.assertEqual(res_verify.status_code, 200)
            verify_data = res_verify.json()
            self.assertIn("status", verify_data)

            # 3. Rollback remediation
            res_rollback = self.client.post(
                f"/api/admin/security/remediations/{rem_id}/rollback",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            self.assertEqual(res_rollback.status_code, 200)
            rb_data = res_rollback.json()
            self.assertTrue(rb_data["success"])
            self.assertEqual(rb_data["status"], "ROLLED_BACK")

    def test_07_security_posture_stats(self):
        admin_token = self._login("admin@acrocorp.com")
        res = self.client.get(
            "/api/admin/security/stats",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(res.status_code, 200)
        stats = res.json()
        self.assertIn("posture_score", stats)
        self.assertGreaterEqual(stats["posture_score"], 0)
        self.assertLessEqual(stats["posture_score"], 100)
        self.assertIn("posture_rating", stats)
        self.assertIn("total_scans", stats)
        self.assertIn("counts", stats)

    def test_08_export_assessment_report(self):
        admin_token = self._login("admin@acrocorp.com")
        res_scan = self.client.post(
            "/api/admin/security/scans",
            json={"scope": ["cryptographic_config", "audit_integrity"]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        scan_id = res_scan.json()["id"]

        # Export report
        res_rep = self.client.get(
            f"/api/admin/security/reports/{scan_id}/export",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(res_rep.status_code, 200)
        report = res_rep.json()
        self.assertEqual(report["report_id"], f"REP-{scan_id.upper()}")
        self.assertIn("executive_summary", report)
        self.assertIn("test_coverage_breakdown", report)
        self.assertIn("findings_detail", report)
        self.assertIn("certification", report)
        self.assertEqual(
            report["certification"]["standard"],
            "CVSS v3.1 / OWASP Top 10 LLM / Zero-Egress Offline Assurance",
        )


if __name__ == "__main__":
    unittest.main()
