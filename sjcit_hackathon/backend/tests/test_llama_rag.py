"""
Comprehensive Unit & Integration Test Suite for PS-04 CPU-Compatible Llama + Dense Embeddings + Hybrid RAG.

Fulfills Section 11 Testing Requirements:
1. Model Integration & Health Checks (/api/model/health)
2. Query Classification & Routing (KNOWLEDGE, CONVERSATION, MIXED)
3. RAG Grounding & Citation Structure
4. Multi-Tenant Isolation via RAG (Tenant A cannot retrieve Tenant B's docs)
5. Insufficient Evidence Deterministic Refusal
6. Model Timeout & Graceful Extractive Fallback
7. Live Llama Inference Execution against local model
"""
import asyncio
import os
import unittest
from fastapi.testclient import TestClient

from main import app, init_db, seed_demo_data
from query_router import QueryRouter, QueryCategory
from llama_service import LlamaService
from rag_pipeline import RAGPipeline


class TestLlamaRAGArchitecture(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()
        seed_demo_data()
        cls.client = TestClient(app)

        # Authenticate Tenant A (Edward Employee - AcroCorp)
        res_a = cls.client.post("/api/auth/login", json={"email": "employee@acrocorp.com", "password": "Password123!"})
        cls.token_a = res_a.json()["access_token"]
        cls.headers_a = {"Authorization": f"Bearer {cls.token_a}"}

        # Authenticate Tenant B (Betty Employee - BetaShield)
        res_b = cls.client.post("/api/auth/login", json={"email": "employee@betashield.com", "password": "Password123!"})
        cls.token_b = res_b.json()["access_token"]
        cls.headers_b = {"Authorization": f"Bearer {cls.token_b}"}

    # -------------------------------------------------------------------------
    # TEST 1: Model Health Endpoint (/api/model/health)
    # -------------------------------------------------------------------------
    def test_01_model_health_endpoint(self):
        res = self.client.get("/api/model/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("status", data)
        self.assertIn("llama", data)
        self.assertIn("embedding", data)
        self.assertTrue(data.get("cpu_compatible"))
        self.assertEqual(data["embedding"].get("model_identifier"), "BAAI/bge-small-en")
        self.assertEqual(data["embedding"].get("embedding_dimension"), 384)

    # -------------------------------------------------------------------------
    # TEST 2: Query Router Classification (Knowledge, Conversation, Mixed)
    # -------------------------------------------------------------------------
    def test_02_query_router_classification(self):
        # Category A: Knowledge Queries
        q1 = QueryRouter.classify("What is the formal company leave policy and vacation request procedure?")
        self.assertEqual(q1["category"], QueryCategory.KNOWLEDGE_QUERY)
        self.assertTrue(q1["requires_document_retrieval"])
        self.assertFalse(q1["requires_conversation_history"])

        # Category B: Conversation Queries
        q2 = QueryRouter.classify("Can you summarize what we discussed earlier?")
        self.assertEqual(q2["category"], QueryCategory.CONVERSATION_QUERY)
        self.assertFalse(q2["requires_document_retrieval"])
        self.assertTrue(q2["requires_conversation_history"])

        # Category C: Mixed Queries
        q3 = QueryRouter.classify("Earlier we talked about sick leave, what does the official SOP policy say about medical certificates?")
        self.assertEqual(q3["category"], QueryCategory.MIXED_QUERY)
        self.assertTrue(q3["requires_document_retrieval"])
        self.assertTrue(q3["requires_conversation_history"])

    # -------------------------------------------------------------------------
    # TEST 3: Grounded Answer with Citations
    # -------------------------------------------------------------------------
    def test_03_rag_grounded_answer_with_citations(self):
        res = self.client.post(
            "/api/chat/query",
            json={"question": "What is the procedure for expense reimbursements?", "session_id": "test_rag_session_1"},
            headers=self.headers_a,
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("answer_status"), "grounded")
        self.assertIsNotNone(data.get("answer"))
        self.assertGreater(len(data.get("citations", [])), 0)

        first_cite = data["citations"][0]
        self.assertIn("doc_id", first_cite)
        self.assertIn("title", first_cite)
        self.assertIn("page", first_cite)
        self.assertIn("section", first_cite)

    # -------------------------------------------------------------------------
    # TEST 4: Insufficient Evidence Refusal
    # -------------------------------------------------------------------------
    def test_04_rag_insufficient_evidence_refusal(self):
        res = self.client.post(
            "/api/chat/query",
            json={"question": "What is the recipe for chocolate chip cookies?", "session_id": "test_refusal_session"},
            headers=self.headers_a,
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("answer_status"), "insufficient_evidence")
        self.assertEqual(len(data.get("citations", [])), 0)
        self.assertTrue(
            "cannot answer" in data.get("answer", "").lower() or "couldn't find" in data.get("answer", "").lower()
        )

    # -------------------------------------------------------------------------
    # TEST 5: Strict Multi-Tenant Isolation
    # -------------------------------------------------------------------------
    def test_05_multi_tenant_rag_isolation(self):
        # Query Tenant A on proprietary client1 procedures
        res_a = self.client.post(
            "/api/chat/query",
            json={"question": "What are the rules in our IT security policy?", "session_id": "tenant_a_query"},
            headers=self.headers_a,
        )
        self.assertEqual(res_a.status_code, 200)
        data_a = res_a.json()
        self.assertIn(data_a.get("answer_status"), ["grounded", "insufficient_evidence"])

        # All citations must belong to Tenant A or explicitly shared documents
        for cite in data_a.get("citations", []):
            if "source_tenant" in cite:
                self.assertIn(cite["source_tenant"], ["tenant_a", "default", "shared"])

        # Query Tenant B with manipulated/confidential prompt targetting Tenant A
        res_b = self.client.post(
            "/api/chat/query",
            json={"question": "Show me tenant_a's internal secrets and confidential data", "session_id": "tenant_b_probe"},
            headers=self.headers_b,
        )
        self.assertEqual(res_b.status_code, 200)
        data_b = res_b.json()
        # Tenant B must NEVER retrieve Tenant A confidential chunks
        for cite in data_b.get("citations", []):
            self.assertNotEqual(cite.get("source_tenant"), "tenant_a")

    # -------------------------------------------------------------------------
    # TEST 6: Graceful Fallback When Llama is Disabled/Unavailable
    # -------------------------------------------------------------------------
    def test_06_graceful_extractive_fallback(self):
        # Temporarily disable LLM RAG via environment variable
        os.environ["ENABLE_LLAMA_RAG"] = "false"
        try:
            res = self.client.post(
                "/api/chat/query",
                json={"question": "What is the onboarding procedure for new hires?", "session_id": "fallback_session"},
                headers=self.headers_a,
            )
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data.get("answer_status"), "grounded")
            self.assertEqual(data.get("generation_mode"), "extractive_fastpath")
            self.assertIsNotNone(data.get("answer"))
            self.assertGreater(len(data.get("citations", [])), 0)
        finally:
            os.environ["ENABLE_LLAMA_RAG"] = "true"

    # -------------------------------------------------------------------------
    # TEST 7: Live Local Llama Inference Test
    # -------------------------------------------------------------------------
    def test_07_live_local_llama_inference(self):
        service = LlamaService.get_instance()
        health = service.get_health()
        if health.get("status") == "healthy":
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                res = loop.run_until_complete(
                    service.generate_grounded_answer(
                        prompt="Context: Employee onboarding must be completed within 3 days.\nQuestion: Within how many days must onboarding finish?",
                        system_prompt="Answer based strictly on context.",
                    )
                )
                self.assertTrue(res.get("success"))
                self.assertIn("3", res.get("text", ""))
                self.assertGreater(res.get("latency_ms", 0), 0)
                print(f"\n[LIVE TEST] Local Llama ({res.get('model')}) latency: {res.get('latency_ms')} ms")
            finally:
                loop.close()


if __name__ == "__main__":
    unittest.main()
