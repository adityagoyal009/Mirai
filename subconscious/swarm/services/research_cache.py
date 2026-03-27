"""
Research Cache — file-based JSON cache for BI research results.
Replaces ChromaDB (which crashes with Rust panics) with instant file I/O.
"""

import hashlib
import json
import os
import time
from typing import Optional, Dict, Any

from ..utils.logger import get_logger

logger = get_logger('mirofish.cache')

_CACHE_TTL_DAYS = 7
_CACHE_DIR = os.path.expanduser("~/.mirai/research_cache")


class ResearchCache:
    """File-based research cache. Instant reads, no ChromaDB dependency."""

    def __init__(self):
        os.makedirs(_CACHE_DIR, exist_ok=True)

    @staticmethod
    def make_key(company: str, industry: str) -> str:
        normalized = f"{company.strip().lower()}:{industry.strip().lower()}"
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def _path(self, key: str) -> str:
        return os.path.join(_CACHE_DIR, f"{key}.json")

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        path = self._path(key)
        if not os.path.exists(path):
            return None
        try:
            with open(path) as f:
                wrapper = json.load(f)
            cached_at = wrapper.get("_cached_at", 0)
            age_days = (time.time() - cached_at) / 86400
            if age_days > _CACHE_TTL_DAYS:
                logger.info(f"[Cache] Key {key} expired ({age_days:.1f}d old)")
                return None
            data = wrapper.get("data", wrapper)
            # Inject cache age so downstream consumers can display staleness
            if isinstance(data, dict):
                data["_cache_age_days"] = round(age_days, 1)
            logger.info(f"[Cache] Key {key} HIT (age={age_days:.1f}d)")
            return data
        except Exception as e:
            logger.warning(f"[Cache] Key {key} read failed (treating as cache miss — expensive re-research will run): {e}")
            return None

    def put(self, key: str, data: dict):
        path = self._path(key)
        try:
            wrapper = {"_cached_at": time.time(), "data": data}
            with open(path, "w") as f:
                json.dump(wrapper, f)
            logger.info(f"[Cache] Stored key {key}")
        except Exception as e:
            logger.warning(f"[Cache] Store failed for key {key}: {e}")

    # Legacy methods for backward compat
    def get_cached(self, industry: str, product: str) -> Optional[Dict[str, Any]]:
        key = self.make_key(industry, product)
        data = self.get(key)
        return {"data": data, "similarity": 1.0, "age_days": 0} if data else None

    def store(self, company: str, industry: str, product: str, research_data: dict):
        key = self.make_key(company, industry)
        self.put(key, research_data)
