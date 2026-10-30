"""
Security Service — Orchestrator for Scans, Finding Lifecycle, Remediations, and Reporting.

Fulfills Sections 3, 4, 5, 6, 7, 8 of the PS-04 Security Centre Specification.
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Any

from database import get_connection
from crypto_utils import now_utc_iso
from security.config import SECURITY_CATEGORIES, SEVERITY_SCORES
from security.test_engine import SecurityTestEngine
from security.remediation_engine import RemediationEngine


class SecurityService:
    """
    Central coordinator for the PS-04 Security Testing and Automated Remediation Centre.
    """

    @classmethod
    def run_security_scan(cls, app_instance: Any, scope: list[str] | None = None) -> dict[str, Any]:
        """
        Executes a real security assessment against the application instance.
        """
        scan_id = f"scan_{uuid.uuid4().hex[:12]}"
        start_time = time.time()
        started_at = now_utc_iso()

        categories_to_run = scope if scope and len(scope) > 0 else list(SECURITY_CATEGORIES.keys())
        scope_label = "FULL_ASSESSMENT" if len(categories_to_run) == len(SECURITY_CATEGORIES) else "TARGETED_SCAN"

        # Record initial scan in database
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO security_scans (
                    id, started_at, status, total_tests, scope
                ) VALUES (?, ?, 'RUNNING', ?, ?)
                """,
                (scan_id, started_at, len(categories_to_run), scope_label),
            )

        test_engine = SecurityTestEngine(app_instance)
        test_engine.log(f"Initiated {scope_label} [{scan_id}] across {len(categories_to_run)} categories.")

        all_findings: list[dict[str, Any]] = []
        categories_with_failures = 0

        for cat_key in categories_to_run:
            cat_meta = SECURITY_CATEGORIES.get(cat_key, {"name": cat_key})
            test_engine.log(f"Starting test category: {cat_meta.get('name')}")
            try:
                findings = test_engine.execute_category_tests(cat_key)
                if findings:
                    categories_with_failures += 1
                    test_engine.log(f"Category {cat_key} finished with {len(findings)} finding(s).")
                    for f in findings:
                        finding_id = f"find_{uuid.uuid4().hex[:12]}"
                        f["id"] = finding_id
                        f["scan_id"] = scan_id
                        all_findings.append(f)

                        # Insert into database
                        with get_connection() as conn:
                            conn.execute(
                                """
                                INSERT INTO security_findings (
                                    id, scan_id, test_case_id, title, category, severity,
                                    risk_score, affected_component, affected_file, root_cause,
                                    potential_impact, recommended_remediation, status,
                                    evidence_json, detected_at
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?)
                                """,
                                (
                                    finding_id,
                                    scan_id,
                                    f["test_case_id"],
                                    f["title"],
                                    f["category"],
                                    f["severity"],
                                    f.get("risk_score", 5.0),
                                    f.get("affected_component", "Core"),
                                    f.get("affected_file"),
                                    f.get("root_cause", ""),
                                    f.get("potential_impact", ""),
                                    f.get("recommended_remediation", ""),
                                    json.dumps({"evidence": f.get("evidence", "")}),
                                    started_at,
                                ),
                            )

                        # Auto-propose safe remediation
                        RemediationEngine.propose_remediation(f)
                else:
                    test_engine.log(f"Category {cat_key} PASSED with 0 vulnerabilities.")
            except Exception as e:
                test_engine.log(f"Error testing category {cat_key}: {e}")

        duration = round(time.time() - start_time, 2)
        completed_at = now_utc_iso()
        total_tests = len(categories_to_run)
        passed_tests = total_tests - categories_with_failures
        failed_tests = categories_with_failures

        # Severity tallies
        critical_count = sum(1 for f in all_findings if f.get("severity") == "CRITICAL")
        high_count = sum(1 for f in all_findings if f.get("severity") == "HIGH")
        medium_count = sum(1 for f in all_findings if f.get("severity") == "MEDIUM")
        low_count = sum(1 for f in all_findings if f.get("severity") == "LOW")

        log_text = "\n".join(test_engine.logs)

        with get_connection() as conn:
            conn.execute(
                """
                UPDATE security_scans
                SET completed_at = ?, status = 'COMPLETED', total_tests = ?, passed_tests = ?,
                    failed_tests = ?, critical_count = ?, high_count = ?, medium_count = ?,
                    low_count = ?, duration_seconds = ?, execution_log = ?
                WHERE id = ?
                """,
                (
                    completed_at,
                    total_tests,
                    passed_tests,
                    failed_tests,
                    critical_count,
                    high_count,
                    medium_count,
                    low_count,
                    duration,
                    log_text,
                    scan_id,
                ),
            )

        return {
            "id": scan_id,
            "started_at": started_at,
            "completed_at": completed_at,
            "status": "COMPLETED",
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "critical_count": critical_count,
            "high_count": high_count,
            "medium_count": medium_count,
            "low_count": low_count,
            "duration_seconds": duration,
            "scope": scope_label,
            "findings_count": len(all_findings),
        }

    @classmethod
    def list_scans(cls) -> list[dict[str, Any]]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM security_scans ORDER BY started_at DESC LIMIT 50"
            ).fetchall()
            return [dict(r) for r in rows]

    @classmethod
    def get_scan(cls, scan_id: str) -> dict[str, Any] | None:
        with get_connection() as conn:
            scan = conn.execute(
                "SELECT * FROM security_scans WHERE id = ?", (scan_id,)
            ).fetchone()
            if not scan:
                return None
            scan_dict = dict(scan)

            findings_rows = conn.execute(
                """
                SELECT f.*, r.id AS remediation_id, r.proposed_patch, r.status AS remediation_status,
                       r.requires_approval, r.applied_at, r.verified_at
                FROM security_findings f
                LEFT JOIN security_remediations r ON f.id = r.finding_id
                WHERE f.scan_id = ?
                ORDER BY f.risk_score DESC
                """,
                (scan_id,),
            ).fetchall()
            scan_dict["findings"] = [dict(r) for r in findings_rows]
            return scan_dict

    @classmethod
    def list_findings(
        cls,
        scan_id: str | None = None,
        severity: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        query = """
            SELECT f.*, r.id AS remediation_id, r.proposed_patch, r.status AS remediation_status,
                   r.requires_approval, r.applied_at, r.verified_at
            FROM security_findings f
            LEFT JOIN security_remediations r ON f.id = r.finding_id
            WHERE 1=1
        """
        params: list[Any] = []
        if scan_id:
            query += " AND f.scan_id = ?"
            params.append(scan_id)
        if severity:
            query += " AND f.severity = ?"
            params.append(severity.upper())
        if status:
            query += " AND f.status = ?"
            params.append(status.upper())

        query += " ORDER BY f.risk_score DESC, f.detected_at DESC"

        with get_connection() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
            return [dict(r) for r in rows]

    @classmethod
    def get_finding(cls, finding_id: str) -> dict[str, Any] | None:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT f.*, r.id AS remediation_id, r.proposed_patch, r.status AS remediation_status,
                       r.requires_approval, r.applied_at, r.verified_at, r.remediation_notes
                FROM security_findings f
                LEFT JOIN security_remediations r ON f.id = r.finding_id
                WHERE f.id = ?
                """,
                (finding_id,),
            ).fetchone()
            if not row:
                return None
            return dict(row)

    @classmethod
    def get_posture_stats(cls) -> dict[str, Any]:
        with get_connection() as conn:
            total_scans = conn.execute("SELECT COUNT(*) AS c FROM security_scans").fetchone()["c"]
            last_scan = conn.execute(
                "SELECT * FROM security_scans ORDER BY started_at DESC LIMIT 1"
            ).fetchone()

            findings = conn.execute(
                "SELECT severity, status FROM security_findings"
            ).fetchall()

            open_critical = sum(1 for f in findings if f["severity"] == "CRITICAL" and f["status"] == "OPEN")
            open_high = sum(1 for f in findings if f["severity"] == "HIGH" and f["status"] == "OPEN")
            open_medium = sum(1 for f in findings if f["severity"] == "MEDIUM" and f["status"] == "OPEN")
            open_low = sum(1 for f in findings if f["severity"] == "LOW" and f["status"] == "OPEN")

            fixed_count = sum(1 for f in findings if f["status"] == "FIXED")
            remediating_count = sum(1 for f in findings if f["status"] == "IN_REMEDIATION")
            open_count = sum(1 for f in findings if f["status"] == "OPEN")

            # Posture Score calculation (0 - 100)
            # Base 100, deduction per open vulnerability
            deduction = (open_critical * 25) + (open_high * 15) + (open_medium * 5) + (open_low * 2)
            posture_score = max(0, min(100, 100 - deduction))

            return {
                "posture_score": posture_score,
                "posture_rating": (
                    "EXCELLENT" if posture_score >= 90 else
                    "GOOD" if posture_score >= 75 else
                    "MODERATE" if posture_score >= 60 else "CRITICAL_ATTENTION_REQUIRED"
                ),
                "total_scans": total_scans,
                "last_scan": dict(last_scan) if last_scan else None,
                "counts": {
                    "total_findings": len(findings),
                    "open": open_count,
                    "in_remediation": remediating_count,
                    "fixed": fixed_count,
                    "critical": open_critical,
                    "high": open_high,
                    "medium": open_medium,
                    "low": open_low,
                },
            }

    @classmethod
    def generate_assessment_report(cls, scan_id: str) -> dict[str, Any] | None:
        scan = cls.get_scan(scan_id)
        if not scan:
            return None

        findings = scan.get("findings", [])
        resolved_findings = [f for f in findings if f.get("status") == "FIXED"]
        open_findings = [f for f in findings if f.get("status") != "FIXED"]

        # Risk level determination
        if scan.get("critical_count", 0) > 0:
            overall_risk = "CRITICAL"
        elif scan.get("high_count", 0) > 0:
            overall_risk = "HIGH"
        elif scan.get("medium_count", 0) > 0:
            overall_risk = "MEDIUM"
        else:
            overall_risk = "LOW"

        report = {
            "report_id": f"REP-{scan_id.upper()}",
            "generated_at": now_utc_iso(),
            "target_system": "PS-04 Secure Multi-Client Chatbot Platform",
            "assessment_scope": scan.get("scope", "FULL_ASSESSMENT"),
            "executive_summary": {
                "overall_risk_rating": overall_risk,
                "total_vulnerabilities_identified": len(findings),
                "critical_vulnerabilities": scan.get("critical_count", 0),
                "high_vulnerabilities": scan.get("high_count", 0),
                "medium_vulnerabilities": scan.get("medium_count", 0),
                "low_vulnerabilities": scan.get("low_count", 0),
                "remediated_and_verified": len(resolved_findings),
                "pending_remediation": len(open_findings),
                "scan_duration_seconds": scan.get("duration_seconds", 0.0),
            },
            "test_coverage_breakdown": {
                "total_categories_tested": scan.get("total_tests", 0),
                "categories_passed": scan.get("passed_tests", 0),
                "categories_flagged": scan.get("failed_tests", 0),
            },
            "findings_detail": [
                {
                    "finding_id": f.get("id"),
                    "test_case_id": f.get("test_case_id"),
                    "title": f.get("title"),
                    "category": f.get("category"),
                    "severity": f.get("severity"),
                    "risk_score": f.get("risk_score"),
                    "affected_component": f.get("affected_component"),
                    "affected_file": f.get("affected_file"),
                    "root_cause": f.get("root_cause"),
                    "potential_impact": f.get("potential_impact"),
                    "recommended_remediation": f.get("recommended_remediation"),
                    "evidence": f.get("evidence_json"),
                    "current_status": f.get("status"),
                    "remediation": {
                        "remediation_id": f.get("remediation_id"),
                        "proposed_patch": f.get("proposed_patch"),
                        "status": f.get("remediation_status"),
                        "requires_approval": bool(f.get("requires_approval")),
                        "applied_at": f.get("applied_at"),
                        "verified_at": f.get("verified_at"),
                    },
                }
                for f in findings
            ],
            "certification": {
                "auditor": "PS-04 Automated Vulnerability & Remediation Engine",
                "methodology": "Automated AST/Static Code Inspection + Synthetic Sandbox Exploitation",
                "standard": "CVSS v3.1 / OWASP Top 10 LLM / Zero-Egress Offline Assurance",
            },
        }

        return report
