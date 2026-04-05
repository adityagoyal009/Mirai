# OpenClaw Integration — Mirai + CleanSentinels

## Overview

Both Mirai and CleanSentinels route AI calls through the OpenClaw gateway at `http://127.0.0.1:18789`. OpenClaw handles auth, model routing, sub-agent lifecycle, and provides native tools (web_search, web_fetch, file read) to spawned agents.

## Gateway Auth

- **Auth mode:** `token` (set in `~/.openclaw/openclaw.json`)
- **Token:** `0c74d3c311773a969a1ec043c24a54244de99cd2713d4aa8`
- **Config location:** `~/.openclaw/openclaw.json` → `gateway.auth`

```json
{
  "gateway": {
    "auth": {
      "mode": "token",
      "token": "0c74d3c311773a969a1ec043c24a54244de99cd2713d4aa8"
    }
  }
}
```

## HTTP API Scopes (IMPORTANT)

As of OpenClaw `2026.3.28`, the `/v1/chat/completions` endpoint requires an explicit scopes header:

```
x-openclaw-scopes: operator.read,operator.write
```

Without this header, all calls return `403: missing scope: operator.write`.

The `/tools/invoke` endpoint does NOT require this header.

## How Mirai Uses OpenClaw

### Research (agentic_researcher.py)
- Calls `POST /v1/chat/completions` with `model: "openclaw"`
- OpenClaw spawns a sub-agent with native `web_search` + `web_fetch` tools
- Sub-agent does deep research, returns findings as text
- Fallback chain: OpenClaw → Gemini → built-in BI research
- Auth: `OPENCLAW_GATEWAY_TOKEN` env var → falls back to `~/.openclaw/openclaw.json` token

### LLM Routing (llm_client.py)
- `model: "openclaw"` → routes through OpenClaw gateway (sub-agent with tools)
- Claude models → `claude` CLI (headless, subscription auth) → gateway fallback
- OpenAI models → `codex` CLI (headless) → gateway fallback
- Free tier APIs (NVIDIA, Groq, Cerebras, Mistral, Cohere, SambaNova, Cloudflare) → direct REST

## How CleanSentinels Uses OpenClaw

### Vision Analysis (lib/openclaw.ts)
- Calls `POST /tools/invoke` with `sessions_spawn`
- Spawns a sub-agent that reads an image file and runs sentinel analysis prompts
- Polls for result file at `/tmp/cleansentinels/results/{jobId}.json`
- Auth: `GATEWAY_TOKEN` env var in `.env.local`

## Environment Variables

### Mirai (`~/Downloads/mirai/.env`)
```
OPENCLAW_GATEWAY_TOKEN=your-active-openclaw-token
```

### CleanSentinels (`~/Downloads/cleansentinels/.env.local`)
```
GATEWAY_TOKEN=your-active-openclaw-token
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `403: missing scope: operator.write` | Missing `x-openclaw-scopes` header | Add header to HTTP calls |
| `401: Unauthorized` | Wrong token/password | Check `~/.openclaw/openclaw.json` auth config |
| `Research FAILED: HTTP Error 403` | Auth or scope issue | Check both token AND scopes header |
| Falls back to Gemini | OpenClaw research failed | Check gateway logs: `/tmp/openclaw/openclaw-YYYY-MM-DD.log` |
| `token_mismatch` in browser TUI | Dashboard cached old token | Refresh browser, paste new token |

## Version Notes

- **v2026.3.24:** `auth.mode: "none"` worked for HTTP endpoints (no scopes needed)
- **v2026.3.28:** HTTP endpoints now require `x-openclaw-scopes` header even when authenticated
- If OpenClaw updates again, check if scope behavior changed

## Files Modified for This Integration

- `subconscious/swarm/services/agentic_researcher.py` — added scopes header
- `subconscious/swarm/utils/llm_client.py` — added scopes header for openclaw path
- `~/.openclaw/openclaw.json` — gateway auth config
- `~/Downloads/mirai/.env` — OPENCLAW_GATEWAY_TOKEN
- `~/Downloads/cleansentinels/.env.local` — GATEWAY_TOKEN
- Gateway may auto-generate a new token on restart -- always verify ~/.openclaw/openclaw.json has the active token
