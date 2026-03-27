"""
LLM Client Wrapper — routes all calls through Mirai Gateway (OpenAI-compatible API).

Direct HTTP calls to localhost:19789 — no CLI subprocess overhead.
Falls back to CLI if gateway is unavailable.

Gateway handles auth profile rotation, rate limiting, and model routing.
"""

import json
import os
import re
import threading
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from .logger import get_logger

logger = get_logger('mirai.llm_client')

# Gateway config
_GATEWAY_URL = os.environ.get("MIRAI_GATEWAY_URL", "http://127.0.0.1:19789")
_GATEWAY_TOKEN = os.environ.get("MIRAI_GATEWAY_TOKEN", "mirai-local-token")
_GATEWAY_AVAILABLE: Optional[bool] = None  # None = not checked yet

# ---------------------------------------------------------------------------
# _LLMObserver — lightweight, file-based observability for every LLM call
# ---------------------------------------------------------------------------
_LOG_DIR = os.path.expanduser("~/.mirai/logs")
_LOG_FILE = os.path.join(_LOG_DIR, "llm_calls.jsonl")


class _LLMObserver:
    """Singleton observer that logs per-call metrics to a JSONL file and
    maintains aggregate statistics in memory."""

    _instance: Optional["_LLMObserver"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "_LLMObserver":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._init_state()
                    cls._instance = inst
        return cls._instance

    def _init_state(self) -> None:
        os.makedirs(_LOG_DIR, exist_ok=True)
        self._write_lock = threading.Lock()
        self.total_calls: int = 0
        self.total_failures: int = 0
        self.total_json_failures: int = 0
        self._latency_sum: float = 0.0

    def record(
        self,
        *,
        model: str,
        latency_ms: float,
        input_tokens: int,
        output_tokens: int,
        success: bool,
        json_parse_ok: Optional[bool] = None,
        error: Optional[str] = None,
    ) -> None:
        entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": model,
            "latency_ms": round(latency_ms, 2),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "success": success,
            "json_parse_ok": json_parse_ok,
            "error": error,
        }
        try:
            with self._write_lock:
                with open(_LOG_FILE, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            pass
        with self._write_lock:
            self.total_calls += 1
            self._latency_sum += latency_ms
            if not success:
                self.total_failures += 1
            if json_parse_ok is False:
                self.total_json_failures += 1

    def report(self) -> Dict[str, Any]:
        with self._write_lock:
            avg = (self._latency_sum / self.total_calls) if self.total_calls else 0.0
            json_fail_rate = (
                (self.total_json_failures / self.total_calls)
                if self.total_calls
                else 0.0
            )
            return {
                "total_calls": self.total_calls,
                "total_failures": self.total_failures,
                "total_json_failures": self.total_json_failures,
                "avg_latency_ms": round(avg, 2),
                "json_parse_failure_rate": round(json_fail_rate, 4),
            }


_observer = _LLMObserver()


def _check_gateway() -> bool:
    """Check if Mirai Gateway is reachable. Cached after first check. No fallback — errors propagate."""
    global _GATEWAY_AVAILABLE
    if _GATEWAY_AVAILABLE is not None:
        return _GATEWAY_AVAILABLE
    try:
        req = urllib.request.Request(
            f"{_GATEWAY_URL}/v1/models",
            headers={"Authorization": f"Bearer {_GATEWAY_TOKEN}"},
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            _GATEWAY_AVAILABLE = resp.status == 200
    except Exception:
        _GATEWAY_AVAILABLE = False
    if _GATEWAY_AVAILABLE:
        logger.info(f"[LLMClient] Mirai Gateway available at {_GATEWAY_URL}")
    else:
        logger.error(f"[LLMClient] Mirai Gateway NOT available at {_GATEWAY_URL} — all LLM calls will fail")
    return _GATEWAY_AVAILABLE


def _call_gateway(
    model: str,
    messages: List[Dict[str, str]],
    max_tokens: int = 4096,
    temperature: float = 0.7,
    timeout: int = 180,
) -> str:
    """Call Mirai Gateway, OpenClaw Gateway, or Cloudflare Workers AI."""
    # Route openclaw model to OpenClaw gateway
    if model == "openclaw" or model.startswith("openclaw/"):
        return _call_openclaw_gateway(messages, max_tokens, timeout)

    # Route Cloudflare models directly to Workers AI REST API
    if model.startswith("@cf/"):
        return _call_cloudflare_ai(model, messages, max_tokens, temperature, timeout)

    # Route Groq models directly to Groq API (OpenAI-compatible)
    _GROQ_MODELS = {"llama-3.3-70b-versatile", "llama-3.1-8b-instant",
                    "meta-llama/llama-4-scout-17b-16e-instruct",
                    "moonshotai/kimi-k2-instruct", "moonshotai/kimi-k2-instruct-0905",
                    "openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3-32b"}
    if model in _GROQ_MODELS:
        return _call_groq(model, messages, max_tokens, temperature, timeout)

    # Route Cerebras models directly to Cerebras API (OpenAI-compatible)
    _CEREBRAS_MODELS = {"llama3.1-8b", "qwen-3-235b-a22b-instruct-2507"}
    if model in _CEREBRAS_MODELS:
        return _call_cerebras(model, messages, max_tokens, temperature, timeout)

    # Route Mistral models directly to Mistral API (OpenAI-compatible)
    _MISTRAL_MODELS = {"mistral-small-latest", "mistral-medium-latest", "mistral-large-latest",
                       "mistral-small-2603", "mistral-medium-2508", "open-mistral-nemo"}
    if model in _MISTRAL_MODELS:
        return _call_mistral(model, messages, max_tokens, temperature, timeout)

    # Route SambaNova models directly to SambaNova API (OpenAI-compatible)
    _SAMBANOVA_MODELS = {"DeepSeek-V3.1", "DeepSeek-V3.1-Terminus", "DeepSeek-V3-0324",
                         "DeepSeek-R1-0528", "DeepSeek-R1-Distill-Llama-70B",
                         "Llama-4-Maverick-17B-128E-Instruct", "Meta-Llama-3.3-70B-Instruct",
                         "Meta-Llama-3.1-8B-Instruct", "Qwen3-32B", "Qwen3-235B",
                         "MiniMax-M2.5", "gemma-3-12b-it", "gpt-oss-120b"}
    if model in _SAMBANOVA_MODELS:
        return _call_sambanova(model, messages, max_tokens, temperature, timeout)

    # Route Claude models through headless CLI first, gateway as fallback
    if "claude" in model.lower():
        return _call_claude_cli(model, messages, max_tokens, temperature, timeout)

    # Route OpenAI models through Codex CLI first, gateway as fallback
    if "gpt" in model.lower() or model.lower() in ("o3", "o4-mini"):
        return _call_codex_cli(model, messages, max_tokens, temperature, timeout)

    # Fallback: gateway for any unrecognized models
    if "/" not in model:
        if "gemini" in model.lower():
            model = f"google/{model}"

    payload = json.dumps({
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
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
        raise RuntimeError(f"Gateway returned no choices: {body}")

    content = choices[0].get("message", {}).get("content", "")
    if not content:
        raise RuntimeError(f"Gateway returned empty content: {body}")

    return content


# ── Claude CLI (headless, bypasses gateway) ──────────────────────────────

def _call_claude_cli(
    model: str,
    messages: List[Dict[str, str]],
    max_tokens: int = 4096,
    temperature: float = 0.7,
    timeout: int = 120,
) -> str:
    """Call Claude via headless CLI. Uses Claude Code subscription auth directly."""
    import subprocess

    # Build prompt from messages
    parts = []
    for m in messages:
        if m["role"] == "system":
            parts.append(m["content"])
        elif m["role"] == "user":
            parts.append(m["content"])
    prompt = "\n\n".join(parts)

    # Strip provider prefix if present (claude CLI doesn't want "anthropic/")
    cli_model = model.replace("anthropic/", "")

    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--model", cli_model, "--output-format", "text"],
            capture_output=True, text=True, timeout=timeout,
        )
        content = result.stdout.strip()
        if content:
            logger.info(f"[Claude CLI] {cli_model}: {len(content)} chars")
            return content
    except subprocess.TimeoutExpired:
        logger.warning(f"[Claude CLI] {cli_model} timed out after {timeout}s")
    except FileNotFoundError:
        logger.warning("[Claude CLI] 'claude' command not found")
    except Exception as e:
        logger.warning(f"[Claude CLI] {cli_model} failed: {e}")

    # Fallback to gateway
    logger.info(f"[Claude CLI] Falling back to gateway for {model}")
    normalized = f"anthropic/{cli_model}" if "/" not in cli_model else cli_model
    payload = json.dumps({
        "model": normalized, "messages": messages,
        "max_tokens": max_tokens, "temperature": temperature,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{_GATEWAY_URL}/v1/chat/completions", data=payload,
        headers={"Authorization": f"Bearer {_GATEWAY_TOKEN}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    choices = body.get("choices", [])
    if not choices:
        raise RuntimeError(f"Gateway returned no choices for {model}: {body}")
    content = choices[0].get("message", {}).get("content", "")
    if not content:
        raise RuntimeError(f"Gateway returned empty content for {model}")
    return content


# ── Codex CLI (headless, bypasses gateway) ───────────────────────────────

def _call_codex_cli(
    model: str,
    messages: List[Dict[str, str]],
    max_tokens: int = 4096,
    temperature: float = 0.7,
    timeout: int = 120,
) -> str:
    """Call OpenAI via Codex CLI. Uses Codex subscription auth directly."""
    import subprocess

    parts = []
    for m in messages:
        if m["role"] == "system":
            parts.append(m["content"])
        elif m["role"] == "user":
            parts.append(m["content"])
    prompt = "\n\n".join(parts)

    try:
        result = subprocess.run(
            ["codex", "exec", prompt, "-s", "read-only"],
            capture_output=True, text=True, timeout=timeout,
        )
        raw = result.stdout.strip()
        if raw:
            # Codex outputs header lines (version, model, workdir) then content
            # Find the actual content after the header block
            lines = raw.split("\n")
            content_lines = []
            past_header = False
            for line in lines:
                if past_header:
                    content_lines.append(line)
                elif line.strip() == "" and not past_header:
                    # Empty line after header = content starts
                    past_header = True
                elif not any(line.startswith(h) for h in ["OpenAI Codex", "--------", "workdir:", "model:", "provider:"]):
                    # Not a header line — must be content already
                    past_header = True
                    content_lines.append(line)

            content = "\n".join(content_lines).strip()
            # Codex sometimes appends "tokens used\nN\nOK" at the end
            if "\ntokens used\n" in content:
                content = content.split("\ntokens used\n")[0].strip()

            if content:
                logger.info(f"[Codex CLI] {model}: {len(content)} chars")
                return content
    except subprocess.TimeoutExpired:
        logger.warning(f"[Codex CLI] {model} timed out after {timeout}s")
    except FileNotFoundError:
        logger.warning("[Codex CLI] 'codex' command not found")
    except Exception as e:
        logger.warning(f"[Codex CLI] {model} failed: {e}")

    # Fallback to gateway
    logger.info(f"[Codex CLI] Falling back to gateway for {model}")
    normalized = f"openai/{model}" if "/" not in model else model
    payload = json.dumps({
        "model": normalized, "messages": messages,
        "max_tokens": max_tokens, "temperature": temperature,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{_GATEWAY_URL}/v1/chat/completions", data=payload,
        headers={"Authorization": f"Bearer {_GATEWAY_TOKEN}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    choices = body.get("choices", [])
    if not choices:
        raise RuntimeError(f"Gateway returned no choices for {model}: {body}")
    content = choices[0].get("message", {}).get("content", "")
    if not content:
        raise RuntimeError(f"Gateway returned empty content for {model}")
    return content


# ── Groq API (OpenAI-compatible, free tier) ──────────────────────────────
_GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")


def _call_groq(
    model: str,
    messages: List[Dict[str, str]],
    max_tokens: int = 4096,
    temperature: float = 0.7,
    timeout: int = 60,
) -> str:
    """Call Groq API (OpenAI-compatible). Blazing fast inference on LPU hardware."""
    import http.client
    import ssl

    payload = json.dumps({
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }).encode("utf-8")

    conn = http.client.HTTPSConnection("api.groq.com", timeout=timeout,
                                        context=ssl.create_default_context())
    conn.request("POST", "/openai/v1/chat/completions", body=payload, headers={
        "Authorization": f"Bearer {_GROQ_API_KEY}",
        "Content-Type": "application/json",
    })
    resp = conn.getresponse()
    raw_body = resp.read().decode("utf-8")
    conn.close()

    if resp.status != 200:
        logger.error(f"[Groq] HTTP {resp.status} for {model}: {raw_body[:300]}")
        raise RuntimeError(f"Groq HTTP {resp.status} for {model}: {raw_body[:300]}")

    body = json.loads(raw_body)
    choices = body.get("choices", [])
    if not choices:
        raise RuntimeError(f"Groq returned no choices for {model}: {body}")

    msg = choices[0].get("message", {})
    content = msg.get("content", "")
    if not content:
        # GPT-OSS puts response in reasoning field, others use reasoning_content
        content = msg.get("reasoning_content", "") or msg.get("reasoning", "")

    if not content:
        raise RuntimeError(f"Groq returned empty content for {model}: {body}")

    # Strip thinking tags from reasoning models
    if "</think>" in content:
        content = content.split("</think>", 1)[-1].strip()

    return content


# ── Mistral API (OpenAI-compatible, free tier 500K tok/min) ──────────────
_MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")


def _call_mistral(
    model: str,
    messages: List[Dict[str, str]],
    max_tokens: int = 4096,
    temperature: float = 0.7,
    timeout: int = 60,
) -> str:
    """Call Mistral API (OpenAI-compatible). European lab, different training data."""
    import http.client
    import ssl

    payload = json.dumps({
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }).encode("utf-8")

    conn = http.client.HTTPSConnection("api.mistral.ai", timeout=timeout,
                                        context=ssl.create_default_context())
    conn.request("POST", "/v1/chat/completions", body=payload, headers={
        "Authorization": f"Bearer {_MISTRAL_API_KEY}",
        "Content-Type": "application/json",
    })
    resp = conn.getresponse()
    raw_body = resp.read().decode("utf-8")
    conn.close()

    if resp.status != 200:
        logger.error(f"[Mistral] HTTP {resp.status} for {model}: {raw_body[:300]}")
        raise RuntimeError(f"Mistral HTTP {resp.status} for {model}: {raw_body[:300]}")

    body = json.loads(raw_body)
    choices = body.get("choices", [])
    if not choices:
        raise RuntimeError(f"Mistral returned no choices for {model}: {body}")

    content = choices[0].get("message", {}).get("content", "")
    if not content:
        raise RuntimeError(f"Mistral returned empty content for {model}: {body}")

    return content


# ── SambaNova API (OpenAI-compatible, free tier) ─────────────────────────
_SAMBANOVA_API_KEY = os.environ.get("SAMBANOVA_API_KEY", "")


def _call_sambanova(
    model: str,
    messages: List[Dict[str, str]],
    max_tokens: int = 4096,
    temperature: float = 0.7,
    timeout: int = 60,
) -> str:
    """Call SambaNova API (OpenAI-compatible). Fast inference on custom hardware."""
    import http.client
    import ssl

    payload = json.dumps({
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }).encode("utf-8")

    conn = http.client.HTTPSConnection("api.sambanova.ai", timeout=timeout,
                                        context=ssl.create_default_context())
    conn.request("POST", "/v1/chat/completions", body=payload, headers={
        "Authorization": f"Bearer {_SAMBANOVA_API_KEY}",
        "Content-Type": "application/json",
    })
    resp = conn.getresponse()
    raw_body = resp.read().decode("utf-8")
    conn.close()

    if resp.status != 200:
        logger.error(f"[SambaNova] HTTP {resp.status} for {model}: {raw_body[:300]}")
        raise RuntimeError(f"SambaNova HTTP {resp.status} for {model}: {raw_body[:300]}")

    body = json.loads(raw_body)
    choices = body.get("choices", [])
    if not choices:
        raise RuntimeError(f"SambaNova returned no choices for {model}: {body}")

    content = choices[0].get("message", {}).get("content", "")
    if not content:
        raise RuntimeError(f"SambaNova returned empty content for {model}: {body}")

    # Strip thinking tags from reasoning models
    if "</think>" in content:
        content = content.split("</think>", 1)[-1].strip()

    return content


# ── Cerebras API (OpenAI-compatible, free tier 1M tokens/day) ────────────
_CEREBRAS_API_KEY = os.environ.get("CEREBRAS_API_KEY", "")


def _call_cerebras(
    model: str,
    messages: List[Dict[str, str]],
    max_tokens: int = 4096,
    temperature: float = 0.7,
    timeout: int = 60,
) -> str:
    """Call Cerebras API (OpenAI-compatible). Wafer-scale chip, insane speed."""
    import http.client
    import ssl

    payload = json.dumps({
        "model": model,
        "messages": messages,
        "max_completion_tokens": max_tokens,
        "temperature": temperature,
    }).encode("utf-8")

    conn = http.client.HTTPSConnection("api.cerebras.ai", timeout=timeout,
                                        context=ssl.create_default_context())
    conn.request("POST", "/v1/chat/completions", body=payload, headers={
        "Authorization": f"Bearer {_CEREBRAS_API_KEY}",
        "Content-Type": "application/json",
    })
    resp = conn.getresponse()
    raw_body = resp.read().decode("utf-8")
    conn.close()

    if resp.status != 200:
        logger.error(f"[Cerebras] HTTP {resp.status} for {model}: {raw_body[:300]}")
        raise RuntimeError(f"Cerebras HTTP {resp.status} for {model}: {raw_body[:300]}")

    body = json.loads(raw_body)
    choices = body.get("choices", [])
    if not choices:
        raise RuntimeError(f"Cerebras returned no choices for {model}: {body}")

    content = choices[0].get("message", {}).get("content", "")
    if not content:
        raise RuntimeError(f"Cerebras returned empty content for {model}: {body}")

    # Strip thinking tags from reasoning models
    if "</think>" in content:
        content = content.split("</think>", 1)[-1].strip()

    return content


# ── Cloudflare Workers AI ────────────────────────────────────────────────
_CF_ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
_CF_API_TOKEN = os.environ.get("CLOUDFLARE_AI_TOKEN", "")


def _call_cloudflare_ai(
    model: str,
    messages: List[Dict[str, str]],
    max_tokens: int = 4096,
    temperature: float = 0.7,
    timeout: int = 120,
) -> str:
    """Call Cloudflare Workers AI REST API directly. Model must start with @cf/."""
    # Cloudflare API uses 'max_tokens' only for some models; omit if not supported
    body_dict: Dict[str, Any] = {
        "messages": messages,
        "temperature": temperature,
    }
    if max_tokens and max_tokens < 16000:
        body_dict["max_tokens"] = max_tokens

    payload = json.dumps(body_dict).encode("utf-8")

    # Use http.client directly to avoid urllib mangling the @ in model IDs
    import http.client
    import ssl
    conn = http.client.HTTPSConnection("api.cloudflare.com", timeout=timeout,
                                        context=ssl.create_default_context())
    path = f"/client/v4/accounts/{_CF_ACCOUNT_ID}/ai/run/{model}"
    headers = {
        "Authorization": f"Bearer {_CF_API_TOKEN}",
        "Content-Type": "application/json",
    }
    conn.request("POST", path, body=payload, headers=headers)
    resp = conn.getresponse()
    raw_body = resp.read().decode("utf-8")
    conn.close()

    if resp.status != 200:
        logger.error(f"[Cloudflare AI] HTTP {resp.status} for {model}: {raw_body[:300]}")
        raise RuntimeError(f"Cloudflare AI HTTP {resp.status} for {model}: {raw_body[:300]}")

    resp_body = json.loads(raw_body)

    if not resp_body.get("success", False):
        errors = resp_body.get("errors", [])
        err_msg = errors[0].get("message", "Unknown error") if errors else str(resp_body)
        raise RuntimeError(f"Cloudflare AI error for {model}: {err_msg}")

    result = resp_body.get("result", {})

    # Cloudflare models use two response formats:
    # 1. Simple: result.response (string) — used by most models
    # 2. OpenAI-compat: result.choices[0].message.content — used by gpt-oss models
    content = result.get("response", "")
    if not content and "choices" in result:
        choices = result.get("choices", [])
        if choices:
            msg = choices[0].get("message", {})
            content = msg.get("content") or msg.get("reasoning_content", "")

    if not content:
        raise RuntimeError(f"Cloudflare AI returned empty response for {model}: {resp_body}")

    # Strip thinking tags from reasoning models (DeepSeek-R1, QwQ)
    # They output <think>...</think> before the actual response
    if "</think>" in content:
        content = content.split("</think>", 1)[-1].strip()

    return content


# OpenClaw gateway config
_OPENCLAW_URL = os.environ.get("OPENCLAW_GATEWAY_URL", "http://127.0.0.1:18789")
_OPENCLAW_TOKEN_CACHED = None


def _get_openclaw_token() -> str:
    """Read OpenClaw gateway token from config."""
    global _OPENCLAW_TOKEN_CACHED
    if _OPENCLAW_TOKEN_CACHED:
        return _OPENCLAW_TOKEN_CACHED
    try:
        config_path = os.path.expanduser("~/.openclaw/openclaw.json")
        with open(config_path) as f:
            cfg = json.load(f)
        _OPENCLAW_TOKEN_CACHED = cfg.get("gateway", {}).get("auth", {}).get("token", "")
    except Exception:
        _OPENCLAW_TOKEN_CACHED = ""
    return _OPENCLAW_TOKEN_CACHED


def _call_openclaw_gateway(
    messages: List[Dict[str, str]],
    max_tokens: int = 4096,
    timeout: int = 300,
) -> str:
    """Call OpenClaw gateway as an agent with native tools (web_search, web_fetch)."""
    token = _get_openclaw_token()
    if not token:
        raise RuntimeError("OpenClaw gateway token not found in ~/.openclaw/openclaw.json")

    payload = json.dumps({
        "model": "openclaw",
        "messages": messages,
        "max_tokens": max_tokens,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{_OPENCLAW_URL}/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    choices = body.get("choices", [])
    if not choices:
        raise RuntimeError(f"OpenClaw gateway returned no choices: {body}")

    content = choices[0].get("message", {}).get("content", "")
    if not content:
        raise RuntimeError(f"OpenClaw gateway returned empty content: {body}")

    return content


def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences from LLM output."""
    text = text.strip()
    text = re.sub(r'^```(?:json|html)?\s*\n?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\n?```\s*$', '', text)
    return text.strip()


def _extract_json_from_text(text: str) -> str:
    """Find the first JSON object or array in text."""
    text = _strip_markdown_fences(text)
    first_brace = text.find('{')
    first_bracket = text.find('[')
    starts = [i for i in [first_brace, first_bracket] if i >= 0]
    if starts:
        return text[min(starts):]
    return text


def _repair_truncated_json(text: str) -> Optional[Dict]:
    """Try to repair JSON truncated by max_tokens."""
    if not text or text[0] not in '{[':
        return None
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


class LLMClient:
    """LLM Client — routes to Mirai Gateway API or OpenClaw Gateway. No CLI fallback."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.model = model or "claude-opus-4-6"
        # OpenClaw model always uses gateway (its own gateway, not Mirai's)
        self._use_gateway = True if self.model == "openclaw" else _check_gateway()

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None
    ) -> str:
        """Send a chat request via gateway API. No CLI fallback — fails loud if gateway is down."""
        t0 = time.perf_counter()

        try:
            result = _call_gateway(
                self.model, messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            result = _strip_markdown_fences(result)
            latency_ms = (time.perf_counter() - t0) * 1000

            _observer.record(
                model=self.model,
                latency_ms=latency_ms,
                input_tokens=sum(len(m.get('content', '')) for m in messages) // 4,
                output_tokens=len(result) // 4,
                success=True,
            )
            return result

        except Exception as exc:
            latency_ms = (time.perf_counter() - t0) * 1000
            _observer.record(
                model=self.model,
                latency_ms=latency_ms,
                input_tokens=sum(len(m.get('content', '')) for m in messages) // 4,
                output_tokens=0,
                success=False,
                error=f"{type(exc).__name__}: {exc}",
            )
            raise

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """Send a chat request and return parsed JSON."""
        # Add JSON enforcement to the last user message
        json_instruction = "\n\nYou MUST respond with valid JSON only. No markdown fences, no explanation, no text before or after the JSON."
        enriched = list(messages)
        if enriched and enriched[-1].get("role") == "user":
            enriched[-1] = {**enriched[-1], "content": enriched[-1]["content"] + json_instruction}
        else:
            enriched.append({"role": "user", "content": json_instruction})

        t0 = time.perf_counter()
        try:
            raw = self.chat(enriched, temperature=temperature, max_tokens=max_tokens)
            json_text = _extract_json_from_text(raw)

            try:
                result = json.loads(json_text)
            except json.JSONDecodeError:
                repaired = _repair_truncated_json(json_text)
                if repaired is not None:
                    result = repaired
                else:
                    raise ValueError(f"Invalid JSON from {self.model}: {json_text[:200]}")

            latency_ms = (time.perf_counter() - t0) * 1000
            _observer.record(
                model=self.model,
                latency_ms=latency_ms,
                input_tokens=sum(len(m.get('content', '')) for m in messages) // 4,
                output_tokens=0,
                success=True,
                json_parse_ok=True,
            )
            return result

        except ValueError:
            raise
        except Exception as exc:
            latency_ms = (time.perf_counter() - t0) * 1000
            _observer.record(
                model=self.model,
                latency_ms=latency_ms,
                input_tokens=sum(len(m.get('content', '')) for m in messages) // 4,
                output_tokens=0,
                success=False,
                error=f"{type(exc).__name__}: {exc}",
            )
            raise

    @staticmethod
    def _messages_to_prompt(messages: List[Dict[str, str]]) -> str:
        """Convert OpenAI-style message list to a single prompt string."""
        parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                parts.append(f"SYSTEM INSTRUCTIONS:\n{content}\n")
            elif role == "assistant":
                parts.append(f"ASSISTANT:\n{content}\n")
            else:
                parts.append(content)
        return "\n".join(parts)
