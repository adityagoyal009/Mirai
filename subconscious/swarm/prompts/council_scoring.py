"""
Stage-Calibrated Council Scoring Rubrics.

Each stage gets anchors appropriate for what's expected at that level.
A pre-seed with 30 customer interviews should score well on social proof,
not get penalized for not having revenue.
"""

VERSION = "4.0.0"

# ── Stage-invariant dimensions (same anchors regardless of stage) ──

_MARKET_TIMING = (
    "1. market_timing — Is this the right moment for this product?\n"
    "   9-10: Market inflection happening NOW (30%+ YoY growth, clear adoption wave)\n"
    "   7-8: Strong growth (15-30% YoY), window open for 2-3 years\n"
    "   5-6: Steady market, no strong tailwinds or headwinds\n"
    "   3-4: Market declining or inflection 3+ years away\n"
    "   1-2: Market saturated or facing structural decline\n"
)

_COMPETITION = (
    "2. competition_landscape — How defensible is their position?\n"
    "   9-10: Clear moat (network effects, patents, >2yr tech lead), <5 direct competitors\n"
    "   7-8: Meaningful differentiation, 5-15 competitors but top 3 position achievable\n"
    "   5-6: Some differentiation on GTM, commodity product, 15+ competitors\n"
    "   3-4: Hard to differentiate, 20+ competitors, price competition\n"
    "   1-2: Commoditized, no moat possible, incumbents dominate\n"
)

_REGULATORY = (
    "5. regulatory_news_environment — Help or hindrance?\n"
    "   9-10: Recent regulation creates moat (compliance = barrier to entry)\n"
    "   7-8: Favorable policy environment, no major regulatory risks\n"
    "   5-6: Neutral — established regulatory regime, predictable\n"
    "   3-4: Upcoming regulation could restrict market or increase costs\n"
    "   1-2: Imminent regulatory threat, prohibitive compliance burden\n"
)

_PATTERN = (
    "7. pattern_match — What do historical precedents predict?\n"
    "   9-10: Strong positive precedent (similar companies at this stage succeeded 70%+)\n"
    "   7-8: Good pattern (comparable exits exist, category proven)\n"
    "   5-6: Mixed precedent (some wins, some failures in category)\n"
    "   3-4: Negative pattern (most similar attempts failed)\n"
    "   1-2: Historically this approach fails (anti-pattern)\n"
)

_EXIT = (
    "10. exit_potential — What's the path to liquidity?\n"
    "   9-10: Multiple strategic acquirers identified, IPO-scale TAM, category leaders acquired at 10x+\n"
    "   7-8: Clear acquirer landscape, proven M&A activity in category\n"
    "   5-6: Some exit precedent, moderate acquirer interest\n"
    "   3-4: Few natural acquirers, small market limits exit size\n"
    "   1-2: No clear exit path, niche market with no acquirer interest\n"
)


# ── Stage-calibrated dimensions ──

_BUSINESS_MODEL = {
    "early": (
        "3. business_model_viability — Is the model plausible for this stage?\n"
        "   9-10: Clear revenue model, pricing validated with target customers, unit economics modeled\n"
        "   7-8: Logical pricing based on buyer research, plausible path to margins\n"
        "   5-6: Revenue model identified but unvalidated, reasonable assumptions\n"
        "   3-4: Vague monetization plan, pricing not grounded in buyer reality\n"
        "   1-2: No revenue model or fundamentally broken economics\n"
    ),
    "mid": (
        "3. business_model_viability — Does the unit economics work?\n"
        "   9-10: Proven unit economics (LTV > 3x CAC), clear path to profitability\n"
        "   7-8: Strong model with realistic margins, some metrics validated\n"
        "   5-6: Plausible model, early revenue but unit economics unproven at scale\n"
        "   3-4: Questionable economics, high CAC or low margins relative to stage\n"
        "   1-2: Burning cash with no viable path to unit economics\n"
    ),
    "mid_b": (
        "3. business_model_viability — Are unit economics proven and improving?\n"
        "   9-10: Strong unit economics at scale (LTV > 4x CAC), gross margins >60%, path to profitability within 18 months\n"
        "   7-8: Healthy margins, CAC payback <18 months, unit economics hold at 3x current scale\n"
        "   5-6: Acceptable margins but CAC rising or LTV compression at scale, needs optimization\n"
        "   3-4: Unit economics deteriorating with scale, subsidizing growth with capital\n"
        "   1-2: Fundamentally uneconomic at current scale, growth making margins worse\n"
    ),
    "late": (
        "3. business_model_viability — Are unit economics proven at scale?\n"
        "   9-10: Best-in-class unit economics (LTV > 5x CAC), profitable or near-profitable\n"
        "   7-8: Strong margins, clear path to profitability within 12-18 months\n"
        "   5-6: Acceptable margins but CAC trending up or LTV uncertain at scale\n"
        "   3-4: Unit economics deteriorating, growth subsidized by capital\n"
        "   1-2: Fundamentally uneconomic at current scale, no fix in sight\n"
    ),
}

