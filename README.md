# Mirai (未来)
**AI-Powered Startup Prediction and Autonomous Intelligence System**

Mirai is a startup prediction platform backed by autonomous AI subsystems that research, predict, learn, and act:

1. **The Brain (Mirai Gateway):** In-house Node.js LLM proxy (forked from OpenClaw, rebranded as `mirai` CLI). Multi-model onboarding — log in with multiple LLM providers. Dynamic LLM Council uses ALL logged-in models for high-stakes decisions.
2. **The Hands (Browser-use + Crawl4AI):** Computer-vision Playwright engine for interactive web navigation. Crawl4AI for fast bulk extraction. E2B sandbox for safe code execution.
3. **The Subconscious (MiroFish):** Swarm intelligence engine spawning background AI agents. Swarm Predictor with 50-1000 diverse persona agents. OASIS social simulation. ChromaDB + Mem0 hybrid memory.
4. **Business Intelligence:** Research (SearXNG + ChromaDB + Mem0 + OpenBB + Crawl4AI/browser), predict (7-dimension scoring with Dynamic LLM Council + Swarm Predictor + CrewAI multi-agent), plan (risks, moves, 90-day timeline).
5. **Self-Learning:** Experience memory → reflection → strategy journal. Capability gap detection. Market signal monitoring. All rules self-learned, persisted, and injected into future decisions.

## Architecture

```text
Mirai/
├── cortex/                 # Main autonomous loop
│   ├── mirai_cortex.py     # Heartbeat loop + gateway management
│   ├── api_server.py       # HTTP bridge (port 8100) — browse, think, memory
│   ├── gateway_launcher.py # GatewayLauncher — auto-starts Mirai Gateway on boot
│   ├── sandbox_runner.py   # E2B sandbox for safe code execution
│   ├── system_prompt.py    # LLM personality + 6 JSON action schemas
│   ├── learning/           # Self-learning: ExperienceStore, Reflection, SkillForge, MarketRadar
│   └── browser_engine/     # Ported from browser-use (15+ LLM providers, CDP caching fix)
│
├── dashboard/              # Pixel Art War Room Dashboard (React + Canvas 2D + Vite)
│   ├── src/                # React app — SwarmScoreboard, Canvas renderer, WebSocket hooks
│   │   ├── api/miraiApi.ts         # REST + WebSocket client for Flask backend
│   │   ├── hooks/useSwarmAgents.ts  # Agent lifecycle, spawning, animation state
│   │   └── components/SwarmScoreboard.tsx  # Structured input form + live results
│   └── scripts/generate-warroom.py  # Generates 45x35 tile war room (5 zones, 50 seats, 165 furniture)
│
├── subconscious/           # Background prediction + memory
│   ├── memory/             # ChromaDB (episodic) + Mem0 (relationship-aware BI)
│   ├── swarm/              # MiroFish Flask backend (port 5000)
│   │   ├── api/            # REST: graph, simulation, report, predict, BI + WebSocket /ws/swarm
│   │   ├── services/       # BI engine, SearXNG, OpenBB, CrewAI, web researcher, simulation
│   │   │   ├── swarm_predictor.py   # Swarm Predictor — 50-1000 agents, hybrid wave execution
│   │   │   └── persona_engine.py    # Persona Engine — 2.3M+ personas + trait-based generator
│   │   ├── models/         # Project, Task
│   │   └── utils/          # LLM client, file parser, logger, retry
│   └── lab/                # Autoresearch (parked — kept as reference)
│
├── data/                   # Persona and index data
│   ├── personas.jsonl      # 2.3M+ real personas from FinePersonas (HuggingFace)
│   └── label_index.json    # Label index for smart persona-industry matching
│
└── gateway/                # Mirai Gateway — in-house Node.js LLM proxy (forked from OpenClaw)
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full directory tree, data flows, and environment variables.

## Pixel Art Dashboard

Mirai ships with a pixel art "war room" dashboard (forked from pixel-agents, MIT). Accessible at **`localhost:5000/dashboard/`**.

The dashboard renders a top-down office war room on a 45x35 tile grid with five color-coded role zones: **Investors**, **Customers**, **Operators**, **Analysts**, and **Contrarians**. Each zone contains desks, PCs, sofas, plants, bookshelves, whiteboards, and other furniture (165 items total across 50 seats).

**Structured Input Form** -- The scoreboard panel includes a proper form with validated fields: Company Name, Industry (dropdown), Product/Service, Target Market, Business Model, Stage (dropdown), Funding Raised, Traction, Team, Ask, and Competitive Advantage. Required fields are validated before the swarm can start. No free-text parsing.

**Real-Time Visualization** -- When a swarm analysis starts, agents spawn as animated pixel characters walking to their assigned zone seats. A live WebSocket feed (`/ws/swarm`) streams events (`swarmStarted`, `agentSpawned`, `agentActive`, `agentVoted`, `swarmProgress`, `swarmComplete`) to the dashboard, which renders a live vote feed, consensus gauges, and a progress bar.

```bash
# Start the dashboard (served by the Flask backend)
# Dashboard is available at http://localhost:5000/dashboard/ when the swarm backend is running
cd dashboard && npm run build   # Vite production build
```

## Getting Started

### One-Line Install

```bash
git clone https://github.com/adityagoyal009/Mirai.git && cd Mirai && bash install.sh
```

This handles everything: Python deps, Node.js 22, pnpm, gateway build, npm link (`mirai` CLI), dashboard build, and multi-model onboarding. The `mirai` CLI is also symlinked at `/usr/local/bin/mirai` for system-wide access without nvm.

### Manual Setup

Prerequisites: Python 3.10+, Node.js 22+, pnpm

```bash
# 1. Install Python dependencies
pip install playwright chromadb requests flask flask-cors openai python-dotenv mem0ai crawl4ai e2b-code-interpreter crewai
playwright install --with-deps chromium

