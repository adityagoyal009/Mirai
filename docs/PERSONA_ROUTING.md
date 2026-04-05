# Persona Routing And Form Influence

## Purpose

This document describes the current founder-submission contract from the website form through extraction, research, council, swarm, OASIS, and reporting.

The key design rule is:

- every meaningful intake field should matter somewhere
- not every field should directly choose personas
- the `customer` lane is intentionally the most sector-biased lane

## End-To-End Flow

1. The website form writes a normalized submission row.
2. The website builds `exec_summary` plus `structured_fields`.
3. The queue sends both to FastAPI `/api/bi/analyze`.
4. FastAPI builds `ExtractionResult` directly from `structured_fields` when present.
5. Research uses that structured extraction instead of relying on lossy LLM-only parsing.
6. Council scoring uses `exec_summary`, research, stage, and data quality.
7. Swarm receives:
   - the full `exec_summary`
   - research context
   - first-class buyer/workflow fields
   - the full `persona_context` copied from `structured_fields`
8. OASIS uses the resulting extraction, verdict context, and swarm outputs.
9. Reporting uses the analysis outputs plus preserved enhancements.

## Sources Of Truth

- Website intake write: [website/app/api/portal/submit/route.ts](/home/aditya/Downloads/mirai/website/app/api/portal/submit/route.ts)
- Queue payload rebuild: [website/lib/analysis-queue.ts](/home/aditya/Downloads/mirai/website/lib/analysis-queue.ts)
- FastAPI structured passthrough: [subconscious/swarm/app.py](/home/aditya/Downloads/mirai/subconscious/swarm/app.py)
- Extraction schema: [subconscious/swarm/services/business_intel.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/business_intel.py)
- Swarm routing: [subconscious/swarm/services/swarm_predictor.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/swarm_predictor.py)
- Persona engine: [subconscious/swarm/services/persona_engine.py](/home/aditya/Downloads/mirai/subconscious/swarm/services/persona_engine.py)

## What Directly Chooses Personas

These fields have first-class routing power inside the persona engine:

- `industry`
- `product`
- `target_market`
- `end_user`
- `economic_buyer`
- `switching_trigger`
- `current_substitute`
- `stage`

These fields are used in three distinct ways:

1. Direct role priority and exclusion
2. Context-key generation
3. Persona prompt conditioning

### 1. Direct Role Priority And Exclusion

The engine first applies:

- stage priorities and exclusions
- industry role packs
- context role packs
- context exclusions

This is why:

- pre-seed companies do not get late-stage investor-heavy panels
- enterprise procurement software gets enterprise buyers
- direct-to-consumer products do not keep inheriting enterprise procurement roles

### 2. Context-Key Generation

The engine derives routing keys from structured fields. Current keys include:

- `procurement_heavy`
- `individual_buyer`
- `plg_motion`
- `low_touch_self_serve`
- `channel_motion`
- `high_touch_implementation`
- `manual_substitute`
- `incumbent_substitute`
- `technical_founder`
- `domain_expert_founder`
- `pilot_traction`
- `revenue_traction`
- `regulatory_risk`
- `gtm_risk`
- `technical_risk`
- `competition_risk`
- `workflow_trigger`
- `cost_savings_trigger`
- `compliance_trigger`

These keys are created from fields like:

- `sales_motion`
- `pricing_model`
- `typical_contract_size`
- `implementation_complexity`
- `time_to_value`
- `economic_buyer`
- `current_substitute`
- `switching_trigger`
- `technical_founder`
- `founder_problem_fit`
- `founder_years_in_industry`
- `has_customers`
- `generating_revenue`
- `loi_count`
- `pilot_count`
- `paid_customer_count`
- `active_customer_count`
- `monthly_revenue_value`
- `revenue`
- `business_model`
- `primary_risk_category`
- `risk`

### 3. Persona Prompt Conditioning

Many fields do not change the lane mix directly, but they still shape the persona prompts through routing notes. These notes tell each agent what kind of company it is evaluating.

Prompt-conditioning fields include:

- `country`
- `location`
- `website_url`
- `year_founded`
- `business_model`
- `pricing_model`
- `starting_price`
- `sales_motion`
- `typical_contract_size`
- `implementation_complexity`
- `time_to_value`
- `traction`
- `growth_rate`
- `funding`
- `currently_fundraising`
- `team`
- `founder_problem_fit`
- `founder_years_in_industry`
- `advantage`
- `ask`
- `primary_risk_category`
- `risk`
- `known_competitors`
- `industry_priority_areas`
- `keywords`
- `demo_url`
- `customer_proof_url`
- `pilot_docs_url`
- `extra_context`

These fields matter because they change how each persona interprets the startup, even when they do not alter the role pool directly.

## Lane Bias Rules

The lanes are intentionally biased differently.

### Customer Lane

This is the most sector-biased lane.

Customer personas should reflect:

