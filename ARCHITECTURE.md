# Mirai (未来) — System Architecture

## Overview

Mirai is an AI-powered startup prediction platform with four autonomous subsystems:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         mirai_cortex.py                                  │
│                    (10-second heartbeat loop)                            │
│                                                                          │
│  ┌──────────────┐  ┌────────────────┐  ┌───────────────────────────────┐ │
│  │    Brain      │  │     Hands      │  │         Subconscious          │ │
│  │(Mirai Gateway)│  │  (browser-use) │  │         (MiroFish)            │ │
│  │→ Dynamic LLM  │  │→ Playwright    │  │→ Swarm Predictor (50-1000)    │ │
│  │   Council     │  │→ CDP/WebSocket │  │→ ChromaDB + Mem0 memory       │ │
│  │→ All logged-in│  │→ Vision DOM    │  │→ Business Intel (BI)          │ │
│  │   models      │  │→ Crawl4AI      │  │→ SearXNG + OpenBB + CrewAI    │ │
│  └──────┬───────┘  └───────┬────────┘  └──────────────┬────────────────┘ │
│         │                  │                           │                  │
│  ┌──────┴───────┐  ┌──────┴────────┐  ┌──────────────┴────────────────┐ │
│  │  Gateway     │  │  E2B Sandbox  │  │     Self-Learning System       │ │
│  │  Launcher    │  │  (code exec)  │  │  ExperienceStore → Reflection  │ │
│  │  auto-start/ │  │  safe→subproc │  │  → SkillForge → MarketRadar    │ │
│  │  watchdog    │  │  code→sandbox │  │  (every N cycles)              │ │
│  │              │  │               │  │                                │ │
│  └──────────────┘  └───────────────┘  └────────────────────────────────┘ │
│                                                                          │
│                    ┌────────────────────┐                                │
│                    │  Cortex API Server │                                │
│                    │  (port 8100)       │                                │
│                    │  HTTP bridge for   │                                │
│                    │  gateway + swarm   │                                │
│                    └────────────────────┘                                │
└──────────┬───────────────────┬──────────────────────────┬────────────────┘
           │                   │                          │
    Mirai Gateway         Chromium CDP             Flask API (port 5000)
    (local, port 3000)         │                    ┌────┴────────────────┐
           │             Browser Engine            │  /ws/swarm WebSocket │
      Multi-model OAuth                            │  /dashboard/ static  │
                                                   └────┬────────────────┘
                                                        │
                                              ┌─────────┴──────────┐
                                              │  Pixel Art Dashboard│
                                              │  (React + Canvas)  │
                                              │  War Room: 5 zones │
                                              │  Animated agents   │
                                              │  Live vote feed    │
                                              └────────────────────┘
