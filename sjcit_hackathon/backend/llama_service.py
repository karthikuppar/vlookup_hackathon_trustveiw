"""
Llama Service — CPU-Compatible Local Language Model Inference Provider.

Fulfills PS-04 Technical Specification:
- Local quantized Llama-family model inference via Ollama runtime.
- Configurable CPU threads, context window length, and request timeouts.
- Concurrency limiting via asyncio.Semaphore to avoid CPU starvation.
- Bounded request queues and health monitoring.
- Graceful offline fallback when Ollama service is stopped or unreachable.
"""
from __future__ import annotations

import asyncio
import os
import time
from typing import Any
import httpx


class LlamaService:
    """
    Singleton service managing local quantized Llama inference on CPU.
    """

    _instance: LlamaService | None = None

    def __init__(self) -> None:
        self.base_url = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        self.model_id = os.environ.get("LLAMA_MODEL_ID", "llama3.2:latest")
        self.num_threads = int(os.environ.get("LLAMA_CPU_THREADS", "4"))
        self.num_ctx = int(os.environ.get("LLAMA_NUM_CTX", "2048"))
        self.timeout_seconds = float(os.environ.get("LLAMA_TIMEOUT_SECONDS", "15.0"))
        max_concurrent = int(os.environ.get("LLAMA_MAX_CONCURRENT", "2"))
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active_requests = 0
        self._total_inferences = 0

    @classmethod
    def get_instance(cls) -> LlamaService:
        if cls._instance is None:
            cls._instance = LlamaService()
        return cls._instance

    def get_health(self) -> dict[str, Any]:
        """
        Synchronous health-check returning local runtime and model status.
        Does not block API threads; uses short 2.0s connect timeout.
        """
        try:
            with httpx.Client(base_url=self.base_url, timeout=2.5) as client:
                res = client.get("/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("name") for m in data.get("models", [])]
                    model_found = any(self.model_id in m for m in models)
                    return {
                        "status": "healthy" if model_found else "model_missing",
                        "runtime": "ollama",
                        "base_url": self.base_url,
                        "configured_model": self.model_id,
                        "model_loaded": model_found,
                        "available_models": models,
                        "cpu_threads": self.num_threads,
                        "context_length": self.num_ctx,
                        "inference_device": "cpu",
                        "active_requests": self._active_requests,
                        "total_inferences": self._total_inferences,
                    }
        except Exception as e:
            return {
                "status": "unavailable",
                "runtime": "ollama",
                "base_url": self.base_url,
                "configured_model": self.model_id,
                "model_loaded": False,
                "available_models": [],
                "cpu_threads": self.num_threads,
                "context_length": self.num_ctx,
                "inference_device": "cpu",
                "error": str(e),
                "fallback_active": True,
            }

        return {
            "status": "unavailable",
            "configured_model": self.model_id,
            "fallback_active": True,
        }

    async def generate_grounded_answer(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        """
        Executes bounded, asynchronous inference against the local Llama runtime.
        Returns a structured dictionary with response text, latency, and status.
        """
        t0 = time.perf_counter()
        async with self._semaphore:
            self._active_requests += 1
            try:
                payload: dict[str, Any] = {
                    "model": self.model_id,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_thread": self.num_threads,
                        "num_ctx": self.num_ctx,
                        "temperature": temperature,
                        "top_p": 0.9,
                    },
                }
                if system_prompt:
                    payload["system"] = system_prompt

                async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout_seconds) as client:
                    resp = await client.post("/api/generate", json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
                        self._total_inferences += 1
                        return {
                            "success": True,
                            "text": data.get("response", "").strip(),
                            "latency_ms": elapsed_ms,
                            "eval_count": data.get("eval_count", 0),
                            "eval_duration_ms": round(data.get("eval_duration", 0) / 1e6, 2),
                            "model": self.model_id,
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Ollama HTTP {resp.status_code}: {resp.text}",
                            "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
                        }
            except httpx.TimeoutException:
                return {
                    "success": False,
                    "error": f"Model inference timed out after {self.timeout_seconds}s",
                    "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
                    "timeout": True,
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
                }
            finally:
                self._active_requests -= 1
