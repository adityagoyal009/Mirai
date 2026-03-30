# Mirai Changelog

## [0.11.1] — 2026-03-30

### Changed — Queue Recovery, Internal API Hardening, Founder-Safe Status

**Swarm API Hardening**
- `/api/bi/analyze`, `/api/bi/job/{id}`, and `/api/report/share` now require an internal key for normal operation
- Internal auth key is `MIRAI_INTERNAL_API_KEY`, with `NEXTAUTH_SECRET` as the compatibility fallback
- No-key fallback mode only allows loopback callers
- Local fallback throttle now matches operating budget defaults: `50/day`, configurable via `MIRAI_ANALYSIS_RATE_LIMIT_MAX` and `MIRAI_ANALYSIS_RATE_LIMIT_WINDOW`
- Share-link creation now enforces a maximum HTML payload size before writing to disk

**Queue Reliability**
- Website queue startup recovery now reconstructs resumable `queued` and `reviewing` jobs from the database
- Mid-analysis submissions are reset to `queued` and automatically reinserted into the in-memory queue after restart
- Retry count is preserved from stored retry notes when resuming restart-safe jobs

**Founder Portal Safety**
- Founder dashboard and "my submissions" APIs now return sanitized `status_message` values instead of raw `admin_notes`
- Founder queue API now returns per-user positions only, rather than global pending submission IDs
- Dashboard UI now renders founder-safe status updates and user-specific queue positions

## [0.11.0] — 2026-03-30

### Added — Professional Form, Pipeline Bias Fixes, Full REST Parity

**Website Form Upgrade**
- 122 searchable industries (from 9), 789 keyword tags (max 15), 195 searchable countries
- 7 new fields: country, industry priority areas, keywords, has customers, generating revenue, currently fundraising, referral source
- New components: SearchableSelect (filterable dropdown), MultiSelect (searchable checkboxes with tags), RadioGroup (styled radio buttons)
- Accessibility: htmlFor/id labels, ARIA roles on custom selects, fieldset/legend on radio groups
- Backend: enum validation, URL format checks, 100K char limit, atomic Prisma transactions
- "None" mutual exclusivity in multiselect (selecting None clears others)

**20 Pipeline Bias Fixes**
- GEO_BEHAVIORAL rewritten: neutral market-context descriptions, no value judgments or stereotypes
- MBTI_BEHAVIORAL rewritten: analytical style only, removed all "score higher/lower" directives
- DELIBERATION_WEIGHT reduced 1.5 to 1.0 (equal weight for all agents)
- Verdict override removed: swarm divergence is now an advisory note, not a hard override
- Industry weights capped at 1.5x base (HealthTech/BioTech regulatory was 2.5x)
- Data quality penalty softened: cap raised 0.5 to 0.6, verdicts no longer downgraded
- Stage vocabulary normalized: single `normalize_stage()` maps form/extraction/calibration vocabularies
- Stage and data_quality now wired through analyze() to predict() and swarm.predict()
- ChromaDB scoped to current submission (was searching all collections, cross-tenant leak)
- Prompt injection containment: exec_summary wrapped in `<user_input>` tags in all LLM prompts
- target_market bug fixed: was passing product text instead of actual target market

**REST API Matches Dashboard Pipeline**
- Structured fields passthrough from website form (skips lossy LLM extraction)
- Blind scoring runs in parallel with research (same as dashboard WebSocket path)
- OpenClaw agentic research primary, Gemini fallback, BI built-in fallback
- Council: 11 models deep mode with blind score cache
- Swarm: 50 agents with enriched context and research_data
- OASIS market simulation: auto-enabled, uses swarm agents as panelists
- HTML report generation via generate_html_report()

**Async Job Pattern**
- `/api/bi/analyze` returns job_id immediately (no more dropped connections)
- `/api/bi/job/{id}` polling endpoint (website polls every 15s)
- Analysis queue: 3 retries, 10s delay, health check, 60 min timeout