```

## Directory Structure

```
Mirai/
├── cortex/                        # THE BRAIN + HANDS
│   ├── mirai_cortex.py            # Main heartbeat loop (async)
│   │                              #   MiraiBrain — LLM interface via local Mirai Gateway
│   │                              #   GatewayLauncher — auto-start/watchdog/messaging
│   │                              #   MiraiCortex — heartbeat loop + action dispatch
│   ├── gateway_launcher.py        # GatewayLauncher — auto-starts Mirai Gateway on boot
│   ├── system_prompt.py           # LLM personality + 6 JSON action schemas
│   ├── api_server.py              # HTTP bridge (port 8100) — browse, think, memory, objective
│   ├── sandbox_runner.py          # E2B sandbox — safe→subprocess, code→Firecracker microVM
│   │
│   ├── learning/                  # Self-learning system (3 loops)
│   │   ├── __init__.py            # Exports: ExperienceStore, ReflectionEngine, SkillForge, MarketRadar
│   │   ├── experience_store.py    # Loop 1: Store action→outcome pairs, recall before acting
│   │   ├── reflection.py          # Loop 2: Analyze patterns every N cycles, update strategy journal
│   │   ├── skill_forge.py         # Loop 3: Detect capability gaps from failure patterns
│   │   └── market_radar.py        # Loop 3: Monitor market signals on schedule
│   │
│   └── browser_engine/            # Full browser-use port (with CDP session cache fix)
│       ├── __init__.py            # Main exports: Agent, BrowserSession, BrowserProfile
│       ├── config.py              # Comprehensive configuration management
│       ├── agent/                 # Agent orchestrator
│       │   ├── service.py         # Main agent service
│       │   ├── prompts.py         # LLM prompts for browsing
│       │   ├── views.py           # Agent state views
│       │   ├── judge.py           # Action judging
│       │   ├── message_manager/   # Message lifecycle management
│       │   └── system_prompts/    # 8 system prompt variants (.md files)
│       ├── browser/               # Playwright wrapper
│       │   ├── session.py         # Browser session manager
│       │   ├── profile.py         # Browser profiles
│       │   ├── cloud/             # Cloud integration
│       │   └── watchdogs/         # Safety mechanisms (16 watchdog modules)
│       ├── dom/                   # DOM serialization + CDP caching
│       │   ├── service.py         # DOM service with stale-session recovery
│       │   └── serializer/        # DOM/HTML serialization
│       ├── llm/                   # Multi-provider LLM abstraction
│       │   ├── models.py          # Model definitions
│       │   ├── messages.py        # Message types
│       │   ├── anthropic/         # Claude support
│       │   ├── openai/            # GPT support
│       │   ├── google/            # Gemini support
│       │   └── ...                # 12+ more providers (groq, mistral, azure, deepseek, etc.)
│       ├── tools/                 # Tool registry + structured extraction
│       ├── mcp/                   # Model Context Protocol server/client
│       ├── screenshots/           # Vision-based screenshot service
│       ├── sandbox/               # Code execution sandbox (browser-use internal)
│       ├── code_use/              # Code generation utilities
│       ├── integrations/          # Third-party integrations (Gmail)
│       ├── filesystem/            # Filesystem operations
│       └── controller/            # Controller logic
│
├── subconscious/                  # THE SUBCONSCIOUS
│   ├── memory/                    # Memory systems
│   │   ├── __init__.py            # Exports: EpisodicMemoryStore, Mem0MemoryStore
│   │   ├── episodic_store.py      # ChromaDB-backed episodic memory (333 lines)
│   │   │                          #   MemoryNode, MemoryEdge dataclasses
│   │   │                          #   Collections: {graph_id}_episodes/_nodes/_edges
│   │   │                          #   Semantic search via built-in embeddings
│   │   └── mem0_store.py          # Mem0 hybrid memory (275 lines)
│   │                              #   Vector + graph + KV unified memory
│   │                              #   Relationship-aware recall for BI
│   │                              #   Local mode (ChromaDB) or cloud (Mem0 platform)
│   │
│   ├── swarm/                     # MiroFish social simulation engine (Flask, port 5000)
│   │   ├── __init__.py            # Flask app factory (create_app)
│   │   ├── config.py              # Config: LLM, ChromaDB, SearXNG, Mem0, OpenBB, E2B, Neo4j, Gateway
│   │   │                          #   Council model discovery via models.council.models
│   │   │                          #   OAuth auto-discovery from ~/.openclaw/openclaw.json
│   │   │
│   │   ├── api/                   # REST + WebSocket endpoints (Flask Blueprints)
│   │   │   ├── __init__.py        # Blueprint registration (graph, simulation, report, predict, bi)
│   │   │   ├── websocket.py       # WS /ws/swarm — real-time swarm event streaming
│   │   │   │                      #   Events: swarmStarted, agentSpawned, agentActive,
│   │   │   │                      #   agentVoted, swarmProgress, swarmComplete
│   │   │   ├── graph.py           # POST /api/graph/* — ontology + graph construction
│   │   │   ├── simulation.py      # POST /api/simulation/* — simulation CRUD + execution
│   │   │   ├── report.py          # POST /api/report/* — report generation
│   │   │   ├── predict.py         # POST /api/predict/ — quick-predict for cortex
│   │   │   └── business_intel.py  # /api/bi/* — BI analysis API
│   │   │                          #   POST /api/bi/analyze — full pipeline
│   │   │                          #   POST /api/bi/research — research only
│   │   │                          #   POST /api/bi/predict — predict only
│   │   │                          #   POST /api/bi/validate — validate exec summary
│   │   │                          #   GET /api/bi/template — recommended input template
│   │   │                          #   GET /api/bi/history — past analyses
│   │   │
│   │   ├── models/                # SQLAlchemy-style data models
│   │   │   ├── project.py         # Project model
│   │   │   └── task.py            # Task model
│   │   │
│   │   ├── services/              # Business logic
│   │   │   ├── business_intel.py           # BI engine — research → predict → plan
│   │   │   ├── swarm_predictor.py          # Swarm Predictor — 50-1000 agents, hybrid wave execution
│   │   │   │                               #   Wave 1: up to 100 individual calls (3 concurrent workers)
│   │   │   │                               #   Wave 2: batched 25 per call (2 concurrent workers)
│   │   │   │                               #   Round-robin across models, throttled for rate limits
│   │   │   ├── persona_engine.py           # Persona Engine — 2.3M+ real personas + trait generator
│   │   │   │                               #   FinePersonas dataset (HuggingFace, stored locally)
│   │   │   │                               #   Smart label-based matching to startup industry
│   │   │   │                               #   Fallback: 60 roles x 16 MBTI x 5 risk x 5 exp x ...
│   │   │   ├── web_researcher.py           # Multi-path web research (358 lines)
│   │   │   │                               #   SearXNG → Crawl4AI → browser-use
│   │   │   ├── search_engine.py            # SearXNG metasearch client (192 lines)
│   │   │   ├── market_data.py              # OpenBB financial data service (270 lines)
│   │   │   ├── crew_orchestrator.py        # CrewAI multi-agent analysis (239 lines)
│   │   │   ├── graph_builder.py            # ChromaDB graph construction
│   │   │   ├── simulation_manager.py       # Simulation lifecycle management
│   │   │   ├── simulation_runner.py        # Background simulation process execution
│   │   │   ├── simulation_ipc.py           # File-based IPC for simulation processes
│   │   │   ├── ontology_generator.py       # LLM-based ontology extraction from documents
│   │   │   ├── oasis_profile_generator.py  # AI agent persona generation for OASIS sims
│   │   │   ├── simulation_config_generator.py # Smart simulation config generation
│   │   │   ├── report_agent.py             # LLM-powered analysis report generation
│   │   │   ├── text_processor.py           # Text chunking utilities
│   │   │   ├── zep_entity_reader.py        # Legacy Zep wrapper → delegates to ChromaDB
│   │   │   ├── zep_graph_memory_updater.py # Legacy Zep wrapper → delegates to ChromaDB
│   │   │   └── zep_tools.py               # Legacy Zep wrapper → delegates to ChromaDB
│   │   │
│   │   └── utils/                 # Shared utilities
│   │       ├── __init__.py
│   │       ├── llm_client.py      # OpenAI-compatible API wrapper (LLMClient)
│   │       │                      #   Unified chat/chat_json for Claude + OpenAI via Mirai Gateway
│   │       │                      #   Strips text preamble before JSON (handles Claude reasoning output)
│   │       ├── file_parser.py     # PDF/MD/TXT file extraction
│   │       ├── logger.py          # Rotating file + console logging
│   │       ├── retry.py           # Exponential backoff decorators
│   │       └── zep_paging.py      # Legacy Zep paging → delegates to ChromaDB
│   │
│   └── lab/                       # Autoresearch (PARKED — not wired into active system)
│       ├── prepare.py             # Data download + tokenizer training
│       ├── train.py               # GPT model (Flash Attention 3, RoPE, Muon optimizer)
│       ├── program.md             # Agent instructions for autonomous experiments
│       ├── analysis.ipynb         # Experiment tracking + visualization
│       ├── README.md              # Lab documentation
│       ├── pyproject.toml         # Lab-specific dependencies
│       └── progress.png           # Training progress visualization
│
├── dashboard/                     # Pixel Art War Room Dashboard (forked from pixel-agents, MIT)
│   ├── src/                       # React + Canvas 2D + Vite application
│   │   ├── api/
│   │   │   └── miraiApi.ts        # REST + WebSocket client for Flask backend
│   │   ├── hooks/
│   │   │   └── useSwarmAgents.ts   # Agent lifecycle, spawning, animation state management
│   │   ├── components/
│   │   │   └── SwarmScoreboard.tsx  # Structured input form + live vote feed + consensus gauges
│   │   └── ...                    # Canvas renderer, tile engine, sprite sheets
│   ├── scripts/
│   │   └── generate-warroom.py    # Generates 45x35 tile war room layout
│   │                              #   5 color-coded zones: Investors, Customers, Operators,
│   │                              #   Analysts, Contrarians
│   │                              #   50 seats, 165 furniture items (desks, PCs, sofas, plants,
│   │                              #   bookshelves, whiteboards, paintings, coffee tables)
│   ├── package.json               # Vite + React dependencies
│   └── vite.config.ts             # Build config (base: /dashboard/)
│
├── data/                          # Persona and index data
│   ├── personas.jsonl             # 2.3M+ real personas from FinePersonas (HuggingFace)
│   └── label_index.json           # Label index for smart persona-industry matching
│
├── gateway/                       # Mirai Gateway — in-house Node.js LLM proxy (forked from OpenClaw)
├── Dockerfile                     # Container: Python 3.10 + Node 20 + Playwright + all deps
├── mirai_sandbox.sb               # macOS Seatbelt sandbox profile (deny-default)
├── ARCHITECTURE.md                # This file
├── CHANGELOG.md                   # Version history
├── TODO.md                        # Implementation roadmap
└── README.md                      # Project overview + getting started
```

## Action Flow

The cortex heartbeat loop processes these JSON actions from the LLM:

| Action | Handler | Description |
|--------|---------|-------------|
| `browser_navigate` | browser-use Agent | Navigate + interact with web pages autonomously |
| `terminal_command` | E2B sandbox / subprocess | Execute shell commands (code → sandbox, safe → subprocess) |
| `swarm_predict` | HTTP → Flask `/api/predict/` | Wargame scenarios via MiroFish simulation |
| `analyze_business` | HTTP → Flask `/api/bi/analyze` | BI engine: research → predict → plan |
| `message_human` | `mirai message send` | Send WhatsApp messages to operator (direct, no agent overhead) |
| `standby` | (no-op) | Idle state |

## Cortex Heartbeat Cycle

```
Boot:
  1. GatewayLauncher auto-starts Mirai Gateway on port 3000 (if not already running)
  2. Start Cortex API server (port 8100, background thread)

