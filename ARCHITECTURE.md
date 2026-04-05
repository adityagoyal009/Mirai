# Mirai (未来) + Sensei (先生) — System Architecture

## Runtime Truths

These are the current architecture truths that matter:

- The **founder-facing production path** is the website queue calling FastAPI `/api/bi/analyze`.
- The backend is **FastAPI**, not Flask.
- `/ws/swarm` still exists for the dashboard/live operator path, but it is **not** the primary founder submission flow.
- Research is **Claude Code CLI primary** (6-phase WebSearch/WebFetch), OpenClaw fallback, Gemini final fallback.
- The production swarm size is **50 agents** (contrarian capped at 3, wildcard weight 0.2 for B2B).
- A **deterministic risk panel** (10 domain-specific agents) runs post-swarm, pre-OASIS.
- The active OASIS path is the **4-round** simulator.
- Final verdict: **council 78% / swarm 22%**, risk panel subtractive penalty (max 1.2 points).
- **Outcome tracking** stores structured analysis results + company progress for calibration.
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
  → Claude Code CLI 6-phase research (OpenClaw fallback → Gemini fallback)
  → council prediction (11 models, Karpathy 3-stage)
  → 50-agent swarm (persona-driven, context-aware routing)
  → deterministic risk panel (10 domain-specific agents)
  → strategy plan
  → OASIS simulation (4-round market trajectory)
  → final verdict blend (council 78% + swarm 22% + risk penalty + OASIS adjust)
  → report sections
  → deterministic HTML report (with risk panel table)
  → admin summary / warnings / audit metadata
  ↓
Queue polls /api/bi/job/{id}
  ↓
Queue shares report HTML
  ↓
Queue updates submission + writes Prisma Event rows
Queue persists AnalysisResult (structured scores) + creates FollowUp schedule
  ↓
Founder sees simple status
Admin sees full diagnostics in /admin/analytics + /admin/calibration
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
- **Claude Code CLI is the primary research engine** — runs 6 sequential phases via `claude -p` subprocess with `--allowedTools WebSearch,WebFetch`:
  1. Company & Product (website crawl, features, pricing, traction)
  2. Team & Leadership (founder backgrounds, board, gaps)
  3. Funding & Deal History (Crunchbase, PitchBook, SEC)
  4. Competitors Deep Dive (5-8 competitors, each individually searched)
  5. Market, Regulatory, and IP (TAM/SAM, patents, regulation)
  6. Customer Evidence, Pricing, Risks, and Executive Synthesis
- Each phase receives a compact context summary from prior phases. Output is merged into a single research dict.
- **OpenClaw is fallback** if all 6 Claude phases fail. Gemini grounded search is the final fallback.
- Full research context flows to council and swarm **without truncation**.

### Phase 2: Council

- Blind scoring can run in parallel with research.
- The council then scores again with research context.
- Deep mode adds peer review, weighted reconciliation, chairman synthesis, and fact-check penalties.

### Phase 3: Swarm

- [subconscious/swarm/services/swarm_predictor.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/swarm_predictor.py) runs a fixed **50-agent** panel.
- Persona selection uses a layered router fed by the founder intake contract:
  `industry`, `product`, `target_market`, `end_user`, `economic_buyer`, `switching_trigger`, `current_substitute`, `stage`, plus structured business-model, traction, pricing, implementation, and risk fields.
- Zone distribution at 50 agents: investor=10, customer=14, operator=11, analyst=7, **contrarian=3**, wildcard=5.
- **Contrarian capped at 3** — the dedicated risk panel now handles domain-specific risk analysis.
- **Wildcard weight 0.2 for B2B contexts** (1.0 for all other zones). All other agents weight 1.0.
- Scoring discipline: zone prompts use calibrated 4-tier scales (8-10 exceptional, 6-7.9 credible, 4-5.9 mixed, 0-3.9 weak). **5.0-7.0 scores explicitly allowed** for mixed evidence.
- MBTI, backstory, risk posture, and scar tissue are framed as **attention directors** (what to stress-test), not score anchors.
- The `customer` lane is intentionally the most sector-specific lane. Investor selection is stage-first, then sector/context-refined.
- Detailed routing and field influence are documented in [docs/PERSONA_ROUTING.md](/home/aditya/Downloads/mirai/docs/PERSONA_ROUTING.md).

