"""
Mem0 Memory Store — hybrid memory layer for relationship-aware recall.

Provides vector DB + graph DB + key-value store unified memory with
intelligent memory management. 26% higher accuracy than OpenAI's memory,
91% lower latency, 90% token savings (per Mem0 benchmarks).

Used alongside ChromaDB (which stays for MiroFish simulation). Mem0 is
for BI memory where relationships matter — who knows whom, what caused
what, how facts evolve over time.

Usage:
    store = Mem0MemoryStore(user_id="mirai_bi")
    store.add("LegalLens AI raised $5M seed round led by a16z", metadata={"industry": "legaltech"})
    results = store.search("legaltech funding rounds")
"""

import os
import json
from typing import Dict, Any, List, Optional

import logging

logger = logging.getLogger("mirai.memory.mem0")

# Mem0 configuration via environment
_MEM0_API_KEY = os.environ.get("MEM0_API_KEY", "")
_MEM0_ORG_ID = os.environ.get("MEM0_ORG_ID", "")


class Mem0MemoryStore:
    """
    Mem0-backed memory store for relationship-aware recall.

    Supports two modes:
    1. Cloud (with MEM0_API_KEY): Uses Mem0 hosted platform
    2. Local (default): Uses Mem0's open-source local mode with ChromaDB + optional graph store

    Falls back gracefully to a no-op if mem0ai is not installed.
    """

    def __init__(
        self,
        user_id: str = "mirai_bi",
        agent_id: str = "mirai_cortex",
        use_cloud: bool = False,
    ):
        self.user_id = user_id
        self.agent_id = agent_id
        self._client = None
        self._available = None
        self._use_cloud = use_cloud and bool(_MEM0_API_KEY)

    def _ensure_client(self) -> bool:
        """Lazy-initialize Mem0 client."""
        if self._available is not None:
            return self._available

        try:
            if self._use_cloud:
                from mem0 import MemoryClient
                self._client = MemoryClient(api_key=_MEM0_API_KEY)
                if _MEM0_ORG_ID:
                    self._client.org_id = _MEM0_ORG_ID
            else:
                from mem0 import Memory
                config = {
                    "version": "v1.1",
                    "llm": {
                        "provider": "openai",
                        "config": {
                            "model": os.environ.get("LLM_MODEL_NAME", "anthropic/claude-opus-4-6"),
                            "api_key": os.environ.get("LLM_API_KEY", "openclaw"),
                            "openai_base_url": os.environ.get("LLM_BASE_URL", "http://localhost:3000/v1"),
                        },
                    },
                    "embedder": {
                        "provider": "openai",
                        "config": {
                            "model": "text-embedding-3-small",
                            "api_key": os.environ.get("LLM_API_KEY", "openclaw"),
                            "openai_base_url": os.environ.get("LLM_BASE_URL", "http://localhost:3000/v1"),
                        },
                    },
                }

                # Add graph store if Neo4j is available
                neo4j_url = os.environ.get("NEO4J_URL")
                if neo4j_url:
                    config["graph_store"] = {
                        "provider": "neo4j",
                        "config": {
                            "url": neo4j_url,
                            "username": os.environ.get("NEO4J_USER", "neo4j"),
                            "password": os.environ.get("NEO4J_PASSWORD", ""),
                        },
                    }
                    logger.info("[Mem0] Graph store enabled (Neo4j)")

                self._client = Memory.from_config(config)

            self._available = True
            logger.info(
                f"[Mem0] Initialized ({'cloud' if self._use_cloud else 'local'} mode)"
            )
        except ImportError:
            self._available = False
            logger.warning("[Mem0] Not installed. Run: pip install mem0ai")
        except Exception as e:
            self._available = False
            logger.warning(f"[Mem0] Init failed: {e}")

        return self._available

    def is_available(self) -> bool:
        """Check if Mem0 is available."""
        return self._ensure_client()

    def add(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Add a memory. Mem0 auto-decides what to remember, update, or ignore.

        Args:
            content: Text content to memorize.
            metadata: Optional metadata dict.
            user_id: Override default user_id.

        Returns:
            Mem0 response dict or None if unavailable.
        """
        if not self._ensure_client():
            return None

        uid = user_id or self.user_id
        try:
            messages = [{"role": "user", "content": content}]
            if metadata:
                messages[0]["metadata"] = metadata

            result = self._client.add(
                messages=messages,
                user_id=uid,
                agent_id=self.agent_id,
            )
            logger.info(f"[Mem0] Added memory for user={uid}: {content[:80]}")
            return result
        except Exception as e:
            logger.warning(f"[Mem0] Add failed: {e}")
            return None

    def search(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search memories by semantic similarity + relationship graph.

        Returns:
            List of memory dicts with keys: id, memory, metadata, score.
        """
        if not self._ensure_client():
            return []

        uid = user_id or self.user_id
        try:
            results = self._client.search(
                query=query,
                user_id=uid,
                agent_id=self.agent_id,
                limit=limit,
            )

            # Normalize response format
            memories = []
            if isinstance(results, dict):
                results = results.get("results", results.get("memories", []))

            for item in results:
                if isinstance(item, dict):
                    memories.append({
                        "id": item.get("id", ""),
                        "memory": item.get("memory", item.get("text", "")),
                        "metadata": item.get("metadata", {}),
                        "score": item.get("score", 0.0),
                    })

            logger.info(
                f"[Mem0] Search '{query[:50]}' → {len(memories)} results"
            )
            return memories
        except Exception as e:
            logger.warning(f"[Mem0] Search failed: {e}")
            return []

    def get_all(
        self, user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all memories for a user."""
        if not self._ensure_client():
            return []

        uid = user_id or self.user_id
        try:
            results = self._client.get_all(
                user_id=uid,
                agent_id=self.agent_id,
            )
            if isinstance(results, dict):
                return results.get("results", results.get("memories", []))
            return results if isinstance(results, list) else []
        except Exception as e:
            logger.warning(f"[Mem0] Get all failed: {e}")
            return []

    def delete(self, memory_id: str) -> bool:
        """Delete a specific memory by ID."""
        if not self._ensure_client():
            return False

        try:
            self._client.delete(memory_id=memory_id)
            logger.info(f"[Mem0] Deleted memory {memory_id}")
            return True
        except Exception as e:
            logger.warning(f"[Mem0] Delete failed: {e}")
            return False

    def store_bi_analysis(
        self,
        analysis_id: str,
        company: str,
        industry: str,
        verdict: str,
        score: float,
        key_findings: str,
        exec_summary: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Store a BI analysis result as a structured memory.
        Mem0 will auto-extract relationships and manage deduplication.
        """
        content = (
            f"BI Analysis [{analysis_id}]: Analyzed {company} in {industry} industry. "
            f"Verdict: {verdict} (score: {score}/10). "
            f"Key findings: {key_findings}. "
            f"Original summary: {exec_summary[:300]}"
        )

        return self.add(
            content=content,
            metadata={
                "type": "bi_analysis",
                "analysis_id": analysis_id,
                "company": company,
                "industry": industry,
                "verdict": verdict,
                "score": score,
            },
        )

    def recall_industry_context(
        self, industry: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Recall past analyses and knowledge about an industry."""
        return self.search(
            query=f"{industry} market analysis trends competitors",
            limit=limit,
        )
