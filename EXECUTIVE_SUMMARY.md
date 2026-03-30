# Mirai (未来) — Executive Summary

**AI-Powered Startup Prediction System with Multi-Model Council, Swarm Intelligence, and Market Simulation**

Version 0.11.0 | March 2026 | Created by Aditya Goyal | vclabs.org

---

## 1. What Mirai Is

Mirai is a full-stack AI system that evaluates startup viability using a combination of multi-model research, LLM council deliberation, crowd simulation via persona-based swarm intelligence, and forward-looking market trajectory modeling. The name "Mirai" (未来) means "future" in Japanese — the system's purpose is to predict whether a startup will succeed or fail.

A user submits a startup via the website form (122 industries, 789 keyword tags, 195 countries, structured fields for stage/funding/traction/team). Mirai then executes a 5-phase pipeline:

1. **Agentic Research** — OpenClaw primary (deep web research via subagent), Gemini grounded search fallback. Blind council scoring runs in parallel with research.
2. **11-Model Council Scoring** — Eleven LLMs across 8 model families independently score the startup across 10 weighted dimensions, with Karpathy 3-stage pattern (individual, peer review, chairman synthesis). Industry weights capped at 1.5x, no geographic or personality-based bias.
3. **Zone-Based Swarm Prediction** — 50 AI persona agents across 6 NVIDIA NIM models (8 concurrent workers), drawn from 88.5B+ persona combinations, evaluate from six zones (Investors, Customers, Operators, Analysts, Contrarians, Wild Cards). Equal deliberation weight, neutral geographic and behavioral lenses.
4. **OASIS Market Simulation** — A 4-round multi-month simulation where 12 swarm-sourced panelists react to LLM-generated market events, producing a sentiment trajectory with uncertainty bands. Auto-enabled on all analyses.
5. **HTML Report** — Professional report with inline charts, agent reasoning, competitive landscape, risk assessment, strategic recommendations, and market trajectory. Opens in new tab.

The output is a comprehensive investment analysis: a composite score out of 10, a verdict (Strong Hit / Likely Hit / Uncertain / Likely Miss / Strong Miss), dimension-by-dimension breakdowns, per-agent reasoning, competitive landscape analysis, risk assessment, strategic recommendations, and a 6-month market trajectory forecast — all exportable as a publication-ready PDF.

---

## 2. Architecture

Mirai runs as four coordinated subsystems:

```
Dashboard (port 5000)        Gateway (port 19789)        SearXNG (port 8888) / Brave Search API
    |                              |                          |
    | WebSocket: startAnalysis     | /v1/chat/completions     | /search?format=json  |  api.search.brave.com
    +----------------------------->|<-------------------------+-------------------->+
    |                              |                          |
    |  Phase 1: Multi-Model Research (Claude + GPT + Gemini parallel)
    |  Phase 2: Council (4 Elders score 7 dimensions)
    |  Phase 3: Swarm (zone-based personas, enriched with research context)
    |  Phase 4: OASIS (6-month market simulation)
    |  Phase 5: ReACT Report Agent (6 LLM-generated sections)
    |  -> analysisComplete (full data for PDF export)

Cortex (port 8100)
    |
    | 10-second heartbeat loop
    | Self-learning: ExperienceStore -> ReflectionEngine -> SkillForge
    | Browser automation (Playwright/CDP)
    | Gateway auto-start + watchdog
```

### 2.1 Mirai Gateway (Node.js, TypeScript — forked from OpenClaw, 5,500+ files)

The gateway is a forked and rebranded version of OpenClaw, serving as an LLM proxy and authentication layer. It runs on port 19789 and provides a unified OpenAI-compatible `/v1/chat/completions` endpoint that routes requests to multiple LLM providers:

- **Anthropic** (Claude Opus 4.6, Claude Sonnet 4.6) — via OAuth
- **OpenAI** (GPT-5.4) — via Codex OAuth
- **Google** (Gemini 3.1 Pro) — via Gemini CLI OAuth

The gateway handles authentication, rate limiting, and model routing. All backend LLM calls go through the gateway, meaning the backend never needs individual API keys — only the gateway manages provider credentials.

Configuration: `~/.mirai/mirai.json` (gateway settings), `~/.mirai/council.json` (model roster)

### 2.2 Flask Backend (Python — ~22,400 lines)

The backend is a Flask application serving both the REST API and WebSocket endpoint. Key modules:

| Module | File | Lines | Purpose |
|--------|------|-------|---------|
| Business Intelligence | `business_intel.py` | ~1,210 | Core 3-phase pipeline: extract, research, predict, plan |
| WebSocket Handler | `websocket.py` | ~630 | Real-time full pipeline orchestration |
| Swarm Predictor | `swarm_predictor.py` | ~590 | Multi-agent parallel prediction with persona assignment |
| Research Agent | `research_agent.py` | ~325 | Multi-model parallel web research |
| Persona Engine | `persona_engine.py` | ~437 | 1.6M persona selection and generation |
| Report Generator | `report_generator.py` | ~580 | PitchBook-quality HTML/PDF with SVG charts |
| Report Agent | `report_agent.py` | ~150 | ReACT-style LLM narrative section generation |
| OASIS Simulator | `oasis_simulator.py` | ~170 | 6-month multi-round market simulation |
| Data Enrichment | `data_enrichment.py` | ~190 | Competitor/company enrichment from 231K company DB |
| Funding Signals | `funding_signals.py` | ~140 | SearXNG news search for live funding rounds |
| Fact Checker | `fact_checker.py` | ~64 | Real fact verification against 5 sources (Brave + SearXNG + SEC EDGAR + Yahoo Finance + Jina) |
| Research Cache | `research_cache.py` | ~105 | Caches research results to avoid redundant fetches |
| Search Engine | `search_engine.py` | ~190 | SearXNG + Brave Search API integration |
| Web Researcher | `web_researcher.py` | ~360 | Crawl4AI + browser-use content extraction |
| LLM Client | `llm_client.py` | ~200 | OpenAI-compatible client with JSON parsing |
| Persona Data | `data/` | 538MB | 1.6M personas + 231K companies |

