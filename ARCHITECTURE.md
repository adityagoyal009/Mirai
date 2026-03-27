# Mirai (未来) + Sensei (先生) — System Architecture v0.10.0

## Overview

Mirai is an AI-powered startup due diligence platform. It evaluates startups through a 5-phase pipeline using multi-model research, LLM council scoring, persona-based swarm intelligence, market simulation, and professional report generation.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Analysis Pipeline                                │
│                                                                         │
│  Phase 1          Phase 2         Phase 3          Phase 4    Phase 5   │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌────────┐  ┌──────┐ │
│  │ Research  │───>│ Council  │───>│  Swarm   │───>│ OASIS  │─>│Report│ │
│  │ OpenClaw │    │10 models │    │50-100    │    │6-month │  │ HTML │ │
│  │ +Gemini  │    │10 dims   │    │agents    │    │sim     │  │      │ │
│  │ fallback │    │ peer rev │    │6 models  │    │gradual │  │SVG   │ │
│  │          │    │ chairman │    │deliberate│    │scores  │  │charts│ │
│  └──────────┘    └──────────┘    └──────────┘    └────────┘  └──────┘ │
│       │                │               │              │          │     │
│  credibility      fact-check      committee       agent-to    heatmap │
│  weighting        integration     roundtable      -agent      radar   │
│  31 domains       contradictions  5-6 members     visibility  scatter │
│                   penalize conf   chair synthesis              donut  │
└─────────────────────────────────────────────────────────────────────────┘

Services:
  Dashboard (5000) — OpenClaw (18789) — Groq/Cerebras/SambaNova/Mistral/NVIDIA (direct REST)
  CLI: claude -p, codex exec — Gemini fallback research — Cortex (8100)