Cycle N:
  1. Gateway watchdog (every 10 cycles: health check → auto-restart if down)
  2. Recall past experiences (semantic search via ExperienceStore)
  3. Load strategy journal (self-learned rules from ReflectionEngine)
  4. Build system prompt with objective + journal + experiences + last result
  5. Query LLM (async via local Mirai Gateway API)
  6. Parse JSON action from LLM response
  7. Execute action (browser/terminal/swarm/BI/messaging/standby)
  8. Store experience (action→outcome pair, heuristic success check)
  9. Periodic: Reflection (every 50 cycles — analyze patterns, update journal)
  10. Periodic: Skill gap detection (on reflection — analyze failure patterns)
  11. Periodic: Market radar (configurable — check market signals)
  12. Sleep 10 seconds → Cycle N+1
```

## Cortex API Server (port 8100)

HTTP bridge so the Mirai Gateway and MiroFish backend can call into the Python cortex.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/status` | Cortex state (cycle, objective, model, learning stats) |
| GET | `/api/journal` | Strategy journal from learning system |
| POST | `/api/think` | Send prompt to LLM via cortex's MiraiBrain |
| POST | `/api/objective` | Set new objective for cortex heartbeat |
| POST | `/api/browse` | Browse single URL via browser-use Agent |
| POST | `/api/browse/batch` | Browse multiple URLs sequentially |
| POST | `/api/memory/search` | Search experience memory (semantic) |
| POST | `/api/memory/store` | Store an experience manually |