### 2.3 Cortex — Autonomous Agent (Python — ~139,000 lines incl. browser-use port)

The Cortex is an autonomous agent subsystem that runs independently of the dashboard. It operates on a 10-second heartbeat loop, making decisions, browsing the web, executing code, and triggering analyses without human intervention.

| Module | File | Lines | Purpose |
|--------|------|-------|---------|
| Cortex Loop | `mirai_cortex.py` | ~28,800 | Main heartbeat loop, action dispatch, LLM interface |
| Gateway Launcher | `gateway_launcher.py` | ~3,970 | Auto-starts gateway on boot, watchdog health checks |
| System Prompt | `system_prompt.py` | ~2,000 | LLM personality + 6 JSON action schemas |
| API Server | `api_server.py` | ~11,700 | HTTP bridge (port 8100) — browse, think, memory, objective |
| Sandbox Runner | `sandbox_runner.py` | ~7,530 | E2B sandbox — safe commands vs. sandboxed code execution |
| Browser Engine | `browser_engine/` | ~95,000 | Full browser-use port (Playwright, CDP, vision, 12+ LLM providers) |
| Learning System | `learning/` | ~4,000 | 4-loop self-learning (see Section 2.3.1) |

**Cortex Actions:**

| Action | Handler | Description |
|--------|---------|-------------|
| `browser_navigate` | browser-use Agent | Navigate + interact with web pages autonomously |
| `terminal_command` | E2B sandbox / subprocess | Execute shell commands (code to sandbox, safe to subprocess) |
| `swarm_predict` | HTTP to Flask `/api/predict/` | Wargame scenarios via MiroFish simulation |
| `analyze_business` | HTTP to Flask `/api/bi/analyze` | BI engine: research, predict, plan |
| `message_human` | `mirai message send` | Send WhatsApp messages to operator |
| `standby` | (no-op) | Idle state |

**Cortex API Server (port 8100):**

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

#### 2.3.1 Self-Learning System (4 Loops)

The Cortex learns from its own actions over time, with four loops that run at different cadences:

**Loop 1 — Experience (every cycle):**
- `ExperienceStore` (ChromaDB-backed) stores action-to-outcome pairs after every heartbeat cycle
- Before acting: `recall_similar(objective)` — semantic search for past experiences matching the current goal
- After acting: `store_experience(situation, action, outcome, success)` — record what happened
- Heuristic success detection: checks for "error", "failed", "blocked", "timed out" in outcome text

**Loop 2 — Reflection (every 50 cycles):**
- `ReflectionEngine` analyzes the last 50 experiences for patterns (what works, what fails)
- Updates a **strategy journal** — persistent self-learned rules injected into the system prompt
- Journal survives restarts (persisted to file), so lessons accumulate across sessions

**Loop 3 — Skill Gap Detection (on reflection):**
- `SkillForge` analyzes failure patterns to detect capability gaps
- Identifies recurring failure modes and suggests new capabilities

**Loop 4 — Market Radar (periodic):**
- `MarketRadar` monitors configured market signals on a schedule
- Surfaces market changes relevant to the current objective

#### 2.3.2 Gateway Management

The `GatewayLauncher` manages the Mirai Gateway lifecycle from within the Cortex:

| Feature | Behavior | When |
|---------|----------|------|
| Auto-start | Starts `gateway/mirai.mjs` as subprocess on configured port | On boot (if not already running) |
| Watchdog | `GET localhost:19789/health` — auto-restart if down | Every 10 heartbeat cycles |
| Direct messaging | `mirai message send --to [number] --message [text]` | On `message_human` action |

### 2.4 Dashboard (React/TypeScript — 10,367 lines)

A pixel art war room built with React, Canvas 2D, and Vite. Forked from pablodelucca/pixel-agents (MIT license). Key components:

| Component | File | Purpose |
|-----------|------|---------|
| SwarmScoreboard | `SwarmScoreboard.tsx` | Input form, phase progress, results display, PDF export |
| AgentLabels | `AgentLabels.tsx` | Hover tooltips, vote tags, agent chat modal |
| useSwarmAgents | `useSwarmAgents.ts` | Agent lifecycle: spawn, walk, vote, wander, sit |
| officeState | `officeState.ts` | Zone seat assignment, character management |
| renderer | `renderer.ts` | Canvas rendering, room labels, floor tiles |
| miraiApi | `miraiApi.ts` | REST + WebSocket client |
| generate-warroom.py | `scripts/` | 52x35 tile grid, 7 rooms, 165 furniture items |

### 2.5 Verification & Observability

Mirai v0.8.0 replaced LLM-circular fact-checking with a real verification pipeline grounded in external data sources:

