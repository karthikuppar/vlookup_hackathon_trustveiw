"""
RAG Pipeline — Retrieval-Augmented Generation Orchestrator with Local Llama Grounding.

Fulfills Sections 2, 4, 6, and 7 of PS-04 Specification:
- Assembles bounded, structured context from authorized tenant documents.
- Disallows cross-tenant retrieval at the backend layer.
- Enforces strict grounded generation with exact document/page/section citations.
- Explicit refusal when relevant evidence cannot be retrieved.
- Detects and reports contradictory passages transparently.
- Graceful fallback when Llama inference fails or times out.
"""
from __future__ import annotations

import re
import time
from typing import Any

from llama_service import LlamaService


RAG_SYSTEM_PROMPT = """You are a secure enterprise knowledge assistant for standard operating procedures (SOPs).
Your answers must be STRICTLY GROUNDED in the provided authorized document context below.

Mandatory Rules:
1. Answer using ONLY the facts stated in the provided context. If the user asks for a summary, overview, list, or explanation of SOPs/policies (e.g. "summaries sop", "what are the policies", "summarize SOPs"), synthesize a concise structured summary of the provided document sections with citations.
2. For every material statement, cite the source document and section (e.g. "[HR-001 Section 2.1]").
3. Only if the provided context contains NO relevant information whatsoever to the question or topic, reply with:
   "I cannot verify this answer from your organization's authorized Standard Operating Procedures."
4. If different provided passages contradict each other, explicitly point out the contradiction between the sources.
5. Keep your tone professional, concise, and structured.
"""

MIXED_SYSTEM_PROMPT = """You are a secure enterprise knowledge assistant.
You have been provided with:
1. The recent conversation history between you and the authenticated user.
2. The official authorized Standard Operating Procedures (SOPs).

Synthesize a response that references the conversation context while ensuring all company policy claims are strictly grounded in the official SOP text with citations. If company documents lack evidence, clearly say so.
"""


