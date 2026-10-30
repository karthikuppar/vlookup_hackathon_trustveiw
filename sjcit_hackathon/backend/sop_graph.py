"""
Lightweight In-Process Knowledge Graph for SOP Retrieval Routing.

Fulfills Sections 3 and 4 of Technical Specification:
- Node Types: Intent, SOP, Section, Chunk, Concept
- Relationship Types: ROUTES_TO, CONTAINS, RELATED_TO, REFERENCES, BELONGS_TO
- Deterministic in-memory graph constructed from SQLite active documents and chunks
- Strict multi-tenant isolation preserved during graph traversal
- Fast candidate routing (<0.5ms) with fallback mechanism for unknown/ambiguous queries
"""
from __future__ import annotations
import re
import time
from collections import defaultdict
from typing import Any

from database import get_connection

# Canonical intents and associated topic concepts
INTENT_CONCEPT_MAPPINGS: dict[str, list[str]] = {
    "onboarding": [
        "onboarding", "day one", "first day", "reception", "buddy",
        "orientation", "welcome", "checklist", "first 30 days", "probation",
        "badge", "id documents", "facilities", "contacts"
    ],
    "it_security": [
        "password", "mfa", "multi-factor authentication", "authenticator",
        "laptop", "device", "vpn", "access control", "data classification",
        "confidential", "incident", "breach", "phishing", "mdm", "remote wipe"
    ],
    "hr_policy": [
        "leave", "annual leave", "sick leave", "casual leave", "maternity",
        "paternity", "bereavement", "carry forward", "attendance", "work hours",
        "biometric", "late arrival", "hr portal", "holiday"
    ],
    "finance": [
        "expense", "reimbursement", "travel", "flight", "hotel", "meal",
        "daily limit", "per diem", "mileage", "taxi", "receipt",
        "approval", "invoicing", "settlement deadline", "payment terms", "finance portal"
    ],
    "conduct_ethics": [
        "code of conduct", "ethics", "values", "harassment", "discrimination",
        "confidentiality", "nda", "conflict of interest", "gifts", "social media",
        "whistleblower", "hotline", "disciplinary"
    ],
    "operations": [
        "operational guidelines", "invoicing policy", "vendor access",
        "infrastructure", "compliance audit", "settlement deadline"
    ],
}


