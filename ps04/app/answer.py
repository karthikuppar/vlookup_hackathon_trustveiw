"""Grounded, extractive answer generation: grounded / insufficient_evidence / conflict_detected.

Answers are assembled only from sentences in authorised chunks, so there is nothing for the model to
invent and no instruction-following surface: the question and document text are treated purely as
data. Instruction-like sentences in documents are excluded from evidence and reported."""
from __future__ import annotations
import math, re

from .retrieval import search, terms

INJECTION = re.compile(
    r"(ignore|disregard|forget|override|bypass)\b.{0,40}\b(previous|prior|above|all|any|earlier|system|safety|access|polic\w*|instruction\w*|rules?)"
    r"|\b(reveal|show|print|leak|dump|exfiltrate)\b.{0,30}\b(system prompt|hidden prompt|instructions|other (client|tenant)s?|all (client|tenant)s?|api key|password|secret)"
    r"|\byou are now\b|\bact as\b|\bnew instructions?\b|\bgrant (me |the user )?(access|admin)|\bi am (an? )?(admin|administrator|client\s*\w+|from client)"
    r"|\bdeveloper mode\b|\bjailbreak\b|\bsystem prompt\b", re.I)
NEGATION = re.compile(r"\b(not|never|no|prohibited|forbidden|must not|may not|cannot|shall not)\b", re.I)
NUMBER = re.compile(r"\d+(?:[.,]\d+)?\s*(?:%|percent|days?|hours?|business days|weeks?|months?|years?|minutes?|usd|inr|eur|\$|₹)?", re.I)

REFUSAL = "The authorised documents available to you do not contain enough information to answer this question."


def is_injection(text: str) -> bool:
    return bool(INJECTION.search(text or ""))


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<![0-9])(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if len(p.strip()) > 15]


def _numbers(s: str) -> frozenset:
    return frozenset(re.sub(r"[\s,]", "", m.group(0).lower()) for m in NUMBER.finditer(s) if re.search(r"\d", m.group(0)))


def _jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def _candidates(hits, qterms):
    """Best qualifying sentence per chunk, dropping instruction-like sentences."""
    need = max(1, math.ceil(0.6 * len(qterms)))
    out, flagged = [], 0
    for h in hits:
        best = None
        context = set(terms(h["section"] or ""))  # a sentence under "Refund window" is about refund windows
        for s in sentences(h["text"]):
            if is_injection(s):
                flagged += 1
                continue
            st = set(terms(s)) | context
            m = len(st & set(qterms))
            if m >= need and (best is None or m > best[0]):
                best = (m, s, st)
        if best:
            out.append({"hit": h, "sentence": best[1], "terms": best[2], "matched": best[0]})
    return out, flagged


def _cite(h, quote) -> dict:
    return {"chunk_id": h["id"], "document_id": h["document_id"], "title": h["title"], "version_id": h["version_id"],
            "version_no": h["version_no"], "page": h["page"], "section": h["section"],
            "char_start": h["char_start"], "char_end": h["char_end"], "quote": quote,
            "shared_from": h["owner_name"] if h["owner_tenant_id"] != h.get("_ctx_tenant") else None}


def _conflicts(cands):
    found = []
    for i in range(len(cands)):
        for j in range(i + 1, len(cands)):
            a, b = cands[i], cands[j]
            if a["hit"]["document_id"] == b["hit"]["document_id"]:
                continue
            ta = {t for t in a["terms"] if not t.isdigit()}
            tb = {t for t in b["terms"] if not t.isdigit()}
            if _jaccard(ta, tb) < 0.4:
                continue
            na, nb = _numbers(a["sentence"]), _numbers(b["sentence"])
            numeric = bool(na and nb and na != nb)
            polarity = bool(NEGATION.search(a["sentence"])) != bool(NEGATION.search(b["sentence"])) and _jaccard(ta, tb) >= 0.5
            if numeric or polarity:
                found.append((a, b, "value_mismatch" if numeric else "polarity_mismatch"))
    return found


def answer_question(conn, tenant_id: str, question: str, at: str | None = None) -> dict:
    qterms = list(dict.fromkeys(terms(question)))
    hits = search(conn, tenant_id, question, k=8, at=at)
    for h in hits:
        h["_ctx_tenant"] = tenant_id
    cands, flagged = _candidates(hits, qterms)
    base = {"question_flagged": is_injection(question), "flagged_document_sentences": flagged, "retrieved": [h["id"] for h in hits]}
    if not qterms or not cands:
        return {**base, "outcome": "insufficient_evidence", "answer": REFUSAL, "citations": [], "conflicts": []}
    conflicts = _conflicts(cands)
    if conflicts:
        involved, seen = [], set()
        for a, b, _ in conflicts:
            for c in (a, b):
                if c["hit"]["id"] not in seen:
                    seen.add(c["hit"]["id"])
                    involved.append(c)
        cites = [_cite(c["hit"], c["sentence"]) for c in involved]
        return {**base, "outcome": "conflict_detected", "citations": cites,
                "conflicts": [{"kind": k, "sources": [_cite(a["hit"], a["sentence"]), _cite(b["hit"], b["sentence"])]} for a, b, k in conflicts],
                "answer": "The authorised sources disagree on this question, so no single answer is given. See the cited passages and confirm with the document owners."}
    cands.sort(key=lambda c: (-c["matched"], -c["hit"]["score"]))
    top = cands[:3]
    cites = [_cite(c["hit"], c["sentence"]) for c in top]
    text = " ".join(f"{c['sentence']} [{i + 1}]" for i, c in enumerate(top))
    return {**base, "outcome": "grounded", "answer": text, "citations": cites, "conflicts": []}
