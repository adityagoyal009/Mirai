# Mirai TODO

## Completed
- [x] Multi-model parallel research (Claude + GPT + Gemini)
- [x] 5-model council (3 providers)
- [x] Zone-based swarm (6 zones, role-specific prompts)
- [x] OASIS 6-month market simulation
- [x] ReACT report agent (6 LLM sections)
- [x] Agent chat (post-analysis follow-up)
- [x] PitchBook-quality PDF with SVG charts
- [x] 7-room pixel art war room with zone labels
- [x] 1.6M personas (FinePersonas + Tencent PersonaHub)
- [x] 231K company database for backtesting
- [x] SearXNG web search integration
- [x] Funding signals service (live funding round discovery)
- [x] Iterative research (3 rounds)
- [x] Action logging (JSONL)
- [x] Agent vote tags (HIT/MISS visible)
- [x] Research agent pixel character
- [x] Live research feed in scoreboard
- [x] OASIS timeline in dashboard + PDF
- [x] PDF export waits for full pipeline completion
- [x] Gemini OAuth integration
- [x] Autonomous Cortex (10-second heartbeat loop)
- [x] Self-learning system (experience store, reflection engine, skill forge, market radar)
- [x] Cortex API server (port 8100, HTTP bridge)
- [x] Gateway auto-start + watchdog from Cortex
- [x] E2B sandboxed code execution (Firecracker microVMs)
- [x] Browser automation (Playwright/CDP, persistent sessions)
- [x] Data enrichment from company database
- [x] Research caching
- [x] Feedback API for accuracy tracking
- [x] Mem0 hybrid memory (relationship-aware)
- [x] OpenBB live financial data
- [x] CrewAI multi-agent analysis (deep mode)
- [x] Crawl4AI fast page extraction
- [x] Fact checker (basic implementation)
- [x] Source credibility weighting (31 premium domains, Gartner/SEC/Bloomberg 3x boost)
- [x] Content truncation expanded (3000→6000 chars crawled, 500→1500 snippets)
- [x] Industry-specific dimension weights (12 industries, auto-normalize)
- [x] Fact-checker integrated into council confidence (contradictions penalize score)
- [x] Research-council feedback loop (contested dimensions trigger re-research)
- [x] OASIS graduated scoring (agents adjust -2 to +2 instead of binary)
- [x] OASIS agent-to-agent visibility (panel summary fed into next round)
- [x] OASIS anti-herding (minority amplification, running scores with inertia)
- [x] 88.5B+ persona trait generator (11 dimensions: roles, MBTI behavioral, risk, experience, biases, geography behavioral, industry, fund context, backstories, decision frameworks, portfolio composition)
- [x] Role-experience compatibility filter (no junior PE Partners)
- [x] Bias-framework anti-redundancy (never same category)
- [x] Contextual persona curation (industry-aware role priority per zone)
- [x] 10 industry mappings (healthtech, fintech, ai, saas, cleantech, cybersecurity, marketplace, biotech, edtech, hardware)
- [x] "Stay in your lane" persona directive (agents focus on domain expertise)
- [x] Consensus vs divergence highlighting (z-scores, zone agreement, critical outliers)
- [x] Simulated deliberation (2-round investment committee debate between outliers)
- [x] Committee chair synthesis (key tension, resolution, recommendation)
- [x] Critical Divergence section in PDF report
- [x] Investment Committee Deliberation section in PDF report
- [x] Dashboard manual form with field cards (no Smart Paste)
- [x] Additional Context textarea (raw text passed verbatim to API)
- [x] OASIS toggle (off by default, +10-15 min note)
- [x] Panel scroll fix (onWheel stopPropagation)
- [x] Dark dropdown fix (select option backgrounds)
- [x] PDF: General Info on page 1, company name bold
- [x] PDF: Market Analysis key figures + appendix for full text
- [x] PDF: Competitor table page-break-inside avoid
- [x] PDF: Council reasoning below chart
- [x] PDF: No em dashes in swarm reasoning
- [x] PDF: Risk Assessment + Strategic Recommendations proper headings
- [x] PDF: Paragraphed narratives throughout
- [x] PDF: OASIS markdown stripped from event text
- [x] Backtest script (backtest.py) with 30 Tier 1 + 10 Tier 2 companies
- [x] Landing page (website/index.html)

## In Progress
- [~] Zone seating (agents in correct rooms)
- [~] Agent labels (hover only)
- [~] Floor tile colors (checkered in some rooms)

## Next Up
- [ ] Custom zone distribution (user picks per-zone agent count)
- [ ] Expand fact-checking (wire fact_checker.py into full pipeline)
- [ ] Reduce score clustering (better scoring rubric)
- [ ] Agent speech bubbles with readable text (HTML overlay)
- [ ] Research room with dedicated agent
- [ ] Sound notifications
- [ ] Backtest validation on 100+ companies
- [ ] Analysis history in dashboard (call /api/bi/history, show past analyses)
- [ ] Error states in dashboard (gateway down, LLM fail, SearXNG unreachable)
- [ ] Loading time estimate (elapsed + estimated remaining)

## Roadmap — Calibration & Accuracy
- [ ] Run backtest on 30 Tier 1 companies and publish accuracy
- [ ] Build calibration analysis layer: which persona types are most predictive?
- [ ] Track contrarian vs investor accuracy (do contrarians catch risks better?)
- [ ] Measure deliberation impact (does it improve accuracy or add noise?)
- [ ] Calibrate dimension weights against real outcomes
- [ ] Scoring rubric tuning based on backtest results (fix clustering if found)

## Roadmap — Investor-Specific Panel Weighting
- [ ] "Who are you pitching to?" dropdown in dashboard form
- [ ] Fund profile presets (a16z, Sequoia, YC, climate fund, family office, etc.)
- [ ] Per-fund persona weighting (a16z preset → growth VCs, aggressive risk, big TAM bias)
- [ ] Per-meeting prep tool: multiple runs per founder per fundraise
- [ ] Store fund profiles as JSON configs

## Roadmap — Product Features
- [ ] "What to fix" diff: re-run with one assumption changed, show score delta
- [ ] Scenario comparison: "if you had 3 paid pilots, score jumps from 7.3 to 8.1"
- [ ] Re-score swarm after OASIS events (dynamic stress test)
- [ ] Async analysis flow: submit via web form, get PDF in 24hrs via email
- [ ] Auth on dashboard (prevent unauthorized API usage)
- [ ] Rate limiting on analysis endpoints
- [ ] Docker-compose verification and one-click deploy
