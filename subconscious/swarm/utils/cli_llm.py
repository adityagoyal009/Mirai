"""
CLI LLM Client — subprocess wrapper for Claude, Codex, and Gemini CLIs.

Replaces claude-proxy (port 4000) with direct headless CLI calls.
Each CLI uses the user's existing subscription — zero API cost.

Usage:
    from ..utils.cli_llm import call_model, call_model_json

    # Simple text generation
    text = call_claude("Summarize this", model="claude-sonnet-4-6")

    # JSON output
    data = call_model_json("claude", "claude-opus-4-6", "Return JSON with key 'name'")

    # Web search
    text = call_claude("Search for AI funding news", web_search=True, max_turns=5)

    # Codex / Gemini
    text = call_codex("Analyze this startup")
    text = call_gemini("Evaluate market size")
"""

import json
import os
import re
import shutil
import subprocess
import time
from typing import Optional, Dict, Any

from .logger import get_logger

logger = get_logger('mirai.cli_llm')

# CLI binary paths (discovered once)
_CLI_PATHS: Dict[str, Optional[str]] = {}

# Default timeout per provider (seconds)
_TIMEOUTS = {
    "claude": 180,
    "codex": 240,  # codex is slower due to startup overhead
    "gemini": 120,
}


def _find_cli(name: str) -> Optional[str]:
    """Find CLI binary path, cached after first lookup."""
    if name not in _CLI_PATHS:
        _CLI_PATHS[name] = shutil.which(name)
        if _CLI_PATHS[name]:
            logger.info(f"[CLI] Found {name} at {_CLI_PATHS[name]}")
        else:
            logger.warning(f"[CLI] {name} not found in PATH")
    return _CLI_PATHS[name]


def _parse_claude_json_envelope(raw: str) -> str:
    """Extract the 'result' field from Claude CLI's JSON output envelope."""
    try:
        envelope = json.loads(raw)
        if isinstance(envelope, dict):
            if envelope.get("is_error") or envelope.get("type") == "error":
                error_msg = envelope.get("result", envelope.get("error", "Unknown CLI error"))
                raise RuntimeError(f"Claude CLI error: {error_msg}")
            # Detect max_turns exhaustion (model tried tool_use but ran out of turns)
            if envelope.get("subtype") == "error_max_turns" and envelope.get("stop_reason") == "tool_use":
                raise RuntimeError("Claude CLI: model tried tool_use but max_turns exhausted (add --allowedTools '' to disable tools)")
            result = envelope.get("result", "")
            if not result and envelope.get("subtype") == "error_max_turns":
                raise RuntimeError("Claude CLI: max_turns exhausted with no result")
            return result
    except json.JSONDecodeError:
        # Not JSON envelope — return raw
        return raw
    return ""


def _parse_codex_ndjson(raw: str) -> str:
    """Extract the agent_message text from Codex NDJSON output."""
    last_message = ""
    for line in raw.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
            if (event.get("type") == "item.completed" and
                    isinstance(event.get("item"), dict) and
                    event["item"].get("type") == "agent_message"):
                last_message = event["item"].get("text", "")
        except json.JSONDecodeError:
            continue
    return last_message