```

## Directory Structure

```
Mirai/
├── cortex/                         # Autonomous Agent
│   ├── mirai_cortex.py             # 10-second heartbeat loop
│   ├── gateway_launcher.py         # Auto-start gateway + watchdog
│   ├── api_server.py               # HTTP bridge (port 8100)
│   ├── sandbox_runner.py           # E2B sandbox routing
│   ├── system_prompt.py            # LLM personality + action schemas
│   ├── learning/                   # 4-loop self-learning system
│   │   ├── experience_store.py     # ChromaDB action→outcome pairs
│   │   ├── reflection.py           # Pattern analysis every 50 cycles
│   │   ├── skill_forge.py          # Capability gap detection
│   │   └── market_radar.py         # Market signal monitoring
│   └── browser_engine/             # Full browser-use port (Playwright/CDP)
│
├── subconscious/                   # Backend Services
│   ├── swarm/
│   │   ├── api/
│   │   │   ├── websocket.py        # WebSocket pipeline orchestrator
│   │   │   │                       #   Verdict blending (council vs swarm)
│   │   │   │                       #   Data pipe: divergence/deliberation → PDF
│   │   │   └── business_intel.py   # REST API endpoints
│   │   │
│   │   ├── services/
│   │   │   ├── business_intel.py   # Core BI engine (1200+ lines)
│   │   │   │                       #   Phase 1: Research (SearXNG + Crawl4AI)
│   │   │   │                       #   Phase 2: Council (4 models, 7 dimensions)
│   │   │   │                       #   Phase 3: Plan (risks + recommendations)
│   │   │   │                       #   Industry-specific dimension weights
│   │   │   │                       #   Research-council feedback loop
│   │   │   │
│   │   │   ├── swarm_predictor.py  # Swarm engine (800+ lines)
│   │   │   │                       #   Wave 1: Individual LLM calls (25 workers)
│   │   │   │                       #   Wave 2: Batch calls (25 per call)
│   │   │   │                       #   Divergence detection (z-score outliers)
│   │   │   │                       #   Committee deliberation (5-6 members)
│   │   │   │                       #   Verdict blending (median + consensus)
│   │   │   │
│   │   │   ├── persona_engine.py   # 88.5B+ persona generator (1000+ lines)
│   │   │   │                       #   11 dimensions: role, MBTI behavioral,
│   │   │   │                       #   risk, experience, bias, geography,
│   │   │   │                       #   industry, fund context, backstory,
│   │   │   │                       #   decision framework, portfolio
│   │   │   │                       #   Contextual curation (10 industries)
│   │   │   │                       #   Role dedup, geo weighting, lane directive
│   │   │   │
│   │   │   ├── research_agent.py   # Multi-model parallel research
│   │   │   │                       #   3 rounds: research → gap → competitor
│   │   │   │                       #   Content limits: 6000/1500 chars
│   │   │   │
│   │   │   ├── brave_search.py      # Brave Search API client
│   │   │   │                       #   High-priority query routing
│   │   │   │                       #   Complements SearXNG for premium results
│   │   │   │
│   │   │   ├── hallucination_guard.py # Post-synthesis faithfulness checker
│   │   │   │                       #   Verifies claims trace to source material
│   │   │   │
│   │   │   ├── search_engine.py    # SearXNG wrapper
│   │   │   │                       #   Source credibility weighting (31 domains)
│   │   │   │                       #   Batch search, news search
│   │   │   │
│   │   │   ├── report_generator.py # PitchBook-quality PDF (900+ lines)
│   │   │   │                       #   SVG charts: zone donut, heatmap,
│   │   │   │                       #   radar, competitive scatter
│   │   │   │                       #   Agent highlights, appendices
│   │   │   │                       #   Methodology section
│   │   │   │
│   │   │   ├── oasis_simulator.py  # 6-month market simulation
│   │   │   │                       #   Graduated scoring (-2 to +2)
│   │   │   │                       #   Agent-to-agent visibility
│   │   │   │                       #   Anti-herding safeguards
│   │   │   │
│   │   │   ├── report_agent.py     # ReACT 6-section LLM narrative
│   │   │   ├── fact_checker.py     # Validates claims, impacts confidence
│   │   │   ├── web_researcher.py   # Crawl4AI + browser-use extraction
│   │   │   ├── data_enrichment.py  # Company DB enrichment
│   │   │   ├── funding_signals.py  # Live funding round discovery
│   │   │   └── research_cache.py   # Avoids redundant fetches
│   │   │
│   │   ├── data/
│   │   │   ├── personas.jsonl      # 1.2M FinePersonas (283 MB)
│   │   │   ├── personahub_elite.jsonl  # 238K Tencent Elite (167 MB)
│   │   │   ├── personahub.jsonl    # 200K Tencent (29 MB)
│   │   │   └── companies.db        # 231K companies (SQLite)
│   │   │
│   │   ├── prompts/                   # Externalized prompt templates
│   │   │   ├── research_synthesis.txt # Semantic synthesis prompt
│   │   │   ├── council_scoring.txt    # Anonymized evaluator prompt
│   │   │   ├── fact_verification.txt  # Real fact-check prompt
│   │   │   ├── swarm_persona.txt      # Persona agent prompt
│   │   │   ├── deliberation_chair.txt # Committee chair synthesis
│   │   │   └── oasis_round.txt        # OASIS simulation round prompt
│   │   │
│   │   ├── utils/
│   │   │   ├── llm_client.py       # OpenAI-compatible client
│   │   │   ├── prompt_registry.py  # Loads & caches prompt templates from prompts/
│   │   │   └── logger.py           # Rotating file + console
│   │   │
│   │   └── validation/
│   │       └── eval_suite.py       # End-to-end evaluation harness
│   │
│   └── memory/                     # ChromaDB + Mem0
│
├── dashboard/                      # Pixel Art War Room
│   ├── src/
│   │   ├── components/
│   │   │   ├── SwarmScoreboard.tsx  # Input form + results panel
│   │   │   ├── AgentLabels.tsx     # Hover tooltips, vote tags
│   │   │   └── BottomToolbar.tsx   # Controls
│   │   ├── hooks/useSwarmAgents.ts # Agent lifecycle management
│   │   ├── office/                 # Canvas engine, renderer
│   │   └── miraiApi.ts            # REST + WebSocket client
│   └── scripts/generate-warroom.py # 52x35 tile layout generator
│
├── gateway/                        # LLM Proxy (forked from OpenClaw)
├── website/                        # Landing page (index.html)
├── backtest.py                     # Accuracy validation script
└── docker-compose.yml              # Multi-service deployment
```

## 5-Phase Pipeline

### Phase 1: Research
- 3 frontier LLMs (Claude, GPT, Gemini) research in parallel
- SearXNG queries 70+ search engines with **source credibility weighting** (31 premium domains get 1.5-3x boost: Gartner, SEC, Bloomberg, EPA)
- **Source credibility fix**: position-based fallback for sources with score=0.0 (ensures all results get meaningful ranking)
- **Differentiated fallback queries** per model focus (each model generates queries aligned to its research angle)
- Crawl4AI extracts content (6000 char limit) with browser-use fallback
- **Brave Search** for high-priority queries (augments SearXNG with premium web results)
- 3 rounds: initial research → gap analysis → competitor deep-dive
- **Semantic synthesis**: findings merged via `confirmed_facts`, `contradictions`, `unique_insights`, and `coverage_gaps` (not naive concatenation)
- **TF-IDF cosine dedup** replaces set-based dedup (eliminates near-duplicate findings across models)
- **Hallucination guard**: faithfulness check after synthesis verifies claims trace back to source material

### Phase 2: Council
- 4 LLMs score 7 dimensions independently (1-10 scale)
- **Anonymized model labels**: models presented as Evaluator A/B/C/D (eliminates brand bias in scoring)
- **Industry-specific dimension weights**: CleanTech weights regulatory 20% (vs default 10%), BioTech weights team 20%. 12 industry profiles, auto-normalized.
- Disagreement detection: 3+ point spread = contested dimension
- **Real fact verification**: Brave Search + SearXNG + SEC EDGAR + Yahoo Finance + Jina DeepSearch (not LLM-asking-LLM)
- **Source citation tracking**: citations flow through the entire pipeline from research → council → report
- **Research-council feedback**: contested dimensions trigger 3 follow-up SearXNG queries

Dimensions and default weights:
| Dimension | Weight |
|-----------|--------|
| market_timing | 20% |
| business_model_viability | 20% |
| competition_landscape | 15% |
| pattern_match | 15% |
| team_execution_signals | 10% |
| regulatory_news_environment | 10% |
| social_proof_demand | 10% |

### Phase 3: Swarm
- 25-1000 persona agents from **88.5B+ unique combinations** (11 trait dimensions)
- **Contextual curation**: 10 industry mappings with priority roles per zone
- 6 zones: Investors, Customers, Operators, Analysts, Contrarians, Wild Cards (35 roles)
- Each agent gets behavioral MBTI, backstory, decision framework, geographic lens
- **"Stay in your lane"** directive + zone-specific evaluation angles force domain vocabulary
- **Role deduplication**: up to 5 retries per zone
- **Customer geography weighting**: 70% from target market region

**Full-swarm divergence**: Wave 1 (individual LLM calls, 25 workers) + Wave 2 (batch calls, 25 per batch). Both waves contribute to divergence detection, not just Wave 1.

**Verdict blending**: Uses MORE CONSERVATIVE of council vs swarm verdict. 19% swarm HIT can't be "Likely Hit" regardless of council score. New "Mixed Signal" verdict for split decisions. `DELIBERATION_WEIGHT=3.0` configurable weighted aggregation controls how much deliberation adjusts final scores.

**Confidence**: Blended council + swarm agreement-based (1 - std/3). Not static. **Confidence-weighted committee members**: each member's influence on final score is proportional to their confidence level.

**Divergence detection**: Z-score outliers (|z| > 1.0), zone agreement tracking, most divided dimension, fallback on 3pt absolute spread.

**Investment committee deliberation** (6-7 LLM calls):
- `_select_committee()` picks 5-6 diverse agents: strongest bull, strongest bear, most conflicted, zone dissenter, unique wild card, operator (if all missed)
- Round 1: Each member writes position statement addressing their biggest disagreement
- Round 2: Chair synthesizes consensus points, unresolved tensions, recommendation
- Score adjustments feed into final aggregation (weighted by `DELIBERATION_WEIGHT`)

### Phase 4: OASIS Market Simulation
- 6-month multi-round simulation with **swarm-sourced 12-agent panel** (drawn from swarm results, not hardcoded roles)
- **Real news-sourced events**: each round injects market events from Brave Search + SearXNG news (not synthetic/random)
- **Graduated scoring**: agents adjust -2 to +2 (0.5 increments), not binary
- **Running scores with inertia**: each agent maintains persistent 1-10 score
- **Uncertainty bands**: each round produces `confidence_low` and `confidence_high` per agent (not just point estimates)
- **Agent-to-agent visibility**: panel summary (bull/bear quotes, minority amplification) fed into next round
- Optional (toggle in dashboard, off by default)

### Phase 5: Report Generation
- 6 LLM-generated professional sections via ReACT agent
- **4 new SVG charts**: zone sentiment donut, agent-dimension heatmap, divergence radar, competitive positioning scatter
- **Agent highlights**: 5-6 most interesting agents as pull-quote cards
- **Critical divergence section**: zone agreement table + outlier cards
- **Investment committee deliberation section**: position statements + chair synthesis
- **Methodology appendix**: models, persona pool, scoring method, deliberation process
- **Appendix D: Research Sources & Citations** table — lists every source URL, domain credibility tier, and which claims it supports
- Full market analysis + competitive landscape in appendices

## WebSocket Event Flow

```
Client sends: startAnalysis {execSummary, agentCount, depth, simulateMarket}
  ↓