_TEAM = {
    "early": (
        "4. team_execution_signals — Can THIS team build THIS at THIS stage?\n"
        "   9-10: Deep domain expertise + technical ability, prior startup or relevant building experience, complementary co-founders\n"
        "   7-8: Strong domain knowledge OR technical depth, has shipped products before, coachable\n"
        "   5-6: Relevant background, first-time founders but learning fast, some gaps addressable\n"
        "   3-4: Limited relevant experience, team gaps in critical areas, unclear founder-market fit\n"
        "   1-2: No domain expertise, no technical depth, solo founder with no clear path to team\n"
    ),
    "mid": (
        "4. team_execution_signals — Can THIS team scale THIS?\n"
        "   9-10: Founder built $5M+ ARR or similar-stage company, full leadership team, strong talent pipeline\n"
        "   7-8: Experienced operator team, key hires made (VP Eng, VP Sales), executing well\n"
        "   5-6: Competent team with gaps, hiring plan exists, some scaling experience\n"
        "   3-4: Key leadership missing, struggling to recruit, founder doing everything\n"
        "   1-2: Team turnover, missing critical roles, execution consistently behind plan\n"
    ),
    "mid_b": (
        "4. team_execution_signals — Is the team scaling with the company?\n"
        "   9-10: Full executive team in place, VP-level hires across functions, proven ability to scale from $3M to $15M+\n"
        "   7-8: Most key hires made, strong middle management emerging, founder transitioning from IC to executive\n"
        "   5-6: Growing but key gaps (missing VP Sales or VP Eng), founder still doing too much IC work\n"
        "   3-4: Team hasn't scaled with company, key departures, hiring behind growth needs\n"
        "   1-2: Leadership crisis, founder burnout, unable to attract senior talent\n"
    ),
    "late": (
        "4. team_execution_signals — Is the leadership team world-class for this scale?\n"
        "   9-10: C-suite from successful scaled companies, deep bench, proven at $50M+ ARR\n"
        "   7-8: Strong operators, most key hires made, track record of hitting milestones\n"
        "   5-6: Adequate team but gaps at VP/C-level, some scaling growing pains\n"
        "   3-4: Under-experienced for this stage, key departures, founder bottleneck\n"
        "   1-2: Leadership crisis, turnover, wrong team for the scale required\n"
    ),
}