class SOPKnowledgeGraph:
    """
    In-memory graph providing deterministic routing of questions to relevant
    SOP candidate chunks before vector/lexical retrieval.
    """

    _instance: SOPKnowledgeGraph | None = None

    def __init__(self):
        # Nodes: node_id -> {type, data}
        self.nodes: dict[str, dict[str, Any]] = {}

        # Edges: source_node -> {relation_type: set(target_nodes)}
        self.edges: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))

        # Reverse Edges: target_node -> {relation_type: set(source_nodes)}
        self.reverse_edges: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))

        # Chunk lookup cache: chunk_id -> chunk_data
        self.chunk_cache: dict[str, dict[str, Any]] = {}

        # Precomputed Inverted Indexes for Sub-Millisecond Routing (Section 3.3)
        self.token_to_concepts: dict[str, set[str]] = defaultdict(set)
        self.intent_to_chunk_ids: dict[str, set[str]] = defaultdict(set)

        # Build stats
        self.last_built_at: float = 0.0
        self.build_time_ms: float = 0.0

    @classmethod
    def get_instance(cls) -> SOPKnowledgeGraph:
        if cls._instance is None:
            cls._instance = SOPKnowledgeGraph()
            cls._instance.build_graph()
        return cls._instance

    def clear(self):
        self.nodes.clear()
        self.edges.clear()
        self.reverse_edges.clear()
        self.chunk_cache.clear()
        self.token_to_concepts.clear()
        self.intent_to_chunk_ids.clear()

    def add_node(self, node_id: str, node_type: str, data: dict[str, Any]):
        self.nodes[node_id] = {"id": node_id, "type": node_type, "data": data}

    def add_edge(self, source: str, relation: str, target: str):
        self.edges[source][relation].add(target)
        self.reverse_edges[target][relation].add(source)

    def build_graph(self) -> dict[str, Any]:
        """
        Constructs the graph from active SQLite SOP documents and chunks.
        Deterministic, local, and zero-egress.
        """
        t0 = time.perf_counter()
        self.clear()

        # 1. Register Canonical Intent Nodes
        for intent_name, concepts in INTENT_CONCEPT_MAPPINGS.items():
            intent_node_id = f"intent:{intent_name}"
            self.add_node(intent_node_id, "Intent", {"name": intent_name})

            # Register Concept Nodes and RELATED_TO edges
            for c in concepts:
                concept_node_id = f"concept:{c}"
                if concept_node_id not in self.nodes:
                    self.add_node(concept_node_id, "Concept", {"name": c})
                self.add_edge(intent_node_id, "RELATED_TO", concept_node_id)

        # 2. Ingest Active SOP Documents & Chunks from SQLite
        with get_connection() as conn:
            docs = conn.execute(
                """
                SELECT d.id AS doc_id, d.tenant_id, d.title, d.original_filename, v.version_num
                FROM documents d
                JOIN document_versions v ON d.id = v.doc_id
                WHERE v.status = 'active'
                """
            ).fetchall()

            for doc in docs:
                doc_id = doc["doc_id"]
                tenant_id = doc["tenant_id"]
                title = doc["title"]
                v_num = doc["version_num"]
                sop_node_id = f"sop:{doc_id}"

                self.add_node(
                    sop_node_id,
                    "SOP",
                    {
                        "doc_id": doc_id,
                        "tenant_id": tenant_id,
                        "title": title,
                        "version_num": v_num,
                        "filename": doc["original_filename"],
                    },
                )

                # Connect Intent to SOP via ROUTES_TO based on title & domain
                title_lower = title.lower()
                for intent_name, concepts in INTENT_CONCEPT_MAPPINGS.items():
                    intent_node_id = f"intent:{intent_name}"
                    # If document title or concepts match intent domain
                    if intent_name in title_lower or any(c in title_lower for c in concepts):
                        self.add_edge(intent_node_id, "ROUTES_TO", sop_node_id)

                # 3. Ingest Chunks for this Document
                chunks = conn.execute(
                    """
                    SELECT id AS chunk_id, doc_id, version_num, tenant_id, page, section, text, token_count
                    FROM document_chunks
                    WHERE doc_id = ? AND version_num = ?
                    ORDER BY id
                    """,
                    (doc_id, v_num),
                ).fetchall()

                for chunk in chunks:
                    chunk_id = chunk["chunk_id"]
                    sec_name = chunk["section"] or "General"
                    sec_node_id = f"section:{doc_id}:{sec_name}"

                    # Add Section node if not present
                    if sec_node_id not in self.nodes:
                        self.add_node(
                            sec_node_id,
                            "Section",
                            {"doc_id": doc_id, "tenant_id": tenant_id, "section": sec_name, "title": title},
                        )
                        self.add_edge(sop_node_id, "CONTAINS", sec_node_id)
                        self.add_edge(sec_node_id, "BELONGS_TO", sop_node_id)

                    # Add Chunk node
                    chunk_node_id = f"chunk:{chunk_id}"
                    chunk_data = {
                        "chunk_id": chunk_id,
                        "doc_id": doc_id,
                        "version_num": v_num,
                        "tenant_id": tenant_id,
                        "page": chunk["page"],
                        "section": sec_name,
                        "text": chunk["text"],
                        "token_count": chunk["token_count"],
                        "title": title,
                    }
                    self.add_node(chunk_node_id, "Chunk", chunk_data)
                    self.chunk_cache[chunk_id] = chunk_data

                    self.add_edge(sec_node_id, "CONTAINS", chunk_node_id)
                    self.add_edge(chunk_node_id, "BELONGS_TO", sec_node_id)

                    # Connect chunk content to Concepts via RELATED_TO
                    chunk_lower = chunk["text"].lower()
                    for concept_node_id, cnode in self.nodes.items():
                        if cnode["type"] == "Concept":
                            c_name = cnode["data"]["name"]
                            if c_name in chunk_lower:
                                self.add_edge(sec_node_id, "RELATED_TO", concept_node_id)
                                self.add_edge(concept_node_id, "RELATED_TO", chunk_node_id)

                    # Cross-section references (e.g. mentions "refer to Remote Work" or "Code of Conduct")
                    if "refer to" in chunk_lower or "see " in chunk_lower:
                        for other_doc in docs:
                            if other_doc["doc_id"] != doc_id and other_doc["title"].lower() in chunk_lower:
                                other_sop = f"sop:{other_doc['doc_id']}"
                                self.add_edge(sec_node_id, "REFERENCES", other_sop)

        # 4. Precompute Inverted Indexes for Sub-Millisecond Routing (Section 3.3)
        for intent_name in INTENT_CONCEPT_MAPPINGS:
            intent_node = f"intent:{intent_name}"
            sops = self.edges.get(intent_node, {}).get("ROUTES_TO", set())
            for sop_id in sops:
                secs = self.edges.get(sop_id, {}).get("CONTAINS", set())
                for sec_id in secs:
                    chks = self.edges.get(sec_id, {}).get("CONTAINS", set())
                    self.intent_to_chunk_ids[intent_name].update(chks)

        for concept_node_id, node in self.nodes.items():
            if node["type"] == "Concept":
                c_name = node["data"]["name"].lower()
                self.token_to_concepts[c_name].add(concept_node_id)
                for part in c_name.split():
                    if len(part) >= 3:
                        self.token_to_concepts[part].add(concept_node_id)

        self.last_built_at = time.time()
        self.build_time_ms = round((time.perf_counter() - t0) * 1000, 2)
        return self.get_stats()

    def route_query(
        self,
        intent: str | list[str],
        query_tokens: list[str],
        permitted_tenants: list[str],
        min_confidence: float = 0.30,
    ) -> tuple[list[dict[str, Any]], float, str, int]:
        """
        Traverses the graph to route an incoming question to candidate chunks.
        Supports single intent or multiple candidate intents for ambiguous queries.
        Preserves strict multi-tenant authorization during traversal.

        Returns:
            (candidate_chunks, confidence_score, traversal_path, candidate_count)
            where traversal_path is 'graph' or 'fallback'.
        """
        t0 = time.perf_counter()
        candidate_chunk_ids: set[str] = set()
        matched_concepts: list[str] = []

        intents_list = [intent] if isinstance(intent, str) else list(intent)

        # 1. Traverse Intent -> Chunks using precomputed inverted routing index
        for it in intents_list:
            if it != "knowledge":
                candidate_chunk_ids.update(self.intent_to_chunk_ids.get(it, set()))

        # 2. Traverse query tokens -> Concept matching -> RELATED_TO -> Chunks using token index
        clean_tokens = [t.lower() for t in query_tokens if len(t) >= 3]
        for token in clean_tokens:
            concept_ids = self.token_to_concepts.get(token, set())
            for cid in concept_ids:
                if cid in self.nodes:
                    c_name = self.nodes[cid]["data"]["name"]
                    matched_concepts.append(c_name)
                    linked_chunks = self.edges.get(cid, {}).get("RELATED_TO", set())
                    candidate_chunk_ids.update(linked_chunks)

        # 3. Collect and verify candidate chunk payloads with strict tenant authorization
        candidates: list[dict[str, Any]] = []
        for chk_node_id in candidate_chunk_ids:
            chunk_raw_id = chk_node_id.replace("chunk:", "")
            if chunk_raw_id in self.chunk_cache:
                c_data = self.chunk_cache[chunk_raw_id]
                if c_data.get("tenant_id") in permitted_tenants:
                    candidates.append(c_data)

        # 4. Compute Intent & Graph Confidence Score
        confidence = 0.0
        has_domain_intent = any(it != "knowledge" for it in intents_list)
        if has_domain_intent and candidates:
            # High-confidence intent matched
            confidence = 0.75 + min(0.20, len(matched_concepts) * 0.05)
        elif matched_concepts and candidates:
            # Concept-based match without clear intent
            confidence = 0.50 + min(0.25, len(matched_concepts) * 0.08)
        elif candidates:
            confidence = 0.35
        else:
            confidence = 0.10

        traversal_time_ms = (time.perf_counter() - t0) * 1000

        # 5. Routing Decision: Confident Graph Path vs Fallback Trigger
        if candidates and confidence >= min_confidence:
            return candidates, round(confidence, 3), "graph", len(candidates)
        else:
            # Fallback path triggered
            return [], round(confidence, 3), "fallback", 0

    def add_or_update_sop(self, doc_id: str, tenant_id: str) -> None:
        """Triggered upon document upload or version replacement."""
        self.build_graph()

    def remove_sop(self, doc_id: str) -> None:
        """Removes a document from the graph."""
        self.build_graph()

    def get_stats(self) -> dict[str, Any]:
        """Provides graph topology metrics for transparency and inspection."""
        type_counts = defaultdict(int)
        for node in self.nodes.values():
            type_counts[node["type"]] += 1

        rel_counts = defaultdict(int)
        for src, rel_dict in self.edges.items():
            for rel, targets in rel_dict.items():
                rel_counts[rel] += len(targets)

        return {
            "status": "ready",
            "total_nodes": len(self.nodes),
            "total_edges": sum(rel_counts.values()),
            "nodes_by_type": dict(type_counts),
            "edges_by_relationship": dict(rel_counts),
            "indexed_chunks": len(self.chunk_cache),
            "build_time_ms": self.build_time_ms,
            "last_built_at": self.last_built_at,
        }