Server broadcasts:
  researchStarted → researchProgress (per round) → researchComplete
  councilStarted → councilComplete {verdict, score, dimensions, models}
  swarmStarted → agentSpawned → agentVoted (per agent) → swarmComplete
  deliberationStarted → (internal 6-7 LLM calls)
  planStarted → planComplete {risks, moves}
  oasisStarted → oasisRound (×6) → oasisComplete (if enabled)
  narrativeStarted
  analysisComplete {fullResult} → PDF export ready
```

**Verdict override in fullResult**: After swarm completes, websocket compares council verdict vs swarm verdict and uses the more conservative one. Confidence is blended average.

## Data Flow: Divergence + Deliberation → PDF

```
SwarmPredictor.predict()
  → _compute_divergence(agents) → divergence dict
  → _deliberate(agents, divergence) → deliberation dict + adjusted scores
  → _aggregate(updated_agents) → SwarmResult with divergence + deliberation
  ↓
websocket.py: swarm_dict includes divergence + deliberation
  ↓
fullResult.swarm includes divergence + deliberation
  ↓
report_generator.py: renders Critical Divergence + Committee Deliberation sections
```

## Persona Engine (88.5B+ combinations)

11 trait dimensions combined per agent:

| Dimension | Options | Zone-Gated? |
|-----------|---------|-------------|
| Roles | 142 | Yes |
| MBTI (behavioral) | 16 | No |
| Risk Profiles | 7 | No |
| Experience | 7 (with role compatibility) | No |
| Cognitive Biases | 22 (categorized) | No |
| Geography | 28 (with behavioral notes) | Customer zone weighted |
| Industry Focus | 26 | No |
| Fund/Budget Context | 6-8 per zone | Yes |
| Backstories | 15-18 per zone | Yes |
| Decision Frameworks | 10-12 per zone | Yes |
| Portfolio Composition | 8 (investor-only) | Yes |

**Safeguards**:
- Role-experience compatibility (no junior PE Partners)
- Bias-framework anti-redundancy (never same category)
- Industry role exclusions (no Crypto VCs on CleanTech)
- Customer geography weighting (70% from target market)
- Role deduplication (5 retries per zone)

## Research Quality Features

- **Source credibility**: 31 premium domains (Gartner 3x, SEC 3x, EPA 2.5x, Wikipedia 1.5x). Results re-sorted by weighted score.
- **Industry dimension weights**: 12 industry profiles auto-adjust the 7 scoring dimensions.
- **Fact-checker integration**: Contradicted claims penalize council confidence. Critical contradictions surfaced.
- **Research-council feedback**: Contested dimensions trigger follow-up SearXNG queries.
- **Content expansion**: Crawled content 6000 chars, snippets 1500 chars.

## Ports

| Port | Service |
|------|---------|
| 19789 | Mirai Gateway (LLM proxy, multi-provider OAuth) |
| 8100 | Cortex API Server (browse, think, memory, objective) |
| 5000 | Flask + Dashboard + WebSocket |
| 8888 | SearXNG (Docker, 70+ search engines) |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_BASE_URL` | `http://localhost:19789/v1` | Gateway URL |
| `LLM_API_KEY` | `mirai-local-token` | Gateway auth token |
| `MIRAI_GATEWAY_PORT` | `19789` | Gateway port |
| `SEARXNG_URL` | `http://localhost:8888` | SearXNG instance |
| `MIRAI_API_PORT` | `8100` | Cortex API port |

