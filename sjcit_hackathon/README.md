# AegisKB — Secure Multi-Client Enterprise Knowledge & SOP Assistant

[![Offline Zero-Egress](https://img.shields.io/badge/Offline-Zero--Egress%20Runtime-15803D?style=flat-square)](#offline-zero-egress-runtime)
[![Confidential Computing](https://img.shields.io/badge/Enclave-TEE%20Attestation%20(Simulated)-0369A1?style=flat-square)](#hardware-enclave-tee-simulation)
[![Tamper Evident](https://img.shields.io/badge/Audit-SHA--256%20Hash--Chained-B45309?style=flat-square)](#blockchain-lite-tamper-evident-audit-ledger)
[![Architecture](https://img.shields.io/badge/NLP-3--Layer%20Vector%20Pipeline-49372B?style=flat-square)](#3-layer-nlp--in-memory-vector-engine)

**AegisKB** is a privacy-first, offline-capable, document-grounded enterprise assistant designed to serve multiple corporate clients and internal teams under strict security boundaries. Built in full compliance with the **PS-04 Secure Multi-Client Specification**, AegisKB guarantees complete tenant data isolation, exact source citation with zero hallucinations, automated conflict detection, atomic document versioning, and tamper-evident blockchain-lite audit logging.

---

## 📑 Table of Contents
1. [Core Features & Highlights](#-core-features--highlights)
2. [System Architecture](#-system-architecture)
3. [Pre-Seeded Demo Accounts](#-pre-seeded-demo-accounts)
4. [Technology Stack](#-technology-stack)
5. [Directory Layout](#-directory-layout)
6. [Quick Start Guide](#-quick-start-guide)
7. [Feature Deep Dive](#-feature-deep-dive)
8. [Acceptance Test Suite](#-acceptance-test-suite)
9. [API Documentation](#-api-documentation)

---

## 🌟 Core Features & Highlights

- **🔒 Strict Server-Side Data Isolation**: Candidate search documents are filtered directly at the database layer using cryptographic JWT claims before any retrieval or inference occurs.
- **📖 Grounded Citations (Zero Hallucinations)**: Answers cite Document ID, Version Number, Page, and Section excerpt (`grounded_answer`, `insufficient_evidence`, `conflicting_sources`).
- **📄 Automated PDF SOP Ingestion**: Administrator portal for uploading corporate SOP documents with instant text extraction, page-aware chunking, vector indexing, and employee attribution (e.g. Sam, Edward).
- **⚡ In-Memory Vector DB & Sub-Millisecond Retrieval**: High-performance TF-IDF cosine similarity vector retrieval operating in under 2ms directly in-memory, paired with an LRU cache.
- **⛓️ Blockchain-Lite Tamper-Evident Ledger**: Every query, login, upload, and sharing grant is canonicalized and chained using SHA-256 hashes.
- **🛡️ Hardware Enclave (TEE) Simulation**: Disclosing simulated confidential computing status (Intel TDX / AMD SEV-SNP) with cryptographic attestation policy validation.
- **📴 100% Offline Zero-Egress Runtime**: Operates air-gapped without external network calls.
- **🎨 Warm Luxury Enterprise UI**: Designed with high-contrast accessibility typography (pure black numbers, monospace hashes, and clear status indicators).

---

## 👥 Pre-Seeded Demo Accounts

| Name | Role | Email | Password | Organization |
|---|---|---|---|---|
| **Alice Admin** | Client Administrator | `admin@acrocorp.com` | `Password123!` | AcroCorp (org_a) |
| **Sam Employee** | Client Employee | `sam@acrocorp.com` | `Password123!` | AcroCorp (org_a) |
| **Edward Employee** | Client Employee | `employee@acrocorp.com` | `Password123!` | AcroCorp (org_a) |
| **Bob Admin** | Client Administrator | `admin@betashield.com` | `Password123!` | BetaShield (org_b) |
| **Betty Employee** | Client Employee | `employee@betashield.com` | `Password123!` | BetaShield (org_b) |
| **System Admin** | Super Administrator | `sysadmin@ps04platform.com` | `Password123!` | Platform |

---

## 🚀 Quick Start Guide

### 1. Launch the Backend
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```
- **Backend API**: `http://127.0.0.1:8000`
- **Interactive Swagger Docs**: `http://127.0.0.1:8000/docs`

### 2. Launch the Frontend
```powershell
cd frontend
npm install
npm run dev
```
- **Web Application**: `http://localhost:5173`

---

## 🧪 Acceptance Test Suite

Run the full acceptance test suite covering all 11 criteria from Section 12 of the PS-04 specification:
```powershell
cd backend
python -m unittest tests/test_ps04_acceptance.py -v
```
