# Mirai Changelog

## [0.7.1] — 2026-03-23

### Added — Research & Council Upgrades
- **Source credibility weighting** — 31 premium domains (Gartner, SEC, Bloomberg, EPA) get 1.5-3x score boost. Results re-sorted by credibility-weighted score.
- **Industry-specific dimension weights** — 12 industry profiles (HealthTech, BioTech, FinTech, CleanTech, AI, SaaS, Cybersecurity, EdTech, Hardware, Marketplace). CleanTech weights regulatory 20% vs default 10%. BioTech weights team 20% vs default 10%. Auto-normalized to sum 1.0.
- **Fact-checker integrated into council** — Contradicted research claims now penalize council confidence (-5% per contradiction). Critical contradictions surfaced in reasoning.
- **Research-council feedback loop** — When council dimensions are contested (3+ point spread), system auto-generates follow-up search queries to re-research those specific topics.
- **Content truncation expanded** — Crawled web content limit doubled (3000→6000 chars), search snippets tripled (500→1500 chars). Regulatory documents and financial reports no longer gutted.

### Added — Critical Bug Fixes
- **CRITICAL: Verdict override** — PDF verdict now uses MORE CONSERVATIVE of council vs swarm. 19% swarm HIT → can't be "Likely Hit" regardless of council score. New "Mixed Signal" verdict for split decisions.
- **CRITICAL: Data pipe** — Divergence, deliberation, swarm verdict, and swarm confidence now flow through to PDF report. Previously computed but never sent to report generator.
- **CRITICAL: Confidence** — Blended council + swarm agreement-based confidence. No more static 72%.
- **Role deduplication** — Up to 5 retries per zone to avoid duplicate roles at 100 agents.
- **Heatmap agent names** — "[Zone] Role" format instead of truncated backstory text.
- **Zone rebalancing at 100 agents** — Investor 20→12, Analyst 15→18, Contrarian 15→18, Wildcard 20→25.
- **Wild card pool** — Expanded from 12 to 35 roles (utility worker, EPA admin, fishing guide, tribal advocate, etc.).
- **Non-competitor filter** — Scatter plot excludes research firms and consultancies.
- **Convergence fix** — Zone-specific evaluation angles force domain vocabulary. Anti-convergence directive prevents generic VC-speak.

### Added — Persona Engine (v2)
- **Full VC committee deliberation** — 5-6 member roundtable (strongest bull, strongest bear, most conflicted, zone dissenter, unique wild card, operator). 2 rounds + chair synthesis. 6-7 LLM calls.
- **Contextual persona curation** — 10 industry mappings with priority roles per zone.
- **"Stay in your lane"** directive enforces domain-specific reasoning.
- **Customer geography weighting** — 70% of customer personas from target market region.
- **Industry role exclusion** — No Crypto VCs on CleanTech panels.

## [0.7.0] — 2026-03-22

### Added — Persona Engine Overhaul (88.5B+ unique personas)
- **11-dimension trait generator** — roles (142), MBTI behavioral (16 with scoring tendencies), risk profiles (7), experience levels (7 with role compatibility), cognitive biases (22, categorized), geographic lens (28 with behavioral notes), industry focus (26), fund/budget context (zone-specific), backstories/scar tissue (77 across 6 zones, balanced bull/bear), decision frameworks (58 across 6 zones, categorized), portfolio composition (investor-only)
- **Role-experience compatibility** — PE Partners can't have "early career" experience, Sovereign Wealth Fund Managers need veteran+. 32 roles with experience floors.
- **Bias-framework anti-redundancy** — biases and frameworks categorized, never drawn from same category
- **Geographic behavioral notes** — "Tel Aviv: evaluate through exit velocity toward US/EU acquirers" not just "based in Tel Aviv"
- **Portfolio composition** — investor-only dimension: "Your portfolio has 2 investments in this sector" affects evaluation