## Data Sources

| Source | Records | Purpose |
|--------|---------|---------|
| FinePersonas (Argilla) | 1,200,000 | Real persona descriptions |
| Tencent PersonaHub Elite | 238,443 | Top 1% domain experts |
| Tencent PersonaHub | 200,000 | General personas |
| Company Database | 231,213 | Competitor enrichment, backtesting |
| SearXNG | 70+ engines | Live web research |
| Trait Generator | 88.5B+ combos | On-the-fly persona generation |

## Security Model

- macOS: `mirai_sandbox.sb` (Seatbelt, deny-default)
- Docker: Non-root `mirai_user`
- Terminal: Regex blocklist for dangerous patterns
- E2B: LLM-generated code in Firecracker microVMs
- Gateway: OAuth-only, no raw API keys in backend
- **Zero external package dependencies** beyond core (`openai`, `flask`, `requests`, `chromadb`) — no bloated ML/NLP frameworks
- **All fact-checking via direct HTTP** to free public APIs (SEC EDGAR, Yahoo Finance, Brave Search, SearXNG, Jina)

---

## Cortex Autonomous Agent

### Action Flow

The cortex heartbeat loop processes these JSON actions from the LLM:

| Action | Handler | Description |
|--------|---------|-------------|
| `browser_navigate` | browser-use Agent | Navigate + interact with web pages autonomously |
| `terminal_command` | E2B sandbox / subprocess | Execute shell commands (code → sandbox, safe → subprocess) |
| `swarm_predict` | HTTP → Flask `/api/predict/` | Wargame scenarios via MiroFish simulation |
| `analyze_business` | HTTP → Flask `/api/bi/analyze` | BI engine: research → predict → plan |
| `message_human` | `mirai message send` | Send WhatsApp messages to operator |
| `standby` | (no-op) | Idle state |

