"""
Web Researcher — multi-path web research for BI.

Three extraction paths (no degradation):
1. SearXNG → fast structured URL discovery (replaces DuckDuckGo navigation)
2. Crawl4AI → fast bulk content extraction for static pages
3. Browser-use Agent → full Playwright for interactive pages (login walls, dynamic content)

SearXNG finds URLs → Crawl4AI extracts content from static pages →
browser engine handles anything Crawl4AI can't. No capability is removed.
"""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional

import requests

from ..utils.logger import get_logger

logger = get_logger('mirofish.web_researcher')

_CORTEX_URL = os.environ.get("MIRAI_CORTEX_URL", "http://localhost:8100")


class WebResearcher:
    """
    Multi-path web research engine.

    Priority order for URL discovery:
    1. SearXNG (fast, structured JSON) — if available
    2. DuckDuckGo via browser engine (fallback)

    Priority order for content extraction:
    1. Crawl4AI (fast, LLM-optimized markdown) — for static pages
    2. Browser-use Agent via cortex (full Playwright) — for interactive pages
    """

    def __init__(self, cortex_url: Optional[str] = None):
        self.cortex_url = cortex_url or _CORTEX_URL
        self._crawl4ai = None
        self._crawl4ai_checked = False
        self._searxng = None
        self._searxng_checked = False

    # ── SearXNG integration ───────────────────────────────────────

    def _get_searxng(self):
        """Lazy-init SearXNG search engine."""
        if not self._searxng_checked:
            self._searxng_checked = True
            try:
                from .search_engine import SearchEngine
                engine = SearchEngine()
                if engine.is_available():
                    self._searxng = engine
                    logger.info("[WebResearch] SearXNG available for URL discovery")
                else:
                    logger.info("[WebResearch] SearXNG not available — using browser fallback")
            except Exception as e:
                logger.warning(f"[WebResearch] SearXNG init failed: {e}")
        return self._searxng

    # ── Crawl4AI integration ──────────────────────────────────────

    def _get_crawl4ai(self):
        """Lazy-init Crawl4AI crawler."""
        if not self._crawl4ai_checked:
            self._crawl4ai_checked = True
            try:
                from crawl4ai import AsyncWebCrawler
                self._crawl4ai = True  # Mark as available
                logger.info("[WebResearch] Crawl4AI available for fast extraction")
            except ImportError:
                logger.info(
                    "[WebResearch] Crawl4AI not installed — using browser for all extraction. "
                    "Install with: pip install crawl4ai"
                )
        return self._crawl4ai

    def _crawl4ai_extract(self, url: str) -> Optional[str]:
        """
        Extract content from a URL using Crawl4AI (sync wrapper).
        Returns markdown content or None if extraction fails.
        """
        try:
            import asyncio
            from crawl4ai import AsyncWebCrawler

            async def _crawl():
                async with AsyncWebCrawler(verbose=False) as crawler:
                    result = await crawler.arun(url=url)
                    if result.success:
                        return result.markdown[:5000]
                    return None

            # Run in a new event loop if we're in a sync context
            try:
                loop = asyncio.get_running_loop()
                # Already in async context — run in thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, _crawl())
                    return future.result(timeout=30)
            except RuntimeError:
                return asyncio.run(_crawl())

        except Exception as e:
            logger.warning(f"[Crawl4AI] Extraction failed for {url}: {e}")
            return None

    # ── Browser engine (original full-power path) ─────────────────

    def _check_cortex(self) -> bool:
        """Check if the cortex API server is reachable."""
        try:
            resp = requests.get(f"{self.cortex_url}/health", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def browse(self, url: str, task: str = "Extract the main text content") -> Dict[str, Any]:
        """
        Browse a single URL using the cortex's browser engine.
        Returns {"success": bool, "url": str, "content": str}.
        """
        try:
            resp = requests.post(
                f"{self.cortex_url}/api/browse",
                json={"url": url, "task": task, "max_steps": 5},
                timeout=120,
            )
            return resp.json()
        except Exception as e:
            logger.warning(f"Browse failed for {url}: {e}")
            return {"success": False, "url": url, "error": str(e)}

    def browse_batch(
        self, urls: List[str], task: str = "Extract the main text content"
    ) -> List[Dict[str, Any]]:
        """
        Browse multiple URLs via the cortex's batch endpoint.
        Uses the same browser session for efficiency.
        """
        try:
            resp = requests.post(
                f"{self.cortex_url}/api/browse/batch",
                json={"urls": urls, "task": task, "max_steps": 5},
                timeout=300,
            )
            result = resp.json()
            if result.get("success"):
                return result.get("results", [])
            return [{"url": u, "success": False, "error": result.get("error", "")} for u in urls]
        except Exception as e:
            logger.warning(f"Batch browse failed: {e}")
            return [{"url": u, "success": False, "error": str(e)} for u in urls]

    # ── Smart content extraction ──────────────────────────────────

    def extract_content(self, url: str, task: str = "Extract the main text content") -> Dict[str, Any]:
        """
        Extract content from a URL using the best available method:
        1. Try Crawl4AI first (fast, optimized for LLM consumption)
        2. Fall back to browser engine (full Playwright for interactive pages)
        """
        # Try Crawl4AI first for speed
        if self._get_crawl4ai():
            content = self._crawl4ai_extract(url)
            if content and len(content) > 100:
                return {
                    "success": True,
                    "url": url,
                    "content": content,
                    "method": "crawl4ai",
                }

        # Fall back to browser engine
        result = self.browse(url, task=task)
        if result.get("success"):
            result["method"] = "browser_engine"
        return result

    def extract_batch(
        self,
        urls: List[str],
        task: str = "Extract the main text content",
        max_workers: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Extract content from multiple URLs.
        Uses Crawl4AI for bulk extraction, browser engine for failures.
        """
        results = []
        browser_fallback_urls = []

        if self._get_crawl4ai():
            # Try Crawl4AI first for all URLs (parallel)
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                future_to_url = {
                    pool.submit(self._crawl4ai_extract, url): url for url in urls
                }
                for future in as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        content = future.result()
                        if content and len(content) > 100:
                            results.append({
                                "success": True,
                                "url": url,
                                "content": content,
                                "method": "crawl4ai",
                            })
                        else:
                            browser_fallback_urls.append(url)
                    except Exception:
                        browser_fallback_urls.append(url)
        else:
            browser_fallback_urls = list(urls)

        # Browser engine fallback for failed/missing URLs
        if browser_fallback_urls and self._check_cortex():
            browser_results = self.browse_batch(browser_fallback_urls, task=task)
            for br in browser_results:
                br["method"] = "browser_engine"
                results.append(br)

        return results

    # ── Research queries (main BI research interface) ─────────────

    def research_queries(
        self,
        queries: List[str],
        max_results_per_query: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Research a list of queries:
        1. SearXNG finds URLs (fast, structured) — or browser-based DuckDuckGo search
        2. Crawl4AI / browser engine extracts content from top results

        Returns list of {"query": str, "findings": str, "source_urls": list}.
        """
        searxng = self._get_searxng()
        cortex_available = self._check_cortex()

        if not searxng and not cortex_available:
            logger.warning(
                "[WebResearch] Neither SearXNG nor cortex available — no web research possible"
            )
            return []

        logger.info(
            f"[WebResearch] Researching {len(queries)} queries "
            f"(SearXNG: {'yes' if searxng else 'no'}, "
            f"Crawl4AI: {'yes' if self._get_crawl4ai() else 'no'}, "
            f"Browser: {'yes' if cortex_available else 'no'})"
        )

        results = []

        def _research_single(query: str) -> Dict[str, Any]:
            source_urls = []
            findings_parts = []

            if searxng:
                # ── Path A: SearXNG for URL discovery ──────────────
                search_results = searxng.search(
                    query=query,
                    max_results=max_results_per_query,
                )

                if search_results:
                    # Collect snippets from search results
                    for sr in search_results:
                        if sr.get("content"):
                            findings_parts.append(
                                f"[{sr.get('title', 'Untitled')}] {sr['content']}"
                            )
                        if sr.get("url"):
                            source_urls.append(sr["url"])

                    # Extract full content from top URLs
                    top_urls = [sr["url"] for sr in search_results[:2] if sr.get("url")]
                    if top_urls:
                        for url in top_urls:
                            extracted = self.extract_content(url)
                            if extracted.get("success") and extracted.get("content"):
                                findings_parts.append(
                                    f"[Full: {url}] {extracted['content'][:1000]}"
                                )

                if findings_parts:
                    return {
                        "query": query,
                        "findings": "\n\n".join(findings_parts),
                        "source_urls": source_urls,
                        "success": True,
                        "method": "searxng",
                    }

            # ── Path B: DuckDuckGo via browser (original fallback) ──
            if cortex_available:
                search_url = f"https://duckduckgo.com/?q={requests.utils.quote(query)}&t=h_&ia=web"
                browse_result = self.browse(
                    url=search_url,
                    task=(
                        f"Search for: {query}. "
                        f"Extract the top {max_results_per_query} search result titles, "
                        f"snippets, and URLs. Return them as structured text."
                    ),
                )

                if browse_result.get("success"):
                    return {
                        "query": query,
                        "findings": browse_result.get("content", ""),
                        "source_urls": [search_url],
                        "success": True,
                        "method": "browser_duckduckgo",
                    }

            return {
                "query": query,
                "findings": "",
                "source_urls": [],
                "success": False,
                "error": "No search method available",
            }

        # Run queries in parallel
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {pool.submit(_research_single, q): q for q in queries}
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                    if result["success"]:
                        logger.info(
                            f"[WebResearch] '{result['query'][:50]}' — "
                            f"{len(result['findings'])} chars via {result.get('method', 'unknown')}"
                        )
                except Exception as e:
                    query = futures[future]
                    logger.warning(f"[WebResearch] Query failed: {query[:50]} — {e}")
                    results.append({
                        "query": query,
                        "findings": "",
                        "source_urls": [],
                        "success": False,
                        "error": str(e),
                    })

        successful = sum(1 for r in results if r["success"])
        logger.info(
            f"[WebResearch] Complete: {successful}/{len(queries)} queries returned results"
        )
        return results