- **Real Fact Verification** — Claims are verified against 5 independent sources: Brave Search API (free tier, 1,000 queries/month), SearXNG (self-hosted metasearch), SEC EDGAR (public filings), Yahoo Finance (market data), and Jina DeepSearch (optional deep web grounding). This eliminates the circular problem of asking an LLM to verify its own outputs.
- **Hallucination Guard** — TF-IDF traceability scoring compares generated report narratives against source research. If faithfulness drops below 0.6, the section is automatically re-synthesized from source material. Semantic dedup (TF-IDF cosine similarity) removes redundant findings before they enter the pipeline.
- **Prompt Registry** — All LLM prompts are version-tracked with SHA-256 hashes, enabling prompt regression testing (17 test cases, pure Python) and reproducible evaluations via the Mirai Eval Suite (LLM-as-judge, no deepeval dependency).
- **LLM Observability** — Every LLM call is logged to `~/.mirai/logs/llm_calls.jsonl` with model, provider, latency, token counts, and prompt hashes. A calibration pipeline tracks per-dimension, per-zone, and per-model accuracy over time.
- **Zero External Dependencies** — All verification, evaluation, and observability tooling is implemented in pure Python with no external package dependencies (removed semhash, deepeval, edgartools, yfinance, langfuse, promptfoo).

### 2.6 SearXNG (Docker, port 8888)

A self-hosted metasearch engine aggregating 70+ search engines via JSON API. Provides structured web search results for the research phase. Runs as a Docker container with custom settings enabling JSON format output.

---

## 3. The 5-Phase Pipeline (Deep Dive)

### Phase 1: Multi-Model Parallel Research

Three frontier LLMs research the startup simultaneously using `ThreadPoolExecutor(max_workers=3)`:

| Model | Provider | Focus |
|-------|----------|-------|
| Claude Opus 4.6 | Anthropic | Market analysis, regulatory landscape |
| GPT-5.4 | OpenAI | Competitors, funding landscape |
| Gemini 3.1 Pro | Google | Recent news, market trends |

**Process:**

1. Each model generates 4 targeted search queries via LLM (not hardcoded), tailored to the startup's industry
2. Brave Search API and SearXNG execute the queries, returning structured results from multiple sources
3. Crawl4AI extracts full-page content from the top results (with browser-use as fallback for dynamic pages)
4. Each model synthesizes its findings independently, producing a JSON structure with summary, competitors, facts, and trends
5. **Round 2 (Gap Analysis):** Claude Sonnet analyzes what's missing from the combined findings and generates 3 follow-up search queries
6. **Round 3 (Competitor Deep-Dive):** All named competitors are individually researched for funding, revenue, and valuation data
7. **Final Merge:** All findings across all models and rounds are deduplicated and merged into a unified `ResearchFindings` object

The key design decision: all three models research the same topics (not split by focus area). Each model brings different training data and different perspectives, so the same query yields different insights from Claude vs GPT vs Gemini. The merged output is richer than any single model could produce.

### Phase 2: 4-Elder Council Scoring

Four LLMs independently score the startup across 7 weighted dimensions:

| Dimension | Weight | What It Measures |
|-----------|--------|------------------|
| Market Timing | 20% | Is now the right time? Regulatory tailwinds, market maturity |
| Business Model Viability | 20% | Unit economics, revenue model, scalability |
| Competition Landscape | 15% | Incumbents, moat, defensibility |
| Pattern Match | 15% | Similarity to past successes/failures |
| Team Execution Signals | 10% | Founder experience, hiring, shipping velocity |
| Regulatory/News Environment | 10% | Legal risk, policy tailwinds/headwinds |
| Social Proof/Demand | 10% | Traction, testimonials, waitlist, press |

**Council Models:**

| Elder | Model | Provider |
|-------|-------|----------|
| 1 | Claude Opus 4.6 | Anthropic |
| 2 | Claude Sonnet 4.6 | Anthropic |
| 3 | GPT-5.4 | OpenAI |
| 4 | Gemini 3.1 Pro | Google |

Each Elder receives the full research context and scores all 7 dimensions independently (1-10 scale). The system then:

- Averages scores per dimension across all Elders
- Computes a weighted composite score
- Detects disagreements: if any dimension has a spread of 3+ points between models, it is flagged as **contested** (with a -0.05 confidence penalty per contested dimension)
- Produces a verdict: Strong Hit (>7.5), Likely Hit (>6.0), Uncertain (>4.5), Likely Miss (>3.0), Strong Miss (<=3.0)

### Phase 3: Zone-Based Swarm Prediction

The swarm is the core differentiator. 10 to 1,000 AI persona agents independently evaluate the startup, each from a unique perspective shaped by their persona, role, psychology, and geographic lens.

**Persona Pool: 1,638,443 Real-World Personas**

| Source | Count | Description |
|--------|-------|-------------|
| FinePersonas (Argilla/HuggingFace) | 1,200,000 | Real persona descriptions with labels |
| Tencent PersonaHub Elite | 238,443 | Top 1% domain experts |
| Tencent PersonaHub | 200,000 | General persona descriptions |
| Trait-Based Generator (fallback) | Unlimited | 60 roles x 16 MBTI x 5 risk profiles x 5 experience levels x 14 biases x 15 geographies x 26 industries |

Personas are selected by label relevance to the startup's industry using a pre-built label index. If dataset personas aren't available, the trait-based generator creates unique combinations from:

