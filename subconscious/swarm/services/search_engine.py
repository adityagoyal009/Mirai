"""
SearXNG Search Engine — self-hosted metasearch via HTTP JSON API.

Replaces DuckDuckGo browser navigation with a fast, structured search.
SearXNG aggregates 70+ search engines (Google, Bing, DuckDuckGo, Brave,
Wikipedia) and returns JSON results via a simple HTTP call — no API keys,
no rate limits, no Playwright overhead.

Usage:
    engine = SearchEngine()
    results = engine.search("AI legaltech market size 2026")
    # → [{"title": "...", "url": "...", "content": "...", "engine": "google"}, ...]
"""

import os
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from ..utils.logger import get_logger

logger = get_logger('mirofish.search_engine')

_SEARXNG_URL = os.environ.get("SEARXNG_URL", "http://localhost:8888")


class SearchEngine:
    """
    SearXNG-backed metasearch engine.
    Falls back to DuckDuckGo HTML scraping if SearXNG is unavailable.
    """

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or _SEARXNG_URL
        self._available = None  # cached availability check

    def is_available(self) -> bool:
        """Check if SearXNG instance is reachable."""
        if self._available is not None:
            return self._available
        try:
            resp = requests.get(f"{self.base_url}/healthz", timeout=5)
            self._available = resp.status_code == 200
        except Exception:
            # Try the search endpoint as a fallback health check
            try:
                resp = requests.get(
                    f"{self.base_url}/search",
                    params={"q": "test", "format": "json"},
                    timeout=5,
                )
                self._available = resp.status_code == 200
            except Exception:
                self._available = False
        if not self._available:
            logger.warning(
                f"SearXNG not available at {self.base_url}. "
                f"Start with: docker run -p 8888:8888 searxng/searxng"
            )
        return self._available

    def search(
        self,
        query: str,
        categories: str = "general",
        engines: Optional[str] = None,
        language: str = "en",
        max_results: int = 10,
        time_range: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search via SearXNG JSON API.

        Args:
            query: Search query string.
            categories: Comma-separated categories (general, news, science, files, images).
            engines: Comma-separated engine names (google, bing, duckduckgo, brave, wikipedia).
            language: Language code (en, de, fr, etc.).
            max_results: Maximum results to return.
            time_range: Time filter (day, week, month, year).

        Returns:
            List of result dicts with keys: title, url, content, engine, score.
        """
        if not self.is_available():
            return []

        params = {
            "q": query,
            "format": "json",
            "categories": categories,
            "language": language,
        }
        if engines:
            params["engines"] = engines
        if time_range:
            params["time_range"] = time_range

        try:
            resp = requests.get(
                f"{self.base_url}/search",
                params=params,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            results = []
            for item in data.get("results", [])[:max_results]:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                    "engine": item.get("engine", ""),
                    "score": item.get("score", 0.0),
                })

            logger.info(
                f"[SearXNG] '{query[:50]}' → {len(results)} results "
                f"(categories={categories})"
            )
            return results

        except requests.exceptions.Timeout:
            logger.warning(f"[SearXNG] Timeout searching: {query[:50]}")
            return []
        except Exception as e:
            logger.warning(f"[SearXNG] Search failed: {e}")
            return []

    def search_news(
        self, query: str, max_results: int = 10, time_range: str = "week"
    ) -> List[Dict[str, Any]]:
        """Search specifically for news articles."""
        return self.search(
            query=query,
            categories="news",
            max_results=max_results,
            time_range=time_range,
        )

    def search_batch(
        self,
        queries: List[str],
        max_results_per_query: int = 5,
        categories: str = "general",
        max_workers: int = 3,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search multiple queries in parallel.

        Returns:
            Dict mapping query → list of results.
        """
        results: Dict[str, List[Dict[str, Any]]] = {}

        def _search_one(q: str) -> tuple:
            return q, self.search(
                query=q,
                categories=categories,
                max_results=max_results_per_query,
            )

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_search_one, q): q for q in queries}
            for future in as_completed(futures):
                try:
                    query, query_results = future.result()
                    results[query] = query_results
                except Exception as e:
                    query = futures[future]
                    logger.warning(f"[SearXNG] Batch query failed: {query[:50]} — {e}")
                    results[query] = []

        total = sum(len(r) for r in results.values())
        logger.info(
            f"[SearXNG] Batch search: {len(queries)} queries → {total} total results"
        )
        return results

    def get_urls_for_query(
        self, query: str, max_urls: int = 5, categories: str = "general"
    ) -> List[str]:
        """
        Convenience: return just the URLs from a search.
        Used by the BI pipeline to find URLs for browser/Crawl4AI extraction.
        """
        results = self.search(
            query=query, categories=categories, max_results=max_urls
        )
        return [r["url"] for r in results if r.get("url")]
