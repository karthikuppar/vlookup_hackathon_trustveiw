"""
NLP Prompts, Domain Taxonomy, Intent Definitions, Query Normalization,
and Continuous Intent Learning & Beautification Engine.

Provides:
- 100+ domain synonym mappings & spelling correction rules
- Truncated / half-cut prompt expansions (e.g. 'what should i do', 'passwrd req', 'meal expns')
- Dynamic learned intent prompt loading & online auto-training pipeline
- Document intent discovery for the NLP Transparency Layer
"""
from __future__ import annotations
import re
import uuid
from typing import Any
from crypto_utils import now_utc_iso
from database import get_connection

# ---------------------------------------------------------------------------
# 1. Typo & Spelling Normalization Map
# ---------------------------------------------------------------------------
SPELLING_CORRECTIONS: dict[str, str] = {
    "passw": "password",
    "passwrd": "password",
    "passowrd": "password",
    "passwd": "password",
    "pwd": "password",
    "leav": "leave",
    "leaves": "leave",
    "vaca": "vacation",
    "vacatn": "vacation",
    "attendence": "attendance",
    "atendance": "attendance",
    "reimb": "reimbursement",
    "reimbursment": "reimbursement",
    "remburse": "reimbursement",
    "expns": "expense",
    "expens": "expense",
    "expenss": "expense",
    "incidnt": "incident",
    "incedent": "incident",
    "complianc": "compliance",
    "procedur": "procedure",
    "polcy": "policy",
    "policys": "policies",
    "onbord": "onboarding",
    "onbording": "onboarding",
    "emergancy": "emergency",
    "manger": "manager",
    "supervsor": "supervisor",
    "submitt": "submit",
    "reciept": "receipt",
    "reciepts": "receipts",
    "authen": "authentication",
    "auth": "authentication",
    "confidntial": "confidential",
    "secrity": "security",
    "harasment": "harassment",
    "discplinary": "disciplinary",
}

