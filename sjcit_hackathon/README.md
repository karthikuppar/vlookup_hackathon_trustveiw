# AegisKB — PS-04 Secure Multi-Client Knowledge Chatbot

An offline-capable, document-grounded chatbot system that serves multiple enterprise clients while enforcing strict tenant data isolation, server-side authorization, tamper-evident audit logging, and explicit knowledge sharing.

Based on the [PS-04 Implementation Specification](file:///c:/Users/uppar/OneDrive/Desktop/VLOOKUP/PS04_SECURE_MULTI_CLIENT_CHATBOT_SPEC.md).

---

## Key Features

1. **Strict Server-Side Isolation**: Candidate search documents are filtered directly in the SQL layer using the verified JWT claims before any retrieval or inference. Natural language prompt injection cannot alter tenant boundaries.
2. **Grounded Answers & Citations**: Answers are grounded with exact citations (`doc_id`, `version_num`, `page`, `section`, `excerpt`). Distinguishes between `grounded`, `insufficient_evidence` (refuses without hallucination), and `conflicting_sources` (surfaces contradictions).
3. **Atomic Document Versioning**: Version replacements atomically supersede older versions. Superseded documents are excluded from active retrieval but retained for audit.
4. **Explicit Knowledge Sharing (Section 4)**: Cross-client access requires an explicit grant with justification. Revocation takes effect instantaneously on subsequent queries.
5. **Blockchain-Lite Tamper-Evident Audit Ledger (Section 5)**: Canonical JSON serialization (`_canonical`) with SHA-256 hash chaining. Real-time verification detects altered records, broken links, or deleted events.
6. **TEE Simulation (Section 6)**: Truthful disclosure of simulated confidential computing status with attestation policy verification.
7. **Offline Operation (Section 7)**: 100% zero-egress runtime operation without outbound network dependencies.

---

## Quick Start

### 1. Start the Backend (FastAPI)
```powershell
cd sjcit_hackathon/backend
python main.py
```
*Backend runs on `http://127.0.0.1:8000` with Swagger UI at `http://127.0.0.1:8000/docs`.*

### 2. Start the Frontend (React + Vite)
```powershell
cd sjcit_hackathon/frontend
npm run dev
```
*Frontend runs on `http://localhost:5173`.*

---

## Pre-seeded Demo Accounts
- **Alice Admin (Client A - AcroCorp)**: `admin@acrocorp.com` / `Password123!`
- **Edward Employee (Client A - AcroCorp)**: `employee@acrocorp.com` / `Password123!`
- **Bob Admin (Client B - BetaShield)**: `admin@betashield.com` / `Password123!`
- **Betty Employee (Client B - BetaShield)**: `employee@betashield.com` / `Password123!`
- **System SuperAdmin**: `sysadmin@ps04platform.com` / `Password123!`

---

## Verification & Acceptance Tests

Run the full acceptance test suite covering all 11 criteria from Section 12 of the PS-04 specification:
```powershell
cd sjcit_hackathon/backend
python -m unittest tests/test_ps04_acceptance.py -v
```