### Added — Contextual Persona Curation
- **Industry-role priority mapping** — 10 industries (healthtech, fintech, ai, saas, cleantech, cybersecurity, marketplace, biotech, edtech, hardware) with curated priority roles per zone
- **Fuzzy industry matching** — "CleanTech / Environmental Water Monitoring" matches to cleantech via keyword containment
- **60/40 priority/random split** — curated roles fill 60% of zone slots, 40% remain random for diversity
- **"Stay in your lane" directive** — persona prompt tells agents to focus on domain expertise, not generic startup advice
- **Clean data flow** — extraction.industry/product passed from websocket to swarm predictor to persona engine (replaces naive regex parsing)

### Added — Consensus vs Divergence Highlighting
- **Per-agent z-score computation** — identifies critical outliers (|z| > 1.5 SD from median)
- **Zone agreement tracking** — within each zone, what % voted the same way
- **Most divided dimension** — dimension with highest std across agents
- **Critical Divergence PDF section** — outlier cards with z-score, zone agreement table
- **`divergence` field** in swarmComplete WebSocket event (backward compatible)

### Added — Simulated Deliberation (Investment Committee)
- **2-round debate** — most bullish and most bearish outliers challenge each other (2 parallel LLM calls)
- **Committee chair synthesis** — summarizes key tension, resolution status, recommendation (1 LLM call)
- **Score adjustment** — defenders can adjust their score during deliberation, affecting final aggregation
- **Trigger condition** — only fires when divergence finds >= 2 critical outliers (no artificial conflict)
- **Investment Committee Deliberation PDF section** — debate dialogue with concessions, maintained positions, score changes, and chair synthesis

### Added — OASIS Improvements
- **Graduated scoring** — agents return -2.0 to +2.0 adjustments (0.5 increments) instead of binary IMPROVED/WORSENED
- **Running scores with inertia** — each agent maintains a persistent 1-10 score, no more 0-100% swings
- **Agent-to-agent visibility** — panel summary (bull/bear quotes, sentiment breakdown, minority amplification) fed into next round
- **Anti-herding safeguards** — minority views explicitly flagged as worth considering, lopsided splits highlighted

### Added — Dashboard & UX
- **Manual form with field cards** — green border when filled, OK indicator, required counter
- **Additional Context textarea** — raw text passed verbatim to API, nothing lost
- **OASIS toggle** — off by default in form, "+10-15 min" note
- **Panel scroll fix** — onWheel stopPropagation so canvas doesn't steal scroll
- **Dark dropdown backgrounds** — select options match dark theme

### Added — PDF Report Improvements
- General Info on page 1 (no leak to page 2), company name bold
- Market Analysis: key figures as summary cards, full text in Appendix A
- Competitive Analysis: short summary inline, full text in Appendix B
- Competitor table: page-break-inside avoid
- Council reasoning shown below chart
- No em dashes in swarm reasoning, risk assessment, strategy
- Risk Assessment and Strategic Recommendations with proper section headings
- Paragraphed narratives throughout (auto-split long text blocks)
- OASIS events: markdown stripped, em dashes removed
- Critical Divergence section (zone agreement + outlier cards)
- Investment Committee Deliberation section (debate dialogue + chair synthesis)

### Added — Infrastructure
- **Backtest script** (`backtest.py`) — 30 Tier 1 companies (15 successes, 15 failures) + 10 Tier 2, checkpoint/resume support
- **Landing page** (`website/index.html`) — dark theme, pipeline visualization, report preview, submit form

### Fixed
- **SwarmAgent zone field** — zone was never persisted on SwarmAgent objects, now a proper dataclass field
- **OASIS sentiment swings** — binary voting (0% or 100%) replaced with graduated scoring (smooth 35-75% range)

### Changed
- Persona generator: 7 dimensions (163M combos) → 11 dimensions (88.5B+ combos)
- Persona prompts: ~80 tokens → ~300-350 tokens (behavioral descriptions, backstories, frameworks)
- OASIS: 12 binary votes per round → 12 graduated adjustments with running scores
- Dashboard: Smart Paste primary → Manual form primary with Additional Context
- Reframed: "AI Startup Prediction" → "AI Due Diligence"
- SwarmResult.to_dict() now includes divergence and deliberation fields
- Report footer: "AI Startup Prediction System" → "AI Due Diligence Platform"

