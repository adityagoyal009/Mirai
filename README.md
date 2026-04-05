# Mirai (未来) + Sensei (先生)
**AI Due Diligence Reports + AI Mentor Sessions — VCLabs.org**

## Current State

These notes reflect the current runtime as of **2026-04-04** (v0.12.0).

- **Founder-facing production path**: the website intake on `vclabs.org` stores submissions in Prisma, queues them, and sends them to the internal FastAPI endpoint `/api/bi/analyze`.
- **Primary backend**: [subconscious/swarm/app.py](/home/aditya/Downloads/mirai/subconscious/swarm/app.py) is the live FastAPI application.
- **Research**: Claude Code CLI is the primary research engine (6-phase WebSearch/WebFetch). OpenClaw is fallback. Gemini is final fallback.
- **Council**: 11 models across 8 families with peer review, chairman reconciliation, and fact-check penalties.
- **Swarm**: **50 agents** with calibrated scoring (contrarian capped at 3, wildcard weight 0.2 for B2B, 5-7 mid-range scores validated). Council weight **78%**, swarm weight **22%** in final blend.
- **Risk panel**: **10 deterministic domain-specific risk agents** run post-swarm. Subtractive penalty (max 1.2 points) applied to final score.
- **OASIS**: 4-round market trajectory simulation, feeds trajectory signal into the final blend.
- **Reports**: deterministic HTML renderer with risk panel table. Admin can request optional LLM comparison render.
- **Outcome tracking**: structured AnalysisResult persisted per analysis (45 queryable columns). Outcomes tracked via admin/founder APIs. Calibration endpoint for score distributions and predictive analysis.
- **Admin analytics**: backend diagnostics, warnings, calibration summary, and follow-up management surfaced in admin dashboard.

## What Mirai Does

Mirai takes a startup’s structured submission, preserves the buyer / proof / pricing / implementation context from the founder, researches the company and market via Claude Code CLI (6-phase deep research), scores it with a multi-model council, pressure-tests the thesis with a 50-agent persona swarm, runs a deterministic 10-domain risk panel, simulates market trajectory with OASIS, blends all signals into a final verdict, generates a consistent HTML report, and stores structured results for calibration.

## Primary Runtime Paths

### 1. Founder Submission Flow

1. Founder submits through the website intake.
2. The website stores the submission in Prisma and enqueues it in a single-worker analysis queue.
3. The queue calls FastAPI `/api/bi/analyze` with internal auth and polls `/api/bi/job/{id}`.
4. FastAPI runs extraction → 6-phase Claude CLI research → council → swarm → risk panel → plan → OASIS → final verdict.
5. FastAPI generates report sections, deterministic HTML with risk panel table, admin-only diagnostics, and optional admin-only LLM preview data.
6. The website queue shares the HTML report, updates the submission, persists structured AnalysisResult, creates follow-ups, and writes analytics `Event` rows.

### 2. Live Dashboard Flow

- The pixel dashboard uses WebSocket events from `/ws/swarm` for real-time phase streaming and operator visibility.
- That path is useful for live debugging and parity work, but it is not the founder-facing production path.

### 3. Sensei Flow

- Sensei runs on `/game/` and uses `/ws/sensei` on the same FastAPI backend.
- It reuses Mirai research context and the shared persona system for mentor conversations.

## Analysis Pipeline

### Phase 1: Research
- Claude Code CLI performs 6-phase deep web research (company, team, funding, competitors, market/regulatory/IP, evidence/pricing/risks/synthesis).
- OpenClaw is fallback if Claude CLI fails. Gemini grounded search is final fallback.
- Full research flows to council/swarm without truncation.

### Phase 2: Council
- Blind scoring can run in parallel with research.
- The council then rescoring pass uses the full research payload.
- Deep mode adds peer review, reconciliation, chairman synthesis, and fact-check penalties.