- **60 roles**: Angel Investor, Seed VC, Series-A VC, PE Partner, Target Customer (Enterprise/SMB/Consumer), CTO, CMO, VP Sales, Competitor CEO, Patent Attorney, Behavioral Economist, Market Strategist (McKinsey), Government Policy Advisor, etc.
- **16 MBTI types**: INTJ, ENTP, ISFJ, etc.
- **5 risk profiles**: Very Conservative to Very Aggressive
- **5 experience levels**: Junior (2-3 years) to Legendary (30+ years)
- **14 cognitive biases**: Optimistic about technology, skeptical of hype, focused on unit economics, contrarian thinker, etc.
- **15 geographic lenses**: Silicon Valley, London, Bangalore, Tel Aviv, Lagos, etc.
- **26 industry focuses**: SaaS, FinTech, HealthTech, DeepTech, AI/ML, etc.

**Zone System:**

Agents are assigned to 6 zones, each with a role-specific evaluation prompt that forces diverse perspectives:

| Zone | Example Roles | Evaluation Pressure |
|------|---------------|---------------------|
| Investors | Angel, VC, PE, Family Office, Hedge Fund | "Would you write a check? At what valuation?" |
| Customers | Target SMB/Enterprise, IT Director, Procurement | "Would you buy this? What's your willingness to pay?" |
| Operators | Failed/Successful Founder, CTO, CMO, VP Sales | "Would you quit your job to join? What's the execution risk?" |
| Analysts | Gartner, McKinsey, Academic, Economist, Journalist | "What does the data say? Where are the blind spots?" |
| Contrarians | Competitor CEO, Patent Attorney, Regulatory Expert, Risk Analyst | "Find the fatal flaw. Why will this fail?" |
| Wild Card | Random from all datasets | "React from your unique life experience" |

**Zone Distribution (for 25 agents):**
Investors: 6, Customers: 4, Operators: 4, Analysts: 3, Contrarians: 3, Wild Card: 5

**Execution:**
- **Wave 1**: Up to 100 individual LLM calls with unique detailed personas (25 parallel workers)
- **Wave 2**: Remaining agents batched (25 per call, 10 parallel workers)
- Models distributed round-robin across all logged-in providers
- Each agent receives: the executive summary, full research context, council verdict, zone-specific evaluation prompt
- Each agent returns: 4 sub-scores (market, team, product, timing), overall score (1-10), and detailed reasoning
- A vote of HIT (>= 5.5) or MISS (< 5.5) is derived from the overall score

**Output:** Positive/negative percentages, score distribution, key themes (positive and negative), contested themes, per-agent reasoning, zone-level breakdowns.

### Phase 4: OASIS Market Simulation

OASIS (Opinion and Sentiment Interactive Simulation) runs a 6-month forward-looking simulation:

1. A panel of 12 agents is sourced from the actual swarm panelists (not a separate hardcoded roster), preserving their persona perspectives from Phase 3
2. For each of 6 months:
   - Real market events are sourced via Brave Search API and SearXNG news queries specific to the startup's industry (replacing purely LLM-generated events)
   - All 12 agents evaluate whether the event IMPROVED or WORSENED their sentiment, with accumulated context from all previous months
   - Sentiment percentage is computed (% of agents who said IMPROVED), with uncertainty bands (confidence_low/high per round)
3. Output: Timeline of events and sentiment, overall trajectory (improving / stable / declining), start and end sentiment percentages, confidence intervals

The simulation runs with `ThreadPoolExecutor(max_workers=6)` for agent parallelism within each round, but rounds are sequential (each round sees the history of previous rounds).

### Phase 5: ReACT Report Agent

Six separate LLM calls generate professional report sections:

| Section | Word Target | Content |
|---------|-------------|---------|
| Executive Summary | 300 | Verdict, score, key strengths and weaknesses |
| Market Analysis | 500 | TAM, growth, regulatory landscape, timing |
| Competitive Landscape | 400 | Named competitors, positioning, defensibility |
| Risk Assessment | 400 | Top 3-5 risks with severity and mitigation |
| Strategic Recommendations | 400 | 5 actionable moves with effort, impact, timeline |
| Investment Verdict | 300 | Invest or pass, at what terms, milestone triggers |

**Anti-hallucination rules are enforced in every prompt and verified post-generation:**
- "Use ONLY facts from AVAILABLE DATA. Do NOT invent statistics."
- "If data unavailable, say so. Do NOT fabricate."
- "Name competitors. Cite specific numbers."
- "No markdown formatting. Plain flowing prose only."
- Generated sections are passed through the hallucination guard (TF-IDF faithfulness check); sections scoring below 0.6 are re-synthesized from verified source material.

Each section receives the full data context: extraction, prediction scores, research findings, swarm results (HIT/MISS reasons), plan risks and moves.

---

## 4. PDF Report

The final output is a PitchBook-quality PDF generated via WeasyPrint (HTML to PDF). The report includes:

1. **Cover/Highlights Page**: Score gauge (semicircle SVG), verdict badge, HIT/MISS donut chart, confidence, data quality, model count, agent count
2. **7-Dimension Scoring**: Color-coded horizontal bar chart (green >= 7, orange < 7, red < 5) with contested dimension warnings
3. **General Information**: Company, industry, product, target market, business model, stage — all extracted from the input
4. **Market Analysis**: Full LLM-generated narrative (~500 words)
5. **Competitor Table**: Up to 8 competitors enriched from the 231K company database with industry, status, and funding
6. **Competitive Position**: LLM narrative on positioning and defensibility
7. **Council Deliberation**: Per-dimension bars showing council consensus
8. **Swarm Analysis**: Full agent table grouped by zone, with per-zone HIT percentages, individual agent votes, scores, and complete reasoning
9. **OASIS Market Trajectory**: 6-month timeline table with events, sentiment percentages, and directional changes
10. **Risk Assessment**: Risk cards with severity labels (HIGH/MEDIUM)
11. **Strategic Recommendations**: Numbered move cards
12. **Investment Verdict**: Final thesis
13. **Actionable Improvements**: Auto-generated suggestions for dimensions scoring below 7
14. **Appendix D — Source Citations**: Cited facts traced through the verification pipeline with source URLs and confidence scores
15. **Footer**: Data sources, model count, agent count, timestamp

