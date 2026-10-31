"""
Static Code, Configuration, and Secrets Scanners for PS-04.
"""
from __future__ import annotations

import os
import re
from typing import Any

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class StaticAnalyzer:
    """
    Performs static analysis across Python backend code to detect security anti-patterns.
    """

    @classmethod
    def scan_codebase(cls) -> list[dict[str, Any]]:
        findings = []
        py_files = []
        for root, _, files in os.walk(BACKEND_DIR):
            if "__pycache__" in root or "tests" in root or "models" in root:
                continue
            for f in files:
                if f.endswith(".py"):
                    py_files.append(os.path.join(root, f))

        for file_path in py_files:
            rel_path = os.path.relpath(file_path, BACKEND_DIR)
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as fp:
                    lines = fp.readlines()
            except Exception:
                continue

            for idx, line in enumerate(lines, start=1):
                # 1. Unsafe SQL concatenation: e.g. f"SELECT ... {var}" or "SELECT " + var
                if re.search(r'execute\s*\(\s*f["\'].*SELECT.*\{', line, re.IGNORECASE):
                    findings.append({
                        "test_case_id": "STATIC_SQLI_01",
                        "title": "Potential Unparameterized SQL Query Detected",
                        "category": "sql_injection",
                        "severity": "CRITICAL",
                        "affected_file": rel_path,
                        "line": idx,
                        "evidence": line.strip()[:200],
                        "root_cause": "SQL query string constructed via string interpolation instead of parameter binding (?)",
                        "potential_impact": "SQL injection enabling unauthorized data extraction or data manipulation",
                        "recommended_remediation": "Use parameterized queries with placeholder tuples, e.g., conn.execute('SELECT ... WHERE col = ?', (val,))",
                    })

                # 2. Unsafe command execution
                if re.search(r'\b(eval|exec|os\.system|subprocess\.Popen\(.*shell\s*=\s*True)\b', line):
                    findings.append({
                        "test_case_id": "STATIC_RCE_01",
                        "title": "Potentially Dangerous Execution Function",
                        "category": "api_security",
                        "severity": "HIGH",
                        "affected_file": rel_path,
                        "line": idx,
                        "evidence": line.strip()[:200],
                        "root_cause": "Direct shell execution or dynamic evaluation of strings",
                        "potential_impact": "Arbitrary code execution if user inputs reach the execution call",
                        "recommended_remediation": "Remove eval/exec and avoid invoking external shell interpreters directly",
                    })

                # 3. Insecure debug mode
                if re.search(r'debug\s*=\s*True', line):
                    findings.append({
                        "test_case_id": "STATIC_CFG_DEBUG",
                        "title": "Debug Mode Flag Enabled",
                        "category": "security_config",
                        "severity": "MEDIUM",
                        "affected_file": rel_path,
                        "line": idx,
                        "evidence": line.strip()[:200],
                        "root_cause": "Application framework configured with debug=True",
                        "potential_impact": "Exposure of detailed stack traces and debugging consoles to end users",
                        "recommended_remediation": "Disable debug mode in production and load from environment variable with False default",
                    })

        return findings


class SecretsScanner:
    """
    Audits codebase and configuration files for exposed secrets, API tokens, and private keys.
    """

    SECRET_PATTERNS = [
        (r'BEGIN (RSA|EC|DSA|OPENSSH) PRIVATE KEY', "Exposed Private Key", "CRITICAL"),
        (r'(?i)(api[_-]?key|secret[_-]?key|password)\s*=\s*["\'][a-zA-Z0-9_\-]{20,}["\']', "Hardcoded Secret / API Key", "HIGH"),
        (r'ghp_[a-zA-Z0-9]{36}', "GitHub Personal Access Token", "CRITICAL"),
    ]

    @classmethod
    def scan_secrets(cls) -> list[dict[str, Any]]:
        findings = []
        for root, _, files in os.walk(BACKEND_DIR):
            if "__pycache__" in root or "tests" in root or "models" in root:
                continue
            for f in files:
                if f.endswith((".py", ".json", ".yaml", ".yml", ".env")):
                    file_path = os.path.join(root, f)
                    rel_path = os.path.relpath(file_path, BACKEND_DIR)
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as fp:
                            content = fp.read()
                    except Exception:
                        continue

                    for pattern, title, severity in cls.SECRET_PATTERNS:
                        match = re.search(pattern, content)
                        if match and "hash_password" not in match.group(0) and "Password123!" not in match.group(0):
                            findings.append({
                                "test_case_id": "SECRET_EXPOSURE_01",
                                "title": title,
                                "category": "secrets_exposure",
                                "severity": severity,
                                "affected_file": rel_path,
                                "evidence": f"Pattern '{pattern}' matched content in {rel_path}",
                                "root_cause": "Hardcoded secret, key, or token in plaintext repository files",
                                "potential_impact": "Credential exposure allowing unauthorized system impersonation",
                                "recommended_remediation": "Store secrets exclusively in environment variables or hardware key stores",
                            })
        return findings


class ConfigScanner:
    """
    Audits application configuration, HTTP security headers, CORS settings, and token parameters.
    """

    @classmethod
    def audit_configuration(cls) -> list[dict[str, Any]]:
        findings = []

        # Check .env / JWT secrets
        jwt_secret = os.environ.get("JWT_SECRET", "")
        if jwt_secret and len(jwt_secret) < 32:
            findings.append({
                "test_case_id": "CFG_WEAK_JWT_SECRET",
                "title": "Short or Weak JWT Secret Key",
                "category": "cryptographic_config",
                "severity": "HIGH",
                "affected_component": "auth_security.py",
                "evidence": f"JWT secret length is {len(jwt_secret)} characters (recommended >= 32)",
                "root_cause": "Cryptographic key length is below minimum recommended standard for HS256",
                "potential_impact": "Tokens could be forged through offline brute force dictionary attacks",
                "recommended_remediation": "Use a cryptographically secure random secret with at least 32 characters (256 bits)",
            })

        # Check offline mode environment variables
        hf_offline = os.environ.get("HF_HUB_OFFLINE", "0")
        tr_offline = os.environ.get("TRANSFORMERS_OFFLINE", "0")
        if hf_offline != "1" or tr_offline != "1":
            findings.append({
                "test_case_id": "CFG_OFFLINE_EGRESS",
                "title": "Strict Offline Zero-Egress Environment Flags Missing",
                "category": "security_config",
                "severity": "MEDIUM",
                "affected_component": "embedding_manager.py",
                "evidence": f"HF_HUB_OFFLINE={hf_offline}, TRANSFORMERS_OFFLINE={tr_offline}",
                "root_cause": "HuggingFace offline flags not exported at environment level",
                "potential_impact": "Runtime could inadvertently attempt outbound network requests if models are missing",
                "recommended_remediation": "Set HF_HUB_OFFLINE=1 and TRANSFORMERS_OFFLINE=1 in environment variables",
            })

        return findings