_SOCIAL_PROOF = {
    "early": (
        "6. social_proof_demand — Is there real pull at this stage?\n"
        "   9-10: Paying pilots or LOIs from target customers, waitlist, organic inbound interest\n"
        "   7-8: Strong customer discovery (50+ interviews), signed LOIs, accelerator validation\n"
        "   5-6: Meaningful customer conversations (20+), positive signal but no commitments\n"
        "   3-4: Limited customer contact, mostly founder's network, weak pull signals\n"
        "   1-2: No evidence of customer interest, solution looking for a problem\n"
    ),
    "mid": (
        "6. social_proof_demand — Is there proven demand?\n"
        "   9-10: Strong revenue growth ($1M+ ARR), expanding customer base, referenceable logos\n"
        "   7-8: Growing revenue, repeat customers, organic referrals, low churn\n"
        "   5-6: Some paying customers, early revenue, demand exists but unscaled\n"
        "   3-4: Struggling to convert pilots to contracts, high churn, slow growth\n"
        "   1-2: Minimal revenue despite time in market, customers churning\n"
    ),
    "mid_b": (
        "6. social_proof_demand — Is demand scaling predictably?\n"
        "   9-10: $3M+ ARR, strong NRR (>110%), expanding into new segments, recognized brand in vertical\n"
        "   7-8: $1.5M+ ARR, healthy growth rate (>2x YoY), repeat expansion, low logo churn (<10%)\n"
        "   5-6: Revenue growing but below expectations, some expansion but high new-logo dependency\n"
        "   3-4: Growth stalling, churn offsetting new revenue, struggling to break into new segments\n"
        "   1-2: Revenue plateauing or declining, high churn, market not pulling\n"
    ),
    "late": (
        "6. social_proof_demand — Is market pull undeniable?\n"
        "   9-10: $10M+ ARR, category leader recognition, enterprise logos, strong NRR (>120%)\n"
        "   7-8: $5M+ ARR, healthy growth, known brand in vertical, solid retention\n"
        "   5-6: Revenue growing but below category benchmarks, some market recognition\n"
        "   3-4: Growth stalling, losing to competitors, brand not resonating\n"
        "   1-2: Revenue declining, market share eroding, existential demand problem\n"
    ),
}

_CAPITAL_EFFICIENCY = {
    "early": (
        "8. capital_efficiency — How well are they using limited resources?\n"
        "   9-10: Bootstrapped or minimal burn to meaningful milestones, grants/non-dilutive funding secured\n"
        "   7-8: Lean operations, 18+ months runway, smart use of accelerator resources\n"
        "   5-6: Normal burn for stage, 12+ months runway, spending on right priorities\n"
        "   3-4: Burning faster than stage warrants, spending before validation\n"
        "   1-2: Wasteful spending, no financial discipline, will run out before next milestone\n"
    ),
    "mid": (
        "8. capital_efficiency — How well do they deploy capital?\n"
        "   9-10: Efficient growth (burn multiple < 1.5x), 18+ months runway, milestones ahead of plan\n"
        "   7-8: Healthy burn rate for stage, 12-18 months runway, capital-efficient growth\n"
        "   5-6: Normal burn, 6-12 months runway, on track but tight\n"
        "   3-4: High burn rate, <6 months runway, spending ahead of validation\n"
        "   1-2: Burning cash with no clear milestones, will need emergency raise\n"
    ),
    "mid_b": (
        "8. capital_efficiency — Is capital driving efficient scale?\n"
        "   9-10: Burn multiple < 1.5x at $3M+ ARR, 18+ months runway, could reach profitability if needed\n"
        "   7-8: Healthy burn for growth rate, 12-18 months runway, clear milestones for next raise\n"
        "   5-6: Burn higher than growth justifies, 6-12 months runway, needs optimization\n"
        "   3-4: Burning faster than revenue growing, <6 months runway, no path to efficient growth\n"
        "   1-2: Cash crisis, burn unsustainable, growth not covering increasing costs\n"
    ),
    "late": (
        "8. capital_efficiency — Is the path to profitability clear?\n"
        "   9-10: Cash flow positive or clear path within 6 months, efficient growth engine\n"
        "   7-8: Improving margins, 18+ months runway, unit economics trending to profitability\n"
        "   5-6: Margins acceptable but improving slowly, dependent on next raise\n"
        "   3-4: Still losing money at scale, no clear path to profitability\n"
        "   1-2: Burning cash faster at scale, profitability requires fundamental model change\n"
    ),
}