All charts are inline SVGs (no external dependencies). The PDF uses a professional navy/white color scheme inspired by PitchBook reports.

---

## 5. Dashboard and Visualization

### 5.1 Pixel Art War Room

A 52x35 tile grid rendered on HTML5 Canvas with 7 themed rooms:

| Room | Zone | Theme | Location |
|------|------|-------|----------|
| Room 1 | Investors | Boardroom (meeting table, formal desks) | Top-left |
| Room 2 | Customers | Lab (workstations, whiteboards) | Top-center |
| Room 3 | Operators | Operations bullpen (dense desks, PCs) | Top-right |
| Room 4 | Analysts | Library (bookshelves, study desks) | Bottom-left |
| Room 5 | Contrarians | War room (standing desks, displays) | Bottom-center-left |
| Room 6 | Wild Card | Creative lounge (sofas, coffee tables) | Bottom-center-right |
| Room 7 | Council | Council chamber (central round table) | Bottom-right |
| Corridor | — | Connecting hallway with room labels | Center row |

The layout is generated by `generate-warroom.py` which places 165 furniture items (desks, PCs, sofas, plants, bookshelves, whiteboards, paintings, coffee tables, clocks) in the original pixel-agents style with mirrored variants and proper spacing.

### 5.2 Agent Lifecycle

Each agent progresses through visual states on the canvas:

1. **Spawn**: Agent appears as a pixel character at their assigned zone seat position
2. **TYPE**: Character sits at desk with typing animation (during LLM evaluation)
3. **Active → Voted**: HIT/MISS tag appears above the character
4. **WALK/WANDER**: 5 seconds after voting, agent stands up and wanders the room for 30 seconds
5. **Sit**: Agent returns to seat and becomes idle

Special agents:
- **Research Agent** (ID 8888): Spawns during Phase 1, wanders between rooms
- **Council Elders** (IDs 9000-9003): Spawn during Phase 2 in the Council room

### 5.3 Scoreboard Panel

The right-side panel (`SwarmScoreboard.tsx`) provides:

- **Input Form**: Company, Industry, Product, Target Market, Business Model, Stage, Funding, Traction, Team, Ask, Competitive Advantage — all validated before submission
- **Smart Paste**: Paste raw pitch deck text → AI auto-fills all form fields via `/api/bi/validate`
- **Phase Progress Bar**: Research → Council → Swarm → Plan → OASIS → Report → Complete
- **Live Research Feed**: Round-by-round progress ("Researching in parallel...", "Synthesizing findings...", "Following up: ...")
- **Council Result**: Verdict badge, composite score, dimension scores
- **Swarm Consensus**: HIT/MISS percentages, total agents
- **OASIS Timeline**: Month-by-month sentiment with events and directional arrows
- **PDF Export Button**: Disabled until all phases complete (shows "GENERATING..." during pipeline)

### 5.4 Agent Interaction

- **Hover Tooltips**: Mouse over any agent to see persona name, zone, activity, vote, score, and full reasoning
- **Vote Tags**: HIT (green) or MISS (red) badges visible above each agent after voting
- **Agent Chat**: Click any agent post-analysis to open a chat modal. The conversation is routed via WebSocket to an LLM that role-plays as that specific persona, maintaining context of their original vote and reasoning

---

## 6. Data Infrastructure

### 6.1 Persona Datasets (538 MB total)

| Dataset | File | Records | Size | Source |
|---------|------|---------|------|--------|
| FinePersonas | `personas.jsonl` | 1,200,000 | 283 MB | Argilla/HuggingFace |
| Tencent PersonaHub Elite | `personahub_elite.jsonl` | 238,443 | 167 MB | Top 1% domain experts |
| Tencent PersonaHub | `personahub.jsonl` | 200,000 | 29 MB | General personas |
| Label Index | `label_index.json` | — | — | Pre-built industry matching index |

Persona selection uses label-based matching: the index maps industry keywords to line numbers in the JSONL files, enabling O(1) lookup of relevant personas without loading the full dataset into memory. `linecache` is used for random-access line reading.

### 6.2 Company Database (59 MB)

A SQLite database at `subconscious/swarm/data/companies.db` with 231,213 companies:

| Source | Companies | Data |
|--------|-----------|------|
| YC-OSS API | 5,690 | Name, industry, status, batch, outcome |
| Crunchbase Dataset 1 | ~66,000 | Name, industry, funding, status |
| Crunchbase Dataset 2 | ~160,000 | Name, industry, status |
| Unicorns 2021 | 534 | Name, valuation, industry |

22,818 companies have known outcomes (success/failure/acquired/IPO), enabling future backtesting of Mirai's predictions against historical results.

The company database is used in two ways:
1. **Competitor enrichment in PDF reports**: When a competitor is named, the DB is queried for industry, status, and funding data
2. **Pattern matching**: Historical companies in the same industry inform the council's pattern_match dimension

### 6.3 Action Logging