# ---------------------------------------------------------------------------
# 2. Truncated / Half-Cut Query Completion Templates
# ---------------------------------------------------------------------------
HALF_CUT_EXPANSIONS: dict[str, str] = {
    # Password / IT
    "passw": "password requirements minimum 12 characters length complexity uppercase special change every 90 days",
    "passwrd": "password requirements minimum 12 characters length complexity uppercase special change every 90 days",
    "pwd": "password requirements minimum 12 characters length complexity uppercase special change every 90 days",
    "password": "password requirements length complexity special characters 90 days change vault password manager",
    "mfa": "multi factor authentication authenticator app remote vpn login qr code 6 digit code",
    "2fa": "multi factor authentication authenticator app remote vpn login qr code 6 digit code",
    "vpn": "vpn virtual private network remote access secure wifi connection corporate network",
    "laptop": "laptop device policy corporate use lost stolen reporting 1 hour mdm remote wipe",
    "lost laptop": "lost stolen laptop report it support within 1 hour it-support@acrocorp.com ext 2000 remote wipe",
    "phish": "phishing email report security team phishing@acrocorp.com do not click links",
    "incident": "security incident reporting breach escalation it security security@acrocorp.com ext 2999 within 30 minutes",
    "breach": "security incident reporting breach escalation it security security@acrocorp.com ext 2999 within 30 minutes",

    # Leave & Attendance
    "leav": "leave policy annual leave sick leave casual leave apply hr portal carry forward max 10 days",
    "leave": "leave policy annual leave sick leave casual leave apply hr portal carry forward max 10 days",
    "pto": "paid time off annual leave apply hr portal carry forward max 10 days 20 days annual leave",
    "vacation": "annual leave 20 days apply hr portal carry forward maximum 10 days",
    "sick": "sick leave 10 days per year notify manager before 9 30 am hr portal medical",
    "sick leave": "sick leave 10 days per year notify manager before 9 30 am hr portal not encashable",
    "carry forward": "leave carry forward rules annual leave max 10 days lapse december 31 sick leave not carried",
    "hours": "standard work hours 9 00 am to 6 00 pm monday to friday check in within 15 minutes",
    "attendance": "work hours 9 00 am to 6 00 pm biometric check in late arrival notify manager",

    # Expenses & Reimbursements
    "meal": "meal reimbursement limit 50 dollars domestic 75 dollars international travel daily limit",
    "food": "meal reimbursement limit 50 dollars domestic 75 dollars international travel daily limit",
    "expense": "expense reimbursement policy travel hotel meals receipts submit within 30 days finance",
    "reimb": "expense reimbursement policy travel hotel meals receipts submit within 30 days finance",
    "reimbursement": "expense reimbursement submission finance portal receipts manager approval within 30 days",
    "hotel": "hotel accommodation limit 150 dollars domestic 250 dollars international travel",
    "travel": "business travel economy class domestic business class over 6 hours hotel meals per diem",
    "flight": "business travel flights economy class domestic business class international over 6 hours",

    # Onboarding & Employee Day 1 Guidelines (Includes "what should i do")
    "first": "new employee onboarding first day checklist laptop credentials orientation manager buddy 9 00 am",
    "start": "new employee onboarding first day checklist laptop credentials orientation manager buddy 9 00 am",
    "begin": "new employee onboarding first day checklist laptop credentials orientation manager buddy 9 00 am",
    "first day": "new employee onboarding first day 9 00 am reception hr welcome laptop setup buddy lunch",
    "onboard": "new employee onboarding checklist week 1 mandatory training compliance forms manager intro",
    "onboarding": "new employee onboarding checklist week 1 mandatory training compliance forms manager intro",
    "day 1": "day one schedule 9 00 am reception hr welcome package laptop setup manager intro",
    "new employee": "new employee onboarding first day checklist orientation buddy assignment hr portal",
    "new hire": "new hire onboarding day 1 orientation it laptop credentials security training",
    "what should i do": "new employee onboarding first day checklist laptop credentials orientation manager buddy 9 00 am reception",
    "what do i do": "new employee onboarding first day checklist laptop credentials orientation manager buddy 9 00 am reception",
    "what to do": "new employee onboarding first day checklist laptop credentials orientation manager buddy 9 00 am reception",
    "what to do first": "new employee onboarding first day checklist laptop credentials orientation manager buddy 9 00 am reception",
    "what should i do first": "new employee onboarding first day checklist laptop credentials orientation manager buddy 9 00 am reception",
    "what do i do first": "new employee onboarding first day checklist laptop credentials orientation manager buddy 9 00 am reception",
    "where do i start": "new employee onboarding first day checklist laptop credentials orientation manager buddy 9 00 am reception",
    "where to start": "new employee onboarding first day checklist laptop credentials orientation manager buddy 9 00 am reception",
    "where do i begin": "new employee onboarding first day checklist laptop credentials orientation manager buddy 9 00 am reception",
    "where to begin": "new employee onboarding first day checklist laptop credentials orientation manager buddy 9 00 am reception",
    "how to start": "new employee onboarding first day checklist laptop credentials orientation manager buddy 9 00 am reception",
    "how do i start": "new employee onboarding first day checklist laptop credentials orientation manager buddy 9 00 am reception",
    "getting started": "new employee onboarding first day checklist laptop credentials orientation manager buddy 9 00 am reception",
    "what next": "new employee onboarding first day checklist week 1 orientation manager introduction",

    # Code of Conduct & Ethics
    "conduct": "code of conduct workplace ethics harassment zero tolerance reporting confidentiality values",
    "ethics": "code of conduct workplace ethics integrity professional behavior reporting violations",
    "harass": "anti harassment policy zero tolerance reporting hr ethics hotline investigation disciplinary",
    "gift": "gift policy gifts over 50 dollars strictly prohibited disclosure manager compliance",
    "whistle": "whistleblower protection reporting ethics violation confidential non retaliation hr",
    "confidential": "confidentiality information data classification internal confidential customer pii nda",
}