_SCALABILITY = {
    "early": (
        "9. scalability_potential — Can this concept scale?\n"
        "   9-10: Software/platform model with near-zero marginal cost, clear architecture for growth\n"
        "   7-8: Scalable approach with some ops needed, no fundamental bottleneck\n"
        "   5-6: Can scale with proportional investment, reasonable growth path\n"
        "   3-4: Scaling will require heavy ops/human intervention, linear cost growth\n"
        "   1-2: Fundamentally hard to scale (heavy services, local-only, regulatory per-market)\n"
    ),
    "mid": (
        "9. scalability_potential — Can this 10x without breaking?\n"
        "   9-10: Architecture proven at current scale, near-zero marginal cost, ops leverage built\n"
        "   7-8: Clear technical path to 10x, some infrastructure investment needed\n"
        "   5-6: Can scale with significant investment, no fundamental blockers\n"
        "   3-4: Scaling hitting bottlenecks, requires re-architecture or heavy ops\n"
        "   1-2: Current model breaks at 3-5x, fundamental redesign needed\n"
    ),
    "mid_b": (
        "9. scalability_potential — Is the architecture proven for the next 10x?\n"
        "   9-10: Infrastructure handles 10x current load, ops automated, marginal cost decreasing\n"
        "   7-8: Architecture solid, some investment needed for next order of magnitude\n"
        "   5-6: Growing pains visible, infrastructure investment required before next scale jump\n"
        "   3-4: Scaling causing reliability issues, architecture needs significant rework\n"
        "   1-2: Breaking at current scale, technical debt blocking growth\n"
    ),
    "late": (
        "9. scalability_potential — Is scale proven?\n"
        "   9-10: Operating at scale with efficient margins, proven 100x capacity\n"
        "   7-8: Scaled successfully, infrastructure solid, ops efficient\n"
        "   5-6: Scaling but with growing pains, ops costs rising\n"
        "   3-4: Scale creating quality/reliability issues, ops costs outpacing revenue\n"
        "   1-2: Breaking under current scale, fundamental architecture problems\n"
    ),
}


def _stage_to_tier(stage: str) -> str:
    """Map stage names to rubric tiers."""
    stage_lower = (stage or "").lower().strip()
    if stage_lower in ("idea", "pre-seed", "pre seed", "preseed", "seed", "mvp"):
        return "early"
    elif stage_lower in ("series a", "series-a", "revenue"):
        return "mid"
    elif stage_lower in ("series b", "series-b"):
        return "mid_b"
    elif stage_lower in ("series c", "series c+", "series-c", "growth", "pre-ipo", "late stage", "scaling"):
        return "late"
    else:
        return "early"  # Default to early (safer than mid — avoids penalizing young startups)


def get_scoring_prompt(stage: str = "") -> str:
    """Build the council scoring prompt calibrated for the startup's stage."""
    tier = _stage_to_tier(stage)
    stage_label = stage or "unknown stage"

    header = (
        f"You are a venture analyst evaluating a {stage_label} startup. "
        "For EACH of the 10 dimensions below, first write 2-3 sentences of reasoning, THEN assign a score 1-10.\n\n"
        f"IMPORTANT: Score anchors are calibrated for {stage_label} companies. "
        f"Judge this startup against what is EXPECTED at the {stage_label} stage, "
        "not against later-stage companies.\n\n"
        "SCORING RUBRIC:\n\n"
    )

    dimensions = [
        _MARKET_TIMING,
        _COMPETITION,
        _BUSINESS_MODEL[tier],
        _TEAM[tier],
        _REGULATORY,
        _SOCIAL_PROOF[tier],
        _PATTERN,
        _CAPITAL_EFFICIENCY[tier],
        _SCALABILITY[tier],
        _EXIT,
    ]

    footer = (
        "\nIMPORTANT: Write your reasoning BEFORE choosing a score. Do not pick a number first.\n"
        "Use decimal scores (e.g., 3.5, 6.2, 7.8) for precision — a 6.2 is meaningfully different from a 6.8.\n"
        "ANTI-CENTER-BIAS: If your reasoning clearly supports a score above 7.0 or below 4.0, "
        "commit to it. Scores of 5.0-6.0 mean genuinely average — not 'I'm unsure.' "
        "Do not hedge toward the middle when your analysis points to the extremes.\n\n"
        "Return JSON with key 'dimensions' containing a list of 10 objects, "
        "each with: name (str), reasoning (str), score (float 0.0-10.0). "
        "Also include 'overall_reasoning' (str) and 'confidence' (float 0-1)."
    )

    return header + "\n".join(dimensions) + footer


# Legacy single prompt for backward compatibility
PROMPT = get_scoring_prompt("Seed")
