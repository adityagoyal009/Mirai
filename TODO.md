# Mirai TODO — Implementation Plan

## Status Legend
- [ ] Not started
- [~] In progress
- [x] Complete

---

## Phase 1: ChromaDB Episodic Memory System
**Status**: COMPLETE

- [x] Create `subconscious/memory/__init__.py` — package init
- [x] Create `subconscious/memory/episodic_store.py` — `EpisodicMemoryStore` class
  - `PersistentClient` (survives restarts) at `subconscious/memory/.chromadb_data/`
  - Collections: `{graph_id}_nodes`, `{graph_id}_edges`, `{graph_id}_episodes`
  - Methods: `create_graph`, `add_episodes`, `search`, `add_nodes`, `add_edges`, `get_all_nodes`, `get_all_edges`, `get_node_edges`
  - Semantic search via ChromaDB's built-in sentence-transformer embeddings

## Phase 2: Strip Zep Cloud Dependency
**Status**: COMPLETE

- [x] `subconscious/swarm/config.py` — removed `ZEP_API_KEY`, added `CHROMADB_PERSIST_PATH`
- [x] `subconscious/swarm/utils/zep_paging.py` — rewritten to delegate to `EpisodicMemoryStore`
- [x] `subconscious/swarm/services/graph_builder.py` — uses `EpisodicMemoryStore`
- [x] `subconscious/swarm/services/zep_entity_reader.py` — uses `EpisodicMemoryStore`
- [x] `subconscious/swarm/services/zep_graph_memory_updater.py` — uses `EpisodicMemoryStore`
- [x] `subconscious/swarm/services/zep_tools.py` — replaced `Zep` client with ChromaDB search
- [x] `subconscious/swarm/services/oasis_profile_generator.py` — replaced Zep with ChromaDB
- [x] `subconscious/swarm/services/ontology_generator.py` — removed Zep import reference
- [x] `subconscious/swarm/api/graph.py` — removed `ZEP_API_KEY` guards
- [x] `subconscious/swarm/api/simulation.py` — removed `ZEP_API_KEY` guards

## Phase 3: Wire `swarm_predict` to Cortex
**Status**: COMPLETE

- [x] Created `subconscious/swarm/api/predict.py` — `POST /api/predict`
- [x] Updated `subconscious/swarm/api/__init__.py` — registered `predict_bp`
- [x] Updated `subconscious/swarm/__init__.py` — registered blueprint at `/api/predict`
- [x] Updated `cortex/mirai_cortex.py` — `swarm_predict` handler calls Flask via HTTP

## Phase 4: Implement `terminal_command` Handler
**Status**: COMPLETE

- [x] `cortex/mirai_cortex.py` — `subprocess.run()` with 30s timeout, stdout/stderr capture
- [x] Regex blocklist for dangerous commands (rm -rf /, shutdown, dd, fork bomb, curl|bash, etc.)
- [x] Command output fed back to LLM in next cycle via `self.last_action_result`
- [x] `cortex/system_prompt.py` — added `working_directory` field

## Phase 5: Fix WebSocket Persistence
**Status**: COMPLETE

- [x] `cortex/browser_engine/dom/service.py`
  - Stale-session recovery in `_get_cdp_session()` with fallback to fresh session
  - `clear_cdp_cache()` method for reconnect/target-detach scenarios
  - `__aexit__` clears cache on context manager exit

## Phase 6: Implement `browser_navigate` Handler
**Status**: COMPLETE

- [x] Converted `cortex/mirai_cortex.py` to async (`asyncio.run()`)
- [x] `brain.think()` wrapped in `asyncio.to_thread()` for non-blocking calls
- [x] Lazy-init persistent headless `BrowserSession`
- [x] browser-use `Agent` with URL + task, result fed back to LLM
- [x] `cortex/system_prompt.py` — added `task` field to `browser_navigate` schema

## Phase 7: Business Intelligence Engine
**Status**: COMPLETE

- [x] Created `subconscious/swarm/services/business_intel.py` — `BusinessIntelEngine` class
  - Phase 0: Extract + validate (LLM extraction, data_quality scoring, critical field check)
  - Phase 1: Research (queries → ChromaDB + web + LLM synthesis → ResearchReport)
  - Phase 2: Predict (7-dimension scoring, weighted average, LLM Council for deep mode)
  - Phase 3: Plan (risks, next moves, GTM, validation, 90-day timeline → StrategyPlan)
  - Three depth levels: quick (~30s), standard (~1min), deep (~5min)
