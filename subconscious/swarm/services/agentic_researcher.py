"""
Agentic Researcher — OpenClaw subagent with native web search.

Calls OpenClaw gateway (port 18789) which spawns an agent session
with web_search and web_fetch tools built in. No CLI subprocess needed.
No fallback — if OpenClaw is down, research fails loudly.

Structuring/synthesis uses Mirai gateway API (fast, no subprocess overhead).
"""

import json
import os
import re
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import List, Dict, Optional

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

# OpenClaw gateway config (for subagent research with native web search)
_OPENCLAW_URL = os.environ.get("OPENCLAW_GATEWAY_URL", "http://127.0.0.1:18789")
_OPENCLAW_TOKEN = os.environ.get("OPENCLAW_GATEWAY_TOKEN", "")
_OPENCLAW_AVAILABLE: Optional[bool] = None


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

RESEARCH_PROMPT = """You are a PitchBook-level venture capital analyst producing institutional-quality due diligence. You have live web search. Research MUST match PitchBook depth.

STARTUP UNDER ANALYSIS:
  Company: {company}
  Industry: {industry}
  Product: {product}
  Target Market: {target_market}
  {extra_context}

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
    competitors: List[str] = field(default_factory=list)
    competitor_details: List[Dict] = field(default_factory=list)
    market_data: Dict = field(default_factory=dict)
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
    # AR-2 fix: failure flag so callers can distinguish from real (empty) research
    failed: bool = False
    failure_reason: str = ""
    # AR-4 fix: data quality indicator from parse path taken
    parse_quality: str = "json_clean"  # "json_clean" / "json_repaired" / "gateway_structured" / "prose_only"


class AgenticResearcher:
    """
    Single-session deep researcher using Claude with web search.

    One thorough research session with multiple tool calls replaces
    the old 6-call pipeline (dual researcher + cross-exam + chairman).
    """

    def __init__(self):
        pass

    def research(self, company: str, industry: str, product: str = "",
                 target_market: str = "", website_url: str = "",
                 known_competitors: str = "", extra_context: str = "",
                 on_progress=None) -> AgenticFindings:
        """
        Single deep research session with built-in verification.
        1 CLI call with web search (max_turns=30) + optional structuring via gateway.
        """
        start_time = time.time()

        extra_context_parts = []
        if website_url:
            extra_context_parts.append(f"Company website: {website_url}")
        if known_competitors:
            extra_context_parts.append(f"Known competitors: {known_competitors}")
        if extra_context:
            extra_context_parts.append(extra_context)

        prompt = RESEARCH_PROMPT.format(
            company=company,
            industry=industry,
            product=product or "Not specified",
            target_market=target_market or "Not specified",
            extra_context="\n".join(extra_context_parts),
        )

        if on_progress:
            on_progress(1, "Deep web research in progress...")

        # ── Research call: OpenClaw subagent with native web search ──
        raw = None
        research_method = "openclaw_subagent"
        try:
            if not _check_openclaw():
                raise RuntimeError("OpenClaw gateway not available. Check that OpenClaw is running on port 18789 and ~/.openclaw/openclaw.json has a valid gateway.auth.token")

            logger.info(f"[AgenticResearch] Starting research via OpenClaw subagent for {company} ({industry})")
            raw = _call_openclaw_research(prompt, timeout=600)

            if not raw:
                raise RuntimeError("OpenClaw subagent returned empty response")

            logger.info(f"[AgenticResearch] OpenClaw subagent returned {len(raw)} chars")

        except Exception as e:
            # AR-2 FIX: Re-raise instead of returning a degraded AgenticFindings with
            # summary="Research failed: ..." which gets injected into scoring prompts.
            # The caller (websocket.py) catches this and sets research_failed=True.
            logger.error(f"[AgenticResearch] Research FAILED: {e}")
            raise

        if on_progress:
            on_progress(2, "Research complete. Structuring findings...")

        # ── Parse JSON from response ──
        findings_dict = self._parse_research_json(raw, company)

        if on_progress:
            on_progress(3, "Findings structured. Running verification...")

        # ── Build AgenticFindings ──
        findings = self._dict_to_findings(findings_dict)
        findings.parse_quality = self._last_parse_quality

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
                    "trust_score": findings.trust_score,
                    "duration_s": findings.duration_seconds,
                    "raw_chars": len(raw) if raw else 0,
                })
        except Exception:
            pass

        logger.info(
            f"[AgenticResearch] Complete: {len(findings.facts)} facts, "
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
        findings.competitors = d.get("competitors", [])
        findings.competitor_details = d.get("competitor_details", [])
        findings.market_data = d.get("market_data", {})
        findings.regulatory = d.get("regulatory", [])
        findings.trends = d.get("trends", [])
        findings.pricing_analysis = d.get("pricing_analysis", {})
        findings.customer_evidence = d.get("customer_evidence", [])
        findings.patent_landscape = d.get("patents", d.get("patent_landscape", {}))
        findings.risks = d.get("risks", [])
        findings.facts = d.get("facts", [])
        findings.sources = d.get("sources", [])
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