- who feels the pain
- who approves the budget
- what they use today
- what makes them switch
- how heavy the buying process really is

Examples:

- enterprise procurement software should surface procurement, finance, IT, and incumbent-replacement lenses
- public-sector submissions should surface budget-holder and approval-chain lenses
- direct-to-consumer or individual-buyer products should surface consumer personas, not enterprise procurement roles

### Operator Lane

This lane is moderately sector-biased.

It should reflect deployment and execution reality:

- integration-heavy vs low-touch
- enterprise rollout vs self-serve
- operational complexity
- scaling difficulty

### Investor Lane

This lane is stage-biased first, sector-biased second.

That means:

- stage determines investor maturity band
- sector and context refine which investor archetypes are most relevant

### Contrarian Lane

As of v0.12.0, contrarian is **capped at 3 agents** (was 6). The freed slots go to customer (+2) and operator (+1). Domain-specific risk analysis is now handled by the **deterministic risk panel** (10 agents post-swarm), not the randomized contrarian lane. The remaining 3 contrarians focus on creative adversarial thinking — "what kills this in 18 months?" — not structured IP/regulatory/competition analysis.

### Analyst Lane

Analyst is a mixed lane driven by market structure, benchmarks, and category positioning.

### Scoring Discipline (v0.12.0)

All persona prompts now include:

- Calibrated 4-tier zone prompts (8-10 exceptional, 6-7.9 credible, 4-5.9 mixed, 0-3.9 weak).
- `SCORING_DISCIPLINE_DIRECTIVE` — anchors scores to evidence, validates 5-7 mid-range.
- MBTI, backstory, risk posture, and scar tissue are framed as **attention directors** (what to stress-test), not score anchors.
- Wildcard weight is **0.2 for serious B2B contexts** (procurement, enterprise, industrial). All other zones weight 1.0.

## Sector Bias Versus Generic Routing

The router is universal, but the customer side is intentionally not generic.

The system works in layers:

1. apply one shared routing framework to every founder
2. detect the real buying environment from the form
3. activate sector and context overlays only when the input supports them
4. let the customer lane become the sharpest sector-specific lane

That avoids two bad outcomes:

- hardcoding favoritism toward only a few sectors
- flattening everyone into generic customer personas

## What Does Not Primarily Choose Personas

These fields do matter, but they are not the main role-selection levers:

- `traction`
- `revenue`
- `funding`
- `team`
- `advantage`
- `ask`
- `risk`
- `extra_context`

They mostly affect:

- prompt calibration
- council interpretation
- research emphasis
- confidence and skepticism
- report emphasis

## How The Form Affects The Rest Of The Pipeline

### Extraction

When `structured_fields` is present, FastAPI builds `ExtractionResult` directly from it. This means the website form is now the main extraction source for founder submissions.

### Research

Research uses the structured extraction to anchor:

- company identity
- industry and product framing
- target market and buyer context
- business model
- stage
- competitor and traction context

This improves research quality because the 6-phase Claude CLI researcher starts from typed facts instead of guessing from a loose summary alone.

### Council

Council uses:

- `exec_summary`
- research output
- `stage`
- `data_quality`

Stage affects calibration. Data quality affects how much the system trusts the extracted submission.

### Swarm

Swarm uses:

- `exec_summary`
- research context
- stage
- first-class buyer/workflow fields
- full `persona_context`

This is where most of the structured form influence becomes visible.

### OASIS

OASIS uses:

- extraction
- research
- council verdict
- swarm agents when available

So form quality still matters indirectly at this stage through everything upstream.

### Reporting

Reporting uses:

- structured extraction
- research
- council
- swarm
- OASIS
- enhancements such as `top_fixes`, `score_forecast`, `rewritten_exec_summary`, `similar_funded`

The form therefore influences not just the score, but also which issues get emphasized in the final report.

## Current Production Notes

- Founder submissions use the website queue plus FastAPI structured passthrough.
- Production swarm size is fixed at `50` (investor=10, customer=14, operator=11, analyst=7, contrarian=3, wildcard=5).
- A **deterministic risk panel** (10 domain-specific agents) runs post-swarm.
- Final verdict: council 78%, swarm 22%, risk panel penalty (max 1.2 points).
- The founder-facing report renderer remains deterministic by default, now including a risk panel table.
- **Outcome tracking** stores structured AnalysisResult + auto-creates 3/6/12 month follow-ups.

## Practical Rule For Future Changes

When the intake form changes, audit all of these surfaces:

- website form
- submit API
- database schema
- `structured_fields`
- `ExtractionResult`
- persona routing
- research assumptions
- serializers
- admin displays
- docs

Use [docs/INTAKE_AUDIT.md](/home/aditya/Downloads/mirai/docs/INTAKE_AUDIT.md) and [scripts/intake-audit.sh](/home/aditya/Downloads/mirai/scripts/intake-audit.sh).