- [x] Created `subconscious/swarm/api/business_intel.py` — Flask blueprint endpoints
  - `POST /api/bi/analyze` — full pipeline
  - `POST /api/bi/research` — research phase only
  - `POST /api/bi/predict` — predict phase only
  - `POST /api/bi/validate` — validate exec summary without analysis
  - `GET /api/bi/template` — recommended input template + example
  - `GET /api/bi/history` — past analyses from ChromaDB
- [x] Registered `bi_bp` blueprint in `api/__init__.py` and `swarm/__init__.py`
- [x] Added `analyze_business` action handler in `cortex/mirai_cortex.py`
- [x] Updated `cortex/system_prompt.py` with `analyze_business` action schema

## Phase 7b: Self-Learning System
**Status**: COMPLETE

- [x] Created `cortex/learning/` package
  - [x] `experience_store.py` — `ExperienceStore` (ChromaDB-backed action→outcome memory)
  - [x] `reflection.py` — `ReflectionEngine` (pattern analysis every 50 cycles, strategy journal)
  - [x] `skill_forge.py` — `SkillForge` (capability gap detection from failure patterns)
  - [x] `market_radar.py` — `MarketRadar` (periodic market signal monitoring)
- [x] Lazy-initialized in `MiraiCortex._init_learning()` — no crash if unavailable
- [x] Experience recall injected into system prompt before each LLM call
- [x] Strategy journal injected into system prompt (self-learned rules)
- [x] Experience stored after every action (heuristic success detection)

## Phase 7c: Cortex API Server
**Status**: COMPLETE

- [x] Created `cortex/api_server.py` — HTTP bridge on port 8100
  - `GET /health` — health check
  - `GET /api/status` — cortex state (cycle, objective, model, learning)
  - `GET /api/journal` — strategy journal
  - `POST /api/think` — LLM inference via cortex brain
  - `POST /api/objective` — set cortex objective
  - `POST /api/browse` — single URL browsing via browser-use Agent
  - `POST /api/browse/batch` — batch URL browsing
  - `POST /api/memory/search` — semantic search in experience memory
  - `POST /api/memory/store` — store experience manually
- [x] Runs in background thread, started on cortex boot
- [x] Reuses cortex's BrowserSession for browse endpoints

---

## Phase 8: Capability Expansion — Forkable Repos + OpenClaw Hardening
**Status**: COMPLETE

### Tier 1: Integrated (Highest ROI)

- [x] **SearXNG** — Self-hosted metasearch (26.7k stars)
  - [x] New `subconscious/swarm/services/search_engine.py` (192 lines)
  - [x] `SearchEngine` class: `search()`, `search_news()`, `search_batch()`, `get_urls_for_query()`
  - [x] Wired into `web_researcher.py` as primary URL discovery path
  - [x] Wired into BI research phase (replaces DuckDuckGo browser navigation)
  - [x] Graceful fallback to DuckDuckGo via browser if SearXNG unavailable
  - [x] Deploy: `docker run -d -p 8888:8888 searxng/searxng`

- [x] **Mem0** — Hybrid memory layer (37k stars)
  - [x] New `subconscious/memory/mem0_store.py` (275 lines)
  - [x] `Mem0MemoryStore` class: `add()`, `search()`, `get_all()`, `delete()`
  - [x] Convenience: `store_bi_analysis()`, `recall_industry_context()`
  - [x] Supports local mode (ChromaDB) and cloud mode (Mem0 platform)
  - [x] Optional Neo4j graph store for relationship-aware queries
  - [x] BI stores analyses in Mem0 for cross-analysis relationship linking
  - [x] BI research phase queries Mem0 for industry context
  - [x] ChromaDB retained for MiroFish simulation (stable, unchanged)

- [x] **OpenBB** — Financial data platform (62.5k stars)
  - [x] New `subconscious/swarm/services/market_data.py` (270 lines)
  - [x] `MarketDataService` class: company overview, stock price, financial metrics, news, search
  - [x] `get_industry_context()` — one-call aggregation for BI research
  - [x] BI research phase fetches live financial data before scoring
  - [x] Graceful fallback: LLM training knowledge if OpenBB unavailable

### Tier 2: Integrated (High Value)

- [x] **Crawl4AI** — LLM-optimized web crawling (51k stars)
  - [x] Integrated into `web_researcher.py` as fast extraction path
  - [x] `extract_content()` — Crawl4AI first → browser engine fallback
  - [x] `extract_batch()` — parallel Crawl4AI → browser fallback for failures
  - [x] Browser engine remains for interactive pages (login walls, dynamic content)
  - [x] No capability degradation — Crawl4AI adds speed, doesn't replace Playwright

