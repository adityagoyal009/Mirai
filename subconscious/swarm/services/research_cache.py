"""
Research Cache — file-based JSON cache for BI research results.
Replaces ChromaDB (which crashes with Rust panics) with instant file I/O.
"""

import copy
import hashlib
import json
import os
import time
from typing import Optional, Dict, Any

from ..utils.logger import get_logger

logger = get_logger('mirofish.cache')

_CACHE_TTL_DAYS = int(os.environ.get("MIRAI_RESEARCH_CACHE_TTL_DAYS", "14"))
_CACHE_DIR = os.path.expanduser("~/.mirai/research_cache")
_CACHE_VERSION = "research_v3_exact_form_claude6"


class ResearchCache:
    """File-based research cache. Instant reads, no ChromaDB dependency."""

    def __init__(self):
        os.makedirs(_CACHE_DIR, exist_ok=True)

    @staticmethod
    def make_key(company: str, industry: str) -> str:
        normalized = f"{company.strip().lower()}:{industry.strip().lower()}"
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    @staticmethod
    def _normalize_value(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                str(key): ResearchCache._normalize_value(value[key])
                for key in sorted(value.keys(), key=lambda item: str(item))
            }
        if isinstance(value, list):
            return [ResearchCache._normalize_value(item) for item in value]
        if isinstance(value, tuple):
            return [ResearchCache._normalize_value(item) for item in value]
        if isinstance(value, str):
            return " ".join(value.split()).strip()
        return value

    @staticmethod
    def make_exact_key(
        exec_summary: str,
        structured_fields: Optional[Dict[str, Any]] = None,
        *,
        depth: str = "deep",
        version: str = _CACHE_VERSION,
    ) -> str:
        payload = {
            "version": version,
            "depth": depth,
            "exec_summary": ResearchCache._normalize_value(exec_summary),
            "structured_fields": ResearchCache._normalize_value(structured_fields or {}),
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:24]

    def _path(self, key: str) -> str:
        return os.path.join(_CACHE_DIR, f"{key}.json")

    def _phase_path(self, key: str) -> str:
        return os.path.join(_CACHE_DIR, f"{key}.phase.json")

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
            data = copy.deepcopy(wrapper.get("data", wrapper))
            meta = wrapper.get("_meta", {})
            # Inject cache age so downstream consumers can display staleness
            if isinstance(data, dict):
                data["_cache_age_days"] = round(age_days, 1)
                data["_cache_hit"] = True
                data["_cache_key"] = key
                data["_cache_meta"] = meta
            logger.info(f"[Cache] Key {key} HIT (age={age_days:.1f}d)")
            return data
        except Exception as e:
            logger.warning(f"[Cache] Key {key} read failed (treating as cache miss — expensive re-research will run): {e}")
            return None

    def put(self, key: str, data: dict, *, meta: Optional[Dict[str, Any]] = None):
        path = self._path(key)
        try:
            wrapper = {
                "_cached_at": time.time(),
                "_version": _CACHE_VERSION,
                "_meta": meta or {},
                "data": data,
            }
            with open(path, "w") as f:
                json.dump(wrapper, f)
            logger.info(f"[Cache] Stored key {key}")
        except Exception as e:
            logger.warning(f"[Cache] Store failed for key {key}: {e}")

    def delete(self, key: str) -> bool:
        path = self._path(key)
        if not os.path.exists(path):
            return False
        try:
            os.remove(path)
            logger.info(f"[Cache] Deleted key {key}")
            return True
        except Exception as e:
            logger.warning(f"[Cache] Delete failed for key {key}: {e}")
            return False

    def get_phase_checkpoint(self, key: str) -> Optional[Dict[str, Any]]:
        path = self._phase_path(key)
        if not os.path.exists(path):
            return None
        try:
            with open(path) as f:
                wrapper = json.load(f)
            cached_at = wrapper.get("_cached_at", 0)
            age_days = (time.time() - cached_at) / 86400
            if age_days > _CACHE_TTL_DAYS:
                logger.info(f"[Cache] Phase checkpoint {key} expired ({age_days:.1f}d old)")
                return None
            data = copy.deepcopy(wrapper.get("data", wrapper))
            if isinstance(data, dict):
                data["_cache_age_days"] = round(age_days, 1)
                data["_cache_key"] = key
            logger.info(f"[Cache] Phase checkpoint {key} HIT (age={age_days:.1f}d)")
            return data
        except Exception as e:
            logger.warning(f"[Cache] Phase checkpoint read failed for key {key}: {e}")
            return None

    def put_phase_checkpoint(self, key: str, data: Dict[str, Any], *, meta: Optional[Dict[str, Any]] = None):
        path = self._phase_path(key)
        try:
            wrapper = {
                "_cached_at": time.time(),
                "_version": _CACHE_VERSION,
                "_meta": meta or {},
                "data": data,
            }
            with open(path, "w") as f:
                json.dump(wrapper, f)
            logger.info(f"[Cache] Stored phase checkpoint {key}")
        except Exception as e:
            logger.warning(f"[Cache] Store failed for phase checkpoint {key}: {e}")

    def delete_phase_checkpoint(self, key: str) -> bool:
        path = self._phase_path(key)
        if not os.path.exists(path):
            return False
        try:
            os.remove(path)
            logger.info(f"[Cache] Deleted phase checkpoint {key}")
            return True
        except Exception as e:
            logger.warning(f"[Cache] Delete failed for phase checkpoint {key}: {e}")
            return False

    # Legacy methods for backward compat
    def get_cached(self, industry: str, product: str) -> Optional[Dict[str, Any]]:
        key = self.make_key(industry, product)
        data = self.get(key)
        return {"data": data, "similarity": 1.0, "age_days": 0} if data else None

    def store(
        self,
        company: str,
        industry: str,
        product: str,
        research_data: dict,
        *,
        exec_summary: str = "",
        structured_fields: Optional[Dict[str, Any]] = None,
        depth: str = "deep",
    ):
        key = self.make_key(company, industry)
        self.put(
            key,
            research_data,
            meta={
                "company": company,
                "industry": industry,
                "product": product,
                "scope": "legacy_company_industry",
            },
        )
        exact_key = self.make_exact_key(exec_summary, structured_fields, depth=depth)
        self.put(
            exact_key,
            research_data,
            meta={
                "company": company,
                "industry": industry,
                "product": product,
                "scope": "exact_form",
                "depth": depth,
            },
        )
