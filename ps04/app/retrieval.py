"""Access-filtered retrieval. The tenant/share predicate is part of the SQL, so unauthorised chunks are
never loaded into memory, never scored, and never reach answer generation. Corpus statistics (IDF) are
computed only over the authorised set, so scores cannot leak information about other tenants."""
from __future__ import annotations
import math, re
from collections import Counter

from .audit import now

STOP = set("a an the and or of to in on for with is are was were be been by at as it this that these those from what which who how when where "
           "do does did can could should would will shall may might must about into than then there their its our your you we i me my not no".split())

# A chunk is visible to tenant :tid if it is the tenant's own, or covered by an active, unexpired grant.
# :now is a parameter so tests can control time. Used by search, document reads and citation reads alike.
VISIBLE = """
  (d.tenant_id = :tid OR EXISTS (
     SELECT 1 FROM shares s JOIN tenants ot ON ot.id = s.owner_tenant_id
     WHERE s.owner_tenant_id = d.tenant_id AND s.grantee_tenant_id = :tid AND s.revoked_at IS NULL
       AND (s.expires_at IS NULL OR s.expires_at > :now) AND (s.document_id IS NULL OR s.document_id = d.id)
       AND ot.status = 'active'))
"""


def stem(w: str) -> str:
    for suf in ("ing", "ed", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)]
    return w


def terms(text: str) -> list[str]:
    return [stem(w) for w in re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", text.lower()) if w not in STOP and len(w) > 1]


def authorised_chunks(conn, tenant_id: str, at: str | None = None):
    """Current, fully-processed chunks the given tenant context may read (own + actively shared)."""
    return conn.execute(
        f"""SELECT c.id, c.document_id, c.version_id, c.page, c.section, c.char_start, c.char_end, c.text,
                   d.title, d.tenant_id AS owner_tenant_id, v.version_no, t.name AS owner_name
            FROM chunks c JOIN document_versions v ON v.id = c.version_id
            JOIN documents d ON d.id = c.document_id JOIN tenants t ON t.id = d.tenant_id
            WHERE v.is_current = 1 AND v.status = 'ready' AND {VISIBLE}""",
        {"tid": tenant_id, "now": at or now()}).fetchall()


def search(conn, tenant_id: str, query: str, k: int = 8, at: str | None = None) -> list[dict]:
    """BM25 over the authorised set only."""
    rows = authorised_chunks(conn, tenant_id, at)
    q = list(dict.fromkeys(terms(query)))
    if not rows or not q:
        return []
    docs = [Counter(terms(r["text"] + " " + (r["title"] or ""))) for r in rows]
    n, avg = len(rows), sum(sum(d.values()) for d in docs) / len(rows) or 1
    df = {t: sum(1 for d in docs if t in d) for t in q}
    scored = []
    for r, d in zip(rows, docs):
        ln = sum(d.values())
        s = 0.0
        for t in q:
            if d[t]:
                idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                s += idf * d[t] * 2.2 / (d[t] + 1.2 * (0.25 + 0.75 * ln / avg))
        if s > 0:
            scored.append({**dict(r), "score": s})
    return sorted(scored, key=lambda x: -x["score"])[:k]
