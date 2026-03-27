# Mirai (未来)
**AI-Powered Startup Prediction System with Multi-Model Council, Swarm Intelligence, and Market Simulation**

## What Mirai Does

Give Mirai a startup's details → it researches the market, scores across 7 dimensions using a 4-model council, simulates crowd reaction with 10-1000 persona agents, runs a 6-month market trajectory simulation, and generates a PitchBook-quality PDF report.

## Key Features

- **Multi-Model Research** — Claude, GPT, and Gemini research the same startup simultaneously, each bringing different knowledge. Findings merged into unified report.
- **4-Elder Council** — 4 LLMs (Opus, Sonnet, GPT-5.4, Gemini 3.1 Pro) score 7 dimensions independently. Disagreements flagged as "contested."
- **88.5B+ Persona Swarm** — 10-1000 agents generated from 11 trait dimensions (role, MBTI behavioral, risk profile, experience, cognitive bias, geographic lens, industry, fund context, backstory, decision framework, portfolio composition). Each persona evaluates from their unique perspective with "stay in your lane" domain focus.
- **Contextual Persona Curation** — Industry-aware panel selection: a CleanTech startup gets Impact Investor (climate), Environmental Compliance Officer, and a Farmer/Rancher instead of random generic roles. 10 industry mappings with priority roles per zone.
- **Investment Committee Deliberation** — After independent evaluation, the most bullish and bearish agents argue with each other in a 2-round simulated debate. A committee chair synthesizes the tension and renders a recommendation. Adjusted scores feed back into the final verdict.
- **Critical Divergence Analysis** — Z-score outlier detection identifies which agents disagree most sharply with the consensus. Zone agreement tracking shows which perspectives are aligned and which are split. The gold is in the disagreements.
- **OASIS Market Simulation** — 6-month multi-round simulation with graduated scoring, agent-to-agent visibility, and anti-herding safeguards. Agents see what the panel thought last round and adjust incrementally, creating natural consensus/divergence dynamics.
- **Autonomous Cortex** — 10-second heartbeat loop that browses the web, executes sandboxed code, triggers analyses, and sends messages without human prompting. 4 self-learning loops (experience, reflection, skill forge, market radar).
- **Pixel Art War Room** — 7-room pixel art office with animated agents, zone labels, and hover tooltips.
- **PitchBook-Quality PDF** — SVG charts, zone-grouped agent reasoning, competitive landscape, critical divergence analysis, investment committee deliberation dialogue, strategic recommendations. Appendices with full market and competitive narratives.
- **Agent Chat** — Click any agent after voting to ask follow-up questions.
- **Zero API Key Config** — Mirai Gateway handles all provider auth via OAuth. Users log in once during onboarding; the backend never touches API keys.
- **Graceful Degradation** — Optional services (Mem0, OpenBB, CrewAI, E2B, Crawl4AI) enrich output when available but never block the pipeline.
- **Source-Credibility-Weighted Research** — 31 premium domains (Gartner, SEC, Bloomberg, EPA) get 1.5-3x boost over random blogs. Industry-specific dimension weights tune scoring for each vertical.
- **Calibration-Ready** — Every report generates structured training data (per-agent JSONL logs). Feedback API tracks outcomes against predictions. 22,818 companies with known outcomes for backtesting. The system gets more accurate with volume.

## Architecture

```
Dashboard (port 5000)        Gateway (port 19789)        SearXNG (port 8888)
    │                              │                          │
    │ WebSocket: startAnalysis     │ /v1/chat/completions     │ /search?format=json
    ├─────────────────────────────►│◄─────────────────────────┤
    │                              │                          │
    │  Phase 1: Multi-Model Research (Claude + GPT + Gemini parallel)
    │  Phase 2: Council (4 Elders score 7 dimensions)
    │  Phase 3: Swarm (zone-based personas, enriched with research context)
    │  Phase 4: OASIS (6-month market simulation)
    │  Phase 5: ReACT Report Agent (6 LLM-generated sections)
    │  → analysisComplete (full data for PDF export)

Cortex (port 8100)
    │  10-second heartbeat loop (autonomous agent)
    │  Self-learning: ExperienceStore → ReflectionEngine → SkillForge
    │  Browser automation (Playwright/CDP)
    │  Gateway auto-start + watchdog
    │  E2B sandboxed code execution
```

## Quick Start

```bash
git clone https://github.com/adityagoyal009/Mirai.git && cd Mirai && bash install.sh

# Start SearXNG
docker run -d --name searxng -p 8888:8080 -v /tmp/searxng/settings.yml:/etc/searxng/settings.yml:ro searxng/searxng

# Start Gateway (port 19789)
cd gateway && node mirai.mjs gateway run --port 19789 &

# Start Dashboard + Backend (port 5000)
export LLM_BASE_URL="http://localhost:19789/v1" LLM_API_KEY="mirai-local-token"
python3 -m flask --app subconscious/swarm run --host 0.0.0.0 --port 5000

# Open http://localhost:5000/dashboard/
```

## Models (5 across 3 providers)

| Elder | Model | Provider |
|-------|-------|----------|
| 1 | Claude Opus 4.6 | Anthropic |
| 2 | Claude Sonnet 4.6 | Anthropic |
| 3 | GPT-5.4 | OpenAI |
| 4 | Gemini 3.1 Pro | Google |

Config: `~/.mirai/council.json`

## 7-Dimension Scoring

| Dimension | Weight |
|-----------|--------|
| market_timing | 20% |
| business_model_viability | 20% |
| competition_landscape | 15% |
| pattern_match | 15% |
| team_execution_signals | 10% |
| regulatory_news_environment | 10% |
| social_proof_demand | 10% |

## Data Sources

| Source | Count |
|--------|-------|
| FinePersonas (Argilla) | 1,200,000 |
| Tencent PersonaHub Elite | 238,443 |
| Tencent PersonaHub | 200,000 |
| Company Database | 231,213 |
| SearXNG Web Search | 70+ engines |

## Ports

| Port | Service |
|------|---------|
| 19789 | Mirai Gateway |
| 8100 | Cortex API Server |
| 5000 | Flask + Dashboard |
| 8888 | SearXNG |

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/bi/analyze` | Full analysis |
| POST | `/api/bi/report/pdf` | Generate PDF |
| POST | `/api/bi/feedback` | Record outcome |
| GET | `/api/bi/accuracy` | Accuracy stats |
| GET | `/api/bi/history` | Past analyses |
| WS | `/ws/swarm` | Real-time events |
