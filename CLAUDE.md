## Design System
Always read DESIGN.md before making any visual or UI decisions.
All font choices, colors, spacing, and aesthetic direction are defined there.
Do not deviate without explicit user approval.
In QA mode, flag any code that doesn't match DESIGN.md.

Key rules:
- HTML reports use Instrument Serif (display), DM Sans (body/data), Source Serif 4 italic (agent quotes)
- Primary navy: #0f2440. Accent blue: #2563eb. HIT green: #059669. MISS red: #dc2626.
- Agent quote cards use tinted backgrounds (green for HIT, red for MISS) with serif italic text
- Score bars use red-amber-green gradients, not solid fills
- Dashboard (pixel art war room) has its own separate design system — do not apply report design rules to it

## Pipeline Architecture
- Research: OpenClaw primary (port 18789), Gemini grounded search fallback
- Council: 10 models across 8 families. Karpathy 3-stage pattern (individual → peer review → chairman)
- Chairman: Opus primary, Qwen3.5 397B (NVIDIA) fallback
- Swarm: 50-100 agents across 6 free models (Groq + SambaNova + Mistral)
- All data flows WITHOUT truncation — full research context to council and swarm
- Hallucination guard runs on every swarm agent reasoning
- Report: HTML (not PDF). Opens in new tab. No Playwright/Chromium dependency.

## Model Routing (llm_client.py)
- `@cf/` models → Cloudflare Workers AI (kept but not in active council)
- Groq models → `_call_groq()` direct REST API
- Cerebras models → `_call_cerebras()` direct REST API
- SambaNova models → `_call_sambanova()` direct REST API
- Mistral models → `_call_mistral()` direct REST API
- NVIDIA NIM models → `_call_nvidia()` direct REST API
- Claude models → `_call_claude_cli()` subprocess, gateway fallback
- OpenAI/GPT/O3 models → `_call_codex_cli()` subprocess, gateway fallback
- OpenClaw models → `_call_openclaw_gateway()` port 18789

## Key Decisions
- No Gemini in council or swarm (unreliable CLI, hangs)
- No backtest with known companies (temporal mismatch)
- No research fallback/degraded mode — if both OpenClaw AND Gemini fail, pipeline stops
- Swarm agents are blind to council scores (independent evaluation)
- Frontend sends structured fields directly (bypasses LLM extraction for form data)
