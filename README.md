# Mirai (未来) + Sensei (先生)
**AI Due Diligence Reports + AI Mentor Sessions — VCLabs.org**

## Current State

These notes reflect the current live pipeline as of 2026-03-30.

- **Live research**: OpenClaw is the primary fresh-facts engine. Gemini is fallback only. The old BI degraded research path is not used in the live website flow.
- **Council**: 11-model council with peer review and chairman reconciliation. Council fact-checking now verifies council reasoning text, not the raw research JSON blob.
- **Persona swarm**: 50-agent stage-aware, target-market-aware swarm. Persona selection now uses `industry + product + target_market + stage`, and pre-seed runs no longer receive late-stage finance personas.
- **Wildcard control**: B2B / industrial startups now get fewer, more relevant wildcard seats instead of noisy generic personas.
- **Final verdict**: REST and WebSocket share the same final-verdict math. Final score is numeric council + swarm + OASIS adjustment, not a simple conservative override.
- **OASIS**: 4-round / 4-month simulation using structured company context and real live-search events. Trajectory is measured from the pre-simulation baseline, not only from month 1.
- **Reports**: HTML report is generated after OASIS and final verdict enrichment. Fact-check data now surfaces correctly from swarm / prediction / top-level payloads. The report label is `Final Confidence`.

## What Mirai Does

Give Mirai a startup's details → it researches the market with OpenClaw live web search (Gemini fallback only if needed), scores across 10 dimensions using an 11-model council with peer review and chairman reconciliation, simulates crowd reaction with a 50-agent persona swarm across 6 zones, runs a 4-round OASIS market trajectory simulation, and generates a PitchBook-quality HTML report with inline SVG charts.

## Key Features

- **OpenClaw Web Research** — OpenClaw agent with native web search does deep 10-step research (company, team, funding, competitors, market, patents, regulatory, customers, pricing, risks). Gemini grounded search as fallback when Anthropic is down. Research cached 7 days with staleness indicator.
- **10-Model Council (Karpathy Pattern)** — 10 LLMs across 8 families (Opus 4.6, GPT-5.4, Llama 3.3 70B, Llama 4 Scout, Kimi K2, Qwen3 235B, GPT-OSS 120B, Mistral Large 675B, Qwen3.5 397B, GLM-5) score 10 dimensions independently. Stage 2 peer review where models cross-evaluate each other anonymously. Chairman (Opus, Qwen3.5 fallback) reconciles with peer rankings + flagged claims. Disagreements classified as "disputed" or "heavily contested."
- **88.5B+ Persona Swarm** — 50-100 agents generated from 16 trait dimensions (role, MBTI behavioral, risk profile, experience, cognitive bias, geographic lens, industry, fund context, backstory, decision framework, portfolio composition, thesis style, technical depth, failure scars, network strength, decision speed). Each persona evaluates from their unique perspective with "stay in your lane" domain focus. Hallucination guard on every agent's reasoning. 6 free models across 5 families (Groq: Llama 3.3, Scout, Kimi K2. SambaNova: DeepSeek V3.1, Maverick. Mistral: Small).
- **Contextual Persona Curation** — Industry-aware panel selection: a CleanTech startup gets Impact Investor (climate), Environmental Compliance Officer, and a Farmer/Rancher instead of random generic roles. 10 industry mappings with priority roles per zone.
- **Investment Committee Deliberation** — After independent evaluation, the most bullish and bearish agents argue with each other in a 2-round simulated debate. A committee chair synthesizes the tension and renders a recommendation. Committee members receive DELIBERATION_WEIGHT=1.5 in weighted aggregation. Adjusted scores feed back into the final verdict.
- **Critical Divergence Analysis** — Z-score outlier detection across ALL swarm agents (Wave 1 + Wave 2) identifies which agents disagree most sharply with the consensus. Zone agreement tracking shows which perspectives are aligned and which are split. The gold is in the disagreements.
- **OASIS Market Simulation** — 6-month multi-round simulation with real news-sourced market events, swarm-sourced panelists (strongest bull/bear, per-zone reps), uncertainty bands per round, graduated scoring, agent-to-agent visibility, and anti-herding safeguards.
- **Source-Credibility-Weighted Research** — 31 premium domains (Gartner, SEC, Bloomberg, EPA) get 1.5-3x boost over random blogs. Industry-specific dimension weights tune scoring for each vertical.
- **Real Fact Verification** — Brave Search, SEC EDGAR, Yahoo Finance, Jina DeepSearch verify quantitative claims against real sources. No circular LLM-asking-LLM.
- **Hallucination Guard** — TF-IDF traceability check on every research synthesis. Claims not traceable to raw sources flagged as [LLM-INFERRED].
- **Source Citations** — Every fact tracked from source URL through pipeline to PDF (Appendix D).
- **Autonomous Cortex** — 10-second heartbeat loop that browses the web, executes sandboxed code, triggers analyses, and sends messages without human prompting. 4 self-learning loops (experience, reflection, skill forge, market radar).
- **Pixel Art War Room** — 7-room pixel art office with animated agents, 8 council elders on sofas, zone labels, and hover tooltips.
- **HTML Report with PitchBook-Density Charts** — LLM-generated HTML report opens in new tab. SVG charts: score radar, swarm donut, valuation step-up, TAM funnel, competitive positioning scatter. Full agent reasoning in editorial serif italic (Source Serif 4). Design system: Instrument Serif display, DM Sans body, navy #0f2440.
- **Agent Chat** — Click any agent after voting to ask follow-up questions.
- **Multi-Provider Free Inference** — Council and swarm use free APIs from Groq (300ms), Cerebras (200ms), SambaNova, Mistral, and NVIDIA NIM. Claude and GPT-5.4 via headless CLI (subscription). Gateway as fallback only. Zero marginal API cost for swarm.
- **Zero External Dependencies** — All evaluation, dedup, fact-checking is Mirai-owned code. No semhash, deepeval, yfinance packages.
- **Graceful Degradation** — Optional services (Mem0, OpenBB, CrewAI, E2B, Crawl4AI) enrich output when available but never block the pipeline.
- **Calibration-Ready** — Every report generates structured training data (per-agent JSONL logs). Feedback API tracks outcomes against predictions. 22,818 companies with known outcomes for backtesting. The system gets more accurate with volume.

