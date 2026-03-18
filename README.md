# Mirai (未来)
**An Autonomous, Perpetual, Predictive AI System**

Mirai is a convergence of autonomous AI subsystems that research, predict, learn, and act:

1. **The Brain (OpenClaw):** Zero-cost Claude Opus 4.6 / GPT-5.4 via OAuth. Auto-updates, self-heals with `doctor`, monitors gateway health. LLM Council mode for high-stakes decisions.
2. **The Hands (Browser-use + Crawl4AI):** Computer-vision Playwright engine for interactive web navigation. Crawl4AI for fast bulk extraction. E2B sandbox for safe code execution.
3. **The Subconscious (MiroFish):** Swarm intelligence engine spawning background AI agents. OASIS social simulation. ChromaDB + Mem0 hybrid memory.
4. **Business Intelligence:** Research (SearXNG + ChromaDB + Mem0 + OpenBB + Crawl4AI/browser), predict (7-dimension scoring with optional LLM Council + CrewAI multi-agent), plan (risks, moves, 90-day timeline).
5. **Self-Learning:** Experience memory → reflection → strategy journal. Capability gap detection. Market signal monitoring. All rules self-learned, persisted, and injected into future decisions.

## Architecture

```text
Mirai/
├── cortex/                 # Main autonomous loop
│   ├── mirai_cortex.py     # Heartbeat loop + OpenClaw hardening (786 lines)
│   ├── api_server.py       # HTTP bridge (port 8100) — browse, think, memory
│   ├── sandbox_runner.py   # E2B sandbox for safe code execution
│   ├── system_prompt.py    # LLM personality + 6 JSON action schemas
│   ├── learning/           # Self-learning: ExperienceStore, Reflection, SkillForge, MarketRadar
│   └── browser_engine/     # Ported from browser-use (15+ LLM providers, CDP caching fix)
│
├── subconscious/           # Background prediction + memory
│   ├── memory/             # ChromaDB (episodic) + Mem0 (relationship-aware BI)
│   ├── swarm/              # MiroFish Flask backend (port 5000)
│   │   ├── api/            # REST: graph, simulation, report, predict, BI
│   │   ├── services/       # BI engine, SearXNG, OpenBB, CrewAI, web researcher, simulation
│   │   ├── models/         # Project, Task
│   │   └── utils/          # LLM client, file parser, logger, retry
│   └── lab/                # Autoresearch (parked — kept as reference)
│
└── gateway/                # OpenClaw Node.js proxy (started externally)
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full directory tree, data flows, and environment variables.

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js 20+ (for OpenClaw)
- OpenClaw CLI installed (`npm install -g @openclaw/cli`)

### Quick Start

```bash
# 1. Authenticate with OpenClaw and start the gateway
openclaw onboard
openclaw gateway

# 2. (Optional) Start SearXNG for fast web search
docker run -d -p 8888:8888 searxng/searxng

# 3. Start the MiroFish backend
export FLASK_APP=subconscious/swarm/__init__.py:create_app
flask run --port 5000

# 4. Launch the Mirai Cortex
python cortex/mirai_cortex.py
```

On boot, the cortex will:
1. Run `openclaw update --channel stable` (auto-update)
2. Run `openclaw doctor` (pre-flight health check, auto-repair if needed)
3. Start the Cortex API server on port 8100
4. Enter the 10-second heartbeat loop

### Docker

```bash
docker build -t mirai .
docker run -p 8100:8100 -p 5000:5000 mirai
```

## Business Intelligence

Give Mirai a company executive summary and it will:
1. **Research** — extract fields via LLM, search SearXNG + ChromaDB + Mem0 + OpenBB, extract content via Crawl4AI/browser, synthesize findings
2. **Predict** — score across 7 weighted dimensions, classify as Strong Hit → Strong Miss. Deep mode: LLM Council (Opus 4.6 + GPT-5.4) + CrewAI multi-agent analysis
3. **Plan** — top risks with mitigations, prioritized next moves, go-to-market, validation experiments, 90-day timeline

```bash
# Quick analysis (~30s)
curl -X POST localhost:5000/api/bi/analyze \
  -H "Content-Type: application/json" \
  -d '{"exec_summary": "Company: LegalLens AI. Industry: legaltech. Product: AI contract analysis..."}'

# Deep analysis (~5min, LLM Council + CrewAI + full web research)
curl -X POST localhost:5000/api/bi/analyze \
  -H "Content-Type: application/json" \
  -d '{"exec_summary": "...", "research_depth": "deep"}'

# Validate input before analysis
curl -X POST localhost:5000/api/bi/validate \
  -H "Content-Type: application/json" \
  -d '{"exec_summary": "We are building..."}'

# Get recommended template
curl localhost:5000/api/bi/template

