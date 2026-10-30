# TrustView

TrustView is a secure, tenant-isolated knowledge and case-management MVP. It provides grounded document answers with document/version/page citations, deterministic CRM routing, controlled case lifecycles, tamper-evident audit events, and a role-aware React console.

## Included

- Tenant ID bound to the authenticated JWT; never taken from a prompt or model response.
- Tenant-scoped document ingestion, active-version retrieval, citations, and honest refusals.
- Controlled CRM cases, derived overdue state, append-only action logs, and dashboards.
- HMAC-pseudonymised telemetry plus a SHA-256 audit chain with simulated anchoring.
- Truthful security status: no enabled TEE, simulated chain anchor, and no Trustbeam integration.

## Run locally

Set the two deployment secrets before starting. `VICO_AUDIT_HMAC_KEY` is mandatory for knowledge and case routes; set `SECRET_KEY` separately before any non-development deployment.

```powershell
cd backend
$env:VICO_AUDIT_HMAC_KEY = 'replace-with-a-long-random-secret'
$env:SECRET_KEY = 'replace-with-a-separate-long-random-secret'
python -m pip install -r requirements.txt
python main.py
```

```powershell
cd frontend
npm ci
npm run dev
```

Open `http://localhost:5173`, register an admin or manager with a tenant such as `T0002`, then ingest documents through `POST /vico/ingest` before using grounded chat.

## Verify

```powershell
cd backend
python -m unittest discover -s tests -v
python -m tests.e2e_vico_demo

cd ../frontend
npm run build
```

See `DOUBTS.md`, `SECURITY_FINDINGS.md`, and `MANUAL_CHECKS.md` for known operational limits and production checks.