**Reliability Fixes**
- Claude CLI timeout increased to 7 minutes (research synthesis takes 5-7 min)
- Swarm workers reduced 15 to 8 (stays under NVIDIA NIM 40 RPM limit)
- OpenClaw health check hits /health instead of /v1/models (was failing on auth scope)
- Report generator: fixed import (ReportGenerator class to generate_html_report function)
- Trends join TypeError fix in plan phase (dict items in list)
- Startup recovery: stuck "reviewing" submissions reset to "queued" on server restart

**Cleanup**
- Deleted oasis_profile_generator.py (dead code, never imported by pipeline)
- Removed broken imports from __init__.py and simulation_manager.py
- Removed 6 sensitive/demographic keywords from form options

## [0.9.0] — 2026-03-25

### Changed — Flask→FastAPI, claude-proxy, 10 Dimensions, Dual Research

**Backend Migration**
- Migrated from Flask+flask-sock to **FastAPI** with native async WebSocket
- Fixed critical broadcast race condition — analysis messages were silently lost due to monkey-patch/restore pattern in daemon threads
- Permanent broadcast patch in lifespan context manager
- Fixed `asyncio.get_event_loop()` deprecation (4 occurrences → `get_running_loop()`)
- Fixed PDF endpoint returning JSON metadata instead of actual PDF bytes

**claude-proxy Integration (Zero-Cost LLM)**
- Replaced OpenClaw gateway (port 18789) and Mirai gateway (port 19789) with **claude-proxy** (port 4000)
- All LLM calls now route through existing Claude Code, ChatGPT Plus subscriptions — zero API cost
- Council models: Claude Opus 4.6, Claude Sonnet 4.6, GPT-5.4, GPT-5.3 Codex
- Removed all `anthropic/`, `openai-codex/`, `google-gemini-cli/` model name prefixes
- Unified JSON enforcement via prompt injection (no more `response_format` incompatibility)

**Dual-Model Parallel Research**
- Agentic researcher rewritten — runs **Claude Opus 4.6-web + GPT 5.4-web in parallel**
- Both independently search the web and research the startup using built-in web search
- Findings merged with deduplication (competitors, facts, sources, trends)
- ~20-30s total (parallel) instead of 2+ min (sequential 5-iteration tool-call loop)
- Old manual action loop (search/fetch/done JSON) replaced with native web search

**10-Dimension Scoring**
- Added 3 new dimensions: `capital_efficiency`, `scalability_potential`, `exit_potential`
- Updated weights, correlated pairs, industry adjustments, and fact-check keyword mappings
- Chairman prompt updated for 10 dimensions
- `max_tokens` increased from 3000 to 4500 for scoring calls
- JSON repair for truncated LLM responses (closes incomplete JSON brackets)

**Removed SearXNG + ChromaDB**
- Deleted `web_researcher.py` (SearXNG-based BI research — all engines were suspended/dead)
- Deleted `funding_signals.py` (SearXNG news search — redundant with agentic researcher)
- `search_engine.py` gutted to utility-only (SOURCE_CREDIBILITY, _extract_root_domain) with no-op stub
- Replaced ChromaDB research cache with **file-based JSON cache** (~/.mirai/research_cache/)
  - Instant reads (vs 16s ChromaDB cold-start), no Rust panics, no SQLite corruption
  - Fixed cache hit logic: `hasattr(dict, 'summary')` (always False) → `'summary' in dict`

**PDF Report Audit**
- LLM auto-audit (Opus 4.6) runs on every PDF before download
- Programmatic layer: fixes "7→10 dimensions", "Ai" industry bug, detects empty fields/pages
- LLM layer: reads report text, returns find/replace fixes for inconsistencies and garbled text

**Frontend**
- Start Analysis button: added running/connected guards, disabled during analysis, shows status
- Batched `setSpawnedIds` (500ms debounce) — no more agent count flickering (40→23→40)
- Council elders: 4 → 8 pixel agents, persist through swarm phase
- Council room: tables+chairs replaced with sofa arrangement, 8 seats
- "Elders scoring 7 dimensions" → "Elders scoring 10 dimensions"

**Extraction & Report**
- Full extraction fields now passed to report (website, location, revenue, team, funding, known_competitors)
- Competitor industry matching improved (no more false "Ai" from keyword `ai` in snippets)
- Data sources updated: "SearXNG" → "Brave Search"

