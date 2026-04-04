# Mirai (未来) + Sensei (先生) — System Architecture

## Runtime Truths

These are the current architecture truths that matter:

- The **founder-facing production path** is the website queue calling FastAPI `/api/bi/analyze`.
- The backend is **FastAPI**, not Flask.
- `/ws/swarm` still exists for the dashboard/live operator path, but it is **not** the primary founder submission flow.
- Research is **OpenClaw-first** with Gemini fallback.
- The production swarm size is **50 agents**.
- The active OASIS path is the **4-round** simulator.
- Founder reports use the **deterministic HTML renderer by default**.
- Admin-only diagnostics are persisted into website analytics, not exposed to submitters.

## Runtime Topology

```
Founder / Admin Browser
    │
    ├── Website (Next.js + Prisma)
    │     ├── /submit, /dashboard, /admin, /admin/analytics
    │     ├── Submission persistence
    │     ├── Single-worker analysis queue
    │     └── Admin analytics from Prisma Event rows
    │
    ├── FastAPI App (port 5000)
    │     ├── /api/bi/analyze
    │     ├── /api/bi/job/{id}
    │     ├── /api/report/share
    │     ├── /ws/swarm
    │     ├── /ws/sensei
    │     ├── /dashboard/
    │     └── /game/
    │
    ├── Mirai Gateway (port 19789)
    │     └── Multi-provider LLM routing
    │
    ├── Cortex (port 8100)
    │     └── Autonomous agent / browser / memory subsystem
    │
    └── Optional research infra
          └── SearXNG and other enrichments when deployed
```

## Subsystems

### Website

The website is the production intake and admin surface.

- Intake form writes submissions into Prisma.
- [website/lib/analysis-queue.ts](/home/aditya/Downloads/mirai/website/lib/analysis-queue.ts) serializes analysis jobs.
- The queue calls FastAPI with internal auth, polls for completion, shares the report, updates the submission, and writes analytics `Event` rows.
- [website/app/api/admin/analytics/route.ts](/home/aditya/Downloads/mirai/website/app/api/admin/analytics/route.ts) aggregates those events.
- [website/app/admin/analytics/page.tsx](/home/aditya/Downloads/mirai/website/app/admin/analytics/page.tsx) is the admin analytics UI.

### FastAPI App

[subconscious/swarm/app.py](/home/aditya/Downloads/mirai/subconscious/swarm/app.py) is the live backend.

It hosts:

- internal BI REST endpoints
- Sensei WebSocket sessions
- legacy/live dashboard WebSocket sessions
- shared static serving for dashboard/game builds
- the founder report generation path used by the website queue

### Dashboard And Game

- `/dashboard/` is the live operator / visual analysis UI.
- `/game/` is the Sensei mentor product.
- Both are served by the same FastAPI app.

### Gateway

The gateway provides the OpenAI-compatible LLM interface and provider auth layer. Backend LLM traffic routes through it rather than directly embedding per-provider credentials into every service.

### Cortex

Cortex is separate from the founder submission flow. It can browse, think, recall memory, and trigger internal analyses, but it is not the queue that processes founder submissions.

## Primary Founder Submission Flow

```
Founder submits form
  ↓
Website stores Prisma submission
  ↓
Analysis queue marks submission reviewing
  ↓
POST /api/bi/analyze (internal auth, async job mode)
  ↓
FastAPI job runs:
  extraction
  → OpenClaw research
  → council prediction
  → 50-agent swarm
  → strategy plan
  → OASIS simulation
  → final verdict blend
  → report sections
  → deterministic HTML report
  → admin summary / warnings / audit metadata
  ↓
Queue polls /api/bi/job/{id}
  ↓
Queue shares report HTML
  ↓
Queue updates submission + writes Prisma Event rows
  ↓
Founder sees simple status
Admin sees full diagnostics in /admin/analytics
```

## Optional Live Dashboard Flow

The legacy/live dashboard flow still exists and uses `/ws/swarm`.

It is useful for:

- streaming phase-by-phase activity
- live debugging
- parity testing
- operator demos

It is not the source of truth for the website submission lifecycle.

## Analysis Stages

### Phase 0: Extraction

- Uses structured website fields when provided.
- Falls back to extraction logic only when needed.
- Computes data quality and required-field completeness.

### Phase 1: Research

- Implemented through [subconscious/swarm/services/business_intel.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/business_intel.py) and [subconscious/swarm/services/agentic_researcher.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/agentic_researcher.py).
- OpenClaw is the primary research engine.
- Gemini grounded search is fallback.
- The output is normalized into a stable research schema for later phases.

### Phase 2: Council

- Blind scoring can run in parallel with research.
- The council then scores again with research context.
- Deep mode adds peer review, weighted reconciliation, chairman synthesis, and fact-check penalties.

