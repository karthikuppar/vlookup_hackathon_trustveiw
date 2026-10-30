# PS-04: Secure Multi-Client Knowledge Chatbot

An offline-capable, document-grounded chatbot system designed to serve multiple corporate clients while enforcing strict tenant data isolation, server-side authorization, tamper-evident audit logging, and explicit knowledge sharing.

## Key Features
- **Strict Tenant & Client Isolation**: Enforced server-side before retrieval candidate generation.
- **Grounded Responses & Citations**: Direct citations (Document ID, Version, Page/Section) with honest refusals (`insufficient_evidence`) and contradiction handling (`conflicting_sources`).
- **Prompt Injection Defense**: Untrusted user prompts and retrieved documents cannot override access controls or trigger unauthorized operations.
- **Controlled Knowledge Sharing**: Explicit, revocable cross-tenant knowledge base sharing grants.
- **Tamper-Evident Audit Ledger**: SHA-256 hash-chained event ledger with integrity verification.
- **Offline Capable**: Designed for zero-egress offline runtime operation.

## PS-04 implementation

A working implementation of this spec (FastAPI, SQLite, tests, docs) lives in [`ps04/`](ps04/). See
[`ps04/README.md`](ps04/README.md) for setup and the demo script, and [`ps04/docs/SECURITY.md`](ps04/docs/SECURITY.md)
for the security model. The TEE component is a simulation.
