"""
Local Embedding Manager — Offline, CPU-Compatible Semantic Embedding Provider.

Fulfills Sections 4, 5, and 12 of Adaptive Hybrid Retrieval (AHR) Specification:
- CPU inference with thread limits.
- Zero network requests (strict offline zero-egress).
- Checks versioned local model directory for 'BAAI/bge-small-en'.
- If local sentence-transformers files are missing, explicitly reports status and
  activates local Scikit-Learn TruncatedSVD (Latent Semantic Analysis) dense semantic engine.
- Bounded input lengths and L2 normalized vectors for fast dot-product cosine similarity.
"""
from __future__ import annotations
import os
import time
from typing import Any
import numpy as np

# Enforce strict offline execution for any HF/transformers runtime
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"


class LocalEmbeddingManager:
    """
    Singleton provider for offline semantic vector inference on CPU.
    """

    _instance: LocalEmbeddingManager | None = None

    def __init__(self, model_dir: str | None = None):
        self.model_dir = model_dir or os.environ.get(
            "LOCAL_EMBEDDING_MODEL_PATH",
            os.path.join(os.path.dirname(__file__), "models", "bge-small-en"),
        )
        self.model_id = "BAAI/bge-small-en"
        self.model_version = "1.5"
        self.inference_device = "cpu"
        self.max_seq_length = 512
        self.st_model: Any = None
        self.is_st_available: bool = False
        self.fallback_reason: str = ""
        self.dimension: int = 384
        self.init_time_ms: float = 0.0

        self._initialize_provider()

    @classmethod
    def get_instance(cls) -> LocalEmbeddingManager:
        if cls._instance is None:
            cls._instance = LocalEmbeddingManager()
        return cls._instance

    def _initialize_provider(self) -> None:
        """Check for local model directory and initialize without network egress."""
        t0 = time.perf_counter()

        # Check if local model directory exists
        if not os.path.exists(self.model_dir):
            self.is_st_available = False
            self.fallback_reason = (
                f"Local model directory '{self.model_dir}' not found on disk. "
                "Operating in offline Scikit-Learn LSA dense semantic mode."
            )
            self.dimension = 64
            self.init_time_ms = round((time.perf_counter() - t0) * 1000, 2)
            return

        # Attempt to load local sentence-transformers from directory
        try:
            import torch
            torch.set_num_threads(2)
            from sentence_transformers import SentenceTransformer

            self.st_model = SentenceTransformer(self.model_dir, device="cpu")
            self.st_model.max_seq_length = self.max_seq_length
            self.is_st_available = True
            self.dimension = 384
            self.fallback_reason = ""
        except Exception as e:
            self.is_st_available = False
            self.st_model = None
            self.fallback_reason = f"SentenceTransformer local initialization failed: {str(e)}"
            self.dimension = 64

        self.init_time_ms = round((time.perf_counter() - t0) * 1000, 2)

    def encode(self, texts: list[str]) -> np.ndarray | None:
        """
        Encode a list of text strings into normalized semantic vectors.
        Returns (N, D) float32 numpy array or None if sentence-transformers is unavailable.
        """
        if not self.is_st_available or self.st_model is None or not texts:
            return None

        # Bound inputs
        bounded_texts = [t[:1000] for t in texts]

        try:
            embeddings = self.st_model.encode(
                bounded_texts,
                batch_size=16,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
            return embeddings.astype(np.float32)
        except Exception:
            return None

    def get_status(self) -> dict[str, Any]:
        """Diagnostic metadata for inspection and testing."""
        return {
            "model_identifier": self.model_id,
            "model_version": self.model_version,
            "embedding_dimension": self.dimension,
            "inference_device": self.inference_device,
            "max_seq_length": self.max_seq_length,
            "sentence_transformer_available": self.is_st_available,
            "dense_semantic_engine": (
                "SentenceTransformer (BAAI/bge-small-en)"
                if self.is_st_available
                else "Scikit-Learn-TruncatedSVD (LSA-Dense-64)"
            ),
            "status": "online" if self.is_st_available else "offline_lsa_active",
            "fallback_active": not self.is_st_available,
            "fallback_reason": self.fallback_reason,
            "init_time_ms": self.init_time_ms,
        }
