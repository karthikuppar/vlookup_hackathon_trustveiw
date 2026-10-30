"""
Response synthesizer — builds conversational, AI-like answers grounded
strictly in retrieved SOP chunks. Zero external LLM calls.
"""
from __future__ import annotations
import re
from typing import Any

# ---------------------------------------------------------------------------
# Intent classification (pure keyword heuristics, no ML model required)
# ---------------------------------------------------------------------------

GREETING_SIGNALS = {
    "hi", "hey", "hello", "greetings", "howdy", "sup", "yo", "good morning",
    "good afternoon", "good evening", "morning", "afternoon"
}

GREETING_RESPONSES = [
    "Hello! I'm AegisKB, your secure employee SOP assistant. What would you like to know about your organization's procedures today?",
    "Hey there! I'm here to help you navigate your company's standard operating procedures. What can I assist you with?",
    "Hi! Welcome to AegisKB. I can help you look up policies, procedures, and employee guidelines. What do you need?",
]

HELP_SIGNALS = {
    "help", "what can you do", "capabilities", "features", "what do you know",
    "tell me what you know", "what can i ask", "how to use", "guide", "assist"
}

HELP_RESPONSE = """I'm AegisKB -- your private, secure SOP assistant. Here's what I can help you with:

**[Procedures & Steps]** -- Ask "What are the steps for..." or "How do I..."
**[Policies]** -- Ask about leave, expenses, code of conduct, data handling, etc.
**[Onboarding]** -- Ask "What should I do first as a new employee?"
**[Security & Compliance]** -- Ask about access control, password policies, incident reporting
**[Contacts & Escalation]** -- Ask who to contact for IT, HR, or emergencies

All answers are strictly grounded in your organization's authorized SOP documents. I won't guess or fabricate -- if a topic isn't in your docs, I'll tell you.

What would you like to know?"""

FIRST_STEP_SIGNALS = {
    "first", "start", "begin", "onboard", "onboarding", "new employee",
    "just joined", "day one", "day 1", "new joiner", "new hire", "getting started",
    "what to do first", "where to begin", "how to start"
}

# Keyword → richer synonym expansion map for query augmentation
SYNONYM_MAP: dict[str, list[str]] = {
    "first": ["onboarding", "start", "begin", "new employee", "day one"],
    "start": ["onboarding", "first", "begin", "initial"],
    "begin": ["start", "first", "onboarding"],
    "new": ["onboarding", "hire", "joiner", "fresh"],
    "leave": ["vacation", "time off", "holiday", "absence", "pto", "annual leave"],
    "vacation": ["leave", "time off", "holiday", "annual leave", "pto"],
    "pto": ["leave", "vacation", "paid time off", "annual leave"],
    "time off": ["leave", "vacation", "pto"],
    "sick": ["illness", "medical", "health", "sick leave"],
    "expense": ["reimbursement", "claim", "allowance", "cost", "payment"],
    "reimbursement": ["expense", "claim", "allowance", "refund"],
    "password": ["credential", "login", "authentication", "access"],
    "security": ["cybersecurity", "access control", "data protection", "information security"],
    "laptop": ["device", "computer", "workstation", "equipment", "hardware"],
    "device": ["laptop", "computer", "equipment", "hardware"],
    "incident": ["breach", "violation", "issue", "event", "problem", "alert"],
    "report": ["escalate", "notify", "inform", "raise", "flag"],
    "emergency": ["urgent", "crisis", "critical", "immediate"],
    "contact": ["reach", "call", "email", "escalate", "notify"],
    "hr": ["human resources", "people team", "personnel"],
    "it": ["information technology", "tech support", "helpdesk", "technical"],
    "manager": ["supervisor", "lead", "head", "reporting manager"],
    "policy": ["procedure", "guideline", "rule", "protocol", "sop", "standard"],
    "procedure": ["policy", "guideline", "rule", "process", "sop", "steps"],
    "sop": ["standard operating procedure", "policy", "procedure", "guideline", "protocol"],
    "steps": ["procedure", "process", "how to", "instructions", "guide"],
    "how": ["procedure", "steps", "process", "instructions", "guide"],
    "access": ["permission", "authorization", "credentials", "login", "entry"],
    "data": ["information", "records", "files", "documents"],
    "travel": ["trip", "business travel", "flight", "hotel", "accommodation"],
    "meeting": ["conference", "sync", "session", "call"],
    "code of conduct": ["ethics", "behavior", "conduct", "values"],
    "ethics": ["code of conduct", "integrity", "values", "behavior"],
    "compliance": ["regulatory", "audit", "legal", "policy adherence"],
    "training": ["learning", "development", "course", "workshop", "certification"],
    "remote": ["work from home", "wfh", "telecommute", "hybrid", "off-site"],
    "wfh": ["remote", "work from home", "telecommute"],
    "salary": ["compensation", "pay", "wages", "payroll"],
    "payroll": ["salary", "compensation", "pay", "wages", "payment"],
    "probation": ["trial period", "probationary", "new hire period"],
    "performance": ["appraisal", "review", "evaluation", "assessment", "kpi"],
    "appraisal": ["performance", "review", "evaluation", "assessment"],
}