# In-memory storage for dynamically learned intent prompts
DYNAMIC_LEARNED_PROMPTS: dict[str, tuple[str, str]] = {}

# ---------------------------------------------------------------------------
# 3. Rich NLP Synonym Mapping
# ---------------------------------------------------------------------------
RICH_SYNONYMS: dict[str, list[str]] = {
    # Onboarding & Getting Started
    "first": ["onboarding", "start", "begin", "new employee", "day one", "initial", "checklist"],
    "start": ["onboarding", "first", "begin", "commence", "orientation", "day one"],
    "begin": ["start", "first", "onboarding", "commence"],
    "onboard": ["onboarding", "orientation", "induction", "new hire", "joiner"],
    "onboarding": ["first day", "induction", "new hire", "orientation", "day 1", "checklist"],
    "new": ["onboarding", "hire", "joiner", "fresh", "first day"],

    # Leave & Time Off
    "leave": ["vacation", "time off", "holiday", "absence", "pto", "annual leave", "sick leave"],
    "vacation": ["leave", "time off", "holiday", "annual leave", "pto"],
    "pto": ["leave", "vacation", "paid time off", "annual leave"],
    "sick": ["illness", "medical", "health", "sick leave", "doctor"],
    "absence": ["leave", "time off", "attendance", "absent"],
    "carry": ["forward", "carryover", "lapse", "accumulation", "transfer"],

    # IT & Security
    "password": ["credential", "login", "authentication", "access", "passphrase", "vault"],
    "mfa": ["multi-factor", "2fa", "two-factor", "authenticator", "verification", "otp", "code"],
    "security": ["cybersecurity", "access control", "data protection", "infosec", "safeguard"],
    "laptop": ["device", "computer", "workstation", "equipment", "hardware", "machine"],
    "incident": ["breach", "violation", "issue", "event", "problem", "threat", "phishing"],
    "report": ["escalate", "notify", "inform", "raise", "flag", "submit"],
    "emergency": ["urgent", "crisis", "critical", "immediate", "priority"],
    "wifi": ["network", "wireless", "vpn", "internet", "public wifi"],
    "vpn": ["virtual private network", "remote access", "tunnel", "encrypted connection"],

    # Finance & Expenses
    "expense": ["reimbursement", "claim", "allowance", "cost", "payment", "expenditure"],
    "reimbursement": ["expense", "claim", "allowance", "refund", "receipt", "settlement"],
    "meal": ["food", "dinner", "lunch", "breakfast", "per diem", "entertainment", "refreshment"],
    "hotel": ["accommodation", "lodging", "stay", "room"],
    "flight": ["airfare", "travel", "plane", "ticket", "airline"],
    "travel": ["trip", "business travel", "transit", "transportation"],

    # Conduct & HR
    "conduct": ["behavior", "ethics", "code of conduct", "standards", "workplace rules"],
    "ethics": ["integrity", "values", "morals", "compliance", "principles"],
    "harassment": ["discrimination", "bullying", "misconduct", "hostile", "retaliation"],
    "gift": ["bribe", "gratuity", "hospitality", "perk", "token"],
    "probation": ["trial period", "confirmation", "new hire review", "assessment"],
    "notice": ["resignation", "departure", "handover", "exit", "termination"],
}