## Architecture

```
Dashboard (port 5000)        Free LLM APIs              CLI (subscriptions)
    │                        ├── Groq (Llama, Scout,     ├── claude -p (Opus)
    │ WebSocket              │   Kimi K2, GPT-OSS)       ├── codex exec (GPT-5.4)
    ├────────────────────────├── Cerebras (Qwen3 235B)   │
    │                        ├── SambaNova (DeepSeek V3)  OpenClaw (port 18789)
    │                        ├── Mistral (Small)          └── Research agent
    │                        ├── NVIDIA NIM (675B, 397B)      with web search
    │                        └── Gemini (fallback research)
    │
    │  Phase 1: Research (OpenClaw primary → Gemini fallback)
    │  Phase 2: Council (10 models, peer review, chairman reconciliation)
    │  Phase 3: Swarm (50-100 agents across 6 free models)
    │  Phase 4: OASIS (6-month market simulation, optional)
    │  Phase 5: HTML Report (LLM-generated, PitchBook-density SVG charts)
    │  → analysisComplete (VIEW REPORT opens HTML in new tab)
```

## Quick Start

```bash
git clone https://github.com/adityagoyal009/Mirai.git && cd Mirai

# Set API keys (free tier, no credit card needed)
export GROQ_API_KEY="your-groq-key"           # console.groq.com
export CEREBRAS_API_KEY="your-cerebras-key"     # cloud.cerebras.ai
export SAMBANOVA_API_KEY="your-sambanova-key"   # cloud.sambanova.ai
export MISTRAL_API_KEY="your-mistral-key"       # console.mistral.ai
export NVIDIA_API_KEY="your-nvidia-key"         # build.nvidia.com
export GOOGLE_AI_KEY="your-google-key"          # aistudio.google.com

# Start Dashboard + Backend (port 5000)
uvicorn subconscious.swarm.app:app --host 0.0.0.0 --port 5000

# Open http://localhost:5000/dashboard/
```

## Models (10 Council + 6 Swarm + 2 Research)