## [0.6.0] — 2026-03-22

### Added
- **Multi-model parallel research** — Claude, GPT, Gemini research simultaneously with different perspectives, findings merged
- **OASIS market simulation** — 6-month multi-round simulation with evolving agent opinions and market events
- **ReACT report agent** — 6 LLM-generated professional report sections (Executive Summary, Market Analysis, etc.)
- **Agent chat** — click any agent post-analysis to ask follow-up questions via WebSocket
- **Smart paste** — paste pitch deck text, AI auto-fills all form fields via `/api/bi/validate`
- **Research agent in war room** — pixel character wanders during research phase
- **Live research feed** — round-by-round research progress in scoreboard
- **OASIS timeline in dashboard** — month-by-month sentiment with events
- **PDF export gating** — button disabled until full pipeline completes (including OASIS)
- **Per-tile floor color tinting** — subtle color variation per room (tileColors array)
- **Original pixel-agents furniture style** — desk pairs, mirrored variants, sofa corners
- **Room labels on walls** — blue text on corridor wall bars
- **Agent vote tags** — HIT/MISS visible after voting without hover
- **Agents wander after voting** — 30 seconds of walking, then sit back down
- **Action logging** — per-analysis JSONL in `~/.mirai/logs/`

### Fixed
- **CRITICAL: PDF data pipeline** — `'swarm_result' in dir()` always returned False, making swarm_dict empty. Fixed to direct variable check.
- **PDF competitor type crash** — `'int' object is not subscriptable` when competitors contained non-string values
- **LLM chat method signature** — `llm.chat()` requires messages list, not string
- **Funding signals keyword** — `limit` → `max_results` parameter name
- **Persona industry variable** — `industry` → `focus_industry` in `_generate_personas()`
- **WebSocket disconnect race** — removed duplicate `mirai.disconnect()` from scoreboard

### Changed
- Research: single-model → 3 models in parallel
- Layout: 45x35 → 52x35 grid, 7 rooms with unique themes
- Default zoom: auto-fit to screen with 0.5-step rounding
- Agent lifecycle: TYPE → IDLE → WANDER after voting
- Floor sprites: 9 → 14 (tiles 0-13 for all zones)

## [0.5.0] — 2026-03-21

### Added

- **5-Model Council** across 3 providers
  - Claude Opus 4.6 + Sonnet 4.6 (Anthropic)
  - GPT-5.4 (OpenAI Codex OAuth)
  - Gemini 3.1 Pro (Google OAuth via Gemini CLI)
  - Config at `~/.mirai/council.json`

- **Full Pipeline via WebSocket** (`startAnalysis` message type)
  - Research → Council → Swarm → Plan streamed as live events
  - Dashboard shows phase progress bar with real-time updates
  - Swarm agents receive enriched context from research + council verdict

- **7-Room War Room** (52x35 grid)
  - Added Council room with 4 Elder agents at meeting table
  - Added Wild Card room (creative lounge theme)
  - Each room has unique decoration theme (boardroom, lab, bullpen, library, war room, lounge)

- **Zone-Based Persona Selection**
  - 12 investors, 8 customers, 8 operators, 7 analysts, 7 contrarians, 8 wild card (for 50 agents)
  - Zone-specific evaluation prompts that force score diversity
  - Investors: "would you write a check?", Contrarians: "find the fatal flaw"

- **1.6M Real Personas**
  - 1.2M FinePersonas (Argilla/HuggingFace)
  - 238K Tencent PersonaHub Elite (top 1% domain experts)
  - 200K Tencent PersonaHub regular

- **231K Company Database** (SQLite)
  - YC-OSS API (5,690 companies with outcomes)
  - Crunchbase datasets (66K + 160K companies)
  - Unicorns 2021 (534 companies)
  - 22,818 companies with known outcomes for backtesting

- **Funding Signals Service** — SearXNG news search for live funding rounds
- **PDF Report Generator** — HTML→PDF with verdict, dimensions, research, agent table, suggestions
- **Feedback API** — `/api/bi/feedback` + `/api/bi/accuracy` for tracking prediction outcomes
- **Hover Tooltips** — mouse over pixel agents to see persona, zone, model, vote, reasoning
- **SearXNG** — Docker container on port 8888, JSON API enabled