Every analysis is logged to a JSONL file at `~/.mirai/logs/swarm_YYYYMMDD_HHMMSS.jsonl`. Each line records one agent's complete evaluation: agent_id, persona, zone, vote, scores (market, team, product, timing, overall), full reasoning, and confidence. This enables:

- Post-hoc analysis of agent behavior
- Debugging score clustering
- Building training data for future model fine-tuning
- Accuracy tracking when outcomes are recorded via the feedback API

---

## 7. API Reference

### REST Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/bi/analyze` | Full analysis pipeline (research + predict + plan) |
| POST | `/api/bi/validate` | Extract and validate exec summary fields (used by Smart Paste) |
| POST | `/api/bi/report/pdf` | Generate PDF from analysis results |
| POST | `/api/bi/feedback` | Record actual outcome (HIT/MISS) for accuracy tracking |
| GET | `/api/bi/accuracy` | Accuracy statistics across all tracked predictions |
| GET | `/api/bi/history` | Past analyses from ChromaDB |
| GET | `/api/bi/template` | Input template and example |

### WebSocket Messages (`/ws/swarm`)

**Client to Server:**

| Message Type | Payload | Description |
|-------------|---------|-------------|
| `startAnalysis` | `{execSummary, agentCount, simulateMarket}` | Launch full 5-phase pipeline |
| `chatWithAgent` | `{agentId, message, persona, zone, previousVote, previousReasoning}` | Chat with specific agent |

**Server to Client (event stream):**

| Event Type | Phase | Key Data |
|-----------|-------|----------|
| `researchStarted` | 1 | — |
| `researchProgress` | 1 | `{round, message}` |
| `researchComplete` | 1 | `{factsCount, competitorsCount, sourcesCount}` |
| `councilStarted` | 2 | `{models}` |
| `councilComplete` | 2 | `{verdict, score, confidence, dimensions, contested}` |
| `swarmStarted` | 3 | `{agentCount, zones}` |
| `agentSpawned` | 3 | `{agentId, persona, zone, palette}` |
| `agentVoted` | 3 | `{agentId, vote, overall, scores, reasoning}` |
| `swarmComplete` | 3 | `{positivePct, negativePct, totalAgents, avgScores, themes}` |
| `planStarted` | — | — |
| `planComplete` | — | `{risks, moves}` |
| `oasisStarted` | 4 | `{rounds: 6}` |
| `oasisRound` | 4 | `{month, event, sentimentPct, change, quote}` |
| `oasisComplete` | 4 | `{trajectory, startSentiment, endSentiment, timeline}` |
| `narrativeStarted` | 5 | — |
| `analysisComplete` | Final | `{fullResult}` — complete data for PDF export |

---

## 8. Models and Providers

### Provider Authentication

All providers authenticate via OAuth through the Mirai Gateway:

| Provider | Auth Method | Credential Location |
|----------|-----------|---------------------|
| Anthropic | OAuth (manual + default profiles) | `~/.mirai/mirai.json` |
| OpenAI | Codex OAuth | `~/.mirai/mirai.json` |
| Google | Gemini CLI OAuth | `~/.gemini/oauth_creds.json` |

### Model Usage by Phase

| Phase | Models Used | Parallelism |
|-------|-----------|-------------|
| Research Query Generation | All 3 (one per model thread) | 3 parallel |
| Research Synthesis | All 3 (each synthesizes own findings) | 3 parallel |
| Gap Analysis | Claude Sonnet 4.6 (fast) | 1 |
| Council Scoring | All 4 Elders | 4 parallel |
| Swarm Agents | Round-robin across all 4 | 25 parallel workers |
| OASIS Events | Default model | 1 |
| OASIS Agent Votes | Default model | 6 parallel workers |
| ReACT Report Sections | Default model | 6 sequential |

---

## 9. Configuration

### `~/.mirai/council.json`

```json
{
  "council": {
    "models": [
      {"model": "anthropic/claude-opus-4-6", "label": "Elder 1"},
      {"model": "anthropic/claude-sonnet-4-6", "label": "Elder 2"},
      {"model": "openai-codex/gpt-5.4", "label": "Elder 3"},
      {"model": "google-gemini-cli/gemini-3.1-pro-preview", "label": "Elder 4"}
    ]
  },
  "swarm": {
    "models": [
      {"model": "anthropic/claude-opus-4-6"},
      {"model": "anthropic/claude-sonnet-4-6"},
      {"model": "openai-codex/gpt-5.4"},
      {"model": "google-gemini-cli/gemini-3.1-pro-preview"}
    ]
  }
}
```

### `~/.mirai/mirai.json`

Gateway configuration including:
- Port: 19789
- Chat completions endpoint enabled
- Auth profiles for all 3 providers
- Model aliases and routing rules

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_BASE_URL` | `http://localhost:19789/v1` | Gateway URL |
| `LLM_API_KEY` | `mirai-local-token` | Gateway auth token |
| `MIRAI_GATEWAY_PORT` | `19789` | Gateway port |

---

## 10. Installation and Deployment

### One-Line Install

```bash
git clone https://github.com/adityagoyal009/Mirai.git && cd Mirai && bash install.sh
```

`install.sh` handles: Python dependencies, Node.js 22, pnpm, gateway build (tsdown), dashboard build (Vite), npm link, and interactive onboarding (`mirai onboard`).

### Service Ports

| Port | Service | Process |
|------|---------|---------|
| 19789 | Mirai Gateway | `mirai gateway run --port 19789` |
| 8100 | Cortex API Server | Background thread in `mirai_cortex.py` |
| 5000 | Flask + Dashboard | `python3 -m flask --app subconscious/swarm run` |
| 8888 | SearXNG | Docker container |