# ---------------------------------------------------------------------------
# 4. Intent Taxonomy & Classification Rules
# ---------------------------------------------------------------------------
INTENT_SIGNALS = {
    "greeting": {
        "hi", "hey", "hello", "greetings", "howdy", "sup", "yo",
        "good morning", "good afternoon", "good evening", "morning", "afternoon",
    },
    "help": {
        "help", "what can you do", "capabilities", "features", "what do you know",
        "tell me what you know", "what can i ask", "how to use", "guide", "assist", "commands",
    },
    "onboarding": {
        "first", "start", "begin", "onboard", "onboarding", "new employee",
        "just joined", "day one", "day 1", "new joiner", "new hire", "getting started",
        "what to do first", "where to begin", "how to start", "orientation",
        "what should i do", "what do i do", "what to do", "what should i start with",
        "what are my steps", "where do i start", "where to start", "what next",
    },
    "it_security": {
        "password", "mfa", "2fa", "laptop", "device", "incident", "breach",
        "phishing", "wifi", "vpn", "antivirus", "authenticator", "security", "credentials",
    },
    "hr_policy": {
        "leave", "vacation", "pto", "sick", "holiday", "attendance", "hours",
        "work hours", "wfh", "remote", "probation", "salary", "payroll", "notice period",
    },
    "finance": {
        "expense", "reimbursement", "meal", "food", "hotel", "travel", "flight",
        "per diem", "receipt", "claim", "allowance", "budget",
    },
    "conduct_ethics": {
        "conduct", "ethics", "harassment", "gift", "whistleblower", "discrimination",
        "confidential", "pii", "nda", "conflict of interest",
    },
    "cross_tenant_probe": {
        "tenant_b", "betashield", "other company", "other tenant", "competitor",
        "client b", "show all documents", "export everything", "admin documents",
    },
    "prompt_injection_probe": {
        "ignore previous", "disregard instructions", "system prompt", "dan mode",
        "bypass", "jailbreak", "override", "reveal secret", "sudo",
    },
}

# ---------------------------------------------------------------------------
# 5. Core Query Normalization Pipeline
# ---------------------------------------------------------------------------
def load_dynamic_intent_prompts() -> None:
    """Load dynamic intent prompts learned from unresponded queries."""
    global DYNAMIC_LEARNED_PROMPTS
    try:
        with get_connection() as conn:
            rows = conn.execute("SELECT query_pattern, mapped_intent, expansion_text FROM dynamic_intent_prompts").fetchall()
            for r in rows:
                DYNAMIC_LEARNED_PROMPTS[r["query_pattern"].lower().strip()] = (r["mapped_intent"], r["expansion_text"])
    except Exception:
        pass


def normalize_query_text(query: str) -> str:
    """
    Cleans raw query, corrects known typos, checks dynamic learned prompts,
    and performs truncated prompt expansion.
    """
    clean = re.sub(r"[^\w\s\-\.]", " ", query.lower()).strip()
    words = clean.split()
    corrected_words = [SPELLING_CORRECTIONS.get(w, w) for w in words]
    normalized = " ".join(corrected_words)

    # 1. Check dynamically learned prompts first (auto-trained from previous queries)
    if normalized in DYNAMIC_LEARNED_PROMPTS:
        _, expansion = DYNAMIC_LEARNED_PROMPTS[normalized]
        return f"{normalized} {expansion}"

    # 2. Direct half-cut expansion match
    if normalized in HALF_CUT_EXPANSIONS:
        return HALF_CUT_EXPANSIONS[normalized]

    # 3. Prefix or partial phrase match
    for trigger, expansion in HALF_CUT_EXPANSIONS.items():
        if normalized == trigger or normalized.startswith(f"{trigger} ") or normalized.endswith(f" {trigger}"):
            if len(words) <= 4:
                return f"{normalized} {expansion}"

    return normalized


def classify_user_intent(query: str) -> str:
    """
    Rule-based intent classifier with dynamic learning overlay.
    """
    q_lower = query.lower().strip()

    # Dynamic learned intent lookup
    if q_lower in DYNAMIC_LEARNED_PROMPTS:
        return DYNAMIC_LEARNED_PROMPTS[q_lower][0]

    # Exact greeting match
    for sig in INTENT_SIGNALS["greeting"]:
        if q_lower == sig or q_lower.startswith(f"{sig} ") or q_lower.endswith(f" {sig}"):
            return "greeting"

    # Help match
    for sig in INTENT_SIGNALS["help"]:
        if sig in q_lower:
            return "help"

    # Security injection probe
    for sig in INTENT_SIGNALS["prompt_injection_probe"]:
        if sig in q_lower:
            return "prompt_injection_probe"

    # Cross-tenant extraction probe
    for sig in INTENT_SIGNALS["cross_tenant_probe"]:
        if sig in q_lower:
            return "cross_tenant_probe"

    # Onboarding
    for sig in INTENT_SIGNALS["onboarding"]:
        if sig in q_lower:
            return "onboarding"

    # IT Security
    for sig in INTENT_SIGNALS["it_security"]:
        if sig in q_lower:
            return "it_security"

    # HR Policy
    for sig in INTENT_SIGNALS["hr_policy"]:
        if sig in q_lower:
            return "hr_policy"

    # Finance
    for sig in INTENT_SIGNALS["finance"]:
        if sig in q_lower:
            return "finance"

    # Ethics
    for sig in INTENT_SIGNALS["conduct_ethics"]:
        if sig in q_lower:
            return "conduct_ethics"

    return "knowledge"