def classify_intent(question: str) -> str:
    """Classify the query intent."""
    q_lower = question.lower().strip()

    # Greeting
    for signal in GREETING_SIGNALS:
        if q_lower == signal or q_lower.startswith(signal + " ") or q_lower.endswith(" " + signal):
            return "greeting"

    # Help
    for signal in HELP_SIGNALS:
        if signal in q_lower:
            return "help"

    # Onboarding / getting-started
    for signal in FIRST_STEP_SIGNALS:
        if signal in q_lower:
            return "onboarding"

    return "knowledge"


def expand_query_tokens(tokens: list[str]) -> list[str]:
    """Augment tokens with synonyms to improve retrieval recall."""
    expanded = list(tokens)
    seen = set(tokens)
    for token in tokens:
        for synonym in SYNONYM_MAP.get(token, []):
            for part in synonym.split():
                if part not in seen:
                    expanded.append(part)
                    seen.add(part)
        # Also try the raw token mapped from compound phrases
        for phrase, synonyms in SYNONYM_MAP.items():
            if " " in phrase and phrase in " ".join(tokens):
                for s in synonyms:
                    for part in s.split():
                        if part not in seen:
                            expanded.append(part)
                            seen.add(part)
    return expanded


# ---------------------------------------------------------------------------
# Extractive sentence scoring (picks the best N sentences from a chunk)
# ---------------------------------------------------------------------------

def _split_sentences(text: str) -> list[str]:
    """Split text into sentences, preserving numbering / bullets."""
    # Split on sentence-ending punctuation followed by whitespace, or newlines
    parts = re.split(r"(?<=[.!?])\s+|\n{1,}", text)
    return [p.strip() for p in parts if len(p.strip()) > 10]


def _score_sentence(sentence: str, query_tokens: list[str]) -> float:
    """Quick lexical relevance of a single sentence."""
    sl = sentence.lower()
    score = sum(1.5 for t in query_tokens if t in sl)
    # Bonus for numbered steps at start (structured info)
    if re.match(r"^\d+[\.\)]", sentence.strip()):
        score += 0.8
    # Bonus for action verbs typical in SOPs
    for verb in ("must", "should", "required", "ensure", "submit", "contact", "report", "use", "request", "complete"):
        if verb in sl:
            score += 0.4
            break
    return score


def extract_key_sentences(chunk_text: str, query_tokens: list[str], max_sentences: int = 4) -> str:
    """Return the most relevant sentences from a chunk."""
    sentences = _split_sentences(chunk_text)
    if not sentences:
        return chunk_text

    scored = [(s, _score_sentence(s, query_tokens)) for s in sentences]
    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[:max_sentences]

    # Restore original order for readability
    originals_in_order = [s for s, _ in sorted(top, key=lambda x: sentences.index(x[0]))]
    return " ".join(originals_in_order)


# ---------------------------------------------------------------------------
# Conversational answer templates
# ---------------------------------------------------------------------------

