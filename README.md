# Mirai (未来) + Sensei (先生)
**AI Due Diligence Reports + AI Mentor Sessions — VCLabs.org**

## Current State

These notes reflect the current runtime as of **2026-04-03**.

- **Founder-facing production path**: the website intake on `vclabs.org` stores submissions in Prisma, queues them, and sends them to the internal FastAPI endpoint `/api/bi/analyze`.
- **Primary backend**: [subconscious/swarm/app.py](/home/aditya/Downloads/mirai/subconscious/swarm/app.py) is the live FastAPI application. Old Flask wording in older docs is stale.
- **Research**: OpenClaw is the primary fresh-facts engine. Gemini is fallback only.
- **Council**: the main investment scoring path is the multi-model council in `business_intel.py`, with peer review, chairman reconciliation, and fact-check penalties.
- **Swarm**: production swarm size is fixed at **50 agents**.
- **OASIS**: the live simulation path runs **4 rounds** and feeds into the final verdict blend.
- **Reports**: founder reports use the deterministic HTML renderer by default for consistency. Admin can request an optional LLM comparison render without changing the founder-facing default.
- **Admin analytics**: backend diagnostics, warnings, renderer metadata, and enhancement coverage are persisted into website `Event` rows and surfaced in the admin analytics dashboard.
- **WebSocket dashboard path**: `/ws/swarm` still exists for the live operator/dashboard flow, but it is **not** the primary founder submission path.

## What Mirai Does

Mirai takes a startup’s structured submission, preserves the buyer / proof / pricing / implementation context from the founder, researches the company and market with OpenClaw, scores it with a multi-model council, pressure-tests the thesis with a 50-agent persona swarm, runs OASIS trajectory simulation, and generates a consistent HTML report that can be shared back to the founder.

## Primary Runtime Paths

### 1. Founder Submission Flow

1. Founder submits through the website intake.
2. The website stores the submission in Prisma and enqueues it in a single-worker analysis queue.
3. The queue calls FastAPI `/api/bi/analyze` with internal auth and polls `/api/bi/job/{id}`.
4. FastAPI runs extraction → research → council → swarm → plan → OASIS → final verdict.
5. FastAPI generates report sections, deterministic HTML, admin-only diagnostics, and optional admin-only LLM preview data.
6. The website queue shares the HTML report, updates the submission, and writes analytics `Event` rows for the admin dashboard.

### 2. Live Dashboard Flow

- The pixel dashboard uses WebSocket events from `/ws/swarm` for real-time phase streaming and operator visibility.
- That path is useful for live debugging and parity work, but it is not the founder-facing production path.

### 3. Sensei Flow

- Sensei runs on `/game/` and uses `/ws/sensei` on the same FastAPI backend.
- It reuses Mirai research context and the shared persona system for mentor conversations.

## Analysis Pipeline

### Phase 1: Research
- OpenClaw performs the main agentic web research.
- Gemini grounded search is used only as fallback.
- Research is normalized into the `ResearchReport` schema consumed by the rest of the pipeline.

### Phase 2: Council
- Blind scoring can run in parallel with research.
- The council then rescoring pass uses the full research payload.
- Deep mode adds peer review, reconciliation, chairman synthesis, and fact-check penalties.

### Phase 3: Swarm
- The production swarm uses **50 agents**.
- Persona selection is driven by first-class intake context, especially `industry`, `product`, `target_market`, `end_user`, `economic_buyer`, `switching_trigger`, `current_substitute`, and `stage`.
- The `customer` lane is intentionally the most sector-biased lane, while investor selection stays stage-first.
- Detailed routing rules live in [docs/PERSONA_ROUTING.md](/home/aditya/Downloads/mirai/docs/PERSONA_ROUTING.md).
- Swarm output includes not just aggregate sentiment, but also `top_fixes` and `investor_matches`.

### Phase 4: OASIS
- The active OASIS path runs **4 rounds**.
- It produces a trajectory signal that feeds the final verdict blend.

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
- [subconscious/swarm/services/final_verdict.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/final_verdict.py): council + swarm + OASIS blend
- [subconscious/swarm/services/report_generator.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/report_generator.py): deterministic founder-facing HTML
- [subconscious/swarm/services/llm_report_generator.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/llm_report_generator.py): admin-only comparison renderer
- [website/lib/analysis-queue.ts](/home/aditya/Downloads/mirai/website/lib/analysis-queue.ts): website queue and submission orchestration
- [website/app/api/admin/analytics/route.ts](/home/aditya/Downloads/mirai/website/app/api/admin/analytics/route.ts): admin analytics aggregation
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