## [0.8.3] — 2026-03-24

### Changed — OpenClaw Research Integration

**Root cause**: BI engine research produced "formatted emptiness" — SearXNG returned 3 shallow results with fake 0.0 relevance, Crawl4AI extracted 6K chars from static pages only. PDF reports had broken sections (market size "$.T", competitor table all "—", no funding data).

- **New gateway_client.py** — thin Python client for OpenClaw's web_search (Brave, 10 results, real 0-1 relevance) and web_fetch (Readability.js, 30K chars, handles JS sites)
- **research_agent.py** now uses gateway as primary search+extract, with SearXNG+Crawl4AI as automatic fallback
- Search results increased from 3 to 10 per query, content extraction from 6K to 30K chars per page
- Cited facts attribution improved — uses gateway's siteName field instead of naive domain string matching
- Competitor deep-dive gets richer data (30K char pages vs 1.5K snippets)

## [0.8.2] — 2026-03-24

### Fixed — Persona System Overhaul (Audit-Driven)

**Root cause**: Persona audit revealed PERSONA_POOL was dead code, Wave 2 agents got no persona depth,
1.6M dataset was 48% educators, contrarian zone had hardcoded pessimistic prior, zone distribution was fixed.

**Must Fix**
- Deleted 116 lines of dead PERSONA_POOL code (never used, all personas come from PersonaEngine)
- Upgraded Wave 2 batch agents to use PersonaEngine-generated persona briefs (same depth as Wave 1)
- Removed contrarian pessimistic prior ("default to 5 or below") — now scores based on risk survivability
- Adaptive zone distribution — 12 industry-specific zone splits (B2C gets more customers, deeptech more operators)

**Should Fix**
- Pre-filtered 1.6M persona datasets into business_personas.jsonl (151K business-relevant entries, zone-tagged)
- Dataset personality injection — generated personas get human texture from dataset descriptions
- Semantic role dedup — "Series-B VC" and "Growth-Stage VC" now treated as same role group

**New Dimensions (16 total, up from 11)**
- Investment thesis style: thesis-driven / opportunistic / relationship-led / data-driven / contrarian
- Technical depth: deep-technical / business-oriented / generalist
- Failure scar tissue: overhyped market / bad team / regulation / competition / scaling / none
- Network strength: highly-connected / moderate / outsider
- Decision speed: fast-conviction / methodical / consensus-builder

**Updated combinatorics**: ~2.6 quadrillion unique personas per zone (was ~3.2 trillion)

## [0.8.1] — 2026-03-24

### Fixed — Scoring Pipeline Overhaul (Audit-Driven)

**Root cause**: Full pipeline audit (2026-03-24) revealed systematic score clustering into the 5.5-7.0 range
due to research anchoring, missing calibration anchors, persona bias, and conservative verdict blending.

**Tier 1: Rating Accuracy**
- Calibrated scoring rubrics — each dimension now has concrete anchor examples (what 2/4/6/8/10 looks like). Reasoning-before-score instruction reduces anchoring.
- Two-pass council scoring — models score exec summary blind FIRST, then adjust after seeing research (breaks research anchoring).
- Balanced persona scoring — added calibration anchors ("Use the FULL 1-10 range") to individual and batch agent prompts.
- Confidence-weighted verdict blending — council and swarm verdicts combined by confidence weight (replaces "conservative wins" rule that systematically underrated startups).

**Tier 2: Structural**
- Dimension correlation penalty — correlated dimension pairs (e.g., market_timing <-> social_proof_demand) automatically de-weighted 50% when scores are within 1 point, preventing double-counting of correlated signals.
- OASIS wired into verdict — declining 6-month trajectory downgrades optimistic verdicts to Mixed Signal; improving trajectory upgrades pessimistic ones.
- Data quality gates — low-data startups (data_quality < 0.5) get wider "uncertain" band instead of false precision on extreme verdicts.
- Deliberation prompt reordered — agents state their position BEFORE seeing consensus (reduces groupthink anchoring).