_GROUNDED_INTRO_TEMPLATES = [
    "Based on your organization's **{title}**, here's what you need to know:",
    "According to **{title}** (v{version}), here is the relevant guidance:",
    "Your SOP documents have clear guidance on this. From **{title}**:",
    "Here's what your company's official documentation says, sourced from **{title}**:",
    "Great question — I found this in **{title}** (v{version}):",
]

_SUPPLEMENTARY_INTRO = [
    "Additionally, **{title}** adds:",
    "Your documents also reference this in **{title}**:",
    "For more context, **{title}** states:",
]

import hashlib


def _pick_template(templates: list[str], seed_str: str) -> str:
    """Deterministically rotate templates based on a seed (no randomness)."""
    idx = int(hashlib.md5(seed_str.encode()).hexdigest(), 16) % len(templates)
    return templates[idx]


def build_grounded_answer(
    query: str,
    query_tokens: list[str],
    top_chunks: list[dict[str, Any]],
) -> str:
    """
    Synthesize a fluent, conversational grounded answer from top retrieved chunks.
    No external LLM — pure template + extractive composition.
    """
    primary = top_chunks[0]
    rest = top_chunks[1:3]

    # Extract key sentences from primary chunk
    primary_extract = extract_key_sentences(primary["text"], query_tokens, max_sentences=5)

    intro = _pick_template(_GROUNDED_INTRO_TEMPLATES, query).format(
        title=primary["title"],
        version=primary["version_num"],
    )

    parts = [intro, "", primary_extract]

    # Supplementary chunks (if sufficiently different document)
    seen_docs = {primary["doc_id"]}
    for chunk in rest:
        if chunk["doc_id"] not in seen_docs and chunk.get("text"):
            supp_extract = extract_key_sentences(chunk["text"], query_tokens, max_sentences=2)
            if supp_extract and supp_extract != primary_extract:
                supp_intro = _pick_template(_SUPPLEMENTARY_INTRO, chunk["title"]).format(
                    title=chunk["title"]
                )
                parts += ["", supp_intro, "", supp_extract]
                seen_docs.add(chunk["doc_id"])

    # Closing micro-prompt to feel interactive
    parts += [
        "",
        "_Is there anything specific about this procedure you'd like me to clarify?_"
    ]

    return "\n".join(parts)


def build_insufficient_evidence_response(question: str) -> str:
    """Return a helpful, non-robotic refusal with actionable guidance."""
    q_lower = question.lower()

    # Give a tailored hint based on likely category
    hint = ""
    if any(w in q_lower for w in ("salary", "pay", "compensation", "payroll")):
        hint = "For payroll-related queries, please contact HR directly or check your payslip portal."
    elif any(w in q_lower for w in ("password", "login", "access", "vpn", "credentials")):
        hint = "For IT access issues, please raise a helpdesk ticket or contact the IT support team."
    elif any(w in q_lower for w in ("leave", "vacation", "pto", "time off", "sick")):
        hint = "For leave-related queries, check the HR portal or speak with your reporting manager."
    elif any(w in q_lower for w in ("benefit", "health", "insurance", "medical")):
        hint = "For benefits and insurance queries, please reach out to the HR department."

    response = (
        "I wasn't able to find a specific answer to that in your organization's authorized SOP documents.\n\n"
        "This could mean:\n"
        "- The topic hasn't been documented in the current knowledge base yet\n"
        "- It may be covered under a different term or document section\n"
        "- The document may not have been uploaded to AegisKB yet\n\n"
    )
    if hint:
        response += f"💡 **Suggestion:** {hint}\n\n"
    response += (
        "You can try rephrasing your question or asking your team admin to upload the relevant SOP document. "
        "I'm here to help when the information is available!"
    )
    return response


def build_conflict_response(conflict_summary: str) -> str:
    return (
        "⚠️ **Conflicting Guidelines Detected**\n\n"
        "I found relevant information in your SOP documents, but the sources appear to contradict each other on this topic:\n\n"
        f"{conflict_summary}\n\n"
        "**What this means for you:** Please review the cited document versions carefully and consult your team admin or compliance officer for the authoritative ruling. "
        "Using outdated or superseded guidelines may cause compliance issues.\n\n"
        "_Tip: An admin can archive the outdated document version to resolve this conflict in AegisKB._"
    )