### Heartbeat Cycle

```
Boot:
  1. GatewayLauncher auto-starts Mirai Gateway on port 19789
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

### Cortex API Server (port 8100)

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

### Self-Learning System (4 loops)

**Loop 1 — Experience (every cycle):**
- `ExperienceStore` (ChromaDB-backed): store action→outcome pairs, recall before acting
- Heuristic success: checks for "error", "failed", "blocked", "timed out"

**Loop 2 — Reflection (every 50 cycles):**
- `ReflectionEngine`: analyze last 50 experiences, update strategy journal
- Journal persists across restarts, injected into system prompt

**Loop 3 — Skill Gap Detection (on reflection):**
- `SkillForge`: analyze failure patterns, detect capability gaps

**Loop 4 — Market Radar (periodic):**
- `MarketRadar`: monitor configured market signals on schedule

### Gateway Management

| Feature | Behavior | When |
|---------|----------|------|
| Auto-start | Starts `gateway/mirai.mjs` on port 19789 | On boot |
| Watchdog | Health check → auto-restart if down | Every 10 cycles |
| Direct messaging | `mirai message send --to [number] --message [text]` | On `message_human` action |

---

## Key Integration Points

| # | Connection | Protocol | Description |
|---|-----------|----------|-------------|
| 1 | Cortex ↔ Gateway | HTTP API | Local Mirai Gateway (localhost:19789/v1), OpenAI-compatible |
| 2 | Cortex ↔ Browser | async/CDP | browser-use Agent with persistent BrowserSession |
| 3 | Cortex ↔ Flask | HTTP | Calls to Flask backend (port 5000) |
| 4 | Cortex ↔ API Server | HTTP | Background thread on port 8100 |
| 5 | Swarm ↔ ChromaDB | Python SDK | Episodic memory for simulation + BI storage |
| 6 | Swarm ↔ Mem0 | Python SDK | Relationship-aware BI memory |
| 7 | Swarm ↔ LLM | OpenAI API | Via Mirai Gateway |
| 8 | Swarm ↔ SearXNG | HTTP JSON | `GET localhost:8888/search?q=...&format=json` |
| 9 | Swarm ↔ OpenBB | Python SDK | Live financial data (optional) |
| 10 | Swarm ↔ Crawl4AI | Python SDK | Fast LLM-optimized content extraction |
| 11 | Swarm ↔ CrewAI | Python SDK | Multi-agent parallel analysis (deep mode) |
| 12 | Cortex ↔ E2B | Python SDK | Sandboxed code execution (Firecracker microVMs) |
| 13 | Dashboard ↔ Flask | WebSocket | `/ws/swarm` — real-time events |
| 14 | Dashboard ↔ Flask | HTTP | REST API + static assets at `/dashboard/` |
| 15 | Swarm ↔ Brave Search | HTTP JSON | High-priority research queries |
| 16 | Swarm ↔ SEC EDGAR | HTTP JSON | Public company filing verification |
| 17 | Swarm ↔ Yahoo Finance | HTTP JSON | Revenue/market cap verification |
| 18 | Swarm ↔ Jina DeepSearch | HTTP JSON | Claim grounding (optional) |

---

## Dashboard Data Flow

```
User opens localhost:5000/dashboard/
    │
    ├→ React app loads (Vite build served as static assets by Flask)
    ├→ SwarmScoreboard renders input form (pre-filled with demo data)
    │   Fields: Company Name, Industry, Product/Service, Target Market,
    │   Business Model, Pricing Strategy, Stage, Funding, Traction,
    │   Team, Ask, Moat, Additional Context
    │
    ├→ User clicks START ANALYSIS
    │   └→ miraiApi.ts sends WebSocket "startAnalysis" message
    │
    ├→ Flask backend runs 5-phase pipeline via WebSocket
    │   ├→ researchStarted → researchProgress (per round) → researchComplete
    │   ├→ councilStarted → councilComplete
    │   ├→ swarmStarted → agentSpawned → agentVoted (per agent)
    │   ├→ deliberationStarted (if divergence found)
    │   ├→ swarmComplete (with divergence + deliberation data)
    │   ├→ planComplete
    │   ├→ oasisStarted → oasisRound (×6) → oasisComplete (if enabled)
    │   └→ analysisComplete (fullResult with blended verdict)
    │
    ├→ useSwarmAgents.ts receives events → animates pixel characters
    │
    └→ Dashboard renders: canvas war room + scoreboard panel
        ├→ Phase progress pills
        ├→ Council + Swarm verdict cards
        ├→ Dimension score bars
        ├→ Live vote feed
        └→ Export PDF / New Analysis buttons