### Changed

- Gateway port: 3000 → 19789 (avoids conflict with OpenClaw on 18789)
- State directory: `~/.openclaw/` → `~/.mirai/`
- Config file: `openclaw.json` → `mirai.json`
- All env vars: `OPENCLAW_*` → `MIRAI_*`
- Swarm workers: 3 → 25 parallel (faster execution)
- Default agent count: 100 → 25
- Chat completions endpoint enabled on gateway (`gateway.http.endpoints.chatCompletions.enabled: true`)

### Fixed

- White screen on swarm complete (snake_case → camelCase key mapping)
- WebSocket disconnect race condition (removed duplicate mirai.disconnect())

## [0.4.0] — 2026-03-21

### Added

- **Pixel Art Dashboard** (`dashboard/`)
  - Forked from pixel-agents (MIT license), built with React + Canvas 2D + Vite
  - Served at `localhost:5000/dashboard/` by the Flask backend
  - Top-down war room office with animated pixel character agents
  - 5 color-coded role zones: Investors, Customers, Operators, Analysts, Contrarians
  - Agents spawn as pixel characters, walk to assigned zone seats, show thinking/voting animations
  - Key files: `miraiApi.ts` (REST + WebSocket client), `useSwarmAgents.ts` (agent lifecycle),
    `SwarmScoreboard.tsx` (input form + live results)

- **Structured Input Form** (in dashboard scoreboard)
  - Proper form with validated fields: Company Name, Industry (dropdown), Product/Service,
    Target Market, Business Model, Stage (dropdown), Funding Raised, Traction, Team, Ask,
    Competitive Advantage
  - Required fields validated before START — no more free-text parsing

- **Real-Time WebSocket Visualization** (`/ws/swarm` endpoint)
  - Flask backend streams events: `swarmStarted`, `agentSpawned`, `agentActive`, `agentVoted`,
    `swarmProgress`, `swarmComplete`
  - Dashboard renders live vote feed, consensus gauges, progress bar
  - Full bidirectional communication for swarm analysis sessions

- **War Room Layout** (generated by `dashboard/scripts/generate-warroom.py`)
  - 45x35 tile grid with 5 colored zones
  - 50 seats, 165 furniture items (desks, PCs, sofas, plants, bookshelves, whiteboards,
    paintings, coffee tables)

- **Gateway OAuth Auto-Discovery**
  - `Config.LLM_API_KEY`, `Config.LLM_BASE_URL`, `Config.LLM_MODEL_NAME` auto-discovered
    from `~/.openclaw/openclaw.json`
  - Gateway's `/v1/chat/completions` HTTP endpoint enabled
  - All LLM calls route through gateway OAuth — no separate API key needed

- **In-house Mirai Gateway** (`gateway/`)
  - Full OpenClaw fork rebranded as "Mirai Gateway"
  - Binary is `mirai` (not `openclaw`) — installed via `npm link`
  - `mirai` CLI symlinked at `/usr/local/bin/mirai` for system-wide access without nvm
  - Node.js LLM proxy with multi-provider OAuth support

- **Multi-model onboarding**
  - Users can log in with multiple LLM providers during `mirai onboard`
  - All logged-in models available for Council and Swarm round-robin

- **Dynamic LLM Council**
  - Council now uses ALL logged-in models (not just hardcoded 2)
  - Model list discovered from `models.council.models` in gateway config
  - Parallel inference → reconcile → disagreement detection across N models

- **Swarm Predictor** (`subconscious/swarm/services/swarm_predictor.py`)
  - Spawns 50-1000 agents with variable personalities to evaluate startups
  - Hybrid execution: Wave 1 (up to 100 individual calls with unique personas) + Wave 2 (batched, 25 per call)
  - Round-robin model distribution across all logged-in providers
  - New `swarm_count` parameter on `/api/bi/analyze` (0, 50, 100, 250, 500, 1000)