### Docker

```bash
docker-compose up  # Starts all 3 services
```

### Project Structure

```
~/Downloads/mirai/
|-- gateway/           5,531 TypeScript files (LLM proxy)
|-- dashboard/           43 TypeScript/React files (pixel art UI)
|   |-- src/components/  SwarmScoreboard, AgentLabels, BottomToolbar
|   |-- src/hooks/       useSwarmAgents (agent lifecycle)
|   |-- src/office/      Canvas engine, officeState, renderer
|   |-- scripts/         generate-warroom.py (layout generator)
|-- subconscious/        54 Python files (backend)
|   |-- swarm/api/       websocket.py, business_intel.py
|   |-- swarm/services/  All engines (research, swarm, persona, OASIS, report)
|   |-- swarm/data/      538 MB (personas, companies)
|   |-- swarm/utils/     llm_client, logger
|   |-- memory/          ChromaDB, Mem0
|-- cortex/              Autonomous agent subsystem
|   |-- mirai_cortex.py  Main heartbeat loop, action dispatch
|   |-- api_server.py    HTTP bridge (port 8100)
|   |-- gateway_launcher.py  Auto-start + watchdog
|   |-- sandbox_runner.py    E2B sandbox routing
|   |-- learning/        ExperienceStore, ReflectionEngine, SkillForge, MarketRadar
|   |-- browser_engine/  Full browser-use port (Playwright, CDP, 12+ providers)
|-- docs/                Documentation
|-- install.sh           One-line installer
|-- docker-compose.yml   Multi-service deployment
```

---

## 11. Capability Stack (Optional Services)

These services integrate when available and degrade gracefully when not:

| Service | Purpose | Status |
|---------|---------|--------|
| SearXNG | Web search (70+ engines) | Active, required for research |
| Crawl4AI | Fast page extraction | Active, primary extraction path |
| Browser-Use (Playwright) | Full browser for dynamic pages | Fallback for Crawl4AI failures |
| Mem0 | Relationship-aware memory across analyses | Optional |
| OpenBB | Live financial data (stock prices, fundamentals) | Optional |
| CrewAI | Multi-agent parallel analysis | Optional (deep mode) |
| E2B Sandbox | Sandboxed code execution | Optional |
| ChromaDB | Episodic memory, analysis storage | Active |

---

## 12. Accuracy and Feedback Loop

Mirai includes a feedback system for tracking prediction accuracy:

1. **Record Outcome**: `POST /api/bi/feedback` with the analysis ID and actual outcome (HIT or MISS)
2. **Track Accuracy**: `GET /api/bi/accuracy` returns overall hit rate, per-dimension accuracy, and trend over time
3. **Action Logs**: Per-agent JSONL logs enable analysis of which persona types, zones, or models are most accurate
4. **Company Database**: 22,818 companies with known outcomes available for backtesting

The vision is to create a flywheel: as more predictions are tracked against outcomes, the system can learn which agent profiles and scoring rubrics are most predictive, enabling calibration of weights and prompts over time.

---

## 13. Codebase Statistics

| Metric | Count |
|--------|-------|
| Cortex Python lines | ~139,000 (incl. browser-use port) |
| Backend Python lines (subconscious) | ~22,400 |
| Gateway TypeScript files | 5,500+ (forked from OpenClaw) |
| Dashboard TypeScript/React lines | 10,367 |
| Git commits | 9 |
| Persona records | 1,638,443 |
| Company records | 231,213 |
| Data files | 538 MB |
| LLM providers | 3 (Anthropic, OpenAI, Google) |
| LLM models | 4 (Opus, Sonnet, GPT-5.4, Gemini 3.1 Pro) |
| Scoring dimensions | 7 |
| Swarm zones | 6 |
| War room rooms | 7 |
| OASIS simulation rounds | 6 |
| Report sections | 6 |
| Cortex actions | 6 (browse, terminal, swarm, BI, message, standby) |
| Cortex API endpoints | 9 |
| Backend API endpoints | 6 REST + 1 WebSocket |
| Self-learning loops | 4 (experience, reflection, skill forge, market radar) |
| Supported agent counts | 10, 25, 50, 100, 250, 500, 1000 |

---

## 14. What Makes Mirai Different

1. **Multi-model consensus, not single-model opinion.** Four LLMs from three providers score independently. Disagreements surface uncertainty rather than hiding it.

2. **Crowd intelligence at scale.** 1.6 million real-world personas, not generic "helpful AI assistant" responses. A Patent Attorney in Seoul evaluates differently than a Growth VC in Tel Aviv.

3. **Zone-based evaluation pressure.** Contrarians are explicitly told to find fatal flaws. Investors are asked about check-writing willingness. The zone system forces score diversity that a single prompt cannot achieve.

4. **Forward-looking simulation.** OASIS doesn't just score the startup today — it simulates how market events over 6 months could shift sentiment, producing a trajectory rather than a snapshot.

5. **Grounded in real research.** Three models search the live web simultaneously, crawl pages, and synthesize findings. The council and swarm receive this research as context, not just the founder's claims.

6. **Publication-ready output.** The PDF report is modeled on PitchBook private company profiles, with inline SVG charts, zone-grouped agent reasoning, and professional typesetting — ready to share with investors, advisors, or teams.

7. **Interactive post-analysis.** Click any agent to start a conversation. Ask the skeptical PE partner why they voted MISS. Ask the enterprise customer what price point would change their mind. The agent maintains its persona and context.

