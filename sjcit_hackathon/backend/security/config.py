"""
Security Centre Configuration, Test Categories, and CVSS Scoring Standards.
"""
from __future__ import annotations

from typing import Any

# The 20 Mandatory Security Test Categories
SECURITY_CATEGORIES: dict[str, dict[str, Any]] = {
    "prompt_injection": {
        "name": "Prompt Injection Testing",
        "description": "Tests direct and indirect prompt injection attempts against system instructions and RAG context.",
        "default_severity": "HIGH",
    },
    "sql_injection": {
        "name": "SQL Injection Testing",
        "description": "Tests database-backed endpoints against non-destructive SQL syntax manipulation and error leaks.",
        "default_severity": "CRITICAL",
    },
    "xss_testing": {
        "name": "Cross-Site Scripting Testing",
        "description": "Verifies HTML output sanitization in chat message rendering, document titles, and metadata.",
        "default_severity": "HIGH",
    },
    "authentication": {
        "name": "Authentication Testing",
        "description": "Audits credential verification, token tampering, brute force lockout, and session invalidation.",
        "default_severity": "CRITICAL",
    },
    "authorization": {
        "name": "Authorization Testing",
        "description": "Tests role enforcement (client_employee vs client_admin vs system_admin) across protected routes.",
        "default_severity": "CRITICAL",
    },
    "tenant_isolation": {
        "name": "Multi-Tenant Isolation Testing",
        "description": "Verifies strict tenant boundary enforcement across document chunks, vector search, and conversations.",
        "default_severity": "CRITICAL",
    },
    "api_security": {
        "name": "API Security Testing",
        "description": "Tests oversized payloads, invalid JSON, unexpected fields, and improper HTTP methods.",
        "default_severity": "MEDIUM",
    },
    "file_upload": {
        "name": "File Upload Security Testing",
        "description": "Audits file extension whitelisting, directory traversal paths, and maximum document size limits.",
        "default_severity": "HIGH",
    },
    "session_security": {
        "name": "Session Security Testing",
        "description": "Tests session fixation, JWT claims verification, expiration enforcement, and session revocation.",
        "default_severity": "HIGH",
    },
    "rate_limiting": {
        "name": "Rate Limiting Testing",
        "description": "Tests brute force login attack mitigation and API request threshold bounding.",
        "default_severity": "MEDIUM",
    },
    "rag_security": {
        "name": "RAG Security Testing",
        "description": "Verifies citation authenticity, cross-tenant chunk exclusion, and RAG context tampering resistance.",
        "default_severity": "HIGH",
    },
    "llm_security": {
        "name": "LLM Security Testing",
        "description": "Tests system prompt disclosure resistance, instruction hierarchy adherence, and context exhaustion.",
        "default_severity": "HIGH",
    },
    "dependencies": {
        "name": "Dependency Vulnerability Testing",
        "description": "Audits active Python and frontend packages for known vulnerabilities and unsafe versions.",
        "default_severity": "MEDIUM",
    },
    "secrets_exposure": {
        "name": "Secret Exposure Testing",
        "description": "Scans application codebase, configuration, and environment for exposed keys or passwords.",
        "default_severity": "CRITICAL",
    },
    "security_config": {
        "name": "Security Configuration Testing",
        "description": "Audits HTTP security headers (CSP, HSTS, X-Frame-Options, nosniff) and CORS origins.",
        "default_severity": "MEDIUM",
    },
    "data_leakage": {
        "name": "Data Leakage Testing",
        "description": "Tests for internal server error stack trace leaks, database schema disclosures, and system information dumps.",
        "default_severity": "MEDIUM",
    },
    "input_validation": {
        "name": "Input Validation Testing",
        "description": "Validates boundary checks, null byte handling, Unicode normalizations, and length caps.",
        "default_severity": "LOW",
    },
    "error_handling": {
        "name": "Error Handling Testing",
        "description": "Ensures uniform 400/401/403/404 responses without exposing underlying implementation details.",
        "default_severity": "LOW",
    },
    "audit_integrity": {
        "name": "Audit Logging Integrity Testing",
        "description": "Verifies SHA-256 blockchain-lite hash chains, sequence numbers, and HMAC checkpoint signatures.",
        "default_severity": "HIGH",
    },
    "cryptographic_config": {
        "name": "Cryptographic Configuration Testing",
        "description": "Audits password hashing iterations, HMAC secret strength, and token signature algorithms.",
        "default_severity": "HIGH",
    },
}

SEVERITY_LEVELS = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFORMATIONAL"]

# Documented CVSS-aligned risk scores
SEVERITY_SCORES: dict[str, float] = {
    "CRITICAL": 9.5,
    "HIGH": 7.5,
    "MEDIUM": 5.0,
    "LOW": 2.5,
    "INFORMATIONAL": 0.0,
}
