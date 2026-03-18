# Mirai Changelog

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