### Phase 3: Swarm

- [subconscious/swarm/services/swarm_predictor.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/swarm_predictor.py) runs a fixed **50-agent** panel.
- Persona selection uses a layered router fed by the founder intake contract:
  `industry`, `product`, `target_market`, `end_user`, `economic_buyer`, `switching_trigger`, `current_substitute`, `stage`, plus structured business-model, traction, pricing, implementation, and risk fields.
- The `customer` lane is intentionally the most sector-specific lane. Investor selection is stage-first, then sector/context-refined.
- Detailed routing and field influence are documented in [docs/PERSONA_ROUTING.md](/home/aditya/Downloads/mirai/docs/PERSONA_ROUTING.md).
- Swarm output includes:
  - aggregate sentiment and score distribution
  - divergence and deliberation metadata
  - `top_fixes`
  - `investor_matches`

### Phase 4: OASIS

- The active OASIS path is [subconscious/swarm/services/oasis_simulator.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/oasis_simulator.py).
- It runs **4 rounds** and contributes trajectory information to the final blend.

### Phase 5: Final Verdict And Report

- [subconscious/swarm/services/final_verdict.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/final_verdict.py) blends council + swarm + OASIS.
- [subconscious/swarm/services/report_agent.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/report_agent.py) creates narrative sections.
- [subconscious/swarm/services/report_generator.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/report_generator.py) renders the production founder-facing HTML report.
- [subconscious/swarm/services/llm_report_generator.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/llm_report_generator.py) is used as an **admin comparison renderer**, not the production default.

## Reporting And Observability

### Founder-Facing Behavior

Founders intentionally do **not** see:

- live phase streaming
- per-agent voting
- council internals
- raw warnings
- audit output

They see the async workflow:

- queued
- reviewing
- report ready

### Admin-Facing Behavior

Admins now get:

- backend runtime duration
- renderer requested / renderer used
- report generation success or degradation
- warnings and warning counts
- enhancement coverage
- optional LLM preview status
- audit log path

These diagnostics are persisted into website Prisma `Event` rows and surfaced in the admin analytics dashboard.

### Audit Storage

- Per-run audit JSON is written under `~/.mirai/audits`.
- The backend also returns an `admin_summary` block with the audit path and selected run metadata.

## Key Files

### Backend

- [subconscious/swarm/app.py](/home/aditya/Downloads/mirai/subconscious/swarm/app.py): FastAPI app and BI endpoints
- [subconscious/swarm/api/websocket.py](/home/aditya/Downloads/mirai/subconscious/swarm/api/websocket.py): live dashboard WebSocket path
- [subconscious/swarm/services/business_intel.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/business_intel.py): research + council
- [subconscious/swarm/services/swarm_predictor.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/swarm_predictor.py): 50-agent swarm
- [subconscious/swarm/services/report_enhancements.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/report_enhancements.py): score forecast, exec rewrite, similar funded
- [subconscious/swarm/utils/audit_log.py](/home/aditya/Downloads/mirai/subconscious/swarm/utils/audit_log.py): audit logging

### Website

- [website/lib/analysis-queue.ts](/home/aditya/Downloads/mirai/website/lib/analysis-queue.ts): queue and job orchestration
- [website/app/api/admin/analytics/route.ts](/home/aditya/Downloads/mirai/website/app/api/admin/analytics/route.ts): analytics aggregation
- [website/app/admin/analytics/page.tsx](/home/aditya/Downloads/mirai/website/app/admin/analytics/page.tsx): admin analytics dashboard

### Sensei

- [subconscious/swarm/app.py](/home/aditya/Downloads/mirai/subconscious/swarm/app.py): `/ws/sensei`
- [subconscious/swarm/services/mentor_session.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/mentor_session.py): mentor sessions
- [dashboard-game/src/sensei/senseiSocket.ts](/home/aditya/Downloads/mirai/dashboard-game/src/sensei/senseiSocket.ts): Sensei client socket

## Ports

| Port | Service |
|------|---------|
| 19789 | Mirai Gateway |
| 5000 | FastAPI app, dashboard assets, game assets, WebSockets |
| 8100 | Cortex API server |
| 8888 | SearXNG when deployed |

## Security Boundary

- Founder submissions reach the analysis backend only through internal website calls.
- Website callers use a dedicated `MIRAI_INTERNAL_API_KEY`.
- If no internal key is configured, internal BI endpoints only allow loopback callers.
- Raw backend diagnostics stay in admin analytics and local audit files.

## Current Caveats

These are still open and intentionally not hidden:

- `/ws/swarm` still exists and can be archived later once parity work is fully complete.
- Some historical docs and changelog entries still mention Flask because they describe prior states.
- The dashboard/live path is still useful for operator debugging even though it is not the primary founder path.