- **Persona Engine** (`subconscious/swarm/services/persona_engine.py`)
  - Loads from FinePersonas dataset (2.3M+ real personas from HuggingFace, stored locally in `data/personas.jsonl`)
  - Smart label-based matching to startup industry (index at `data/label_index.json`)
  - Fallback to trait-based generator: 60 roles x 16 MBTI x 5 risk profiles x 5 experience levels x 14 biases x 15 geographies x 26 industries = millions of unique combinations

- **Gateway auto-start from cortex** (`cortex/gateway_launcher.py`)
  - `GatewayLauncher` class auto-starts Mirai Gateway on boot
  - Watchdog health check every 10 cycles with auto-restart

- **install.sh one-line installer**
  - Handles Python deps, Node.js 22, pnpm, gateway build, dashboard build, npm link, and onboarding

### Changed

- **Performance throttling** — SwarmPredictor uses 3 concurrent workers (wave 1) and 2 concurrent
  workers (wave 2) to prevent CPU hang and API rate limits
- **JSON parse fix** — `llm_client.py` strips text preamble before JSON to handle Claude's
  reasoning/thinking output that precedes the JSON payload
- Cortex uses local Mirai Gateway API instead of external `openclaw` CLI subprocess
- All user-visible "OpenClaw" references rebranded to "Mirai"
- `config.py` updated with council model discovery via `models.council.models` + OAuth auto-discovery
- Environment variables renamed: `OPENCLAW_GATEWAY_PORT` → `MIRAI_GATEWAY_PORT`, `OPENCLAW_WHATSAPP_NUMBER` → `MIRAI_WHATSAPP_NUMBER`

---

## [0.3.0] — 2026-03-18

### Added — Capability Expansion (Tier 1)

- **SearXNG search engine** (`subconscious/swarm/services/search_engine.py`, 192 lines)
  - Self-hosted metasearch aggregating 70+ search engines via JSON API
  - Replaces DuckDuckGo browser navigation for URL discovery (much faster, structured)
  - Methods: `search()`, `search_news()`, `search_batch()`, `get_urls_for_query()`
  - Availability check, parallel batch queries, category/engine/time_range filters
  - Wired into web researcher as primary URL discovery path + BI research phase

- **Mem0 hybrid memory** (`subconscious/memory/mem0_store.py`, 275 lines)
  - Vector DB + graph DB + key-value store unified memory
  - Relationship-aware recall for BI analyses (who knows whom, what caused what)
  - Two modes: local (ChromaDB backend) or cloud (Mem0 platform with MEM0_API_KEY)
  - Optional Neo4j graph store for relationship queries
  - BI analyses stored in Mem0 for cross-analysis relationship linking
  - `store_bi_analysis()` and `recall_industry_context()` convenience methods
  - Runs alongside ChromaDB (which stays unchanged for MiroFish simulation)

- **OpenBB financial data** (`subconscious/swarm/services/market_data.py`, 270 lines)
  - Live company profiles, stock prices, financial metrics (P/E, ROE, revenue growth), market news
  - `search_company()` — find ticker from company name
  - `get_industry_context()` — one-call aggregation: profile + price + metrics + news
  - Grounded BI predictions in real market data instead of relying solely on LLM training knowledge
  - Graceful fallback: BI continues with LLM knowledge if OpenBB unavailable

### Added — Capability Expansion (Tier 2)

- **Crawl4AI fast extraction** (integrated into `web_researcher.py`)
  - LLM-optimized web crawling for static pages (6x faster than browser-use for bulk extraction)
  - `extract_content()` — Crawl4AI first → browser engine fallback
  - `extract_batch()` — parallel Crawl4AI with browser fallback for failures
  - Browser-use Agent remains for interactive pages (login walls, dynamic content)
  - No capability degradation — two-tier extraction adds speed without removing Playwright

- **E2B sandbox** (`cortex/sandbox_runner.py`, 219 lines)
  - Sandboxed code execution in Firecracker microVMs (sub-200ms cold starts)
  - `is_safe_command()` — pattern matching for safe vs. code-execution commands
  - Safe commands (ls, git, cat, head, tail, wc, etc.) stay as subprocess for low latency
  - LLM-generated code routes through E2B for safety
  - Graceful fallback to subprocess with warning if E2B unavailable