8. **Autonomous Cortex agent.** Unlike tools that only respond when asked, the Cortex runs a continuous 10-second heartbeat loop — browsing the web, executing code in sandboxed environments, triggering analyses, and sending messages without human prompting. It can pursue objectives autonomously.

9. **Self-learning system.** The Cortex learns from its own actions. An experience store records every action-outcome pair, a reflection engine distills patterns into strategy rules every 50 cycles, and a skill forge detects capability gaps from failure patterns. Lessons persist across restarts via a strategy journal injected into the system prompt — the system gets better at its job over time.

10. **Zero API key configuration.** The Mirai Gateway handles all provider authentication via OAuth. Users log in once during onboarding (`mirai onboard`) — the backend never touches API keys. Adding a new LLM provider means logging into it through the gateway, not editing config files.

11. **Graceful degradation.** Every optional service (Mem0, OpenBB, CrewAI, E2B, Crawl4AI) is lazy-initialized and fails silently. Mirai runs with just a gateway and SearXNG; each additional service enriches output without being a hard dependency.

12. **Built-in accuracy tracking.** The feedback API (`/api/bi/feedback`) lets users record actual outcomes against predictions. Combined with 22,818 companies with known outcomes in the company database, this creates the foundation for calibrating scoring weights and prompts against real-world results.

13. **Contextual persona curation.** The panel isn't random. A CleanTech startup automatically gets Impact Investor (climate), Environmental Compliance Officer, and a Farmer/Rancher. 10 industry mappings ensure the most relevant domain experts evaluate each startup.

14. **Divergence is the signal.** Critical Divergence analysis identifies which agents disagree most sharply with the consensus using z-score outlier detection. The gold is in the disagreements — when 20 agents say HIT but the patent attorney says MISS with a specific IP concern, that's the insight worth paying for.

15. **Investment committee deliberation.** After independent scoring, the most bullish and most bearish agents argue with each other in a simulated 2-round debate. A committee chair synthesizes the tension and renders a recommendation. Score adjustments from deliberation feed back into the final verdict. This produces richer, more nuanced assessment that's nearly impossible to replicate without the full persona + scoring infrastructure.

16. **Calibration flywheel.** Every report generates structured training data (per-agent JSONL logs with persona, zone, scores, reasoning). Over time, this enables questions nobody else can answer: which persona types are most predictive? Do contrarians catch risks that investors miss? Does deliberation improve accuracy? The architecture can be reverse-engineered. The calibration data requires volume and time.

---

## 15. Current Status and Roadmap

### Completed (v0.7.0)

**Core Pipeline:**
- Multi-model parallel research (Claude + GPT + Gemini)
- 4-model council across 3 providers with contested dimension detection
- Zone-based swarm (6 zones, role-specific evaluation prompts)
- OASIS 6-month market simulation with graduated scoring and agent-to-agent visibility
- ReACT report agent (6 LLM-generated professional sections)
- PitchBook-quality PDF with inline SVG charts

**Persona Engine (88.5B+ unique personas):**
- 11-dimension trait generator (142 roles, 16 behavioral MBTIs, 7 risk profiles, 7 experience levels, 22 biases, 28 geographic lenses, 26 industries, zone-specific fund contexts, 77 backstories, 58 decision frameworks, portfolio composition)
- Contextual persona curation (10 industry mappings with priority roles per zone)
- Role-experience compatibility filter, bias-framework anti-redundancy
- "Stay in your lane" domain focus directive

**Swarm Intelligence:**
- Consensus vs divergence highlighting (z-scores, zone agreement, critical outliers)
- Simulated deliberation (2-round investment committee debate + committee chair synthesis)
- Score adjustments from deliberation feed into final aggregation

**OASIS Simulation:**
- Graduated scoring (-2 to +2 adjustments, running scores with inertia)
- Agent-to-agent visibility (panel summary with bull/bear quotes)
- Anti-herding safeguards (minority amplification)

**Infrastructure:**
- Autonomous Cortex (heartbeat loop, self-learning, browser automation, gateway watchdog)
- 1.6M personas + 231K companies + SearXNG + Crawl4AI + OpenBB + Mem0 + CrewAI
- Feedback API for outcome tracking, action logging (JSONL)
- Backtest script with 30+ companies ready to run

### In Progress

- Zone seating, agent labels, floor tile colors (dashboard visual polish)

### Roadmap — Near Term

- Backtest validation on 30+ companies and publish accuracy
- Analysis history in dashboard
- Error states and loading time estimates
- Wire fact-checker into full pipeline

### Roadmap — Calibration & Accuracy

- Calibration analysis layer: which persona types are most predictive of actual outcomes?
- Track contrarian vs investor accuracy
- Measure deliberation impact on accuracy
- Calibrate dimension weights against real outcomes
- Scoring rubric tuning based on backtest results

### Roadmap — Investor-Specific Panel Weighting

- "Who are you pitching to?" dropdown (a16z, Sequoia, YC, climate fund, family office presets)
- Per-fund persona weighting: panel composition changes based on target investor
- Per-meeting prep tool: multiple runs per founder per fundraise (retention driver)

### Roadmap — Product Features

- "What to fix" diff: re-run with one assumption changed, show score delta
- Re-score swarm after OASIS events (dynamic stress test)
- Async analysis: submit via web form, get PDF in 24hrs via email
- Auth and rate limiting on dashboard

---

*Mirai (未来) — AI due diligence for startups, one swarm at a time.*