### Phase 3: Swarm
- **50 agents** (investor=10, customer=14, operator=11, analyst=7, contrarian=3, wildcard=5).
- Contrarian capped at 3 — the risk panel now handles domain-specific risk analysis.
- Wildcard weight 0.2 for B2B contexts. All other zones weight 1.0.
- Scoring: calibrated 4-tier scales, 5-7 mid-range validated, MBTI/backstory deanchored from scores.
- Final blend: council 78%, swarm 22% (swarm dampened when internally noisy).

### Phase 3b: Risk Panel
- **10 deterministic domain-specific agents** (IP, regulatory, competition, unit economics, platform, technical, market timing, team, customer concentration, legal/corporate).
- Subtractive penalty max 1.2 points. Per-dimension max 0.6.
- Structured findings rendered in the founder report.

### Phase 4: OASIS
- 4-round market trajectory simulation with real news headline sourcing.
- 12 diverse panelists selected from the swarm.

### Phase 5: Reporting
- `ReportAgent` generates narrative sections.
- `report_generator.py` is the production default renderer for founder consistency.
- `llm_report_generator.py` is now used as an **admin comparison path**, not the default founder report path.

## Report Enhancements And Admin Diagnostics

The real backend preserves these higher-value analysis artifacts:

- `top_fixes`
- `investor_matches`
- `score_forecast`
- `rewritten_exec_summary`
- `similar_funded`
- warnings and degradation notes
- report renderer metadata
- audit log path

These are kept for admins and internal operations. Founders still see the simple async workflow and final report delivery.

## Key Files

- [subconscious/swarm/app.py](/home/aditya/Downloads/mirai/subconscious/swarm/app.py): primary FastAPI backend
- [subconscious/swarm/services/business_intel.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/business_intel.py): research + council core
- [subconscious/swarm/services/swarm_predictor.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/swarm_predictor.py): 50-agent swarm
- [subconscious/swarm/services/risk_panel.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/risk_panel.py): 10-domain deterministic risk panel
- [subconscious/swarm/services/final_verdict.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/final_verdict.py): council + swarm + risk panel + OASIS blend
- [subconscious/swarm/services/report_generator.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/report_generator.py): deterministic founder-facing HTML with risk panel table
- [website/lib/analysis-queue.ts](/home/aditya/Downloads/mirai/website/lib/analysis-queue.ts): queue, AnalysisResult persistence, follow-up creation
- [website/app/api/admin/calibration/route.ts](/home/aditya/Downloads/mirai/website/app/api/admin/calibration/route.ts): calibration queries
- [website/app/api/admin/analytics/route.ts](/home/aditya/Downloads/mirai/website/app/api/admin/analytics/route.ts): admin analytics + calibration summary
- [website/app/admin/analytics/page.tsx](/home/aditya/Downloads/mirai/website/app/admin/analytics/page.tsx): admin analytics dashboard UI

## Ports

| Port | Service |
|------|---------|
| 19789 | Mirai Gateway |
| 5000 | FastAPI app: internal BI API, dashboard assets, `/ws/swarm`, `/ws/sensei` |
| 8100 | Cortex API server |
| 8888 | SearXNG (optional / deployment-dependent) |

## Internal Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/bi/analyze` | Internal async analysis submission |
| GET | `/api/bi/job/{id}` | Internal job polling |
| POST | `/api/report/share` | Persist shareable HTML report |
| WS | `/ws/swarm` | Legacy/live dashboard streaming path |
| WS | `/ws/sensei` | Sensei mentor sessions |

## Queue And Security Notes

- Website submissions are serialized through a single-worker FIFO queue.
- Queue callers authenticate to FastAPI using a dedicated `MIRAI_INTERNAL_API_KEY`.
- If no internal key is configured, internal BI endpoints only allow loopback callers.
- Founder-facing status remains intentionally simple: queued, reviewing, report ready.
- Detailed backend diagnostics belong in admin analytics, not in the founder-facing surface.