- [x] **E2B Sandbox** — Safe code execution (8.9k stars)
  - [x] New `cortex/sandbox_runner.py` (219 lines)
  - [x] `SandboxRunner` class: `is_safe_command()`, `execute_subprocess()`, `execute_e2b()`, `execute()`
  - [x] Routes LLM-generated code through Firecracker microVMs
  - [x] Safe commands (ls, git, cat, etc.) stay as subprocess for low latency
  - [x] Graceful fallback to subprocess with warning if E2B unavailable
  - [x] Wired into `MiraiCortex._handle_terminal_command()`

- [x] **CrewAI** — Multi-agent orchestration (45.9k stars)
  - [x] New `subconscious/swarm/services/crew_orchestrator.py` (239 lines)
  - [x] `CrewOrchestrator.analyze_business()` — spawns 3 specialized agents:
    - Market Researcher — TAM, trends, demand signals
    - Competitor Analyst — competitive landscape, moats, threats
    - Strategy Consultant — risks, moves, GTM (uses research + competitor context)
  - [x] Deep BI mode triggers CrewAI analysis, results fed into prediction phase
  - [x] Graceful fallback to single-agent analysis if CrewAI unavailable

### OpenClaw Hardening

- [x] **OpenClawManager class** in `cortex/mirai_cortex.py`
  - [x] `auto_update()` — `openclaw update --channel stable` on boot
  - [x] `preflight()` — `openclaw doctor` + `--repair` if unhealthy
  - [x] `watchdog(cycle_number)` — gateway health check every 10 cycles, auto-restart
  - [x] `send_message(text, to)` — `openclaw message send` (direct, no agent overhead)
  - [x] Fallback to `openclaw agent --message` if `message send` unavailable
- [x] Pre-flight runs before cortex enters heartbeat loop
- [x] Watchdog runs at start of each cycle

### Infrastructure

- [x] Updated `subconscious/swarm/config.py` — new config: SearXNG, Mem0, OpenBB, E2B, Neo4j, OpenClaw
- [x] Updated `subconscious/memory/__init__.py` — exports `Mem0MemoryStore`
- [x] Updated `Dockerfile` — added mem0ai, openbb, crawl4ai, e2b-code-interpreter, crewai, flask, python-dotenv
- [x] Updated `ARCHITECTURE.md`, `TODO.md`, `CHANGELOG.md`, `README.md`

---

## Tier 3: Deploy as Services (Future)

- [ ] **Graphiti by Zep** (23.9k stars) — Temporal knowledge graph with validity windows and provenance tracking. Requires Neo4j or FalkorDB backend as Docker service. Would replace ChromaDB for BI where fact evolution matters.
- [ ] **Apache Superset** (59k stars) — BI dashboards with 40+ visualization types. Deploy as Docker service, push BI results via REST API for executive-facing dashboards.

## Future Improvements

- [ ] Add cross-encoder reranker for better semantic search quality
- [ ] LLM-based entity extraction from episodes (automatic knowledge graph enrichment)
- [ ] ChromaDB → PostgreSQL migration for production scale
- [ ] Docker-compose for cortex + swarm + SearXNG co-deployment
- [ ] WhatsApp/Telegram integration testing with OpenClaw
- [ ] Remove legacy Zep wrapper files (zep_entity_reader.py, zep_graph_memory_updater.py, zep_tools.py, zep_paging.py) — currently delegate to ChromaDB, could be inlined
- [ ] Fine-tune small model (Phi-3, Llama) on Mirai's experience data for fast local inference

## Design Decisions

1. **ChromaDB PersistentClient** over in-memory: data survives restarts
2. **Separate processes**: cortex (port 8100) ↔ swarm (port 5000) communicate via HTTP
3. **Async cortex loop**: required for browser-use (Playwright is async)
4. **SearXNG for URL discovery, browser engine for content extraction** — augment, don't replace Playwright
5. **Mem0 alongside ChromaDB, not replacing it** — MiroFish simulation works on ChromaDB, Mem0 for BI relationships
6. **OpenClaw doctor runs automatically** — cortex self-heals on boot, doesn't wait for human intervention
7. **Crawl4AI as fast path, browser-use as full path** — no capability degradation
8. **E2B for LLM-generated code only** — safe commands (ls, git, cat) stay as subprocess
9. **All new services lazy-initialized** — graceful degradation if any dependency is missing, no crash
10. **LLM Council reconciliation** — average scores, detect disagreements, penalize confidence for contested dimensions