### Council (10 models, 8 families)
| # | Model | Provider | Speed | Cost |
|---|-------|----------|-------|------|
| 1 | Claude Opus 4.6 | CLI (subscription) | ~20s | Subscription |
| 2 | GPT-5.4 | CLI (subscription) | ~30s | Subscription |
| 3 | Llama 3.3 70B | Groq | 248ms | Free |
| 4 | Llama 4 Scout | Groq | 143ms | Free |
| 5 | Kimi K2 | Groq | 181ms | Free |
| 6 | GPT-OSS 120B | Groq | 350ms | Free |
| 7 | Qwen3 235B | Cerebras | 204ms | Free |
| 8 | Mistral Large 675B | NVIDIA NIM | 330ms | Free |
| 9 | Qwen3.5 397B | NVIDIA NIM | 328ms | Free |
| 10 | GLM-5 | NVIDIA NIM | 1.9s | Free |

### Swarm (6 models, 5 families)
| Model | Provider | Speed |
|-------|----------|-------|
| Llama 3.3 70B | Groq | 248ms |
| Llama 4 Scout | Groq | 143ms |
| Kimi K2 | Groq | 181ms |
| DeepSeek V3.1 | SambaNova | 600ms |
| Llama 4 Maverick | SambaNova | 1.0s |
| Mistral Small | Mistral | 610ms |

### Research
| Engine | Provider | Web Search | Role |
|--------|----------|-----------|------|
| OpenClaw Agent | Anthropic (port 18789) | Native tools | Primary |
| Gemini 2.5 Flash | Google AI Studio | Grounded search | Fallback |

Config: `~/.mirai/council.json`
Env vars: `GROQ_API_KEY`, `CEREBRAS_API_KEY`, `SAMBANOVA_API_KEY`, `MISTRAL_API_KEY`, `NVIDIA_API_KEY`, `GOOGLE_AI_KEY`

## 10-Dimension Scoring

| Dimension | Weight | What it measures |
|-----------|--------|-----------------|
| market_timing | 15% | Is this the right moment? |
| business_model_viability | 15% | Do unit economics work? |
| competition_landscape | 12% | How defensible? |
| pattern_match | 10% | Historical precedents |
| team_execution_signals | 10% | Can THIS team build THIS? |
| regulatory_news_environment | 8% | Help or hindrance? |
| social_proof_demand | 8% | Is there real pull? |
| capital_efficiency | 8% | Burn rate, runway, milestones |
| scalability_potential | 7% | Can this 10x without breaking? |
| exit_potential | 7% | Path to liquidity |

## Data Sources

| Source | Volume | Use |
|--------|--------|-----|
| FinePersonas (Argilla) | 1,200,000 | Persona generation |
| Tencent PersonaHub Elite | 238,443 | Domain expert personas |
| Tencent PersonaHub | 200,000 | General personas |
| Company Database | 231,213 | Backtesting |
| Claude Web Search | Built-in (subscription) | Primary research (Opus-web) |
| GPT Web Search | Built-in (subscription) | Parallel research (GPT-5.4-web) |
| SEC EDGAR | Unlimited free | Public company filing verification |
| Yahoo Finance | Free | Revenue/market cap verification |
| Jina DeepSearch | 1M tokens free | Claim grounding with evidence |

## Ports

| Port | Service |
|------|---------|
| 4000 | claude-proxy (LLM + web search) |
| 5000 | FastAPI + Dashboard |
| 8100 | Cortex API Server (optional) |

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/bi/analyze` | Full analysis, async job submission, internal callers only |
| GET | `/api/bi/job/{id}` | Poll async analysis result, internal callers only |
| POST | `/api/bi/report/pdf` | Generate PDF |
| POST | `/api/report/share` | Persist shareable HTML report, internal callers only |
| POST | `/api/bi/feedback` | Record outcome |
| GET | `/api/bi/accuracy` | Accuracy stats |
| GET | `/api/bi/history` | Past analyses |
| WS | `/ws/swarm` | Real-time events |

## Queue And Security Notes

- Website submissions are serialized through an in-memory FIFO queue with an operating target of `50 analyses / 24h`.
- Queue restart recovery reconstructs resumable `queued` and `reviewing` submissions from the database instead of only resetting status flags.
- Website → swarm requests use `MIRAI_INTERNAL_API_KEY`, falling back to `NEXTAUTH_SECRET` for compatibility.
- Swarm-side fallback throttling is only for loopback/no-key traffic and defaults to `50` analyses per `86400` seconds.
