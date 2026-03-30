"""
Gateway Client — OpenClaw-backed web search and fetch helpers.

These helpers are for fresh external facts. They intentionally avoid the old
Claude `web_search=True` shim and route through OpenClaw's native tools.
"""

import json as _json
import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from ..utils.llm_client import _call_openclaw_gateway, _strip_markdown_fences
from ..utils.logger import get_logger

logger = get_logger("mirai.gateway_client")

_SEARCH_CACHE: Dict[Tuple[str, int, str], List[Dict]] = {}


def _openclaw_text(prompt: str, *, max_tokens: int, timeout: int) -> str:
    raw = _call_openclaw_gateway(
        [{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        timeout=timeout,
    )
    return _strip_markdown_fences(raw)


def _extract_json_payload(raw: str) -> str:
    raw = raw.strip()
    first_brace = raw.find("{")
    first_bracket = raw.find("[")
    starts = [i for i in (first_brace, first_bracket) if i >= 0]
    return raw[min(starts):] if starts else raw


def web_search(query: str, count: int = 10, freshness: str = "") -> List[Dict]:
    """
    Search the web via OpenClaw's native tools.

    Returns a list of dicts with: title, url, description.
    Falls back to an empty list on error.
    """
    count = max(1, min(int(count or 10), 10))
    freshness = (freshness or "").strip()
    cache_key = (query.strip(), count, freshness)
    if cache_key in _SEARCH_CACHE:
        return [dict(item) for item in _SEARCH_CACHE[cache_key]]

    freshness_clause = f"\nFreshness preference: {freshness}." if freshness else ""
    prompt = (
        "Search the live web using your native tools.\n"
        f"Query: {query}\n"
        f"Return the top {count} results as a JSON array only.{freshness_clause}\n"
        'Each item must be: {"title": "...", "url": "https://...", "description": "..."}\n'
        "Rules:\n"
        "- Use real live search results only\n"
        "- Omit duplicates\n"
        "- If nothing relevant is found, return []\n"
        "- No prose before or after the JSON"
    )

    try:
        raw = _openclaw_text(prompt, max_tokens=2500, timeout=90)
        payload = _extract_json_payload(raw)
        results = _json.loads(payload)
        cleaned: List[Dict] = []
        if isinstance(results, list):
            for item in results:
                if not isinstance(item, dict) or not item.get("url"):
                    continue
                cleaned.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "description": item.get("description", item.get("snippet", "")),
                        "siteName": item.get("siteName", ""),
                    }
                )
        logger.info(f"[GatewayClient] web_search '{query[:50]}' -> {len(cleaned)} results")
        _SEARCH_CACHE[cache_key] = cleaned
        return [dict(item) for item in cleaned]
    except _json.JSONDecodeError:
        urls = re.findall(r'https?://[^\s\)>\]"]+', raw if "raw" in locals() else "")
        if urls:
            extracted = [{"title": query, "url": u, "description": ""} for u in urls[:count]]
            logger.info(
                f"[GatewayClient] web_search '{query[:50]}' -> {len(extracted)} URLs extracted from prose"
            )
            _SEARCH_CACHE[cache_key] = extracted
            return [dict(item) for item in extracted]
        logger.warning(f"[GatewayClient] web_search JSON parse failed for '{query[:50]}'")
        return []
    except Exception as e:
        logger.warning(f"[GatewayClient] web_search failed: {e}")
        return []


def web_fetch(url: str, max_chars: int = 50000) -> Optional[Dict]:
    """
    Fetch and extract content from a URL via OpenClaw's native browsing tools.

    Returns dict with: url, title, content.
    Returns None on error.
    """
    prompt = (
        "Visit the URL below using your native tools and extract the main body.\n"
        f"URL: {url}\n"
        'Return JSON only: {"title": "...", "content": "..."}\n'
        "Rules:\n"
        "- Extract the main article/page text only\n"
        "- Skip navigation, ads, and boilerplate\n"
        "- Keep content concise but useful"
    )

    try:
        raw = _openclaw_text(prompt, max_tokens=5000, timeout=120)
        payload = _extract_json_payload(raw)
        parsed = _json.loads(payload)
        if isinstance(parsed, dict) and parsed.get("content"):
            return {
                "url": url,
                "title": parsed.get("title", url.split("/")[-1]),
                "content": str(parsed.get("content", ""))[:max_chars],
                "extractor": "openclaw-web",
                "status": 200,
            }
        return None
    except Exception as e:
        logger.warning(f"[GatewayClient] web_fetch failed for {url}: {e}")
        return None


def batch_fetch(urls: List[str], max_chars: int = 30000, max_workers: int = 3) -> List[Dict]:
    """Fetch multiple URLs sequentially. OpenClaw already handles its own tool calls."""
    results = []
    for url in urls[:max_workers]:
        page = web_fetch(url, max_chars)
        if page and page.get("content"):
            results.append(page)
    return results


def search_and_extract(
    query: str,
    count: int = 10,
    max_crawl: int = 5,
    max_chars: int = 30000,
) -> List[Dict]:
    """Search + fetch top results."""
    search_results = web_search(query, count=count)
    if not search_results:
        return []

    extracted = []
    visited = set()
    for result in search_results:
        url = result.get("url", "")
        if not url or url in visited:
            continue
        visited.add(url)
        page = web_fetch(url, max_chars)
        if page and page.get("content"):
            domain = urlparse(url).hostname or ""
            extracted.append(
                {
                    "url": url,
                    "title": page.get("title", result.get("title", "")),
                    "content": page.get("content", ""),
                    "description": result.get("description", ""),
                    "domain": domain,
                }
            )
        if len(extracted) >= max_crawl:
            break
    return extracted