**Tier 3: Efficiency**
- Deliberation weight reduced 3.0 -> 1.5 (was over-amplifying outlier extremes with negligible accuracy benefit).
- Wave 2 batch prompt unified with Wave 1 quality (role-specific language requirement, zone assignment, calibration anchors).

## [0.8.0] — 2026-03-24

### Added — Credibility Overhaul (Phases A-E)

**Phase A: Fixed Broken Foundations**
- Source credibility scoring fix — position-based fallback when SearXNG returns score=0.0. Exact domain matching via urlparse.
- Research query independence — fallback queries differentiated by model focus (market/regulatory, competitors/funding, news/trends).
- Semantic research synthesis — LLM cross-references 3 model findings into {confirmed_facts, contradictions, unique_insights, coverage_gaps}.
- Full-swarm divergence — z-score analysis now runs on ALL agents (Wave 1 + Wave 2), not just first 100.
- Weighted deliberation — committee members get DELIBERATION_WEIGHT=3.0 in aggregation. Configurable.
- Anonymized council labels — models labeled "Evaluator A/B/C/D" during reconciliation to prevent brand bias.

**Phase B: Real Fact Verification**
- Brave Search integration — free tier (1,000 queries/month) for high-priority research queries with real relevance scores.
- Real fact-checker — Brave + SearXNG + SEC EDGAR + Yahoo Finance + Jina DeepSearch verify quantitative claims against real sources. Replaces LLM-asking-LLM circular verification.
- Gateway web_fetch — content extraction via OpenClaw gateway's built-in Readability.js (no Firecrawl API needed).
- Source citation tracking — cited_facts with {text, source_url, source_domain, confidence} flows through entire pipeline. Appendix D in PDF report.

**Phase C: OASIS Grounded in Reality**
- Real market events — OASIS sources news from Brave Search + SearXNG instead of LLM imagination. Falls back to "No significant market event" instead of fabricating.
- Swarm-sourced OASIS agents — 12 panelists selected from actual swarm (strongest bull/bear, per-zone reps). Initial scores from swarm, not neutral 5.0.
- Uncertainty quantification — confidence_low/confidence_high bands per OASIS round based on agent score std_dev.

**Phase D: Observability & Calibration**
- Prompt registry — VERSION + SHA-256 hash per critical prompt. Correlates accuracy changes with prompt versions.
- Hallucination guard — TF-IDF traceability check on research synthesis. Claims with specific numbers not traceable to sources flagged as [LLM-INFERRED]. Re-synthesis if faithfulness < 0.6.
- LLM observability — every call logged to ~/.mirai/logs/llm_calls.jsonl (model, latency, tokens, success, JSON parse result).
- Calibration pipeline — backtest tracks accuracy by dimension, persona zone, and model. Stores results with git commit + prompt hashes.

**Phase E: Evaluation & Testing**
- Mirai Eval Suite — LLM-as-judge metrics (faithfulness, relevancy, council grounding, persona adherence). No external framework.
- Prompt regression tester — 17 test cases across 6 prompts. JSON validity, score ranges, required fields. Run: python -m subconscious.swarm.prompts.test_prompts
- Semantic dedup — TF-IDF cosine similarity replaces set-based dedup for research facts.
- Jina DeepSearch grounding — factuality score (0-1) with evidence references for high-uncertainty claims.

### Changed — Zero External Dependencies
- Removed semhash → replaced with 35-line TF-IDF cosine dedup (stdlib only)
- Removed deepeval → replaced with Mirai-owned LLM-as-judge eval suite
- Removed edgartools → replaced with direct SEC EDGAR REST API calls
- Removed yfinance → replaced with direct Yahoo Finance HTTP calls
- Removed langfuse → file-based JSONL logging retained
- Removed promptfoo → replaced with Python prompt regression tester

### New Files
- subconscious/swarm/services/brave_search.py
- subconscious/swarm/services/hallucination_guard.py
- subconscious/swarm/prompts/ (6 prompt files + registry)
- subconscious/swarm/prompts/test_prompts.py
- subconscious/swarm/validation/eval_suite.py
- subconscious/swarm/utils/prompt_registry.py

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
