"""
Agentic Researcher — multi-provider live web research.

Primary path uses Claude Code CLI with native WebSearch/WebFetch tools.
If Claude research fails, the researcher falls back to the existing OpenClaw
subagent path. Gemini remains the final fallback in business_intel.py.

Structuring/synthesis uses Mirai gateway API for JSON repair/structuring.
"""

import json
import os
import re
import subprocess
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Any, List, Dict, Optional

from ..config import Config, get_researcher_models
# cli_llm imported locally in _parse_research_json for gateway structuring fallback
from ..utils.logger import get_logger
from .search_engine import SOURCE_CREDIBILITY, _extract_root_domain
from .hallucination_guard import check_faithfulness

logger = get_logger('mirofish.agentic_researcher')

# Research model config
_MODELS = get_researcher_models()
RESEARCH_MODEL = _MODELS.get("researcher_a", "claude-sonnet-4-6")
STRUCTURING_MODEL = "claude-sonnet-4-6"

# Claude CLI config (primary research path)
_CLAUDE_CLI_AVAILABLE: Optional[bool] = None

# OpenClaw gateway config (for subagent research with native web search)
_OPENCLAW_URL = os.environ.get("OPENCLAW_GATEWAY_URL", "http://127.0.0.1:18789")
_OPENCLAW_TOKEN = os.environ.get("OPENCLAW_GATEWAY_TOKEN", "")
_OPENCLAW_AVAILABLE: Optional[bool] = None


def _check_claude_cli() -> bool:
    """Check whether Claude Code CLI is installed and callable."""
    global _CLAUDE_CLI_AVAILABLE
    if _CLAUDE_CLI_AVAILABLE is not None:
        return _CLAUDE_CLI_AVAILABLE
    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        _CLAUDE_CLI_AVAILABLE = result.returncode == 0
    except Exception:
        _CLAUDE_CLI_AVAILABLE = False
    if _CLAUDE_CLI_AVAILABLE:
        logger.info("[AgenticResearch] Claude Code CLI available — using Claude-first research")
    else:
        logger.warning("[AgenticResearch] Claude Code CLI not available — will fall back to OpenClaw")
    return _CLAUDE_CLI_AVAILABLE


