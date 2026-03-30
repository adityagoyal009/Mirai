"""
Gateway Client — web_search and web_fetch via Claude CLI headless calls.

Uses Claude's built-in WebSearch tool through the CLI for zero-cost web searches.
Replaces the old claude-proxy HTTP approach with direct subprocess calls.

Usage:
    from .gateway_client import web_search, web_fetch, batch_fetch

    results = web_search("CleanTech market size 2026", count=10)
    page = web_fetch("https://example.com/report")
"""

import json as _json
import re
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..utils.cli_llm import call_claude
from ..utils.logger import get_logger

logger = get_logger('mirai.gateway_client')


def web_search(query: str, count: int = 10, freshness: str = "") -> List[Dict]:
    """
    Search the web via Claude CLI with WebSearch tool.

    Returns list of dicts with: title, url, description.
    Falls back to empty list on error.
    """
    try:
        prompt = (
            f"Search the web for: {query}\n\n"
            f"Return the top {min(count, 10)} results as a JSON array. "
            "Each result must have: title, url, description (1-2 sentence summary). "
            "Return ONLY the JSON array, no other text."
        )
        raw = call_claude(
            prompt,
            model="claude-sonnet-4-6",
            max_tokens=2000,
            web_search=True,
            max_turns=5,
            timeout=45,
        )

        # Extract JSON array from response
        raw = raw.strip()
        first_bracket = raw.find('[')
        if first_bracket >= 0:
            raw = raw[first_bracket:]

        results = _json.loads(raw)
        if isinstance(results, list):
            cleaned = []
            for r in results:
                if isinstance(r, dict) and r.get("url"):
                    cleaned.append({
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "description": r.get("description", r.get("snippet", "")),
                        "siteName": r.get("siteName", ""),
                    })
            logger.info(f"[GatewayClient] web_search '{query[:50]}' -> {len(cleaned)} results")
            return cleaned
        return []
    except _json.JSONDecodeError:
        # Claude returned prose with inline citations — extract URLs
        try:
            urls = re.findall(r'https?://[^\s\)>\]"]+', raw)
            if urls:
                results = [{"title": query, "url": u, "description": ""} for u in urls[:count]]
                logger.info(f"[GatewayClient] web_search '{query[:50]}' -> {len(results)} URLs extracted from prose")
                return results
        except Exception as e:
            logger.debug(f"[GatewayClient] web_search URL extraction from prose also failed: {e}")
        logger.warning(f"[GatewayClient] web_search JSON parse failed for '{query[:50]}'")
        return []
    except Exception as e:
        logger.warning(f"[GatewayClient] web_search failed: {e}")
        return []


def web_fetch(url: str, max_chars: int = 50000) -> Optional[Dict]:
    """
    Fetch and extract content from a URL via Claude CLI with WebSearch.

    Returns dict with: url, title, content.
    Returns None on error.
    """
    try:
        prompt = (
            f"Visit this URL and extract the main text content: {url}\n\n"
            "Return the page title and main body text. Skip navigation, ads, and boilerplate. "
            "Format as plain text, not markdown."
        )
        content = call_claude(
            prompt,
            model="claude-sonnet-4-6",
            max_tokens=4000,
            web_search=True,
            max_turns=5,
            timeout=60,
        )
        if content and len(content) > 50:
            return {
                "url": url,
                "title": url.split("/")[-1],
                "content": content[:max_chars],
                "extractor": "claude-cli-web",
                "status": 200,
            }
        return None
    except Exception as e:
        logger.warning(f"[GatewayClient] web_fetch failed for {url}: {e}")
        return None


def batch_fetch(urls: List[str], max_chars: int = 30000, max_workers: int = 3) -> List[Dict]:
    """Fetch multiple URLs in parallel. Skips failed fetches."""
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(web_fetch, url, max_chars): url for url in urls}
        for f in as_completed(futures):
            r = f.result()
            if r and r.get("content"):
                results.append(r)
    return results


def search_and_extract(query: str, count: int = 10, max_crawl: int = 5,
                       max_chars: int = 30000) -> List[Dict]:
    """Search + fetch top results in one call."""
    search_results = web_search(query, count=count)
    if not search_results:
        return []

    extracted = []
    visited = set()
    for r in search_results:
        url = r.get("url", "")
        if not url or url in visited:
            continue
        visited.add(url)
        page = web_fetch(url, max_chars)
        if page and page.get("content"):
            from urllib.parse import urlparse
            domain = urlparse(url).hostname or ''
            extracted.append({
                "title": r.get("title", page.get("title", "")),
                "url": url,
                "content": page["content"],
                "source_domain": domain.replace("www.", ""),
            })
        if len(extracted) >= max_crawl:
            break
    return extracted
