# Mirai — Open Source Ecosystem Research

> What exists in the wild that could enhance Mirai's startup prediction pipeline.
> Research date: 2026-03-30

---

## Tier 1: Upgrade the Research Phase (Biggest Impact)

Mirai's research is currently OpenClaw sub-agent with web_search/web_fetch, falling back to Gemini. These projects could dramatically upgrade research quality.

### 1. GPT Researcher — Deep Research Agent (assafelovic)
- **Repo:** github.com/assafelovic/gpt-researcher
- **What:** Autonomous deep research agent. Produces detailed, factual, unbiased research reports with citations. Supports any LLM provider.
- **Stars:** Very large community
- **How it helps Mirai:** Replace or augment the agentic_researcher with GPT Researcher's multi-step research methodology. It plans sub-queries, searches in parallel, scrapes pages, synthesizes findings, and generates structured reports — all autonomously.
- **Integration idea:** Use GPT Researcher as Mirai's Phase 1 research engine. Feed its output into the council/swarm. Would give much richer context than current single-pass OpenClaw research.

### 2. Open Deep Research (LangChain) — Configurable Research Agent
- **Repo:** github.com/langchain-ai/open_deep_research
- **What:** Fully open source deep research agent. Works across model providers, search tools, and MCP servers. Performance matches top deep research agents (Deep Research Bench leaderboard).
- **How it helps Mirai:** More configurable than GPT Researcher. Supports MCP which means we could plug in custom tools. Could replace agentic_researcher while keeping our model routing.

### 3. Crawl4AI — LLM-Friendly Web Scraper
- **Repo:** github.com/unclecode/crawl4ai
- **What:** Open-source web crawler designed specifically for LLM consumption. Parallel crawling, structured data extraction, no API keys needed.
- **How it helps Mirai:** When OpenClaw's web_fetch hits Cloudflare 403s (our current pain point), Crawl4AI with its browser-based crawling could handle those protected sites. Could run as a fallback scraper.
- **Integration idea:** Add as a research tool alongside OpenClaw. Route Cloudflare-protected URLs through Crawl4AI.

### 4. DeerFlow (ByteDance) — Long-Horizon SuperAgent
- **Repo:** github.com/bytedance/deer-flow
- **What:** Open-source long-horizon agent that researches, codes, and creates. Sandboxes, memories, tools, sub-agents, message gateway.
- **How it helps Mirai:** Their approach to long-horizon research tasks (tasks taking minutes to hours) is exactly what startup due diligence needs. Could inform how we structure multi-phase research.

### 5. Tongyi Deep Research (Alibaba)
- **Repo:** github.com/Alibaba-NLP/DeepResearch
- **What:** Leading open-source deep research agent. Includes WebWalker, WebDancer, WebSailor — specialized web agents for different research needs.
- **How it helps Mirai:** Their specialized web agents (traversal, seeking, navigation) could handle different types of startup research more effectively than a single generic agent.

---

## Tier 2: Knowledge & Memory (Make the Swarm Smarter)

### 6. Microsoft GraphRAG — Knowledge Graph RAG
- **Repo:** github.com/microsoft/graphrag
- **What:** Graph-based RAG that builds hierarchical knowledge graphs from text. Dramatically better than naive vector search for complex queries.
- **Stars:** Massive (Microsoft-backed)
- **How it helps Mirai:** Build a knowledge graph from all past research/analyses. When evaluating a new startup, query the graph for related companies, market patterns, competitor insights. The swarm gets smarter over time because it has institutional memory.
- **Integration idea:** After each analysis, extract entities (companies, markets, technologies, people) and relationships into a GraphRAG index. Query it during research phase to enrich context.

### 7. Mem0 — Production AI Agent Memory
- **Repo:** Already in Mirai (mem0_store.py exists)
- **What:** Scalable long-term memory for AI agents.
- **Current status:** Partially integrated. Could be used more aggressively.
- **Enhancement:** Feed council scores, swarm verdicts, and actual outcomes back into Mem0. Build a calibration feedback loop — "last time the swarm scored a similar company 6.5, it ended up failing because X."

### 8. Cognee — Knowledge Graphs for LLM Reasoning
- **Repo:** Referenced in Awesome-GraphMemory
- **What:** Optimizes the interface between knowledge graphs and LLMs for complex reasoning.
- **How it helps Mirai:** Could power the "institutional memory" for the swarm — relationships between industries, funding patterns, founder backgrounds that predict success.

### 9. Zep — Temporal Knowledge Graph for Agent Memory
- **Repo:** Referenced in agent memory research
- **What:** Temporal knowledge graph architecture. Tracks how knowledge changes over time.
- **How it helps Mirai:** Track how a startup's trajectory changes between evaluations. "We evaluated them 3 months ago at 5.2, they've since raised a Series A and pivoted."