- **CrewAI multi-agent** (`subconscious/swarm/services/crew_orchestrator.py`, 239 lines)
  - `analyze_business()` spawns 3 specialized agents working sequentially:
    - Market Researcher — TAM, growth trends, demand signals, regulatory environment
    - Competitor Analyst — direct competitors, indirect alternatives, moats, threats
    - Strategy Consultant — risks, next moves, GTM, validation experiments (uses research + competitor context)
  - Activated in deep BI mode, results fed into prediction phase for richer context
  - Graceful fallback to single-agent analysis if CrewAI unavailable

### Added — OpenClaw Hardening

- **OpenClawManager class** in `cortex/mirai_cortex.py`
  - `auto_update()` — `openclaw update --channel stable` before first cycle
  - `preflight()` — `openclaw doctor` → `openclaw doctor --repair` if unhealthy
  - `watchdog(cycle_number)` — gateway health check every 10 cycles, auto-restart if down, OAuth repair
  - `send_message(text, to)` — `openclaw message send` (direct, no agent overhead) with fallback to `openclaw agent`
  - Pre-flight runs on boot before entering heartbeat loop

### Added — Self-Learning System (Phase 7b, implemented earlier, now documented)

- **ExperienceStore** (`cortex/learning/experience_store.py`) — ChromaDB-backed action→outcome memory
- **ReflectionEngine** (`cortex/learning/reflection.py`) — pattern analysis every 50 cycles, strategy journal
- **SkillForge** (`cortex/learning/skill_forge.py`) — capability gap detection from failure patterns
- **MarketRadar** (`cortex/learning/market_radar.py`) — periodic market signal monitoring

### Added — Cortex API Server (Phase 7c, implemented earlier, now documented)

- **`cortex/api_server.py`** (307 lines) — HTTP bridge on port 8100
  - `GET /health`, `GET /api/status`, `GET /api/journal`
  - `POST /api/think`, `POST /api/objective`
  - `POST /api/browse`, `POST /api/browse/batch`
  - `POST /api/memory/search`, `POST /api/memory/store`
  - Runs in background thread, reuses cortex's BrowserSession

### Changed

- `web_researcher.py` — Rewritten (358 lines): multi-path research with SearXNG → Crawl4AI → browser engine, smart extraction routing, parallel batch operations
- `business_intel.py` — Expanded (1155 lines): integrates SearXNG, Mem0, OpenBB, CrewAI into research/analysis pipeline. Lazy-init services, graceful degradation, `data_sources_used` tracking
- `mirai_cortex.py` — Expanded (786 lines): OpenClawManager class, E2B sandbox routing in `_handle_terminal_command`, direct messaging in `_handle_message_human`, pre-flight + watchdog in `run_forever`
- `config.py` — Expanded (104 lines): new config entries for SearXNG, Mem0, OpenBB, E2B, Neo4j, OpenClaw gateway
- `Dockerfile` — Added: mem0ai, openbb, crawl4ai, e2b-code-interpreter, crewai, flask, python-dotenv. Added EXPOSE 8100 5000
- `memory/__init__.py` — Exports `Mem0MemoryStore` alongside `EpisodicMemoryStore`

### Design Decisions

- SearXNG for URL discovery, browser engine for content extraction — augment, don't replace Playwright
- Mem0 alongside ChromaDB — MiroFish simulation stays on ChromaDB, Mem0 for BI relationships
- Crawl4AI as fast path, browser-use as full path — no capability degradation
- E2B for LLM-generated code only — safe commands stay as subprocess
- All new services lazy-initialized and gracefully degrade if unavailable — no crash on missing dep

---

## [0.2.0] — 2026-03-18

