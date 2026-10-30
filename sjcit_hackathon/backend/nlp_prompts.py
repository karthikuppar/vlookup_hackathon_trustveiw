"""
NLP Prompts, Domain Taxonomy, Intent Definitions, and Query Normalization.

Provides:
- 100+ domain synonym mappings & spelling correction rules
- Truncated / half-cut prompt expansions
- Domain-specific prompt context injectors
- Intent classification taxonomy (Greetings, Help, Onboarding, IT Security, HR Policy,
  Finance, Ethics/Conduct, Cross-Tenant Probes, Injections)
"""
from __future__ import annotations
import re
from typing import Any

# ---------------------------------------------------------------------------
# 1. Typo & Spelling Normalization Map (Sub-millisecond dictionary lookup)
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
# Maps minimal or chopped queries into semantically rich query concepts.
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

    # Onboarding
    "first": "new employee onboarding first day checklist laptop credentials orientation manager buddy 9 00 am",
    "start": "new employee onboarding first day checklist laptop credentials orientation manager buddy 9 00 am",
    "begin": "new employee onboarding first day checklist laptop credentials orientation manager buddy 9 00 am",
    "first day": "new employee onboarding first day 9 00 am reception hr welcome laptop setup buddy lunch",
    "onboard": "new employee onboarding checklist week 1 mandatory training compliance forms manager intro",
    "onboarding": "new employee onboarding checklist week 1 mandatory training compliance forms manager intro",
    "day 1": "day one schedule 9 00 am reception hr welcome package laptop setup manager intro",
    "new employee": "new employee onboarding first day checklist orientation buddy assignment hr portal",
    "new hire": "new hire onboarding day 1 orientation it laptop credentials security training",

    # Code of Conduct & Ethics
    "conduct": "code of conduct workplace ethics harassment zero tolerance reporting confidentiality values",
    "ethics": "code of conduct workplace ethics integrity professional behavior reporting violations",
    "harass": "anti harassment policy zero tolerance reporting hr ethics hotline investigation disciplinary",
    "gift": "gift policy gifts over 50 dollars strictly prohibited disclosure manager compliance",
    "whistle": "whistleblower protection reporting ethics violation confidential non retaliation hr",
    "confidential": "confidentiality information data classification internal confidential customer pii nda",
}

# ---------------------------------------------------------------------------
# 3. Rich NLP Synonym Mapping (Expanded for High Recall)
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
# 5. Core Query Normalization & Expansion Pipeline
# ---------------------------------------------------------------------------
def normalize_query_text(query: str) -> str:
    """
    Cleans raw query, corrects known typos, and detects truncated queries.
    """
    clean = re.sub(r"[^\w\s\-\.]", " ", query.lower()).strip()
    words = clean.split()
    corrected_words = [SPELLING_CORRECTIONS.get(w, w) for w in words]
    normalized = " ".join(corrected_words)

    # Check for direct half-cut expansion match
    if normalized in HALF_CUT_EXPANSIONS:
        return HALF_CUT_EXPANSIONS[normalized]

    # Check prefix or partial phrase match
    for trigger, expansion in HALF_CUT_EXPANSIONS.items():
        if normalized == trigger or normalized.startswith(f"{trigger} ") or normalized.endswith(f" {trigger}"):
            # If query is short (< 4 words), enrich with expansion
            if len(words) <= 3:
                return f"{normalized} {expansion}"

    return normalized


def classify_user_intent(query: str) -> str:
    """
    Fast, rule-based intent classifier with zero external overhead.
    Returns: greeting | help | onboarding | it_security | hr_policy | finance |
             conduct_ethics | cross_tenant_probe | prompt_injection_probe | knowledge
    """
    q_lower = query.lower().strip()

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
    """
    Expands base tokens with rich synonyms and domain intent terms.
    Preserves original order, avoids duplicates, guarantees high recall.
    """
    expanded = list(tokens)
    seen = set(tokens)

    # 1. Synonym expansions
    for t in tokens:
        for syn in RICH_SYNONYMS.get(t, []):
            for part in syn.split():
                if part not in seen and len(part) > 2:
                    expanded.append(part)
                    seen.add(part)

    # 2. Intent-specific keyword boosts
    intent_boosters: dict[str, list[str]] = {
        "onboarding": ["onboarding", "day", "first", "checklist", "start", "orientation", "welcome", "sop"],
        "it_security": ["security", "sop", "policy", "requirements", "procedure", "support"],
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