# 2. Build the gateway
cd gateway && pnpm install && pnpm build && cd ..

# 3. Build the dashboard
cd dashboard && npm install && npm run build && cd ..

# 4. Authenticate and onboard
cd gateway && node mirai.mjs onboard && cd ..

# 5. (Optional) Start SearXNG for fast web search
docker run -d -p 8888:8888 searxng/searxng

# 6. Launch the Mirai Cortex (gateway starts automatically)
python cortex/mirai_cortex.py
```

On boot, the cortex will:
1. Auto-start the Mirai gateway on port 3000 (if not already running)
2. Start the Cortex API server on port 8100
3. Start the MiroFish Flask backend on port 5000 (serves the dashboard at `/dashboard/`)
4. Enter the 10-second heartbeat loop

### Docker

```bash
docker build -t mirai .
docker run -p 8100:8100 -p 5000:5000 mirai
```

## Business Intelligence

Give Mirai a company's details via the dashboard's structured input form (or API) and it will:
1. **Research** — extract fields via LLM, search SearXNG + ChromaDB + Mem0 + OpenBB, extract content via Crawl4AI/browser, synthesize findings
2. **Predict** — score across 7 weighted dimensions, classify as Strong Hit → Strong Miss. Dynamic LLM Council (uses ALL logged-in models) + optional Swarm Predictor (50-1000 diverse agents) + CrewAI multi-agent analysis
3. **Plan** — top risks with mitigations, prioritized next moves, go-to-market, validation experiments, 90-day timeline

```bash
# Quick analysis (~30s)
curl -X POST localhost:5000/api/bi/analyze \
  -H "Content-Type: application/json" \
  -d '{"exec_summary": "Company: LegalLens AI. Industry: legaltech. Product: AI contract analysis..."}'

# Deep analysis (~5min, Dynamic LLM Council + CrewAI + full web research)
curl -X POST localhost:5000/api/bi/analyze \
  -H "Content-Type: application/json" \
  -d '{"exec_summary": "...", "research_depth": "deep"}'

# Swarm analysis (100 diverse persona agents evaluate the startup)
curl -X POST localhost:5000/api/bi/analyze \
  -H "Content-Type: application/json" \
  -d '{"exec_summary": "Company: LegalLens AI. Industry: legaltech. Product: AI contract analysis...", "swarm_count": 100}'