## Key Integration Points

| # | Connection | Protocol | Description |
|---|-----------|----------|-------------|
| 1 | Cortex ↔ Brain | HTTP API | Local Mirai Gateway (localhost:3000/v1), OpenAI-compatible |
| 2 | Cortex ↔ Hands | async/CDP | browser-use Agent with persistent BrowserSession |
| 3 | Cortex ↔ Subconscious | HTTP | Calls to MiroFish Flask backend (port 5000) |
| 4 | Cortex ↔ API Server | HTTP | Background thread on port 8100 |
| 5 | Swarm ↔ ChromaDB | Python SDK | Episodic memory for simulation + BI storage |
| 6 | Swarm ↔ Mem0 | Python SDK | Relationship-aware BI memory (alongside ChromaDB) |
| 7 | Swarm ↔ LLM | OpenAI API | Via local Mirai Gateway (localhost:3000/v1) |
| 8 | Swarm ↔ SearXNG | HTTP JSON | `GET localhost:8888/search?q=...&format=json` |
| 9 | Swarm ↔ OpenBB | Python SDK | Live financial data (stock, fundamentals, news) |
| 10 | Swarm ↔ Crawl4AI | Python SDK | Fast LLM-optimized content extraction |
| 11 | Swarm ↔ CrewAI | Python SDK | Multi-agent parallel analysis (deep mode) |
| 12 | Cortex ↔ E2B | Python SDK | Sandboxed code execution (Firecracker microVMs) |
| 13 | Swarm ↔ Swarm Predictor | Python | 50-1000 persona agents, round-robin across models |
| 14 | Dashboard ↔ Flask | WebSocket | `/ws/swarm` — real-time agent spawn/vote/progress events |
| 15 | Dashboard ↔ Flask | HTTP | REST API calls + static asset serving at `/dashboard/` |
| 16 | Flask ↔ Gateway Config | File I/O | OAuth auto-discovery from `~/.openclaw/openclaw.json` |

