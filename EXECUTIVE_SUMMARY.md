# Mirai (未来) — Executive Summary

**AI-powered startup diligence with agentic research, council scoring, 50-agent swarm evaluation, OASIS simulation, and consistent report generation**

Version 0.12.0 | April 2026 | Created by Aditya Goyal | vclabs.org

---

## 1. What Mirai Is

Mirai is a due diligence system for startup evaluation.

It takes a founder submission, preserves structured commercial context, runs live market research, evaluates the business through a multi-model council, pressure-tests it with a fixed 50-agent persona swarm, simulates near-term trajectory through OASIS, and produces a founder-facing report plus admin-only diagnostics.

The important current implementation detail is this:

- the **website queue + FastAPI backend** is the production founder flow
- the **WebSocket dashboard** is still available, but it is not the primary founder submission path

---

## 2. Production Runtime

### Founder Path

1. Founder submits through the website.
2. The website stores the submission in Prisma.
3. A single-worker queue dispatches the run to internal FastAPI `/api/bi/analyze`.
4. FastAPI returns the completed analysis through async job polling.
5. The website shares the HTML report, updates the submission state, and records admin analytics events.

### Admin Path

Admins use the website analytics dashboard to inspect:

- backend run counts
- average runtime
- degraded runs
- renderer used
- report generation failures
- enhancement coverage
- warning counts
- audit log paths

This information is intentionally admin-only.

### Live Dashboard Path

The dashboard WebSocket flow still exists for live visualization and debugging, but it is not the submission path used for founder report delivery.

---

## 3. Core Pipeline

### Phase 1: Research

- OpenClaw is the primary fresh-facts engine.
- Gemini grounded search is fallback only.
- Research is normalized into a stable report object before scoring.

### Phase 2: Council

- Blind scoring can run in parallel with research.
- The main pass scores using full research context.
- Deep mode adds peer review, reconciliation, chairman synthesis, and fact-check penalties.

### Phase 3: Swarm

- The production swarm is fixed at **50 agents**.
- Persona selection is context-aware using industry, product, target market, and stage.
- Swarm returns aggregate sentiment plus richer artifacts like `top_fixes` and `investor_matches`.

### Phase 4: OASIS

- The active OASIS path runs **4 rounds**.
- Its trajectory signal participates in the final verdict blend.

### Phase 5: Reporting

- `ReportAgent` generates narrative sections.
- The founder-facing report uses the deterministic HTML renderer by default.
- An LLM comparison renderer is available for admin use, but it is not the default founder report path.

---

## 4. Why The Current Architecture Matters

Mirai is designed around two different requirements:

### Founder Experience

Founders should not sit and watch the internal pipeline in real time.

So the founder-facing product remains:

- asynchronous
- opaque during execution
- simple in status messaging
- report-oriented rather than process-oriented

### Admin Experience

Admins need observability to debug quality and operations.

So the admin-facing system preserves:

- warnings
- audit logs
- report renderer metadata
- runtime duration
- degradation signals
- enhancement coverage

That split is now reflected in the production architecture.

---

## 5. Current Report Strategy

Mirai now intentionally separates **report consistency** from **report experimentation**.

### Default Founder Report

- deterministic HTML renderer
- consistent structure
- stable output shape across runs

### Admin Comparison Render

- optional LLM-generated comparison HTML
- richer presentation potential
- more variable output
- intended for internal evaluation, not default founder delivery

This protects report consistency while still allowing rendering experiments.

---

## 6. Key Implementation Files

- [subconscious/swarm/app.py](/home/aditya/Downloads/mirai/subconscious/swarm/app.py): FastAPI backend and internal analysis API
- [subconscious/swarm/services/business_intel.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/business_intel.py): research + council
- [subconscious/swarm/services/swarm_predictor.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/swarm_predictor.py): fixed 50-agent swarm
- [subconscious/swarm/services/final_verdict.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/final_verdict.py): final blend
- [subconscious/swarm/services/report_generator.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/report_generator.py): deterministic report renderer
- [subconscious/swarm/services/llm_report_generator.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/llm_report_generator.py): admin comparison renderer
- [website/lib/analysis-queue.ts](/home/aditya/Downloads/mirai/website/lib/analysis-queue.ts): queue orchestration
- [website/app/api/admin/analytics/route.ts](/home/aditya/Downloads/mirai/website/app/api/admin/analytics/route.ts): admin analytics API
- [website/app/admin/analytics/page.tsx](/home/aditya/Downloads/mirai/website/app/admin/analytics/page.tsx): admin analytics UI

---

## 7. Ports

| Port | Service |
|------|---------|
| 19789 | Mirai Gateway |
| 5000 | FastAPI application |
| 8100 | Cortex API server |
| 8888 | SearXNG when deployed |

---

## 8. Current Caveats

- The live dashboard WebSocket flow still exists and can be archived later.
- Historical docs and changelog entries still mention older Flask-era states where relevant to project history.
- Sensei and the dashboard are served by the same FastAPI app, but they are separate product surfaces from the founder submission queue.

---

## 9. Bottom Line

Mirai’s production architecture is now:

- **FastAPI**, not Flask
- **website queue first**, not WebSocket first
- **50-agent swarm**, not variable production swarm counts
- **deterministic founder reports by default**
- **admin-only observability through website analytics**

That is the current system to reason about when making backend, report, and operations changes.