---

## Tier 3: Pitch Deck & Document Analysis

### 10. PitchPilot — AI Pitch Deck Analyzer
- **Repo:** github.com/Akshat2634/PitchPilot-AI-Powered-Investor-Deck-Analyzer-Coach
- **What:** Reviews pitch decks, provides actionable feedback, simulates investor Q&A. Uses LangGraph.
- **How it helps Mirai:** Add pitch deck upload as an input. Extract structured data from decks (team, market, traction, ask) and feed into the analysis pipeline. Currently Mirai only takes text exec summaries.
- **Integration idea:** New input mode: upload a PDF pitch deck -> extract structured info -> feed to research + council.

### 11. Multi-Agent Pitch Deck Analyzer
- **Repo:** github.com/rk-vashista/pitch
- **What:** Multi-agent AI technology for pitch deck analysis. Comprehensive feedback on structure, content, improvements.
- **How it helps Mirai:** Their multi-agent approach to deck analysis maps to our council concept. Could add a "deck quality" dimension to scoring.

---

## Tier 4: Data Sources & Intelligence

### 12. OpenBook — Open Source PitchBook Alternative
- **Repo:** github.com/iloveitaly/openbook
- **What:** Open source investor/venture capital database. Like PitchBook but free.
- **How it helps Mirai:** Enrich research with investor data. "Who has invested in similar companies? What's the typical check size for this space? Which VCs are active in this vertical?"
- **Integration idea:** Query OpenBook during research phase to provide investor landscape context to the swarm.

### 13. TrendScan (Bright Data) — Multi-Source Company Intelligence
- **Repo:** github.com/brightdata/trendscan
- **What:** Automated collection + AI analysis from Crunchbase, LinkedIn, Reddit, Twitter/X. Uses MCP.
- **How it helps Mirai:** Multi-source intelligence pipeline. LinkedIn for team analysis, Reddit for product sentiment, Crunchbase for funding history. All structured.
- **Integration idea:** Run TrendScan-style multi-source collection before the swarm phase. Give personas richer, multi-angle context.

### 14. Crunchbase Scrapers — Funding Data
- **Repos:** Various (luminati-io/crunchbase-scraper, etc.)
- **How it helps Mirai:** Automated funding round data, investor lists, company comparisons. Could replace manual exec summary data entry with automated Crunchbase lookups.

### 15. EdgarTools — SEC Filing Analysis
- **Repo:** github.com/dgunning/edgartools
- **What:** Structured access to SEC EDGAR filings, financial statements, insider trades.
- **How it helps Mirai:** For post-revenue startups or public comp analysis. Feed real financial data into the council instead of relying on LLM estimates.

---

## Tier 5: Swarm & Simulation Enhancements

### 16. OASIS (CAMEL-AI) — Million-Agent Social Simulation
- **Repo:** github.com/camel-ai/oasis
- **What:** THE framework that powers MiroFish. Simulates up to 1M agents with 23 social actions (following, commenting, reposting, liking, etc.). Real-time adaptation.
- **How it helps Mirai:** Mirai's OASIS phase is inspired by this but simplified. Integrating the actual OASIS framework could unlock:
  - True social network dynamics (agents influence each other through network effects)
  - Interest-based recommendation systems
  - Hot-score-based content propagation
  - Scale to 10,000+ agents without custom infra
- **Integration idea:** Replace Mirai's custom OASIS simulation with CAMEL-AI's OASIS for the market simulation phase. Massive quality upgrade.

### 17. CAMEL Framework — Multi-Agent Communication
- **Repo:** github.com/camel-ai/camel
- **What:** The underlying multi-agent framework. Role-playing, tool use, structured communication between agents.
- **How it helps Mirai:** Could improve swarm deliberation quality. CAMEL has sophisticated agent-to-agent communication protocols that our current debate rounds lack.

### 18. MiroFish (Original) — Study the Source
- **Repo:** github.com/666ghj/MiroFish
- **What:** The original swarm intelligence prediction engine. Mirai was inspired by this. Backed by Shanda Group.
- **What to study:** Their "God's-eye view" variable injection, parallel world construction from seed materials, GraphRAG integration for long-term memory. See what they've added recently that we haven't.

---

## Tier 6: Calibration & Validation

### 19. ML Startup Success Prediction (RyanFabrick)
- **Repo:** github.com/RyanFabrick/ML-Startup-Success-Prediction
- **What:** Full-stack ML startup predictor using 50K+ company dataset (1990-2015). XGBoost, SHAP interpretability.
- **How it helps Mirai:** Their dataset and feature engineering could calibrate our swarm. Cross-validate: does our swarm consensus correlate with their ML predictions? Use their features (funding, age, location, team size) as structured inputs.
- **Key insight:** Most important features: funding_total_usd, founded_year, time_first_to_last_funding, international presence.