## Self-Learning System

Three learning loops, all lazy-initialized on first cycle:

### Loop 1: Experience (every cycle)
- **ExperienceStore** (`learning/experience_store.py`) — ChromaDB-backed
- Before acting: `recall_similar(objective)` — find past experiences matching current goal
- After acting: `store_experience(situation, action, outcome, success)` — save what happened
- Heuristic success detection: checks for "error", "failed", "blocked", "timed out" in outcome

### Loop 2: Reflection (every 50 cycles)
- **ReflectionEngine** (`learning/reflection.py`)
- Analyzes last 50 experiences for patterns (what works, what fails)
- Updates a **strategy journal** — persistent self-learned rules injected into system prompt
- Journal survives restarts (persisted to file)

### Loop 3: Evolution (periodic)
- **SkillForge** (`learning/skill_forge.py`) — analyzes failure patterns to detect capability gaps
- **MarketRadar** (`learning/market_radar.py`) — monitors configured market signals on schedule

## Gateway Management

The `GatewayLauncher` class (in `cortex/gateway_launcher.py`, used by `mirai_cortex.py`) manages the in-house Mirai Gateway:

| Feature | Behavior | When |
|---------|----------|------|
| Auto-start | Starts `gateway/mirai.mjs` as subprocess on configured port | On boot (if not already running) |
| Gateway watchdog | `GET localhost:3000/health` → auto-restart if down | Every 10 cycles |
| Direct messaging | `mirai message send --to [number] --message [text]` | On `message_human` action |

## Dashboard Data Flow

```
User opens localhost:5000/dashboard/
    │
    ├→ React app loads (Vite build served as static assets by Flask)
    ├→ SwarmScoreboard renders structured input form
    │   Fields: Company Name, Industry (dropdown), Product/Service,
    │   Target Market, Business Model, Stage (dropdown), Funding Raised,
    │   Traction, Team, Ask, Competitive Advantage
    │   Required fields validated before START
    │
    ├→ User fills form → clicks START
    │   ├→ miraiApi.ts sends POST /api/bi/analyze (structured fields)
    │   └→ miraiApi.ts opens WebSocket to /ws/swarm
    │
    ├→ Flask backend processes analysis
    │   ├→ Emits swarmStarted (total agent count, zones)
    │   ├→ Per agent: agentSpawned (persona, zone assignment)
    │   ├→ Per agent: agentActive (agent begins evaluation)
    │   ├→ Per agent: agentVoted (score, verdict, reasoning)
    │   ├→ Periodic: swarmProgress (% complete, running consensus)
    │   └→ Final: swarmComplete (aggregated verdict, scores, plan)
    │
    ├→ useSwarmAgents.ts receives WebSocket events
    │   ├→ Spawns pixel character at zone entrance
    │   ├→ Animates walk to assigned seat
    │   ├→ Shows thinking animation while agentActive
    │   └→ Displays vote result on agentVoted
    │
    └→ Dashboard renders in real time
        ├→ Canvas 2D: war room with animated agents in 5 zones
        ├→ Live vote feed (scrolling list of agent verdicts)
        ├→ Consensus gauges (per-zone and overall)
        └→ Progress bar (% of agents complete)
```