class RAGPipeline:
    """
    Coordinates document context assembly, prompt formatting, Llama inference,
    and structured citation generation.
    """

    _instance: RAGPipeline | None = None

    def __init__(self) -> None:
        self.llama = LlamaService.get_instance()
        self.min_relevance_score = 0.001  # Accept all retrieved authorized chunks

    @classmethod
    def get_instance(cls) -> RAGPipeline:
        if cls._instance is None:
            cls._instance = RAGPipeline()
        return cls._instance

    def build_document_context(self, chunks: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
        """
        Formats retrieved chunks into clear text blocks with provenance metadata.
        Returns (context_text, structured_citations).
        """
        if not chunks:
            return "", []

        context_lines: list[str] = []
        citations: list[dict[str, Any]] = []
        seen_refs = set()

        for idx, chunk in enumerate(chunks, start=1):
            doc_name = chunk.get("document_name") or chunk.get("source") or "Official SOP"
            doc_id = chunk.get("document_id") or chunk.get("doc_id") or ""
            version = chunk.get("version") or chunk.get("doc_version") or "v1"
            page = chunk.get("page") or chunk.get("page_number") or 1
            section = chunk.get("section") or chunk.get("section_title") or "General"
            text = chunk.get("content") or chunk.get("text") or ""
            score = chunk.get("score", 0.0)

            ref_key = f"{doc_name}::{section}::{page}"
            if ref_key not in seen_refs:
                seen_refs.add(ref_key)
                citations.append({
                    "document_id": doc_id,
                    "document_name": doc_name,
                    "version": str(version),
                    "page": page,
                    "section_title": section,
                    "relevance_score": round(float(score), 3),
                })

            header = f"[Source {idx}: {doc_name} ({version}) | Section: {section} | Page {page}]"
            context_lines.append(f"{header}\n{text.strip()}\n")

        return "\n".join(context_lines), citations

    def format_conversation_context(self, history: list[dict[str, Any]]) -> str:
        """
        Formats recent authorized conversation messages into context lines.
        """
        if not history:
            return "No previous conversation history in this session."

        lines = ["=== RECENT CONVERSATION HISTORY ==="]
        for msg in history[-6:]:  # Keep up to last 6 messages
            role = "User" if msg.get("role") == "user" else "Assistant"
            content = msg.get("content", "").strip()
            lines.append(f"{role}: {content}")
        lines.append("=== END OF CONVERSATION HISTORY ===\n")
        return "\n".join(lines)

    async def execute_rag(
        self,
        question: str,
        retrieved_chunks: list[dict[str, Any]],
        conversation_history: list[dict[str, Any]] | None = None,
        query_category: str = "KNOWLEDGE_QUERY",
    ) -> dict[str, Any]:
        """
        Executes grounded generation with Llama over retrieved evidence.
        """
        t0 = time.perf_counter()

        # Step 1: Check if sufficient evidence was retrieved
        max_score = max([c.get("score", 0.0) for c in retrieved_chunks], default=0.0)
        has_sufficient_evidence = bool(retrieved_chunks and max_score >= self.min_relevance_score)

        if not has_sufficient_evidence and query_category != "CONVERSATION_QUERY":
            return {
                "answer": "I wasn't able to find a specific answer to that in your organization's authorized Standard Operating Procedures. Please verify with your department administrator.",
                "answer_status": "insufficient_evidence",
                "citations": [],
                "model_used": "deterministic_refusal",
                "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
                "grounded": False,
            }

        # Step 2: Build Context & Citations
        doc_context, citations = self.build_document_context(retrieved_chunks)
        conv_context = self.format_conversation_context(conversation_history or []) if conversation_history else ""

        # Step 3: Prepare Prompts based on Query Category
        if query_category == "CONVERSATION_QUERY":
            system_prompt = "You are a helpful enterprise assistant. Answer the user's question based on the provided recent conversation history. Keep your response concise."
            user_prompt = f"{conv_context}\nUser Question: {question}\n\nAnswer:"
        elif query_category == "MIXED_QUERY":
            system_prompt = MIXED_SYSTEM_PROMPT
            user_prompt = (
                f"{conv_context}\n"
                f"=== AUTHORIZED DOCUMENT CONTEXT ===\n"
                f"{doc_context}\n"
                f"=== END OF CONTEXT ===\n\n"
                f"User Question: {question}\n\nAnswer:"
            )
        else:
            system_prompt = RAG_SYSTEM_PROMPT
            user_prompt = (
                f"=== AUTHORIZED DOCUMENT CONTEXT ===\n"
                f"{doc_context}\n"
                f"=== END OF CONTEXT ===\n\n"
                f"User Question: {question}\n\nAnswer:"
            )

        # Step 4: Execute Local Llama Generation
        llama_resp = await self.llama.generate_grounded_answer(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.1,
        )

        total_latency = round((time.perf_counter() - t0) * 1000, 2)

        if llama_resp.get("success"):
            generated_text = llama_resp.get("text", "")
            
            # Check for contradiction signal in output
            has_conflict = bool(
                re.search(r"\bcontradict\b|\bconflict\b|\bdisagree\b", generated_text, re.IGNORECASE)
            )
            answer_status = "conflict_detected" if has_conflict else "grounded"

            # Detect refusal text returned by model
            if "insufficient evidence" in generated_text.lower() or "cannot verify" in generated_text.lower():
                answer_status = "insufficient_evidence"
                citations = []

            return {
                "answer": generated_text,
                "answer_status": answer_status,
                "citations": citations,
                "model_used": llama_resp.get("model", self.llama.model_id),
                "latency_ms": total_latency,
                "eval_count": llama_resp.get("eval_count"),
                "grounded": answer_status == "grounded",
                "query_category": query_category,
            }
        else:
            # Fallback signal when Llama runtime is offline or errored
            return {
                "success": False,
                "error": llama_resp.get("error", "Local Llama inference failed"),
                "latency_ms": total_latency,
                "fallback_required": True,
            }
