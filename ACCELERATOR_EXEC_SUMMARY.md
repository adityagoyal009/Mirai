# Mirai — Accelerator Executive Summary

## Overview

Mirai is an AI due diligence platform that produces investment-grade startup evaluations in under 30 minutes. Submit a startup's details. Mirai researches the market with live web search, scores across 10 dimensions using an 11-model council, simulates crowd reaction with 50 persona agents across 6 professional zones, runs a 4-month market trajectory simulation, and generates a PitchBook-quality HTML report with charts, agent reasoning, and strategic recommendations.

The system replaces 40-80 hours of analyst work per deal with a $0 marginal cost AI pipeline. Every evaluation is independent, multi-perspective, and traceable to source citations.

## Team

Aditya Goyal, Founder and CEO. PhD candidate in Materials and Nanotechnology at North Dakota State University. Fellow at ND Water Resources Research Institute. Winner of 2025 3MT Grand Championship and 2025 Possibility Fellowship. Technical background in nanomaterials, strong utility network across the Upper Midwest. Solo founder, built the entire system.

## Product

A founder or investor submits a startup through a web form (122 industries, 789 keyword tags, 195 countries, structured fields for stage, funding, traction, team). Mirai runs a 5-phase pipeline:

**Phase 1: Agentic Research.** An AI agent with native web search researches the company, competitors, market size, regulatory landscape, team credentials, pricing, and funding history. 30+ facts from 120+ real sources. Gemini grounded search as fallback.

**Phase 2: 11-Model Council.** Eleven LLMs across 8 model families (Claude Opus, GPT-5.4, Llama, Qwen, Kimi, Mistral, GLM, Command) score the startup across 10 weighted dimensions. Karpathy 3-stage pattern: individual blind scoring, anonymous peer review, chairman reconciliation. Disagreements classified as disputed or heavily contested.

**Phase 3: 50-Agent Swarm.** Fifty AI persona agents, generated from 88.5 billion possible trait combinations (16 dimensions: role, MBTI, risk profile, experience, cognitive bias, geographic lens, industry expertise, fund context, failure scars, network strength, decision speed), evaluate from six zones: Investors, Customers, Operators, Analysts, Contrarians, Wild Cards. Each agent writes 200+ words of reasoning. A 6-member investment committee debates the most polarizing positions. Hallucination guard on every agent.

**Phase 4: OASIS Market Simulation.** Twelve swarm-sourced panelists react to market events over 4 simulated months, producing a sentiment trajectory with confidence bands. Detects improving or declining trends.

**Phase 5: Report.** Professional HTML report with score gauge, swarm sentiment donut, zone breakdown charts, radar plot, agent highlight cards, market analysis, competitive landscape, risk assessment, strategic recommendations, and investment verdict. Opens in browser, prints to PDF.

Output: a composite score out of 10, a verdict (Strong Hit, Likely Hit, Uncertain, Likely Miss, Strong Miss), per-dimension breakdowns, per-agent reasoning, and actionable next moves.

## Business Model

SaaS. Founders pay for self-serve evaluations. Accelerators and VCs pay for batch analysis of cohort applicants. Advisory firms pay for white-label reports.

Pricing (planned): Free tier (2 reports/month), Pro ($49/month, unlimited), Enterprise (custom).

Marginal cost per analysis: $0. The entire pipeline runs on free-tier LLM APIs (Groq, Cerebras, SambaNova, Mistral, NVIDIA NIM) plus existing Claude and ChatGPT subscriptions. No per-query API charges.

## Market

Every year, 500,000+ startups seek funding globally. VCs review thousands of decks per partner. Accelerators receive 5,000-15,000 applications per cohort. The due diligence bottleneck is analyst hours, not deal flow.

Existing solutions: PitchBook ($24K/year, data only, no evaluation), CB Insights ($50K+/year, data only), manual analyst work (40-80 hours per deal at $150-300/hour). No product today produces an AI-generated investment-quality evaluation report.

TAM: $15B global market research and advisory market. SAM: $2B startup intelligence and due diligence segment. SOM: $50M accelerator and early-stage VC evaluation tools.

## Traction

The system is live and producing reports. Six executive summaries from a gener8tor accelerator cohort have been submitted and evaluated through the full pipeline. The website form, analysis queue, async job system, and report generation are all operational.

Technical milestones completed:
- 11-model council with Karpathy 3-stage peer review
- 50-agent swarm with 88.5B+ persona engine
- OASIS 4-round market simulation with swarm-sourced panelists
- 20 pipeline bias fixes (neutral geographic lenses, no personality-based scoring, equal deliberation weight, capped industry weights, normalized stage vocabulary, scoped data isolation, prompt injection containment)
- Async job pattern (no dropped connections on long analyses)
- Structured fields passthrough from frontend (skips lossy LLM extraction)
- Website form with 122 industries, 789 keywords, 195 countries, backend validation, atomic transactions

231K companies in database. 22.8K with known outcomes for calibration. Baseline to beat: 79% AUC-ROC (XGBoost on Crunchbase features).

## Moat

The value compounds. Every analysis feeds the calibration flywheel. GraphRAG institutional memory means the 1000th analysis is dramatically better than the 1st. Multi-model consensus is hard to replicate (requires routing across 11 LLMs with provider-specific fallbacks). The 88.5B persona engine generates evaluators that no human could staff. And the bias controls (20 fixes across geographic, personality, industry, and verdict dimensions) are the result of systematic auditing that took weeks.

The platform is model-agnostic. When better models ship, Mirai gets better automatically. When models get cheaper, margins improve.

## Competition

No direct competitor produces AI-generated startup evaluation reports with multi-model council, persona swarm, and market simulation.

Adjacent players: PitchBook (data, no AI evaluation), CB Insights (signals, no report generation), Hatcher+ (ML scoring, no qualitative analysis), SignalFire (internal tool, not available to market), Visible.vc (portfolio tracking, not due diligence).

## Ask

Seed funding to hire a frontend engineer, run large-scale calibration (1000+ company backtest to publish accuracy numbers), and launch paid tiers for accelerators.

Milestones for the round:
1. Publish calibration accuracy (target: beat 79% AUC baseline)
2. 10 paying accelerator customers
3. 1,000 analyses completed with outcome tracking

## Why Now

LLM costs hit zero (free tiers from 6 providers). Multi-model consensus became possible in 2025 when Groq, Cerebras, and SambaNova launched free inference APIs. Before this, running 50 agents across 6 models would cost $50+ per analysis. Now it costs $0. The economics of AI due diligence flipped from prohibitive to free overnight.

Accelerator application volume is growing 20-30% annually. YC, Techstars, and gener8tor each receive 10,000+ applications per cycle. The human review bottleneck will only get worse. Mirai eliminates it.