def _call_claude_cli_research(prompt: str, timeout: int = 300) -> str:
    """Call Claude Code CLI with native web search tools enabled."""
    result = subprocess.run(
        [
            "claude",
            "-p",
            prompt,
            "--allowedTools",
            "WebSearch,WebFetch",
            "--output-format",
            "text",
            "--max-turns",
            "30",
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Claude CLI research failed (exit {result.returncode}): "
            f"{(result.stderr or result.stdout or '').strip()[:500]}"
        )
    output = result.stdout.strip()
    if not output:
        raise RuntimeError("Claude CLI returned empty response")
    return output


def _get_openclaw_token() -> str:
    """Read OpenClaw gateway token from config if not in env."""
    global _OPENCLAW_TOKEN
    if _OPENCLAW_TOKEN:
        return _OPENCLAW_TOKEN
    try:
        config_path = os.path.expanduser("~/.openclaw/openclaw.json")
        with open(config_path) as f:
            cfg = json.load(f)
        _OPENCLAW_TOKEN = cfg.get("gateway", {}).get("auth", {}).get("token", "")
    except Exception:
        pass
    return _OPENCLAW_TOKEN


def _check_openclaw() -> bool:
    """Check if OpenClaw gateway is available."""
    global _OPENCLAW_AVAILABLE
    if _OPENCLAW_AVAILABLE is not None:
        return _OPENCLAW_AVAILABLE
    token = _get_openclaw_token()
    if not token:
        _OPENCLAW_AVAILABLE = False
        logger.error("[AgenticResearch] No OpenClaw token configured in ~/.openclaw/openclaw.json")
        return False
    try:
        req = urllib.request.Request(f"{_OPENCLAW_URL}/health")
        with urllib.request.urlopen(req, timeout=3) as resp:
            _OPENCLAW_AVAILABLE = resp.status == 200
    except Exception:
        _OPENCLAW_AVAILABLE = False
    if _OPENCLAW_AVAILABLE:
        logger.info(f"[AgenticResearch] OpenClaw gateway available — using subagent for research")
    else:
        logger.error(f"[AgenticResearch] OpenClaw gateway not available at {_OPENCLAW_URL}")
    return _OPENCLAW_AVAILABLE


def _call_openclaw_research(prompt: str, timeout: int = 600) -> Optional[str]:
    """Call OpenClaw gateway as an agent with native web search tools.
    Returns the agent's response text, or None if failed."""
    token = _get_openclaw_token()
    payload = json.dumps({
        "model": "openclaw",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 16000,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{_OPENCLAW_URL}/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "x-openclaw-scopes": "operator.read,operator.write",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    choices = body.get("choices", [])
    if not choices:
        return None
    content = choices[0].get("message", {}).get("content", "")
    return content if content else None

def _normalize_context_value(value: Any) -> str:
    return str(value or "").strip()


def _has_any(text: str, terms: List[str]) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in terms)


def _build_adaptive_research_emphasis(adaptive_context: Optional[Dict[str, Any]]) -> str:
    if not adaptive_context:
        return "- Keep the universal diligence backbone, but prioritize the strongest available evidence over generic filler."

    stage = _normalize_context_value(adaptive_context.get("stage"))
    business_model = _normalize_context_value(adaptive_context.get("business_model"))
    sales_motion = _normalize_context_value(adaptive_context.get("sales_motion"))
    end_user = _normalize_context_value(adaptive_context.get("end_user"))
    economic_buyer = _normalize_context_value(adaptive_context.get("economic_buyer"))
    switching_trigger = _normalize_context_value(adaptive_context.get("switching_trigger"))
    current_substitute = _normalize_context_value(adaptive_context.get("current_substitute"))
    contract_size = _normalize_context_value(adaptive_context.get("typical_contract_size"))
    implementation_complexity = _normalize_context_value(adaptive_context.get("implementation_complexity"))
    primary_risk = _normalize_context_value(adaptive_context.get("primary_risk_category"))

    emphasis: List[str] = [
        "- Keep the same 10-step diligence backbone for every company. Adapt priority and depth, not the overall framework.",
    ]

    if stage:
        stage_lower = stage.lower()
        if _has_any(stage_lower, ["pre-seed", "preseed", "seed", "angel", "idea", "mvp"]):
            emphasis.append(
                "- Stage emphasis: early stage. Prioritize founder credibility, buyer pain severity, switching behavior, early proof, and whether the wedge is sharp. Do not over-index on missing late-stage financial polish."
            )
        elif _has_any(stage_lower, ["series a", "series-a", "series b", "series-b", "growth", "scale"]):
            emphasis.append(
                "- Stage emphasis: post-seed scaling. Prioritize repeatability, GTM efficiency, retention/expansion, category structure, competitive durability, and evidence that growth is not just one-off."
            )
        else:
            emphasis.append(
                f"- Stage emphasis: {stage}. Calibrate diligence to what is realistic for this stage while still pressure-testing credibility and momentum."
            )

    if business_model:
        model_lower = business_model.lower()
        if _has_any(model_lower, ["saas", "subscription", "recurring"]):
            emphasis.append(
                "- Business-model emphasis: recurring revenue. Verify pricing logic, seat/usage expansion potential, churn or stickiness signals, implementation burden, and margin plausibility."
            )
        elif _has_any(model_lower, ["marketplace", "take rate", "transaction"]):
            emphasis.append(
                "- Business-model emphasis: marketplace/transaction. Verify liquidity constraints, supply-demand balance, take-rate power, disintermediation risk, and repeat usage."
            )
        elif _has_any(model_lower, ["services", "agency", "consulting"]):
            emphasis.append(
                "- Business-model emphasis: services-heavy. Verify delivery margin, dependence on headcount growth, implementation intensity, and whether there is a credible path to scale beyond bespoke work."
            )
        elif _has_any(model_lower, ["hardware", "device", "robot", "manufactur", "industrial", "deeptech"]):
            emphasis.append(
                "- Business-model emphasis: hardware/industrial. Verify deployment reality, supply chain constraints, field reliability, certification/compliance burden, and time to operational proof."
            )

    if sales_motion:
        sales_lower = sales_motion.lower()
        if _has_any(sales_lower, ["enterprise", "top-down", "direct sales", "procurement", "public sector", "district"]):
            emphasis.append(
                "- GTM emphasis: procurement-heavy motion. Focus on budget ownership, buying committee reality, implementation/security review, procurement cycle length, and what proof is required to close."
            )
        elif _has_any(sales_lower, ["plg", "product-led", "self-serve", "bottom-up", "consumer"]):
            emphasis.append(
                "- GTM emphasis: self-serve or bottoms-up. Focus on activation, retention, user love, switching friction, incumbent workaround behavior, and efficient distribution."
            )
        elif _has_any(sales_lower, ["channel", "partner", "reseller"]):
            emphasis.append(
                "- GTM emphasis: channel-led. Focus on partner incentives, ecosystem dependency, implementation ownership, and whether channel economics remain attractive."
            )

    if end_user or economic_buyer:
        emphasis.append(
            f"- Customer specificity: customer and workflow research must match the stated context. End user: {end_user or 'not provided'}. Economic buyer: {economic_buyer or 'not provided'}. Do not substitute generic enterprise buyers if the described customer is sector-specific or consumer."
        )

    if switching_trigger:
        emphasis.append(
            f"- Switching dynamics: investigate whether the stated trigger is real and urgent. Claimed switching trigger: {switching_trigger}."
        )

    if current_substitute:
        emphasis.append(
            f"- Substitute analysis: study the real incumbent or workaround, why it persists, and what friction exists in replacing it. Current substitute: {current_substitute}."
        )

    if contract_size:
        emphasis.append(
            f"- Commercial reality: calibrate diligence to the stated contract size. Typical contract size: {contract_size}. Assess whether buyer proof and sales motion are consistent with that ACV."
        )

    if implementation_complexity:
        emphasis.append(
            f"- Deployment reality: assess onboarding/integration burden and time to operational value. Implementation complexity: {implementation_complexity}."
        )

    if primary_risk:
        emphasis.append(
            f"- Risk emphasis: pressure-test the stated primary risk category with evidence, not generic startup risks. Primary risk category: {primary_risk}."
        )

    return "\n".join(emphasis)


OPENCLAW_FALLBACK_PROMPT = """You are a PitchBook-level venture capital analyst producing institutional-quality due diligence. You have live web search. Research MUST match PitchBook depth.

STARTUP UNDER ANALYSIS:
  Company: {company}
  Industry: {industry}
  Product: {product}
  Target Market: {target_market}
  {extra_context}

ADAPTIVE RESEARCH EMPHASIS:
{adaptive_research_emphasis}

RESEARCH PROTOCOL — Execute EVERY step. Search the web for each one. Follow leads when you find interesting information. If a search returns nothing useful, try alternative queries.

STEP 1: COMPANY DEEP DIVE
- Search for and visit the company's website. Read homepage, product page, pricing page, about/team page.
- Extract: exact product features, pricing tiers with dollar amounts, employee count, office locations.
- Entity type (Private, Public), business status (Generating Revenue, Pre-Revenue, Growth Stage).
- Any customer logos, case studies, or traction metrics on the site.
- LinkedIn URL and social media presence.

STEP 2: TEAM & LEADERSHIP
- Search for each founder/executive by name on LinkedIn, Crunchbase.
- For each person: full name, exact title, prior companies, years of experience, education.
- Board members: name, title, firm they represent.
- Is the team complete or are there critical gaps?

STEP 3: DEAL HISTORY & FUNDING
- Search Crunchbase, PitchBook, news for EVERY funding round.
- For each round: date, deal type, amount raised, pre/post-money valuation, lead investors.
- Total raised to date. Most recent financing status.

STEP 4: COMPETITOR DEEP DIVE
- For each known competitor AND any you discover:
  - Visit their website for: product description, HQ, year founded, employee count.
  - Search for their funding: total raised, last round, valuation.
  - What specifically differentiates them from the startup?
- Find at least 5-8 competitors. Search "[industry] startups funded 2024 2025 2026" for missed ones.

STEP 5: MARKET SIZING
- Search for "[industry] market size 2024 2025" from Grand View Research, MarketsandMarkets, Statista.
- Find: TAM, SAM with specific dollar figures, CAGR, and source citation.
- Industry benchmarks (average margins, CAC, LTV) if available.

STEP 6: PATENT & IP LANDSCAPE
- Search USPTO and Google Patents for patents by the company or founders.
- Count: total families, active, pending, expiring.
- Key competitor patents. Freedom-to-operate assessment.

STEP 7: REGULATORY ENVIRONMENT
- Regulations that apply: EPA, FDA, SEC, state/local, data privacy.
- Pending regulations creating opportunities or threats.
- Compliance costs and barriers to entry.

STEP 8: CUSTOMER EVIDENCE & SOCIAL PROOF
- Search G2, Capterra, Product Hunt, HackerNews, Reddit, Twitter/X for mentions.
- Published case studies, pilot results, LOIs, contracts.
- Customer reviews, NPS scores, retention data.

STEP 9: PRICING & UNIT ECONOMICS
- Company pricing from website (exact tiers and dollar amounts).
- Competitor pricing comparison.
- Assessment: competitive positioning, margin sustainability.

STEP 10: RISK FACTORS
- What could kill this company?
- Similar companies that failed in this space — why?
- Concentration risks, technology risk, execution risk, market timing risk.

VERIFICATION PASS:
After completing Steps 1-10, review your findings. For any claim about funding amounts, team members, market size, or competitor data — verify it with a second search if you're not confident. Flag anything you couldn't verify.

OUTPUT FORMAT — Return ONLY valid JSON (no markdown, no prose, no explanation):
{{
  "summary": "4-5 paragraph executive research summary with specific numbers and source citations",
  "company_profile": {{
    "description": "1-2 sentence company description",
    "product_description": "What they build/sell, key features",
    "entity_type": "Private Company / Public",
    "business_status": "Generating Revenue / Pre-Revenue / Growth Stage",
    "pricing": "Exact pricing tiers or 'Not publicly listed'",
    "employee_count": "Number or estimate",
    "hq_location": "City, State/Country",
    "year_founded": "YYYY",
    "website": "URL",
    "linkedin": "URL or not found",
    "verticals": ["Vertical 1", "Vertical 2"],
    "keywords": ["keyword1", "keyword2"],
    "traction": "Metrics, customers, pilots, revenue",
    "website_findings": "Key claims and data from their website"
  }},
  "team": [
    {{"name": "Full Name", "title": "Exact Title", "background": "Prior companies, experience, education"}}
  ],
  "board_members": [
    {{"name": "Full Name", "title": "Board Member", "representing": "Firm Name or Self"}}
  ],
  "deal_history": [
    {{"date": "DD-Mon-YYYY", "deal_type": "Series A / Seed", "amount": "$XM", "raised_to_date": "$XM", "pre_valuation": "$XM", "post_valuation": "$XM", "lead_investors": "Firm 1", "status": "Completed"}}
  ],
  "total_raised": "$X.XM",
  "last_valuation": "$XM",
  "competitors": ["Company A", "Company B"],
  "competitor_details": [
    {{"name": "Company A", "description": "1-2 sentences", "primary_industry": "Industry", "hq_location": "City, Country", "year_founded": "YYYY", "employees": "X", "financing_status": "VC-Backed / Self-Funded", "total_raised": "$XM", "last_financing": "Date / Type", "post_valuation": "$XM", "differentiator": "vs the startup"}}
  ],
  "market_data": {{
    "tam": "$X.XB",
    "sam": "$X.XB",
    "som": "$X.XM",
    "growth_rate": "X.X% CAGR",
    "source": "Research firm, year",
    "industry_benchmarks": "Avg margins, CAC, LTV if found"
  }},
  "financials": {{
    "revenue": "Amount or Not Available",
    "revenue_growth": "% or Not Available",
    "ebitda": "Amount or Not Available"
  }},
  "patents": {{
    "total_families": 0,
    "active": 0,
    "pending": 0,
    "expiring_12mo": 0,
    "key_patents": ["Patent title - ID - Status"],
    "competitor_ip": "Summary of competitor patent activity",
    "freedom_to_operate": "Assessment"
  }},
  "regulatory": ["Regulation and its specific impact"],
  "trends": ["Industry trend with evidence"],
  "pricing_analysis": {{
    "startup_pricing": "Their pricing",
    "competitor_pricing": "What competitors charge",
    "model_type": "Subscription / Per-use / Freemium",
    "assessment": "Competitive positioning"
  }},
  "customer_evidence": ["Specific review/testimonial/case study"],
  "risks": ["Risk with evidence and severity"],
  "facts": ["Specific verifiable fact [Source: URL or name]"],
  "sources": [{{"url": "https://...", "title": "Source title"}}]
}}

CRITICAL RULES:
1. Return RAW JSON only. No markdown fences. No text before or after.
2. Every claim must come from your web searches, not training data.
3. If you cannot find data for a field, use "Not found" or 0 — do NOT fabricate.
4. Visit actual websites — don't guess what's on them.
5. For competitors, search each one individually.
6. Verify any suspicious numbers with a second search."""


_RESEARCH_PHASES: List[Dict[str, Any]] = [
    {
        "name": "company_product",
        "label": "Company & Product",
        "progress": "Phase 1/6: Company, product, website, and traction...",
        "timeout": 240,
        "instructions": """STEP 1: COMPANY DEEP DIVE
- Search for and visit the company's website. Read homepage, product page, pricing page, about/team page.
- Extract exact product features, pricing tiers with dollar amounts, employee count, office locations.
- Determine entity type (Private/Public) and business status (Generating Revenue / Pre-Revenue / Growth Stage).
- Capture customer logos, case studies, traction metrics, LinkedIn URL, and social presence if available.""",
        "schema": """{
  "company_profile": {
    "description": "1-2 sentence company description",
    "product_description": "What they build/sell, key features",
    "entity_type": "Private Company / Public",
    "business_status": "Generating Revenue / Pre-Revenue / Growth Stage",
    "pricing": "Exact pricing tiers or 'Not publicly listed'",
    "employee_count": "Number or estimate",
    "hq_location": "City, State/Country",
    "year_founded": "YYYY",
    "website": "URL",
    "linkedin": "URL or not found",
    "verticals": ["Vertical 1", "Vertical 2"],
    "keywords": ["keyword1", "keyword2"],
    "traction": "Metrics, customers, pilots, revenue",
    "website_findings": "Key claims and data from their website"
  },
  "financials": {
    "revenue": "Amount or Not Available",
    "revenue_growth": "% or Not Available",
    "ebitda": "Amount or Not Available"
  },
  "facts": ["Specific verifiable fact [Source: URL or name]"],
  "sources": [{"url": "https://...", "title": "Source title"}]
}""",
    },
    {
        "name": "team_leadership",
        "label": "Team & Leadership",
        "progress": "Phase 2/6: Founders, executives, and board...",
        "timeout": 240,
        "instructions": """STEP 2: TEAM & LEADERSHIP
- Search for each founder/executive by name on LinkedIn, Crunchbase, press, and company bios.
- For each person: full name, exact title, prior companies, years of experience, education.
- Identify board members and what firm or background they represent.
- Note whether the leadership team looks complete or whether there are obvious gaps.""",
        "schema": """{
  "team": [
    {"name": "Full Name", "title": "Exact Title", "background": "Prior companies, experience, education"}
  ],
  "board_members": [
    {"name": "Full Name", "title": "Board Member", "representing": "Firm Name or Self"}
  ],
  "facts": ["Specific verifiable fact [Source: URL or name]"],
  "sources": [{"url": "https://...", "title": "Source title"}]
}""",
    },
    {
        "name": "funding_history",
        "label": "Funding & Deal History",
        "progress": "Phase 3/6: Funding rounds and deal history...",
        "timeout": 240,
        "instructions": """STEP 3: DEAL HISTORY & FUNDING
- Search Crunchbase, PitchBook, SEC/news coverage for every funding round you can verify.
- For each round: date, deal type, amount raised, pre/post-money valuation if available, lead investors.
- Estimate total raised to date and latest financing status.
- Prefer sourced facts over speculation.""",
        "schema": """{
  "deal_history": [
    {"date": "DD-Mon-YYYY", "deal_type": "Series A / Seed", "amount": "$XM", "raised_to_date": "$XM", "pre_valuation": "$XM", "post_valuation": "$XM", "lead_investors": "Firm 1", "status": "Completed"}
  ],
  "total_raised": "$X.XM",
  "last_valuation": "$XM",
  "facts": ["Specific verifiable fact [Source: URL or name]"],
  "sources": [{"url": "https://...", "title": "Source title"}]
}""",
    },
    {
        "name": "competitors",
        "label": "Competitor Deep Dive",
        "progress": "Phase 4/6: Competitors and differentiation...",
        "timeout": 360,
        "instructions": """STEP 4: COMPETITOR DEEP DIVE
- For each known competitor and any you discover:
  - Visit their website for product description, HQ, year founded, employee count.
  - Search for their funding: total raised, last round, valuation if available.
  - Capture what specifically differentiates them from the startup.
- Find at least 5-8 competitors. Search "[industry] startups funded 2024 2025 2026" for missed ones.
- Search each competitor individually rather than treating the category generically.""",
        "schema": """{
  "competitors": ["Company A", "Company B"],
  "competitor_details": [
    {"name": "Company A", "description": "1-2 sentences", "primary_industry": "Industry", "hq_location": "City, Country", "year_founded": "YYYY", "employees": "X", "financing_status": "VC-Backed / Self-Funded", "total_raised": "$XM", "last_financing": "Date / Type", "post_valuation": "$XM", "differentiator": "vs the startup"}
  ],
  "facts": ["Specific verifiable fact [Source: URL or name]"],
  "sources": [{"url": "https://...", "title": "Source title"}]
}""",
    },
    {
        "name": "market_regulatory_ip",
        "label": "Market, Regulatory, and IP",
        "progress": "Phase 5/6: Market sizing, regulation, and IP landscape...",
        "timeout": 300,
        "instructions": """STEP 5: MARKET SIZING
- Search for market size, TAM/SAM/SOM, CAGR, and industry benchmarks from reputable market analyses.

STEP 6: PATENT & IP LANDSCAPE
- Search USPTO and Google Patents for patents by the company or founders.
- Count total families, active, pending, expiring, and summarize freedom-to-operate concerns.

STEP 7: REGULATORY ENVIRONMENT
- Search the regulations that actually apply: EPA, FDA, SEC, state/local, data privacy, and industry-specific rules.
- Note pending regulations, compliance costs, or barrier-to-entry implications.

Return evidence, not generic category filler.""",
        "schema": """{
  "market_data": {
    "tam": "$X.XB",
    "sam": "$X.XB",
    "som": "$X.XM",
    "growth_rate": "X.X% CAGR",
    "source": "Research firm, year",
    "industry_benchmarks": "Avg margins, CAC, LTV if found"
  },
  "patents": {
    "total_families": 0,
    "active": 0,
    "pending": 0,
    "expiring_12mo": 0,
    "key_patents": ["Patent title - ID - Status"],
    "competitor_ip": "Summary of competitor patent activity",
    "freedom_to_operate": "Assessment"
  },
  "regulatory": ["Regulation and its specific impact"],
  "trends": ["Industry trend with evidence"],
  "facts": ["Specific verifiable fact [Source: URL or name]"],
  "sources": [{"url": "https://...", "title": "Source title"}]
}""",
    },
    {
        "name": "evidence_risk_synthesis",
        "label": "Customer Evidence, Pricing, Risks, and Synthesis",
        "progress": "Phase 6/6: Customer proof, pricing, risks, and executive synthesis...",
        "timeout": 300,
        "instructions": """STEP 8: CUSTOMER EVIDENCE & SOCIAL PROOF
- Search G2, Capterra, Product Hunt, HackerNews, Reddit, Twitter/X, case studies, pilots, LOIs, contracts.
- Capture customer proof, reviews, and any traction signals you can verify.

STEP 9: PRICING & UNIT ECONOMICS
- Re-check company pricing from website or public collateral.
- Compare pricing against competitors and assess competitive positioning.

STEP 10: RISK FACTORS
- What could kill this company?
- Similar companies that failed in this space — why?
- Concentration risks, technology risk, execution risk, market timing risk.

EXECUTIVE SUMMARY
- Write a 4-5 paragraph executive research summary covering the full company, team, funding, market, competition, patents, regulatory, customers, pricing, and risks.
- Use specific numbers and source citations.""",
        "schema": """{
  "summary": "4-5 paragraph executive research summary with specific numbers and source citations",
  "pricing_analysis": {
    "startup_pricing": "Their pricing",
    "competitor_pricing": "What competitors charge",
    "model_type": "Subscription / Per-use / Freemium",
    "assessment": "Competitive positioning"
  },
  "customer_evidence": ["Specific review/testimonial/case study"],
  "risks": ["Risk with evidence and severity"],
  "facts": ["Specific verifiable fact [Source: URL or name]"],
  "sources": [{"url": "https://...", "title": "Source title"}]
}""",
    },
]


def _build_phase_context_summary(findings: Dict[str, Any]) -> str:
    """Build a compact context summary for later research phases."""
    if not findings:
        return "- None yet."

    company_profile = findings.get("company_profile", {}) if isinstance(findings.get("company_profile"), dict) else {}
    team = findings.get("team", []) if isinstance(findings.get("team"), list) else []
    competitors = findings.get("competitors", []) if isinstance(findings.get("competitors"), list) else []
    market_data = findings.get("market_data", {}) if isinstance(findings.get("market_data"), dict) else {}
    patents = findings.get("patents", findings.get("patent_landscape", {}))
    patents = patents if isinstance(patents, dict) else {}
    regulatory = findings.get("regulatory", []) if isinstance(findings.get("regulatory"), list) else []
    trends = findings.get("trends", []) if isinstance(findings.get("trends"), list) else []

    parts = [
        f"- Website: {company_profile.get('website', 'Not found')}",
        f"- Product: {company_profile.get('product_description', 'Not found')}",
        f"- Pricing: {company_profile.get('pricing', 'Not found')}",
        f"- HQ: {company_profile.get('hq_location', 'Not found')}",
        f"- Team: {', '.join(str(t.get('name', '')) for t in team[:6] if isinstance(t, dict) and t.get('name')) or 'Not found'}",
        f"- Total raised: {findings.get('total_raised', 'Not found') or 'Not found'}",
        f"- Competitors: {', '.join(str(c) for c in competitors[:8]) or 'Not found'}",
        f"- Market size source: {market_data.get('source', 'Not found')}",
        f"- Patents: {patents.get('total_families', 'Not researched')} families",
        f"- Regulatory: {', '.join(str(item)[:80] for item in regulatory[:3]) or 'Not researched'}",
        f"- Trends: {', '.join(str(item)[:80] for item in trends[:3]) or 'Not researched'}",
    ]
    return "\n".join(parts)


def _build_phase_prompt(
    phase: Dict[str, Any],
    *,
    company: str,
    industry: str,
    product: str,
    target_market: str,
    extra_context: str,
    adaptive_research_emphasis: str,
    prior_context: str,
) -> str:
    extra_context_block = extra_context or "No additional founder context provided."
    prior_context_block = prior_context or "- None yet."
    return f"""You are a PitchBook-level venture capital analyst producing institutional-quality due diligence. You have live web search.

STARTUP UNDER ANALYSIS:
  Company: {company}
  Industry: {industry}
  Product: {product}
  Target Market: {target_market}
  {extra_context_block}

ALREADY RESEARCHED CONTEXT:
{prior_context_block}

ADAPTIVE RESEARCH EMPHASIS:
{adaptive_research_emphasis}

CURRENT PHASE:
{phase["label"]}

RESEARCH TASKS:
{phase["instructions"]}

OUTPUT FORMAT — Return ONLY valid JSON (no markdown, no prose):
{phase["schema"]}

CRITICAL RULES:
1. Return RAW JSON only. No markdown fences. No text before or after.
2. Every claim must come from your web searches, not training data.
3. If you cannot find data for a field, use "Not found" or 0 — do NOT fabricate.
4. Visit actual websites when relevant — don't guess what's on them.
5. Verify suspicious numbers with a second search before asserting them."""


def _merge_research_phase_dicts(phases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge N structured research phase outputs into the full findings schema."""
    merged: Dict[str, Any] = {}

    for phase in phases:
        for key, value in phase.items():
            if key in {"facts", "sources"}:
                continue
            if key == "summary":
                if value:
                    merged["summary"] = value
                continue
            if value in (None, "", [], {}):
                merged.setdefault(key, value)
            else:
                merged[key] = value

    all_facts: List[str] = []
    for phase in phases:
        facts = phase.get("facts", [])
        if isinstance(facts, list):
            all_facts.extend(str(f) for f in facts if f)
    merged["facts"] = all_facts

    merged_sources: List[Dict[str, Any]] = []
    seen_urls = set()
    for phase in phases:
        sources = phase.get("sources", [])
        if not isinstance(sources, list):
            continue
        for source in sources:
            if not isinstance(source, dict):
                continue
            url = str(source.get("url", "") or "").strip()
            dedupe_key = url or json.dumps(source, sort_keys=True, default=str)
            if dedupe_key in seen_urls:
                continue
            seen_urls.add(dedupe_key)
            merged_sources.append(source)
    merged["sources"] = merged_sources
    return merged


STRUCTURING_PROMPT = """Extract structured data from this research report into JSON.

RESEARCH REPORT:
{report_text}

Return ONLY valid JSON (no markdown):
{{
  "summary": "3-5 paragraph summary with key data points and source citations",
  "company_profile": {{"description": "...", "product_description": "...", "pricing": "...", "hq_location": "...", "year_founded": "...", "website": "...", "linkedin": "...", "traction": "..."}},
  "team": [{{"name": "...", "title": "...", "background": "..."}}],
  "board_members": [{{"name": "...", "title": "...", "representing": "..."}}],
  "deal_history": [{{"date": "...", "deal_type": "...", "amount": "...", "lead_investors": "..."}}],
  "total_raised": "...",
  "competitors": ["..."],
  "competitor_details": [{{"name": "...", "description": "...", "hq_location": "...", "total_raised": "...", "differentiator": "..."}}],
  "market_data": {{"tam": "...", "sam": "...", "growth_rate": "...", "source": "..."}},
  "patents": {{"total_families": 0, "active": 0, "freedom_to_operate": "..."}},
  "regulatory": ["..."],
  "trends": ["..."],
  "pricing_analysis": {{"startup_pricing": "...", "competitor_pricing": "...", "assessment": "..."}},
  "customer_evidence": ["..."],
  "risks": ["..."],
  "facts": ["fact [Source: url or name]"],
  "sources": [{{"url": "...", "title": "..."}}]
}}"""


@dataclass
class AgenticFindings:
    """Research findings from the agentic researcher."""
    summary: str = ""
    company_profile: Dict = field(default_factory=dict)
    team: List[Dict] = field(default_factory=list)
    board_members: List[Dict] = field(default_factory=list)
    deal_history: List[Dict] = field(default_factory=list)
    total_raised: str = ""
    last_valuation: str = ""
    competitors: List[str] = field(default_factory=list)
    competitor_details: List[Dict] = field(default_factory=list)
    market_data: Dict = field(default_factory=dict)
    financials: Dict = field(default_factory=dict)
    regulatory: List[str] = field(default_factory=list)
    trends: List[str] = field(default_factory=list)
    pricing_analysis: Dict = field(default_factory=dict)
    customer_evidence: List[str] = field(default_factory=list)
    patent_landscape: Dict = field(default_factory=dict)
    risks: List[str] = field(default_factory=list)
    facts: List[str] = field(default_factory=list)
    cited_facts: List[Dict] = field(default_factory=list)
    sources: List[Dict] = field(default_factory=list)
    rounds_completed: int = 0
    tool_calls_made: int = 0
    iterations: int = 0
    duration_seconds: float = 0.0
    trust_score: float = 1.0
    research_method: str = ""
    # AR-2 fix: failure flag so callers can distinguish from real (empty) research
    failed: bool = False
    failure_reason: str = ""
    # AR-4 fix: data quality indicator from parse path taken
    parse_quality: str = "json_clean"  # "json_clean" / "json_repaired" / "gateway_structured" / "prose_only"


class AgenticResearcher:
    """
    Multi-provider deep researcher with Claude-first live web research.

    Primary path uses a six-phase Claude Code CLI workflow with native
    WebSearch/WebFetch tools. If that fails, the researcher falls back to the
    legacy OpenClaw one-shot prompt. Gemini remains the final fallback in the
    caller.
    """

    def __init__(self):
        pass

    def research(self, company: str, industry: str, product: str = "",
                 target_market: str = "", website_url: str = "",
                 known_competitors: str = "", extra_context: str = "",
                 adaptive_context: Optional[Dict[str, Any]] = None,
                 on_progress=None) -> AgenticFindings:
        """
        Run live research with provider order:
        1. Claude Code CLI (6 phases)
        2. OpenClaw subagent fallback
        """
        start_time = time.time()

        extra_context_parts = []
        if website_url:
            extra_context_parts.append(f"Company website: {website_url}")
        if known_competitors:
            extra_context_parts.append(f"Known competitors: {known_competitors}")
        if extra_context:
            extra_context_parts.append(extra_context)

        extra_context_block = "\n".join(extra_context_parts)
        adaptive_research_emphasis = _build_adaptive_research_emphasis(adaptive_context)

        raw_segments: List[str] = []
        phase_qualities: List[str] = []
        findings_dict: Dict[str, Any]
        research_method = "claude_cli_6phase"

        try:
            if not _check_claude_cli():
                raise RuntimeError("Claude Code CLI is not available or not authenticated")

            logger.info(f"[AgenticResearch] Starting 6-phase Claude CLI research for {company} ({industry})")
            phase_results: List[Dict[str, Any]] = []
            merged_so_far: Dict[str, Any] = {}

            for idx, phase in enumerate(_RESEARCH_PHASES, start=1):
                if on_progress:
                    on_progress(idx, phase["progress"])

                prompt = _build_phase_prompt(
                    phase,
                    company=company,
                    industry=industry,
                    product=product or "Not specified",
                    target_market=target_market or "Not specified",
                    extra_context=extra_context_block,
                    adaptive_research_emphasis=adaptive_research_emphasis,
                    prior_context=_build_phase_context_summary(merged_so_far),
                )

                logger.info(f"[AgenticResearch] Claude phase {idx}/6 starting for {company}: {phase['name']}")
                raw_phase = _call_claude_cli_research(prompt, timeout=int(phase.get("timeout", 300)))
                raw_segments.append(raw_phase)
                logger.info(f"[AgenticResearch] Claude phase {idx}/6 returned {len(raw_phase)} chars")

                phase_dict = self._parse_research_json(raw_phase, company)
                phase_results.append(phase_dict)
                phase_qualities.append(self._last_parse_quality)
                merged_so_far = _merge_research_phase_dicts(phase_results)

            findings_dict = merged_so_far

        except Exception as claude_err:
            logger.warning(f"[AgenticResearch] Claude CLI research failed: {claude_err}")
            research_method = "openclaw_subagent"
            raw_segments = []
            phase_qualities = []

            try:
                if on_progress:
                    on_progress(1, "Claude failed. Falling back to OpenClaw research...")

                if not _check_openclaw():
                    raise RuntimeError(
                        "OpenClaw gateway not available. Check that OpenClaw is running on port 18789 "
                        "and ~/.openclaw/openclaw.json has a valid gateway.auth.token"
                    )

                prompt = OPENCLAW_FALLBACK_PROMPT.format(
                    company=company,
                    industry=industry,
                    product=product or "Not specified",
                    target_market=target_market or "Not specified",
                    extra_context=extra_context_block,
                    adaptive_research_emphasis=adaptive_research_emphasis,
                )

                logger.info(f"[AgenticResearch] Starting OpenClaw fallback research for {company} ({industry})")
                raw = _call_openclaw_research(prompt, timeout=600)
                if not raw:
                    raise RuntimeError("OpenClaw subagent returned empty response")

                raw_segments.append(raw)
                logger.info(f"[AgenticResearch] OpenClaw fallback returned {len(raw)} chars")
                findings_dict = self._parse_research_json(raw, company)
                phase_qualities.append(self._last_parse_quality)

            except Exception as openclaw_err:
                logger.error(f"[AgenticResearch] Research FAILED: Claude={claude_err}; OpenClaw={openclaw_err}")
                raise RuntimeError(
                    f"Claude CLI research failed: {claude_err}; OpenClaw fallback failed: {openclaw_err}"
                ) from openclaw_err

        if on_progress:
            on_progress(len(_RESEARCH_PHASES) + 1, "Findings structured. Running verification...")

        findings_dict["research_method"] = research_method

        # ── Build AgenticFindings ──
        findings = self._dict_to_findings(findings_dict)
        if phase_qualities:
            quality_rank = {"json_clean": 0, "json_repaired": 1, "gateway_structured": 2, "prose_only": 3}
            findings.parse_quality = max(phase_qualities, key=lambda q: quality_rank.get(q, 9))
        else:
            findings.parse_quality = self._last_parse_quality
        findings.research_method = research_method

        # ── Hallucination guard ──
        try:
            raw_sources = []
            if findings_dict.get('summary'):
                raw_sources.append(findings_dict['summary'])
            for f in findings_dict.get('facts', []):
                if isinstance(f, str):
                    raw_sources.append(f)
            if findings.summary and raw_sources:
                guard_report = check_faithfulness(findings.summary, raw_sources)
                findings.trust_score = guard_report.get('faithfulness', 1.0)
                if findings.trust_score < 0.6:
                    logger.warning(
                        f"[AgenticResearch] Hallucination guard: faithfulness={findings.trust_score:.2f} "
                        f"({guard_report.get('traceable_count', 0)}/{guard_report.get('total_claims', 0)} claims traceable)"
                    )
                else:
                    logger.info(f"[AgenticResearch] Hallucination guard: faithfulness={findings.trust_score:.2f} OK")
        except Exception as hg_err:
            # AR-3 FIX: set trust_score=None so callers know the check didn't run
            # (vs. trust_score=1.0 which falsely implies a perfect check)
            logger.warning(f"[AgenticResearch] Hallucination guard failed (non-fatal): {hg_err}")
            findings.trust_score = None  # type: ignore[assignment]

        if research_method == "claude_cli_6phase":
            findings.rounds_completed = len(_RESEARCH_PHASES)
            findings.tool_calls_made = len(_RESEARCH_PHASES)
            findings.iterations = len(_RESEARCH_PHASES)
        else:
            findings.rounds_completed = 1
            findings.tool_calls_made = 1
            findings.iterations = 1
        findings.duration_seconds = time.time() - start_time

        # Build cited_facts
        findings.cited_facts = _build_cited_facts(findings.facts, findings.sources)

        # Audit log
        try:
            from ..utils.audit_log import AuditLog
            _audit = AuditLog.get()
            if _audit:
                _audit.log_step("research_single_session", metadata={
                    "model": RESEARCH_MODEL,
                    "facts_count": len(findings.facts),
                    "competitors_count": len(findings.competitors),
                    "sources_count": len(findings.sources),
                    "research_method": findings.research_method,
                    "trust_score": findings.trust_score,
                    "duration_s": findings.duration_seconds,
                    "raw_chars": sum(len(segment) for segment in raw_segments),
                })
        except Exception:
            pass

        logger.info(
            f"[AgenticResearch] Complete via {findings.research_method}: {len(findings.facts)} facts, "
            f"{len(findings.competitors)} competitors, {len(findings.sources)} sources, "
            f"{findings.duration_seconds:.1f}s"
        )

        return findings

    # AR-4 FIX: track parse quality so callers can surface data degradation warnings
    _last_parse_quality: str = "json_clean"

    def _parse_research_json(self, raw: str, company: str) -> Dict:
        """Parse JSON from research output. Falls back to gateway structuring if needed."""
        # Clean markdown fences
        cleaned = raw.strip()
        cleaned = re.sub(r'^```(?:json)?\s*\n?', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\n?```\s*$', '', cleaned)

        # Find first JSON object
        first_brace = cleaned.find('{')
        if first_brace >= 0:
            json_text = cleaned[first_brace:]
            try:
                result = json.loads(json_text)
                self._last_parse_quality = "json_clean"
                return result
            except json.JSONDecodeError:
                # Try to repair truncated JSON
                repaired = self._repair_json(json_text)
                if repaired:
                    self._last_parse_quality = "json_repaired"
                    logger.info("[AgenticResearch] JSON repaired (truncation recovery)")
                    return repaired

        # JSON parsing failed — use gateway API to structure the prose response
        logger.info("[AgenticResearch] Response was prose, structuring via gateway API...")
        try:
            from ..utils.cli_llm import _try_gateway, _strip_markdown_fences
            structuring_prompt = STRUCTURING_PROMPT.format(
                report_text=raw[:15000]
            )
            result = _try_gateway(structuring_prompt, STRUCTURING_MODEL, max_tokens=8000, timeout=120)
            if result:
                result = _strip_markdown_fences(result)
                fb = result.find('{')
                if fb >= 0:
                    result = result[fb:]
                structured = json.loads(result)
                self._last_parse_quality = "gateway_structured"
                logger.info(f"[AgenticResearch] Structured via gateway (parse_quality=gateway_structured): {len(structured.get('facts', []))} facts")

                # Merge URLs from original prose that structuring may have missed
                urls = re.findall(r'https?://[^\s\)>\]"]+', raw)
                existing_urls = {s.get("url") for s in structured.get("sources", [])}
                for u in urls[:25]:
                    if u not in existing_urls:
                        structured.setdefault("sources", []).append({"url": u, "title": ""})

                return structured
        except Exception as e:
            logger.warning(f"[AgenticResearch] Gateway structuring failed: {e}")

        # Last resort: extract what we can from prose
        logger.warning("[AgenticResearch] Falling back to URL extraction from prose (parse_quality=prose_only) — structured fields (competitors, market_data, team, patents) will be empty")
        self._last_parse_quality = "prose_only"
        urls = re.findall(r'https?://[^\s\)>\]"]+', raw)
        return {
            "summary": raw[:4000],
            "competitors": [],
            "facts": [],
            "sources": [{"url": u, "title": ""} for u in urls[:25]],
        }

    def _repair_json(self, text: str) -> Optional[Dict]:
        """Try to repair truncated JSON from max_tokens cutoff."""
        if not text or text[0] != '{':
            return None
        for trim in [text, text.rstrip(',')]:
            opens = trim.count('{') - trim.count('}')
            brackets = trim.count('[') - trim.count(']')
            if opens >= 0 and brackets >= 0:
                closer = ']' * max(brackets, 0) + '}' * max(opens, 0)
                try:
                    return json.loads(trim + closer)
                except json.JSONDecodeError:
                    continue
        return None

    def _dict_to_findings(self, d: Dict) -> AgenticFindings:
        """Convert a research dict to AgenticFindings dataclass."""
        findings = AgenticFindings()
        findings.summary = d.get("summary", "")
        findings.company_profile = d.get("company_profile", {})
        findings.team = d.get("team", [])
        findings.board_members = d.get("board_members", [])
        findings.deal_history = d.get("deal_history", [])
        findings.total_raised = d.get("total_raised", "")
        findings.last_valuation = d.get("last_valuation", "")
        findings.competitors = d.get("competitors", [])
        findings.competitor_details = d.get("competitor_details", [])
        findings.market_data = d.get("market_data", {})
        findings.financials = d.get("financials", {})
        findings.regulatory = d.get("regulatory", [])
        findings.trends = d.get("trends", [])
        findings.pricing_analysis = d.get("pricing_analysis", {})
        findings.customer_evidence = d.get("customer_evidence", [])
        findings.patent_landscape = d.get("patents", d.get("patent_landscape", {}))
        findings.risks = d.get("risks", [])
        findings.facts = d.get("facts", [])
        findings.sources = d.get("sources", [])
        findings.research_method = str(d.get("research_method", "") or "")
        # Fallback: extract source URLs from cited_facts if sources is empty
        if not findings.sources and findings.cited_facts:
            seen = set()
            for cf in findings.cited_facts:
                url = cf.get("source_url", "")
                title = cf.get("source_domain", "") or cf.get("text", "")[:60]
                if url and url not in seen:
                    seen.add(url)
                    findings.sources.append({"url": url, "title": title})
        return findings


def _build_cited_facts(facts: list, sources: list) -> List[Dict]:
    """Build cited_facts with source attribution."""
    from urllib.parse import urlparse

    source_urls = {}
    for s in sources:
        url = s.get("url", "")
        try:
            domain = urlparse(url).hostname or ""
            if domain.startswith("www."):
                domain = domain[4:]
            if domain and domain not in source_urls:
                source_urls[domain] = url
        except Exception:
            pass

    cited = []
    for fact in facts:
        domain_found = ""
        for domain in source_urls:
            if domain.split(".")[0] in fact.lower():
                domain_found = domain
                break
        cited.append({
            "text": fact,
            "source_domain": domain_found,
            "source_url": source_urls.get(domain_found, ""),
            "credibility": SOURCE_CREDIBILITY.get(domain_found, 1.0),
        })
    return cited