### WebSocket API (`/ws/swarm`)

| Event | Direction | Payload | Description |
|-------|-----------|---------|-------------|
| `swarmStarted` | Server → Client | `{totalAgents, zones}` | Analysis begun, agent count confirmed |
| `agentSpawned` | Server → Client | `{agentId, persona, zone, seatIndex}` | Agent created, assigned to zone seat |
| `agentActive` | Server → Client | `{agentId}` | Agent is evaluating (thinking animation) |
| `agentVoted` | Server → Client | `{agentId, score, verdict, reasoning}` | Agent completed evaluation |
| `swarmProgress` | Server → Client | `{percent, consensus}` | Periodic progress update |
| `swarmComplete` | Server → Client | `{verdict, scores, plan, confidence}` | Final aggregated result |

## Security Model

- **macOS**: `mirai_sandbox.sb` (Seatbelt) — deny-default, blocks ~/Documents, ~/Desktop, etc.
- **Docker**: Non-root `mirai_user` with limited permissions
- **Terminal commands**: Python-level regex blocklist (rm -rf /, shutdown, dd, fork bomb, curl|bash, etc.)
- **E2B Sandbox**: LLM-generated code runs in Firecracker microVMs; safe commands (ls, git, cat) stay as subprocess
- **Network**: Allowed for Claude OAuth + browser automation only

## Data Flow for Business Intelligence

```
Exec Summary
    ↓
Phase 0: LLM Extraction (company, industry, product, target_market, ...)
    ↓ data_quality score (0-1), critical field check
Phase 1: Research
    ├→ LLM generates 4-12 research queries (depth-dependent)
    ├→ ChromaDB semantic search across all episode collections
    ├→ Mem0 recall: relationship-aware industry context from past analyses
    ├→ OpenBB: live financial data (company profile, stock price, metrics, news)
    ├→ SearXNG: structured URL discovery → Crawl4AI/browser content extraction
    └→ LLM synthesis of all findings → ResearchReport
    ↓
Phase 1b (deep only): CrewAI multi-agent analysis
    ├→ Market Researcher agent
    ├→ Competitor Analyst agent
    └→ Strategy Consultant agent (uses research + competitor context)
    ↓
Phase 2: Predict
    ├→ 7-dimension scoring (1-10 each, weighted average):
    │   market_timing (20%), competition_landscape (15%),
    │   business_model_viability (20%), team_execution_signals (10%),
    │   regulatory_news_environment (10%), social_proof_demand (10%),
    │   pattern_match (15%)
    ├→ Single LLM (quick/standard) or Dynamic LLM Council (deep)
    │   Council: uses ALL logged-in models (discovered from models.council.models)
    │   Models queried in parallel → reconcile → detect disagreements
    │   Disagreement threshold: ≥3 points spread → contested dimension
    │   Confidence penalty: -0.05 per contested dimension
    └→ Verdict: Strong Hit / Likely Hit / Uncertain / Likely Miss / Strong Miss
    ↓
Phase 2b (optional): Swarm Prediction
    ├→ Triggered by swarm_count parameter (0, 50, 100, 250, 500, 1000)
    ├→ Persona Engine selects diverse agents:
    │   Primary: FinePersonas dataset (2.3M+ real personas, data/personas.jsonl)
    │   Smart label-based matching to startup industry
    │   Fallback: trait-based generator (60 roles x 16 MBTI x 5 risk x 5 exp x ...)
    ├→ Hybrid wave execution:
    │   Wave 1: up to 100 individual LLM calls with unique persona prompts
    │   Wave 2: remaining agents batched (25 per call)
    ├→ Round-robin model distribution across all logged-in providers
    └→ Aggregated swarm verdict merged into final prediction
    ↓
Phase 3: Plan
    ├→ Top 3 risks (severity + mitigation)
    ├→ Top 5 next moves (priority + effort + impact)
    ├→ Go-to-market suggestions
    ├→ Validation experiments
    └→ 90-day timeline milestones
    ↓
Storage: ChromaDB (bi_analyses graph) + Mem0 (relationship-aware)
    ↓
Full Analysis Response (with data_quality, data_sources_used, quality_warning if < 70%)
```