### 20. Startup Classification (ntdoris)
- **Repo:** github.com/ntdoris/startup-classification
- **What:** 80% recall, 73% ROC AUC on startup success/failure classification.
- **How it helps Mirai:** Benchmark our swarm against traditional ML. If our swarm can't beat 73% AUC, the LLM approach isn't adding value over basic features.

### 21. Deep Research Bench
- **Repo:** github.com/Ayanami0730/deep_research_bench
- **What:** Comprehensive benchmark for deep research agents. Leaderboard comparing research quality.
- **How it helps Mirai:** Benchmark our agentic_researcher against the leaderboard. See where we rank vs GPT-5, Claude, etc. on research quality.

---

## Priority Recommendations (What to Add First)

### Highest ROI (Do These First)

1. **GraphRAG** — Give Mirai institutional memory. Every analysis makes the next one smarter. This is the single biggest quality upgrade possible.

2. **GPT Researcher or Open Deep Research** — Replace/augment the agentic_researcher. Current single-pass research misses too much. Multi-step autonomous research is dramatically better.

3. **Pitch Deck Upload** — New input mode. Founders have decks, not exec summaries. Lower the barrier to use Mirai.

4. **OASIS Integration** — Upgrade the market simulation phase with the real OASIS framework instead of our simplified version.

### Medium Priority (Next Quarter)

5. **Crawl4AI** — Fix the Cloudflare 403 problem. Better web scraping = better research.

6. **OpenBook + Crunchbase Data** — Investor landscape intelligence. "3 of the top 5 VCs in this space have already passed on similar companies."

7. **Calibration Dataset** — Use the 50K+ startup dataset to validate swarm predictions against real outcomes.

8. **Mem0 Feedback Loop** — Feed outcomes back. Track prediction accuracy over time. Self-improving system.

### Lower Priority (Future)

9. **TrendScan Multi-Source** — LinkedIn + Reddit + Twitter intelligence pipeline.
10. **EdgarTools** — For post-revenue / public company analysis.
11. **CAMEL Framework** — Improve deliberation quality.
12. **Temporal Knowledge Graph (Zep)** — Track companies over time.

---

## What Makes Mirai Unique (Protect This)

After reviewing the ecosystem, Mirai's differentiators:

1. **5-phase pipeline** — No other project combines research + council + swarm + market sim + report in one system
2. **Multi-model council** — 10+ models scoring independently, with peer review and chairman synthesis
3. **Personality-typed swarm** — 1.6M persona pool with MBTI, experience, biases — not generic agents
4. **Detect-to-treat paradigm** — The calibration flywheel (predictions -> outcomes -> improvement)
5. **Free compute** — $0 API costs via subscription CLIs + free tier APIs
6. **PitchBook-quality PDF reports** — Professional output, not just scores

None of the projects above do ALL of these. TradingAgents does multi-agent but no swarm. MiroFish does swarm but no structured due diligence. GPT Researcher does research but no multi-agent evaluation. Mirai combines all of them.

---

## Key Repos Quick Reference

| Project | Category | Use For | GitHub |
|---------|----------|---------|--------|
| GPT Researcher | Deep Research | Upgrade Phase 1 | assafelovic/gpt-researcher |
| Open Deep Research | Research Agent | Alternative to above | langchain-ai/open_deep_research |
| GraphRAG | Knowledge Graph | Institutional memory | microsoft/graphrag |
| OASIS | Social Sim | Upgrade Phase 4 | camel-ai/oasis |
| Crawl4AI | Web Scraping | Fix 403 problem | unclecode/crawl4ai |
| PitchPilot | Deck Analysis | New input mode | Akshat2634/PitchPilot... |
| OpenBook | VC Database | Investor landscape | iloveitaly/openbook |
| EdgarTools | SEC Data | Financial grounding | dgunning/edgartools |
| FinBERT | Sentiment | Fast pre-filter | ProsusAI/finBERT |
| TrendScan | Multi-Source Intel | Enrich research | brightdata/trendscan |
| ML Startup Prediction | Calibration | Validate swarm | RyanFabrick/ML-Startup... |
| Mem0 | Agent Memory | Feedback loop | Already in Mirai |
| MiroFish | Swarm Engine | Study + learn | 666ghj/MiroFish |
| DeerFlow | Long-Horizon Agent | Research patterns | bytedance/deer-flow |

---

*Next: Adi prioritizes which enhancements to build. GraphRAG + better research = biggest bang for effort.*