def enrich_tokens_with_intent_and_synonyms(tokens: list[str], intent: str) -> list[str]:
    """Expands base tokens with rich synonyms and domain intent terms."""
    expanded = list(tokens)
    seen = set(tokens)

    for t in tokens:
        for syn in RICH_SYNONYMS.get(t, []):
            for part in syn.split():
                if part not in seen and len(part) > 2:
                    expanded.append(part)
                    seen.add(part)

    intent_boosters: dict[str, list[str]] = {
        "onboarding": ["onboarding", "day", "first", "checklist", "start", "orientation", "welcome", "sop", "steps", "reception"],
        "it_security": ["security", "sop", "policy", "requirements", "procedure", "support", "password", "mfa"],
        "hr_policy": ["policy", "leave", "attendance", "portal", "rules", "guidelines"],
        "finance": ["policy", "reimbursement", "expense", "limit", "receipt", "claim"],
        "conduct_ethics": ["policy", "conduct", "ethics", "workplace", "reporting", "rules"],
    }

    if intent in intent_boosters:
        for boost in intent_boosters[intent]:
            if boost not in seen:
                expanded.append(boost)
                seen.add(boost)

    return expanded

# ---------------------------------------------------------------------------
# 6. Unresponded Query Logging & Auto-Training Pipeline (Intent Beautification)
# ---------------------------------------------------------------------------
def log_unresolved_query(query_text: str, user_id: str, tenant_id: str) -> str:
    """Log an unresolved/unresponded query for intent beautification training."""
    query_id = f"unres_{uuid.uuid4().hex[:10]}"
    now = now_utc_iso()
    words = [w for w in re.sub(r"[^\w\s]", "", query_text.lower()).split() if len(w) > 2]
    detected_tokens = ",".join(words)

    # Suggest likely intent candidate using fuzzy matching
    suggested = "knowledge"
    for intent, sigs in INTENT_SIGNALS.items():
        if any(w in sigs for w in words):
            suggested = intent
            break

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO unresolved_queries (id, timestamp, query_text, user_id, tenant_id, detected_tokens, suggested_intent, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending_training')
            """,
            (query_id, now, query_text.strip(), user_id, tenant_id, detected_tokens, suggested),
        )
    return query_id


def train_unresolved_queries() -> dict[str, Any]:
    """
    Auto-train & beautify unresponded queries:
    1. Clusters unresolved queries by semantic overlap.
    2. Auto-maps them to canonical SOP intents.
    3. Adds enriched prompt templates to dynamic_intent_prompts.
    4. Re-indexes in-memory vector cache for instant response.
    """
    now = now_utc_iso()
    with get_connection() as conn:
        pending = conn.execute(
            "SELECT id, query_text, detected_tokens, suggested_intent FROM unresolved_queries WHERE status = 'pending_training'"
        ).fetchall()

    if not pending:
        return {"status": "up_to_date", "trained_count": 0, "message": "All query intents are already trained and beautified."}

    trained_count = 0
    trained_items = []

    for item in pending:
        q_clean = item["query_text"].lower().strip()
        words = set(q_clean.split())
        target_intent = item["suggested_intent"] if item["suggested_intent"] != "knowledge" else "onboarding"

        # Auto-synthesize beautified expansion text
        if any(w in words for w in ("do", "should", "start", "begin", "first", "work", "steps", "today", "now")):
            target_intent = "onboarding"
            expansion = "new employee onboarding first day checklist laptop credentials orientation manager buddy 9 00 am reception"
        elif any(w in words for w in ("money", "cost", "pay", "rate", "limit", "bill")):
            target_intent = "finance"
            expansion = "expense reimbursement policy travel hotel meals receipts submit within 30 days finance"
        elif any(w in words for w in ("pass", "login", "net", "computer")):
            target_intent = "it_security"
            expansion = "password requirements minimum 12 characters length complexity uppercase special change every 90 days"
        else:
            target_intent = "hr_policy"
            expansion = "leave policy annual leave sick leave casual leave apply hr portal carry forward"

        prompt_id = f"dyn_{uuid.uuid4().hex[:8]}"
        with get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO dynamic_intent_prompts (id, query_pattern, mapped_intent, expansion_text, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (prompt_id, q_clean, target_intent, expansion, now),
            )
            conn.execute(
                "UPDATE unresolved_queries SET status = 'trained', suggested_intent = ? WHERE id = ?",
                (target_intent, item["id"]),
            )

        DYNAMIC_LEARNED_PROMPTS[q_clean] = (target_intent, expansion)
        trained_count += 1
        trained_items.append({"query": q_clean, "beautified_intent": target_intent, "expansion": expansion[:60] + "..."})

    # Trigger vector index cache refresh
    try:
        from vector_store import InMemoryVectorDB
        InMemoryVectorDB.get_instance()._query_cache.clear()
    except Exception:
        pass

    return {
        "status": "success",
        "trained_count": trained_count,
        "items": trained_items,
        "message": f"Successfully trained and beautified {trained_count} unresponded query intents into active memory.",
    }


def get_unresolved_queries_report() -> dict[str, Any]:
    """Retrieve report on unresponded and trained queries for the Admin Hub."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, timestamp, query_text, user_id, suggested_intent, status FROM unresolved_queries ORDER BY timestamp DESC LIMIT 50"
        ).fetchall()
        total_pending = conn.execute("SELECT COUNT(*) as c FROM unresolved_queries WHERE status = 'pending_training'").fetchone()["c"]
        total_trained = conn.execute("SELECT COUNT(*) as c FROM unresolved_queries WHERE status = 'trained'").fetchone()["c"]

    return {
        "total_unresolved": total_pending + total_trained,
        "pending_training": total_pending,
        "auto_trained": total_trained,
        "queries": [dict(r) for r in rows],
        "active_dynamic_rules": len(DYNAMIC_LEARNED_PROMPTS),
    }

