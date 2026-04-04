"""
Gateway Client — live web search and fetch helpers.

Provider order:
1. Claude Code CLI with native WebSearch/WebFetch
2. OpenClaw gateway fallback
"""

import json as _json
import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from ..utils.llm_client import _call_openclaw_gateway, _strip_markdown_fences
from ..utils.cli_subprocess import run_cli_to_files
from ..utils.logger import get_logger

logger = get_logger("mirai.gateway_client")

_SEARCH_CACHE: Dict[Tuple[str, int, str], List[Dict]] = {}


def _claude_cli_text(prompt: str, *, max_tokens: int, timeout: int) -> str:
    del max_tokens  # Claude CLI does not expose an equivalent output cap flag here.
    result = run_cli_to_files(
        [
            "claude",
            "-p",
            "--allowedTools",
            "WebSearch,WebFetch",
            "--output-format",
            "text",
            "--max-turns",
            "12",
        ],
        timeout=timeout,
        stdin_data=prompt,
    )
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise RuntimeError(f"Claude CLI failed (exit {result.returncode}): {stderr[:300]}")
    raw = _strip_markdown_fences((result.stdout or "").strip())
    if not raw:
        raise RuntimeError("Claude CLI returned empty output")
    return raw


def _openclaw_text(prompt: str, *, max_tokens: int, timeout: int) -> str:
    raw = _call_openclaw_gateway(
        [{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        timeout=timeout,
    )
    return _strip_markdown_fences(raw)


def _provider_text(prompt: str, *, max_tokens: int, timeout: int) -> Tuple[str, str]:
    errors = []
    try:
        return "claude-cli-web", _claude_cli_text(prompt, max_tokens=max_tokens, timeout=timeout)
    except Exception as e:
        errors.append(f"Claude CLI: {e}")

    try:
        return "openclaw-web", _openclaw_text(prompt, max_tokens=max_tokens, timeout=timeout)
    except Exception as e:
        errors.append(f"OpenClaw: {e}")

    raise RuntimeError(" ; ".join(errors))


def _extract_json_payload(raw: str) -> str:
    raw = raw.strip()
    first_brace = raw.find("{")
    first_bracket = raw.find("[")
    starts = [i for i in (first_brace, first_bracket) if i >= 0]
    return raw[min(starts):] if starts else raw


def _extract_balanced_json(raw: str) -> str:
    payload = _extract_json_payload(raw)
    if not payload or payload[0] not in "[{":
        return payload

    opener = payload[0]
    closer = "}" if opener == "{" else "]"
    depth = 0
    in_string = False
    escape = False

    for idx, ch in enumerate(payload):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return payload[:idx + 1]
    return payload


def _normalize_query(query: str) -> str:
    query = re.sub(r"\s+", " ", (query or "")).strip()
    return query[:180]


def _fallback_query(query: str) -> Optional[str]:
    shortened = re.sub(r'["\']', "", query or "")
    shortened = re.sub(r"\s+", " ", shortened).strip()
    words = shortened.split()
    if len(words) <= 10 and len(shortened) <= 120:
        return None
    return " ".join(words[:10])[:120]


def _coerce_results(results: object, query: str, count: int) -> List[Dict]:
    if isinstance(results, dict):
        for key in ("results", "items", "data"):
            if isinstance(results.get(key), list):
                results = results[key]
                break
        else:
            results = []

    cleaned: List[Dict] = []
    if isinstance(results, list):
        for item in results:
            if not isinstance(item, dict) or not item.get("url"):
                continue
            cleaned.append(
                {
                    "title": item.get("title", "") or query,
                    "url": item.get("url", ""),
                    "description": item.get("description", item.get("snippet", "")),
                    "siteName": item.get("siteName", ""),
                }
            )
            if len(cleaned) >= count:
                break
    return cleaned


def web_search(query: str, count: int = 10, freshness: str = "") -> List[Dict]:
    """
    Search the live web via Claude CLI first, then OpenClaw fallback.

    Returns a list of dicts with: title, url, description.
    Falls back to an empty list on error.
    """
    count = max(1, min(int(count or 10), 10))
    query = _normalize_query(query)
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

    attempts = [(query, 90)]
    fallback_query = _fallback_query(query)
    if fallback_query and fallback_query != query:
        attempts.append((fallback_query, 60))

    last_error: Optional[str] = None
    for attempt_query, timeout in attempts:
        attempt_prompt = prompt.replace(f"Query: {query}", f"Query: {attempt_query}")
        try:
            provider, raw = _provider_text(attempt_prompt, max_tokens=2500, timeout=timeout)
            payload = _extract_balanced_json(raw)
            results = _json.loads(payload)
            cleaned = _coerce_results(results, attempt_query, count)
            if cleaned:
                logger.info(
                    f"[GatewayClient] web_search '{query[:50]}' -> {len(cleaned)} results via {provider}"
                )
                _SEARCH_CACHE[cache_key] = cleaned
                return [dict(item) for item in cleaned]
        except _json.JSONDecodeError:
            urls = re.findall(r'https?://[^\s\)>\]"]+', raw if "raw" in locals() else "")
            if urls:
                extracted = [{"title": attempt_query, "url": u, "description": ""} for u in urls[:count]]
                logger.info(
                    f"[GatewayClient] web_search '{query[:50]}' -> {len(extracted)} URLs extracted from prose"
                )
                _SEARCH_CACHE[cache_key] = extracted
                return [dict(item) for item in extracted]
            last_error = f"JSON parse failed for '{attempt_query[:50]}'"
        except Exception as e:
            last_error = str(e)

    if last_error and "JSON parse failed" in last_error:
        logger.warning(f"[GatewayClient] {last_error}")
    elif last_error:
        logger.warning(f"[GatewayClient] web_search failed: {last_error}")
    return []


def web_fetch(url: str, max_chars: int = 50000) -> Optional[Dict]:
    """
    Fetch and extract content from a URL via Claude CLI first, then OpenClaw fallback.

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
        provider, raw = _provider_text(prompt, max_tokens=5000, timeout=120)
        payload = _extract_json_payload(raw)
        parsed = _json.loads(payload)
        if isinstance(parsed, dict) and parsed.get("content"):
            return {
                "url": url,
                "title": parsed.get("title", url.split("/")[-1]),
                "content": str(parsed.get("content", ""))[:max_chars],
                "extractor": provider,
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
