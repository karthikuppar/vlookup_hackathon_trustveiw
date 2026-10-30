"""
Query Router — Classifies incoming chat requests for targeted processing.

Fulfills Section 5 of PS-04 Specification:
- Category A: KNOWLEDGE_QUERY (policies, SOPs, operational procedures, security, guidelines)
- Category B: CONVERSATION_QUERY (chat history summaries, earlier discussions, greetings, session recalls)
- Category C: MIXED_QUERY (references to past discussion joined with document knowledge)

Provides deterministic, fast classification (<1ms) without external cloud dependencies.
"""
from __future__ import annotations

import re
from typing import Any


class QueryCategory:
    KNOWLEDGE_QUERY = "KNOWLEDGE_QUERY"
    CONVERSATION_QUERY = "CONVERSATION_QUERY"
    MIXED_QUERY = "MIXED_QUERY"


# Signals indicating inquiry about conversation history
CONVERSATION_SIGNALS = [
    r"\bearlier\b",
    r"\bwe discussed\b",
    r"\bwe talked about\b",
    r"\bour discussion\b",
    r"\bour conversation\b",
    r"\bsummarize (our|the|this) (chat|discussion|conversation)\b",
    r"\bwhat did i (ask|say)\b",
    r"\bprevious (message|question|answer|topic)\b",
    r"\blast question\b",
    r"\brepeat that\b",
    r"\bwhat was my\b",
    r"\bhi\b|\bhello\b|\bhey\b|\bgreetings\b|\bthank you\b|\bthanks\b",
]

# Signals indicating inquiry into standard knowledge base documents
KNOWLEDGE_SIGNALS = [
    r"\bsop\b",
    r"\bpolicy\b|\bpolicies\b",
    r"\bprocedure\b|\bprocedures\b",
    r"\bguideline\b|\bguidelines\b",
    r"\brule\b|\brules\b",
    r"\bsecurity\b",
    r"\bleave\b|\bvacation\b|\bsick\b",
    r"\bexpense\b|\breimbursement\b|\binvoice\b",
    r"\bonboarding\b|\borientation\b",
    r"\bconduct\b|\bethics\b",
    r"\bcompliance\b",
    r"\bretention\b",
    r"\baccess control\b",
    r"\bpassword\b|\bmfa\b",
    r"\bhow do i\b|\bwhat is the process\b|\bwhat are the steps\b",
    r"\bdocument\b|\bsection\b|\bclause\b",
]


class QueryRouter:
    """
    Categorizes chat requests into Knowledge, Conversation, or Mixed modes.
    """

    @classmethod
    def classify(cls, question: str) -> dict[str, Any]:
        """
        Classifies query text and returns routing metadata.
        """
        cleaned = question.strip().lower()

        has_conv_signal = any(re.search(pat, cleaned) for pat in CONVERSATION_SIGNALS)
        has_know_signal = any(re.search(pat, cleaned) for pat in KNOWLEDGE_SIGNALS)

        # Distinguish Mixed vs Pure Conversation vs Pure Knowledge
        if has_conv_signal and has_know_signal:
            category = QueryCategory.MIXED_QUERY
            confidence = 0.90
            requires_doc_retrieval = True
            requires_conv_history = True
            description = "Query references previous conversation context and asks for document SOP facts."
        elif has_conv_signal:
            category = QueryCategory.CONVERSATION_QUERY
            confidence = 0.92
            requires_doc_retrieval = False
            requires_conv_history = True
            description = "Query concerns session conversation history or conversational greeting."
        else:
            # Default to Knowledge query for enterprise SOP assistant
            category = QueryCategory.KNOWLEDGE_QUERY
            confidence = 0.88 if has_know_signal else 0.75
            requires_doc_retrieval = True
            requires_conv_history = False
            description = "Query targets official organization Standard Operating Procedures and policies."

        return {
            "category": category,
            "confidence": confidence,
            "requires_document_retrieval": requires_doc_retrieval,
            "requires_conversation_history": requires_conv_history,
            "description": description,
        }