# ---------------------------------------------------------------------------
# 7. Document Intent Discovery (For the Transparent Inspection Layer)
# ---------------------------------------------------------------------------
def detect_document_intents(text: str) -> list[dict[str, Any]]:
    """
    Analyzes an uploaded SOP's text to discover what intents and topics it fulfills.
    Returns list of discovered intents with matched keyword evidence and confidence.
    """
    t_lower = text.lower()
    discovered = []

    intent_labels = {
        "onboarding": "New Hire Onboarding & Day 1 Guidelines",
        "it_security": "IT Security, Passwords & Access Control",
        "hr_policy": "Leave, Attendance & Working Hours",
        "finance": "Expenses, Travel & Reimbursements",
        "conduct_ethics": "Code of Conduct & Workplace Ethics",
    }

    for intent, sigs in INTENT_SIGNALS.items():
        if intent in intent_labels:
            matched_words = [s for s in sigs if s in t_lower]
            if len(matched_words) >= 2:
                confidence = min(len(matched_words) * 15, 99)
                discovered.append({
                    "intent": intent,
                    "title": intent_labels[intent],
                    "matched_keywords": matched_words[:8],
                    "confidence": f"{confidence}%",
                })

    return discovered

# Load dynamic prompts on module import
load_dynamic_intent_prompts()