# Validate input before analysis
curl -X POST localhost:5000/api/bi/validate \
  -H "Content-Type: application/json" \
  -d '{"exec_summary": "We are building..."}'

# Get recommended template
curl localhost:5000/api/bi/template

# Past analyses
curl localhost:5000/api/bi/history
```

### Swarm Predictor

The `swarm_count` parameter (0, 50, 100, 250, 500, 1000) spawns diverse persona agents to evaluate a startup from multiple perspectives. Each agent has a unique persona drawn from 2.3M+ real personas (FinePersonas dataset) or generated via trait combinations.

Execution uses a hybrid wave strategy:
- **Wave 1** — up to 100 individual LLM calls, each with a unique persona prompt
- **Wave 2** — remaining agents batched (25 per call) for efficiency
- Models are distributed round-robin across all logged-in providers

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

The cortex exposes its capabilities via HTTP for integration with the gateway and other tools.

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

## Gateway Management

The cortex manages the Mirai gateway lifecycle automatically:

| Feature | What it does | When |
|---------|-------------|------|
| **Auto-start** | Starts `gateway/mirai.mjs` as subprocess | On boot (if not running) |
| **Gateway watchdog** | Health check → auto-restart if down | Every 10 cycles |
| **Direct messaging** | `mirai message send --to [number] --message [text]` | On `message_human` action |

## Self-Learning

The cortex learns from every action it takes:

1. **Experience** (every cycle) — stores action→outcome pairs in ChromaDB, recalls similar experiences before acting
2. **Reflection** (every 50 cycles) — analyzes patterns across last 50 experiences, updates a persistent strategy journal that's injected into every future LLM call
3. **Evolution** (periodic) — SkillForge detects capability gaps from failure patterns, MarketRadar monitors configured market signals

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_API_KEY` | `mirai` | API key for LLM calls |
| `LLM_BASE_URL` | `http://localhost:3000/v1` | OpenAI-compatible endpoint |
| `LLM_MODEL_NAME` | `anthropic/claude-opus-4-6` | Model identifier |
| `MIRAI_SWARM_URL` | `http://localhost:5000` | MiroFish backend |
| `MIRAI_API_PORT` | `8100` | Cortex API port |
| `SEARXNG_URL` | `http://localhost:8888` | SearXNG instance |
| `E2B_API_KEY` | (empty) | E2B sandbox key |
| `MEM0_API_KEY` | (empty) | Mem0 cloud key (optional) |
| `OPENBB_ENABLED` | `true` | Enable OpenBB data |
| `MIRAI_GATEWAY_PORT` | `3000` | Gateway port |
| `MIRAI_WHATSAPP_NUMBER` | (empty) | Default WhatsApp recipient |

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full environment variable reference.

## Development Goals
- [x] Claude Opus 4.6 connection via built-in gateway
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
- [x] Gateway integration — in-house Node.js gateway, auto-start, watchdog, direct messaging
- [x] Swarm Predictor — 50-1000 diverse persona agents with hybrid wave execution
- [x] Persona Engine — 2.3M+ real personas (FinePersonas) + trait-based generator fallback
- [x] Multi-model onboarding — login with multiple LLM providers during onboard
- [x] Dynamic LLM Council — uses all logged-in models (config: `models.council.models`)
- [x] Pixel Art Dashboard — war room visualization with 5 role zones, animated pixel agents
- [x] Structured Input Form — validated fields (company, industry, stage, etc.), no free-text parsing
- [x] Real-Time WebSocket — `/ws/swarm` streams agent spawn, vote, progress, and completion events
- [x] War Room Layout — 45x35 tile grid, 50 seats, 165 furniture items, generated by Python script
- [x] Gateway OAuth auto-discovery — LLM config from `~/.openclaw/openclaw.json`, no separate API key
- [x] Performance throttling — 3 concurrent workers (wave 1), 2 (wave 2) to prevent CPU hang
- [x] JSON parse fix — `llm_client.py` strips text preamble before JSON for Claude reasoning output
- [x] `mirai` CLI symlink — `/usr/local/bin/mirai` for system-wide access without nvm

See [TODO.md](TODO.md) for the full implementation roadmap and [CHANGELOG.md](CHANGELOG.md) for version history.