```

---

## BI Data Flow (Full Pipeline)

```
Exec Summary
    ↓
Phase 0: LLM Extraction (company, industry, product, target_market, ...)
    ↓ data_quality score (0-1), critical field check
Phase 1: Research
    ├→ LLM generates 4-12 research queries (depth-dependent)
    ├→ SearXNG: 70+ engines, source credibility weighted (31 premium domains)
    ├→ Crawl4AI: content extraction (6000 char limit) with browser fallback
    ├→ ChromaDB semantic search across episode collections
    ├→ Mem0 recall: relationship-aware industry context
    ├→ OpenBB: live financial data (optional)
    └→ LLM synthesis → ResearchReport
    ↓
Phase 1b (deep only): CrewAI multi-agent analysis
    ├→ Market Researcher agent
    ├→ Competitor Analyst agent
    └→ Strategy Consultant agent
    ↓
Phase 2: Council Predict
    ├→ 7 dimensions scored 1-10, industry-specific weights
    ├→ Single LLM (quick/standard) or Dynamic Council (deep)
    ├→ Fact-checker: contradictions penalize confidence
    ├→ Research-council feedback: contested dims trigger re-research
    ├→ Disagreement: ≥3 point spread → contested dimension
    └→ Verdict: Strong Hit / Likely Hit / Mixed Signal / Likely Miss / Strong Miss
    ↓
Phase 2b: Swarm Prediction
    ├→ Persona Engine: 88.5B+ combos, contextual curation, 6 zones
    ├→ Wave 1: individual calls (25 workers) + Wave 2: batch (25 per call)
    ├→ Divergence detection (z-score, zone agreement)
    ├→ Committee deliberation (5-6 members, chair synthesis)
    ├→ Verdict blending: MORE CONSERVATIVE of council vs swarm
    └→ Aggregated: themes, distribution, divergence, deliberation
    ↓
Phase 3: Plan
    ├→ Top risks (severity + mitigation)
    ├→ Next moves (priority + effort + impact)
    ├→ Go-to-market suggestions
    └→ Validation experiments
    ↓
Phase 4 (optional): OASIS 6-month simulation
    ↓
Phase 5: ReACT Report (6 LLM sections) → PDF with 4 SVG charts
    ↓
