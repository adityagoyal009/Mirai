"""
Research Cache — caches BI research results in ChromaDB to avoid
re-running expensive web search + LLM synthesis for similar companies.
"""

import hashlib
import json
import time
from typing import Optional, Dict, Any

from ..utils.logger import get_logger

logger = get_logger('mirofish.cache')

_CACHE_TTL_DAYS = 7
_SIMILARITY_THRESHOLD = 0.85


class ResearchCache:
    """ChromaDB-based research cache with semantic similarity matching."""

    def __init__(self):
        self._collection = None
        self._init_collection()

    def _init_collection(self):
        try:
            import chromadb
            from ..config import Config
            client = chromadb.PersistentClient(path=Config.CHROMADB_PERSIST_PATH)
            self._collection = client.get_or_create_collection(
                name="mirai_research_cache",
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(f"[Cache] Research cache initialized ({self._collection.count()} entries)")
        except Exception as e:
            logger.warning(f"[Cache] Failed to init: {e}")

    def get_cached(self, industry: str, product: str) -> Optional[Dict[str, Any]]:
        """Check for a similar cached research result."""
        if not self._collection:
            return None

        query = f"{industry} {product}"
        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=1,
                include=["documents", "metadatas", "distances"],
            )

            if not results['documents'] or not results['documents'][0]:
                return None

            distance = results['distances'][0][0]
            similarity = 1 - distance  # cosine distance to similarity

            if similarity < _SIMILARITY_THRESHOLD:
                return None

            metadata = results['metadatas'][0][0]
            cached_time = metadata.get('cached_at', 0)
            age_days = (time.time() - cached_time) / 86400

            if age_days > _CACHE_TTL_DAYS:
                logger.info(f"[Cache] Found match but expired ({age_days:.1f} days old)")
                return None

            doc = results['documents'][0][0]
            cached_data = json.loads(doc)
            logger.info(f"[Cache] Hit! similarity={similarity:.2f}, age={age_days:.1f}d, "
                        f"industry={metadata.get('industry','?')}")

            return {
                "data": cached_data,
                "similarity": round(similarity, 3),
                "age_days": round(age_days, 1),
                "original_company": metadata.get("company", "unknown"),
            }

        except Exception as e:
            logger.warning(f"[Cache] Query failed: {e}")
            return None

    def store(self, company: str, industry: str, product: str, research_data: dict):
        """Store research results for future cache hits."""
        if not self._collection:
            return

        cache_id = hashlib.sha256(f"{company}:{industry}:{product}".encode()).hexdigest()[:16]
        query_text = f"{industry} {product}"

        try:
            self._collection.upsert(
                ids=[cache_id],
                documents=[json.dumps(research_data)],
                metadatas=[{
                    "company": company,
                    "industry": industry,
                    "cached_at": time.time(),
                }],
            )
            logger.info(f"[Cache] Stored research for {company} ({industry})")
        except Exception as e:
            logger.warning(f"[Cache] Store failed: {e}")