def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences from LLM output."""
    text = text.strip()
    text = re.sub(r'^```(?:json|html)?\s*\n?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\n?```\s*$', '', text)
    return text.strip()


def _extract_json_from_text(text: str) -> str:
    """Find the first JSON object or array in text."""
    text = _strip_markdown_fences(text)
    # Find first { or [
    first_brace = text.find('{')
    first_bracket = text.find('[')
    starts = [i for i in [first_brace, first_bracket] if i >= 0]
    if starts:
        return text[min(starts):]
    return text


# ── Gateway API (fast path) ─────────────────────────────────────────

_GATEWAY_URL = os.environ.get("MIRAI_GATEWAY_URL", "http://127.0.0.1:19789")
_GATEWAY_TOKEN = os.environ.get("MIRAI_GATEWAY_TOKEN", "mirai-local-token")
_GATEWAY_OK: Optional[bool] = None


def _try_gateway(prompt: str, model: str, max_tokens: int, timeout: int) -> Optional[str]:
    """Try calling via Mirai Gateway API. Returns None if gateway unavailable."""
    global _GATEWAY_OK
    import urllib.request
    import urllib.error

    # Check gateway once
    if _GATEWAY_OK is None:
        try:
            req = urllib.request.Request(
                f"{_GATEWAY_URL}/v1/models",
                headers={"Authorization": f"Bearer {_GATEWAY_TOKEN}"},
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                _GATEWAY_OK = resp.status == 200
        except Exception:
            _GATEWAY_OK = False
        if _GATEWAY_OK:
            logger.info(f"[CLI] Gateway available at {_GATEWAY_URL} — using fast API path")
        else:
            logger.error(f"[CLI] Mirai Gateway not available at {_GATEWAY_URL} — LLM calls will fail")

    if not _GATEWAY_OK:
        return None

    # Normalize model name
    api_model = model
    if "/" not in model:
        if "claude" in model.lower():
            api_model = f"anthropic/{model}"
        elif "gpt" in model.lower() or "o3" in model.lower():
            api_model = f"openai/{model}"
        elif "gemini" in model.lower():
            api_model = f"google/{model}"

    payload = json.dumps({
        "model": api_model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{_GATEWAY_URL}/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {_GATEWAY_TOKEN}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    choices = body.get("choices", [])
    if not choices:
        return None
    content = choices[0].get("message", {}).get("content", "")
    return content if content else None


# ── Claude CLI ──────────────────────────────────────────────────────

def call_claude(
    prompt: str,
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 4096,
    web_search: bool = False,
    max_turns: int = 1,
    timeout: Optional[int] = None,
) -> str:
    """
    Call Claude via Mirai Gateway API. No CLI fallback — fails loud if gateway is down.
    web_search parameter is accepted for backward compatibility but ignored
    (research now uses OpenClaw subagent, not CLI web search).

    Args:
        prompt: The prompt text
        model: Model name (claude-opus-4-6, claude-sonnet-4-6, etc.)
        max_tokens: Max output tokens
        web_search: DEPRECATED — kept for interface compatibility, ignored
        max_turns: DEPRECATED — kept for interface compatibility, ignored
        timeout: Timeout in seconds

    Returns:
        Model's text response (markdown fences stripped)
    """
    timeout = timeout or _TIMEOUTS["claude"]

    if web_search:
        logger.warning("[CLI] web_search=True is deprecated. Research should use OpenClaw subagent instead.")

    # ── Gateway API only — no CLI fallback ──
    t0 = time.time()
    result = _try_gateway(prompt, model, max_tokens, timeout)
    if result is None:
        raise RuntimeError(f"Mirai Gateway returned empty response for {model}. Is the gateway running on {_GATEWAY_URL}?")
    result = _strip_markdown_fences(result)
    elapsed = time.time() - t0
    logger.info(f"[LLM] Claude {model} (gateway) done — {len(result)} chars, {elapsed:.1f}s")
    return result


# ── Codex CLI ───────────────────────────────────────────────────────

def call_codex(
    prompt: str,
    model: str = "gpt-5.4",
    timeout: Optional[int] = None,
) -> str:
    """
    Call OpenAI via Mirai Gateway API. No CLI fallback.

    Args:
        prompt: The prompt text
        model: Model name (gpt-5.4, gpt-5.3-codex, etc.)
        timeout: Timeout in seconds

    Returns:
        Model's text response
    """
    timeout = timeout or _TIMEOUTS["codex"]

    t0 = time.time()
    result = _try_gateway(prompt, model, max_tokens=4096, timeout=timeout)
    if result is None:
        raise RuntimeError(f"Mirai Gateway returned empty response for {model}. Is the gateway running on {_GATEWAY_URL}?")
    result = _strip_markdown_fences(result)
    elapsed = time.time() - t0
    logger.info(f"[LLM] Codex {model} (gateway) done — {len(result)} chars, {elapsed:.1f}s")
    return result


# ── Gemini CLI ──────────────────────────────────────────────────────

def call_gemini(
    prompt: str,
    model: str = "gemini-3.1-pro-preview",
    timeout: Optional[int] = None,
) -> str:
    """
    Call Google Gemini via Mirai Gateway API. No CLI fallback.

    Args:
        prompt: The prompt text
        model: Gemini model name
        timeout: Timeout in seconds

    Returns:
        Model's text response
    """
    timeout = timeout or _TIMEOUTS["gemini"]

    t0 = time.time()
    result = _try_gateway(prompt, model, max_tokens=4096, timeout=timeout)
    if result is None:
        raise RuntimeError(f"Mirai Gateway returned empty response for {model}. Is the gateway running on {_GATEWAY_URL}?")
    result = _strip_markdown_fences(result)
    elapsed = time.time() - t0
    logger.info(f"[LLM] Gemini {model} (gateway) done — {len(result)} chars, {elapsed:.1f}s")
    return result


# ── Dispatcher ──────────────────────────────────────────────────────

# Model → provider mapping
_MODEL_PROVIDERS = {
    "claude-opus-4-6": "claude",
    "claude-sonnet-4-6": "claude",
    "claude-haiku-4-5": "claude",
    # Web variants (same provider, web_search flag set by caller)
    "claude-opus-4-6-web": "claude",
    "claude-sonnet-4-6-web": "claude",
    # OpenAI
    "gpt-5.4": "codex",
    "gpt-5.4-web": "codex",
    "gpt-5.3-codex": "codex",
    "gpt-5.3": "codex",
    "o3": "codex",
    # Gemini
    "gemini-3.1-pro-preview": "gemini",
    "gemini-3-pro-preview": "gemini",
    "gemini-3-flash-preview": "gemini",
    "gemini-2.5-pro": "gemini",
    "gemini-2.5-flash": "gemini",
}


def detect_provider(model: str) -> str:
    """Detect CLI provider from model name."""
    if model in _MODEL_PROVIDERS:
        return _MODEL_PROVIDERS[model]
    model_lower = model.lower()
    if "claude" in model_lower:
        return "claude"
    if "gpt" in model_lower or "codex" in model_lower or model_lower.startswith("o"):
        return "codex"
    if "gemini" in model_lower:
        return "gemini"
    # Default to Claude
    return "claude"


def call_model(
    provider: str,
    model: str,
    prompt: str,
    max_tokens: int = 4096,
    web_search: bool = False,
    max_turns: int = 1,
    timeout: Optional[int] = None,
) -> str:
    """
    Dispatch to the appropriate CLI based on provider.

    Args:
        provider: "claude", "codex", or "gemini"
        model: Model identifier
        prompt: The prompt text
        max_tokens: Max output tokens (Claude only)
        web_search: Enable web search (Claude only)
        max_turns: Max turns (Claude only)
        timeout: Subprocess timeout

    Returns:
        Model's text response
    """
    if provider == "claude":
        # Strip -web suffix for actual model name
        actual_model = model.replace("-web", "")
        is_web = web_search or model.endswith("-web")
        return call_claude(
            prompt, model=actual_model, max_tokens=max_tokens,
            web_search=is_web, max_turns=max_turns if is_web else 1,
            timeout=timeout,
        )
    elif provider == "codex":
        actual_model = model.replace("-web", "")
        return call_codex(prompt, model=actual_model, timeout=timeout)
    elif provider == "gemini":
        return call_gemini(prompt, model=model, timeout=timeout)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def call_model_json(
    provider: str,
    model: str,
    prompt: str,
    max_tokens: int = 4096,
    web_search: bool = False,
    max_turns: int = 1,
    timeout: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Call a model and parse the response as JSON.

    Adds JSON enforcement to the prompt, strips markdown fences,
    and handles truncated JSON repair.
    """
    # Add JSON enforcement suffix
    json_suffix = "\n\nYou MUST respond with valid JSON only. No markdown fences, no explanation, no text before or after the JSON."
    enforced_prompt = prompt + json_suffix

    raw = call_model(
        provider, model, enforced_prompt,
        max_tokens=max_tokens, web_search=web_search,
        max_turns=max_turns, timeout=timeout,
    )

    # Extract JSON from response
    json_text = _extract_json_from_text(raw)

    try:
        return json.loads(json_text)
    except json.JSONDecodeError:
        # Try to repair truncated JSON
        repaired = _repair_truncated_json(json_text)
        if repaired is not None:
            return repaired
        logger.warning(f"[CLI] JSON parse failed for {provider}/{model}: {json_text[:200]}")
        raise ValueError(f"Invalid JSON from {provider}/{model}: {json_text[:200]}")


def _repair_truncated_json(text: str) -> Optional[Dict]:
    """Try to repair JSON truncated by max_tokens."""
    if not text or text[0] not in '{[':
        return None
    # Strip trailing incomplete string
    for trim in [text, text.rstrip(',')]:
        opens = trim.count('{') - trim.count('}')
        brackets = trim.count('[') - trim.count(']')
        if opens >= 0 and brackets >= 0:
            closer = ']' * brackets + '}' * opens
            try:
                return json.loads(trim + closer)
            except json.JSONDecodeError:
                continue
    return None