Storage: ChromaDB + Action Logs (JSONL)
```

### Depth Levels

| Depth | Queries | Search Limit | Max Tokens | Council | Swarm | Web Research | CrewAI | Fact-Check | Time |
|-------|---------|-------------|------------|---------|-------|--------------|--------|-----------|------|
| quick | 4 | 5 | 1500 | No | Optional | News only | No | No | ~30s |
| standard | 8 | 15 | 3000 | No | Optional | News only | No | No | ~1min |
| deep | 12 | 30 | 4096 | Yes (dynamic) | Optional | All queries + credibility weighted | Yes | Yes | ~5min |

---

## Full Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_BASE_URL` | `http://localhost:19789/v1` | Gateway URL |
| `LLM_API_KEY` | `mirai-local-token` | Gateway auth token |
| `MIRAI_GATEWAY_PORT` | `19789` | Gateway port |
| `MIRAI_SWARM_URL` | `http://localhost:5000` | Flask backend URL |
| `MIRAI_CORTEX_URL` | `http://localhost:8100` | Cortex API URL |
| `MIRAI_API_PORT` | `8100` | Cortex API port |
| `SEARXNG_URL` | `http://localhost:8888` | SearXNG instance |
| `CHROMADB_PERSIST_PATH` | `subconscious/memory/.chromadb_data` | ChromaDB storage |
| `MEM0_API_KEY` | (empty) | Mem0 cloud API key (optional) |
| `OPENBB_ENABLED` | `true` | Enable OpenBB financial data |
| `E2B_API_KEY` | (empty) | E2B sandbox API key |
| `BRAVE_SEARCH_API_KEY` | `BSA...` (built-in default) | Brave Search API key for high-priority queries |
| `JINA_API_KEY` | (empty) | Jina DeepSearch API key for claim grounding (optional) |
| `MIRAI_WHATSAPP_NUMBER` | (empty) | Default WhatsApp recipient |

## Gateway OAuth Auto-Discovery

`Config.LLM_API_KEY`, `Config.LLM_BASE_URL`, and `Config.LLM_MODEL_NAME` are automatically read from `~/.mirai/mirai.json` at startup. The gateway's `/v1/chat/completions` HTTP endpoint is used for all LLM calls. No separate API key configuration needed.

## Performance Throttling

| Component | Workers | Limit |
|-----------|---------|-------|
| Swarm Wave 1 | 25 | Individual persona calls |
| Swarm Wave 2 | 10 | Batch calls (25 per batch) |
| OASIS rounds | 6 | Sequential (agents parallel within round) |
| Deliberation | 6 | Committee position statements parallel |
| Research | 3 | Parallel model research |
| SearXNG batch | 3 | Parallel search queries |

---

## Scoring Calibration Notes (2026-03-24)

### Known Bias Mitigations
- **Research anchoring**: Two-pass council (blind score on exec summary -> research-informed adjustment) prevents research from dominating all model scores
- **Score clustering**: Calibrated rubrics with concrete examples anchor what 2/4/6/8/10 mean for each dimension
- **Persona bias**: Calibration anchors in swarm prompts ("Use the FULL 1-10 range, not everything is 5-7")
- **Verdict bias**: Confidence-weighted blend replaces conservative-wins rule
- **Correlated dimensions**: Auto-detected pairs de-weighted 50% when scores align within 1 point
- **Data quality**: Low-data startups get explicit uncertainty flag and wider verdict bands
- **Deliberation anchoring**: Agents state position BEFORE seeing consensus

### Audit Prompt for Future Reviews

To catch scoring methodology issues in future, give Claude Code this prompt:

```
Trace the full scoring pipeline from exec summary input to PDF output.
For each phase (research, council, swarm, OASIS, report), identify:
1. What prompt does the LLM see? Does it have calibration anchors?
2. What information flows from the previous phase? Does it create anchoring?
3. How are scores aggregated? Does averaging kill signal?
4. Is the persona/evaluator pool balanced (bull vs bear)?
5. Does the final verdict accurately represent the underlying score distribution?
Run a mental simulation of a startup scoring 8/10 on one dimension and 3/10 on another.
Does the pipeline preserve this disagreement or compress it to 5.5?
Check: are Wave 1 and Wave 2 prompts equivalent in quality and instruction depth?
Check: does deliberation actually shift scores or is it theater?
Check: does OASIS affect the final verdict or just the PDF display?
```