### Added
- **Business Intelligence Engine** (`subconscious/swarm/services/business_intel.py`)
  - Three-phase pipeline: research → predict → plan
  - 7-dimension scoring: market timing, competition, business model, team, regulatory, demand, pattern match
  - Dimension weights: market_timing (20%), business_model_viability (20%), competition_landscape (15%), pattern_match (15%), team (10%), regulatory (10%), demand (10%)
  - Three depth levels: quick (~30s, 4 queries), standard (~1min, 8 queries), deep (~5min, 12 queries + LLM Council)
  - Data quality scoring: critical fields 60%, important 25%, optional 15%, vague = half-present
  - Verdicts: Strong Hit (>7.5), Likely Hit (>6.0), Uncertain (>4.5), Likely Miss (>3.0), Strong Miss
  - Results stored in ChromaDB `bi_analyses` graph for future recall (flywheel effect)
- **LLM Council** (deep mode)
  - Parallel inference: Claude Opus 4.6 + GPT-5.4 via OpenClaw
  - Score reconciliation: average per dimension, detect disagreements (≥3 point spread)
  - Confidence penalty: -0.05 per contested dimension
- **BI API endpoints** (`subconscious/swarm/api/business_intel.py`)
  - `POST /api/bi/analyze` — full pipeline (returns needs_more_info 422 if critical fields missing)
  - `POST /api/bi/research` — research phase only
  - `POST /api/bi/predict` — predict phase only (requires research data)
  - `POST /api/bi/validate` — validate exec summary without running analysis
  - `GET /api/bi/template` — recommended input template + example
  - `GET /api/bi/history` — past analyses from ChromaDB
- **`analyze_business` cortex action** — cortex can trigger BI analysis autonomously
- **Exec summary template** — structured format with 8 fields (company, industry, product, target_market, business_model, stage, traction, ask)
- Updated system prompt with `analyze_business` action schema (depth: quick/standard/deep)

### Changed
- Autoresearch lab marked as parked — kept as reference, not wired into active system

---

## [0.1.1] — 2026-03-17 (Implementation Sprint)

### Added
- **ChromaDB episodic memory system** (`subconscious/memory/`)
  - `EpisodicMemoryStore` — 3 collections per graph: episodes, nodes, edges
  - `MemoryNode` and `MemoryEdge` dataclasses
  - Semantic search via ChromaDB's built-in sentence-transformer embeddings
  - PersistentClient at `subconscious/memory/.chromadb_data/`
- **Zep Cloud → ChromaDB migration** — all MiroFish services rewritten to use local ChromaDB
- **`swarm_predict` action** — cortex calls MiroFish `POST /api/predict/` via HTTP
- **`terminal_command` action** — `subprocess.run()` with regex blocklist for dangerous patterns
- **WebSocket/CDP session fix** — stale-session recovery in `browser_engine/dom/service.py`
- **`browser_navigate` action** — async cortex loop, browser-use Agent, persistent BrowserSession
- **Cortex API server** (`cortex/api_server.py`) — HTTP bridge on port 8100
- **Self-learning system** (`cortex/learning/`)
  - ExperienceStore, ReflectionEngine (strategy journal), SkillForge, MarketRadar

---

## [0.1.0] — 2025-03-17 (Initial Scaffold)

### Added
- `cortex/mirai_cortex.py` — Main heartbeat loop with OpenClaw LLM integration
- `cortex/system_prompt.py` — Mirai personality and JSON action schemas
- `cortex/browser_engine/` — Full port of browser-use library with CDP session caching fix
  - 15+ LLM providers, agent orchestrator, DOM serialization, Playwright wrapper
  - 16 browser watchdog modules, MCP support, vision screenshot service
- `subconscious/swarm/` — MiroFish Flask backend
  - Flask app factory with CORS, request logging
  - API: graph construction, simulation CRUD, reports, quick-predict
  - Services: ontology generation, profile generation, simulation config, graph building, IPC
  - Utils: LLM client (OpenAI-compatible), file parser, logger, retry
  - Models: Project, Task
- `subconscious/lab/` — Autoresearch framework (prepare.py, train.py, analysis.ipynb)
- `Dockerfile` — Container with Python 3.10, Node.js 20, Playwright
- `mirai_sandbox.sb` — macOS Seatbelt sandbox profile (deny-default)
- `README.md` — Project overview and getting started