### Depth Levels

| Depth | Queries | Search Limit | Max Tokens | Council | Swarm | Web Research | CrewAI | Time |
|-------|---------|-------------|------------|---------|-------|--------------|--------|------|
| quick | 4 | 5 | 1500 | No | Optional | News only | No | ~30s |
| standard | 8 | 15 | 3000 | No | Optional | News only | No | ~1min |
| deep | 12 | 30 | 4096 | Yes (dynamic) | Optional | All queries | Yes | ~5min |

## Data Flow for Simulation

```
Documents → Ontology (LLM) → Knowledge Graph (ChromaDB) → Entity Extraction
    → Agent Profiles (LLM) → Simulation Config (LLM) → OASIS Simulation
    → Agent Actions → Memory Updates (ChromaDB) → Analysis Reports (LLM)
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MIRAI_SWARM_URL` | `http://localhost:5000` | MiroFish Flask backend URL |
| `MIRAI_CORTEX_URL` | `http://localhost:8100` | Cortex API server URL |
| `MIRAI_API_PORT` | `8100` | Cortex API server port |
| `LLM_API_KEY` | auto-discovered | API key for LLM calls (auto-read from `~/.openclaw/openclaw.json`) |
| `LLM_BASE_URL` | auto-discovered | OpenAI-compatible LLM endpoint (auto-read from gateway config) |
| `LLM_MODEL_NAME` | auto-discovered | Model identifier (auto-read from gateway config) |
| `CHROMADB_PERSIST_PATH` | `subconscious/memory/.chromadb_data` | ChromaDB storage path |
| `SEARXNG_URL` | `http://localhost:8888` | SearXNG metasearch instance |
| `MEM0_API_KEY` | (empty) | Mem0 cloud API key (optional) |
| `MEM0_USER_ID` | `mirai_bi` | Mem0 user identifier |
| `OPENBB_ENABLED` | `true` | Enable OpenBB financial data |
| `E2B_API_KEY` | (empty) | E2B sandbox API key |
| `NEO4J_URL` | (empty) | Neo4j URL for Mem0 graph store (optional) |
| `MIRAI_GATEWAY_PORT` | `3000` | Mirai Gateway port |
| `MIRAI_WHATSAPP_NUMBER` | (empty) | Default WhatsApp recipient |
| `FLASK_DEBUG` | `True` | Flask debug mode |

## Gateway OAuth Auto-Discovery

`Config.LLM_API_KEY`, `Config.LLM_BASE_URL`, and `Config.LLM_MODEL_NAME` are automatically read from `~/.openclaw/openclaw.json` at startup. The gateway's `/v1/chat/completions` HTTP endpoint is used for all LLM calls. No separate API key configuration is needed -- all calls route through the gateway's OAuth tokens.

## Performance Throttling

The Swarm Predictor limits concurrent LLM workers to prevent CPU hang and API rate limits:
- **Wave 1** (individual persona calls): 3 concurrent workers
- **Wave 2** (batched calls): 2 concurrent workers

## JSON Parse Hardening

`llm_client.py` strips any text preamble before JSON in LLM responses. This handles Claude's reasoning/thinking output that may precede the JSON payload, preventing parse failures.

## Autoresearch Lab (Parked)

The lab (`subconscious/lab/`) trains small GPT models from scratch for architecture
research. It is **not wired into the active system** — the LLM (Claude/GPT via
Mirai Gateway) is far more capable at BI and reasoning tasks. The lab is kept as
reference for future model architecture experiments. If Mirai needs local models,
fine-tuning an existing small model (Phi-3, Llama) on experience data is the
recommended path.