### Phase 3b: Risk Panel

- [subconscious/swarm/services/risk_panel.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/risk_panel.py) runs **10 deterministic domain-specific risk agents** post-swarm.
- Domains: IP, Regulatory, Competition, Unit Economics, Platform Dependency, Technical, Market Timing, Team, Customer Concentration (conditional), Legal/Corporate (conditional).
- Each agent produces: status (risk_found / no_material_risk_found / insufficient_evidence), severity, confidence, evidence, mitigation, affected dimensions.
- Output: overall penalty (max 1.2 points), per-dimension penalties (max 0.6 each), structured findings for the report.
- Runs concurrently (6 workers) on swarm NIM models. Non-fatal — if the panel fails, the pipeline continues without it.

### Phase 4: OASIS

- The active OASIS path is [subconscious/swarm/services/oasis_simulator.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/oasis_simulator.py).
- It runs **4 rounds** and contributes trajectory information to the final blend.
- Selects 12 diverse panelists from the swarm (strongest bull/bear, zone-diverse, most internally conflicted).
- Sources real news headlines via web search for event injection.

### Phase 5: Final Verdict And Report

- [subconscious/swarm/services/final_verdict.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/final_verdict.py) blends council + swarm + risk panel + OASIS.
- **Council weight: 78%, swarm weight: 22%** (swarm further dampened when internally noisy).
- **Risk panel penalty** subtracted from final score (max 1.2 points). Per-dimension penalties passed through for report display.
- **OASIS trajectory** adjusts score ±0.6-1.0 when declining/improving with low confidence.
- [subconscious/swarm/services/report_generator.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/report_generator.py) renders the production founder-facing HTML report, including a **deterministic risk panel table**.
- [subconscious/swarm/services/llm_report_generator.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/llm_report_generator.py) is used as an **admin comparison renderer**, not the production default.

### Phase 6: Outcome Tracking (Post-Analysis)

- The website analysis queue persists a structured **AnalysisResult** row (45 flat queryable columns: council/swarm dimension scores, risk panel findings, OASIS trajectory, research quality).
- **3 FollowUp records** are auto-created (3, 6, 12 months after analysis).
- Admins record outcomes via `/api/admin/submissions/{id}/outcome`. Founders self-report via `/api/portal/submissions/{id}/outcome`.
- The `/api/admin/calibration` endpoint provides score distributions, verdict-outcome correlation, and dimension predictive power.
- This is the data flywheel: more analyses → more outcomes tracked → better calibration → more trust.

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
- [subconscious/swarm/services/agentic_researcher.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/agentic_researcher.py): 6-phase Claude CLI research
- [subconscious/swarm/services/swarm_predictor.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/swarm_predictor.py): 50-agent swarm
- [subconscious/swarm/services/risk_panel.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/risk_panel.py): 10-domain deterministic risk panel
- [subconscious/swarm/services/persona_engine.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/persona_engine.py): 16-dimension persona generator + routing
- [subconscious/swarm/services/final_verdict.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/final_verdict.py): council/swarm/risk/OASIS blend
- [subconscious/swarm/utils/audit_log.py](/home/aditya/Downloads/mirai/subconscious/swarm/utils/audit_log.py): audit logging

### Website

- [website/lib/analysis-queue.ts](/home/aditya/Downloads/mirai/website/lib/analysis-queue.ts): queue, job orchestration, AnalysisResult persistence
- [website/app/api/admin/analytics/route.ts](/home/aditya/Downloads/mirai/website/app/api/admin/analytics/route.ts): analytics aggregation + calibration summary
- [website/app/api/admin/calibration/route.ts](/home/aditya/Downloads/mirai/website/app/api/admin/calibration/route.ts): benchmarking and calibration queries
- [website/app/api/admin/follow-ups/route.ts](/home/aditya/Downloads/mirai/website/app/api/admin/follow-ups/route.ts): outcome follow-up management
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