# Past analyses
curl localhost:5000/api/bi/history
```

### BI Data Sources

All auto-detected with graceful fallback. No source is required except ChromaDB (built-in).

| Source | What it provides | Deploy |
|--------|-----------------|--------|
| **SearXNG** | Structured web search (70+ engines) | `docker run -p 8888:8888 searxng/searxng` |
| **ChromaDB** | Episodic memory, past analyses | Built-in (auto-created) |
| **Mem0** | Relationship-aware recall across analyses | `pip install mem0ai` |
| **OpenBB** | Live stock prices, fundamentals, market news | `pip install openbb` |
| **Crawl4AI** | Fast LLM-optimized content extraction | `pip install crawl4ai` |
| **CrewAI** | Multi-agent parallel analysis (deep mode) | `pip install crewai` |
| **E2B** | Sandboxed code execution | `pip install e2b-code-interpreter` + API key |

### 7-Dimension Scoring

| Dimension | Weight | What it measures |
|-----------|--------|-----------------|
| market_timing | 20% | Is the market ready? Growing or saturated? |
| business_model_viability | 20% | Does the revenue model make sense? |
| competition_landscape | 15% | How crowded? Any moats? |
| pattern_match | 15% | Do similar companies succeed or fail? |
| team_execution_signals | 10% | Evidence of execution capability? |
| regulatory_news_environment | 10% | Tailwinds or headwinds? |
| social_proof_demand | 10% | Evidence of market demand? |

## Cortex API (port 8100)

The cortex exposes its capabilities via HTTP for integration with OpenClaw and other tools.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/status` | Cortex state: cycle, objective, model, learning stats |
| GET | `/api/journal` | Self-learned strategy journal |
| POST | `/api/think` | Send prompt to LLM (`{"prompt": "..."}`) |
| POST | `/api/objective` | Set cortex objective (`{"objective": "..."}`) |
| POST | `/api/browse` | Browse URL via browser-use Agent (`{"url": "...", "task": "..."}`) |
| POST | `/api/browse/batch` | Batch browse (`{"urls": [...], "task": "..."}`) |
| POST | `/api/memory/search` | Search experience memory (`{"query": "...", "limit": 5}`) |
| POST | `/api/memory/store` | Store experience (`{"situation": "...", "action": "...", "outcome": "..."}`) |

## OpenClaw Hardening

The cortex manages the OpenClaw gateway lifecycle automatically:

| Feature | What it does | When |
|---------|-------------|------|
| **Auto-update** | `openclaw update --channel stable` | On boot |
| **Pre-flight** | `openclaw doctor` → `--repair` if needed | On boot |
| **Gateway watchdog** | Health check → restart if down → OAuth repair | Every 10 cycles |
| **Direct messaging** | `openclaw message send --to [number] --message [text]` | On `message_human` action |

## Self-Learning

The cortex learns from every action it takes:

1. **Experience** (every cycle) — stores action→outcome pairs in ChromaDB, recalls similar experiences before acting
2. **Reflection** (every 50 cycles) — analyzes patterns across last 50 experiences, updates a persistent strategy journal that's injected into every future LLM call
3. **Evolution** (periodic) — SkillForge detects capability gaps from failure patterns, MarketRadar monitors configured market signals

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_API_KEY` | `openclaw` | API key for LLM calls |
| `LLM_BASE_URL` | `http://localhost:3000/v1` | OpenAI-compatible endpoint |
| `LLM_MODEL_NAME` | `anthropic/claude-opus-4-6` | Model identifier |
| `MIRAI_SWARM_URL` | `http://localhost:5000` | MiroFish backend |
| `MIRAI_API_PORT` | `8100` | Cortex API port |
| `SEARXNG_URL` | `http://localhost:8888` | SearXNG instance |
| `E2B_API_KEY` | (empty) | E2B sandbox key |
| `MEM0_API_KEY` | (empty) | Mem0 cloud key (optional) |
| `OPENBB_ENABLED` | `true` | Enable OpenBB data |
| `OPENCLAW_GATEWAY_PORT` | `3000` | Gateway port |
| `OPENCLAW_WHATSAPP_NUMBER` | (empty) | Default WhatsApp recipient |

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full environment variable reference.

## Development Goals
- [x] Claude Opus 4.6 connection via OpenClaw CLI proxy
- [x] browser-use engine with fixed WebSocket persistence
- [x] ChromaDB local episodic memory system (replacing Zep Cloud)
- [x] MiroFish simulation engine with OASIS social sim
- [x] Business Intelligence engine — research, predict, plan
- [x] LLM Council — multi-model scoring with disagreement detection
- [x] Self-learning — experience, reflection, strategy journal
- [x] Cortex API server — HTTP bridge for integrations
- [x] SearXNG — fast structured web search
- [x] Mem0 — relationship-aware memory for BI flywheel
- [x] OpenBB — live financial data grounding
- [x] Crawl4AI — fast content extraction alongside browser-use
- [x] E2B sandbox — safe LLM-generated code execution
- [x] CrewAI — multi-agent parallel BI analysis
- [x] OpenClaw hardening — auto-update, doctor, watchdog, direct messaging

See [TODO.md](TODO.md) for the full implementation roadmap and [CHANGELOG.md](CHANGELOG.md) for version history.
