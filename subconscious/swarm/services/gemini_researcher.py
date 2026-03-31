"""
Gemini Researcher — 5-step grounded web research via Google AI Studio.

Primary research engine. Uses Gemini 2.5 Flash with Google Search grounding.
Each step = 1 API call with web search. Sequential (10 RPM limit).
Returns AgenticFindings-compatible dict for downstream pipeline compatibility.

Fallback: OpenClaw agentic researcher (when Gemini fails or quota exceeded).
"""

import json
import os
import time
import http.client
import ssl
from typing import Dict, List, Optional, Tuple, Any

from ..utils.logger import get_logger

logger = get_logger('mirofish.gemini_researcher')

_GOOGLE_AI_KEY = os.environ.get("GOOGLE_AI_KEY", "")
_MODEL = "gemini-2.5-flash"
_API_HOST = "generativelanguage.googleapis.com"

# 5-step research protocol — each step gets its own grounded search
RESEARCH_STEPS = [
    (
        "company",
        "Research the startup called {company} in the {industry} industry. "
        "They build: {product}. "
        "{founder_context_note}"
        "{website_note}"
        "Find: their website, team members with titles, product features, pricing tiers with dollar amounts, "
        "funding history, employee count, HQ location, year founded, customer testimonials, and any press coverage. "
        "Return specific facts with sources. If you cannot find information, say 'Not found' for that field."
    ),
    (
        "competitors",
        "Find the top 5-8 competitors to {company} in the {industry} market. "
        "{founder_context_note}"
        "{known_competitors_note}"
        "For EACH competitor provide: company name, 1-2 sentence description, HQ location, year founded, "
        "total funding raised, financing status (VC-backed/bootstrapped/public), employee count, "
        "and what specifically differentiates them from {company}'s approach ({product}). "
        "Search for each competitor individually."
    ),
    (
        "market",
        "Find the total addressable market (TAM) and serviceable addressable market (SAM) for the {industry} market. "
        "{founder_context_note}"
        "Search for market size reports from Grand View Research, MarketsandMarkets, Statista, Fortune Business Insights. "
        "Find: TAM in dollars, SAM in dollars, CAGR percentage, growth drivers, and source citations. "
        "Also find the AI/IoT subsegment size if the product involves technology ({product}). "
        "Provide specific dollar figures and percentages, not ranges."
    ),
    (
        "regulatory",
        "What regulations and policies affect the {industry} industry in 2025-2026? "
        "{founder_context_note}"
        "Target market: {target_market}. "
        "Find: relevant EPA, FDA, SEC, or state regulations, pending legislation, compliance costs, "
        "government funding programs (IIJA, IRA, grants), and barriers to entry. "
        "Include specific rule names, effective dates, and dollar amounts where available."
    ),
    (
        "risks",
        "What are the biggest risks for a startup in {industry} building {product}? "
        "{founder_context_note}"
        "Find: similar companies that failed in this space and why, challenges with the target customer segment "
        "({target_market}), technology risks, competitive threats from incumbents, and market timing risks. "
        "Be specific — name actual failed companies if you can find them."
    ),
]


class GeminiResearcher:
    """5-step grounded web research using Gemini 2.5 Flash + Google Search."""

    def research(
        self,
        company: str,
        industry: str,
        product: str = "",
        target_market: str = "",
        website_url: str = "",
        known_competitors: str = "",
        extra_context: str = "",
        on_progress=None,
    ) -> Dict[str, Any]:
        """Run 5-step grounded research. Returns AgenticFindings-compatible dict."""
        if not _GOOGLE_AI_KEY:
            raise RuntimeError("GOOGLE_AI_KEY not set — cannot use Gemini researcher")

        start_time = time.time()
        results: Dict[str, str] = {}
        all_sources: List[Dict] = []
        all_queries: List[str] = []

        website_note = f"Their website is {website_url}. " if website_url else ""
        known_competitors_note = (
            f"Known competitors include: {known_competitors}. Search for these plus any others you find. "
            if known_competitors else ""
        )
        founder_context_note = f"Founder-provided context: {extra_context}. " if extra_context else ""

        for i, (step_name, prompt_template) in enumerate(RESEARCH_STEPS):
            if on_progress:
                on_progress(i + 1, f"Researching {step_name}...")

            prompt = prompt_template.format(
                company=company,
                industry=industry,
                product=product or "their product",
                target_market=target_market or "their target market",
                website_note=website_note,
                known_competitors_note=known_competitors_note,
                founder_context_note=founder_context_note,
            )

            try:
                response_text, sources, queries = self._grounded_search(prompt)
                results[step_name] = response_text
                all_sources.extend(sources)
                all_queries.extend(queries)
                logger.info(
                    f"[Gemini Research] Step {i+1}/{len(RESEARCH_STEPS)} ({step_name}): "
                    f"{len(response_text)} chars, {len(sources)} sources, {len(queries)} queries"
                )
            except Exception as e:
                logger.warning(f"[Gemini Research] Step {step_name} failed: {e}")
                results[step_name] = ""

        duration = time.time() - start_time

        # Build AgenticFindings-compatible dict
        findings = self._build_findings(results, all_sources, company, industry)
        findings["duration_seconds"] = round(duration, 1)
        findings["research_method"] = "gemini_grounded"
        findings["search_queries"] = all_queries

        logger.info(
            f"[Gemini Research] Complete: {len(findings.get('facts', []))} facts, "
            f"{len(findings.get('competitors', []))} competitors, "
            f"{len(all_sources)} sources, {duration:.1f}s"
        )

        # Cache for future use
        if on_progress:
            on_progress(len(RESEARCH_STEPS) + 1, "Research complete. Structuring findings...")

        return findings

    def _grounded_search(self, prompt: str) -> Tuple[str, List[Dict], List[str]]:
        """Call Gemini with Google Search grounding. Returns (text, sources, queries)."""
        payload = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "tools": [{"google_search": {}}],
        }).encode("utf-8")

        path = f"/v1beta/models/{_MODEL}:generateContent?key={_GOOGLE_AI_KEY}"
        conn = http.client.HTTPSConnection(_API_HOST, timeout=60,
                                            context=ssl.create_default_context())
        conn.request("POST", path, body=payload, headers={
            "Content-Type": "application/json",
        })
        resp = conn.getresponse()
        raw = resp.read().decode("utf-8")
        conn.close()

        if resp.status != 200:
            raise RuntimeError(f"Gemini HTTP {resp.status}: {raw[:300]}")

        body = json.loads(raw)

        candidates = body.get("candidates", [])
        if not candidates:
            raise RuntimeError(f"Gemini returned no candidates: {body}")

        candidate = candidates[0]
        parts = candidate.get("content", {}).get("parts", [])
        text = parts[0].get("text", "") if parts else ""

        # Extract grounding metadata (sources + search queries)
        grounding = candidate.get("groundingMetadata", {})
        queries = grounding.get("webSearchQueries", [])

        sources = []
        for chunk in grounding.get("groundingChunks", []):
            web = chunk.get("web", {})
            if web.get("uri"):
                sources.append({
                    "url": web.get("uri", ""),
                    "title": web.get("title", ""),
                })

        return text, sources, queries

    def _build_findings(
        self, results: Dict[str, str], sources: List[Dict],
        company: str, industry: str,
    ) -> Dict[str, Any]:
        """Convert 5-step results into AgenticFindings-compatible dict."""
        # Combine all step results into a summary
        summary_parts = []
        for step_name in ["company", "competitors", "market", "regulatory", "risks"]:
            text = results.get(step_name, "")
            if text:
                summary_parts.append(text)

        summary = "\n\n".join(summary_parts)

        # Extract competitor names from the competitors step
        competitors = []
        competitor_details = []
        comp_text = results.get("competitors", "")
        if comp_text:
            # Simple extraction — look for numbered items or bold names
            import re
            # Match patterns like "1. CompanyName" or "**CompanyName**" or "### CompanyName"
            names = re.findall(r'(?:^|\n)\s*(?:\d+\.\s*\*?\*?|###?\s*)([\w][\w\s&./\'-]{2,40})', comp_text)
            for name in names[:10]:
                clean = name.strip().rstrip(':')
                if clean and clean.lower() not in (company.lower(), 'and', 'the', 'for', 'with'):
                    competitors.append(clean)

        # Extract market data
        market_data = {}
        market_text = results.get("market", "")
        if market_text:
            import re
            # Look for TAM figures like "$X.X billion" or "$X billion"
            tam_match = re.search(r'(?:TAM|total addressable market|market size)[^$]*\$([0-9.,]+)\s*(billion|million|B|M)', market_text, re.IGNORECASE)
            if tam_match:
                market_data["tam"] = f"${tam_match.group(1)} {tam_match.group(2)}"
            # Look for CAGR
            cagr_match = re.search(r'CAGR[^0-9]*([0-9.]+)%', market_text, re.IGNORECASE)
            if cagr_match:
                market_data["growth_rate"] = f"{cagr_match.group(1)}% CAGR"

        # Extract facts (sentences with specific numbers or citations)
        facts = []
        import re
        for text in summary_parts:
            # Find sentences with dollar amounts, percentages, or dates
            sentences = re.split(r'(?<=[.!?])\s+', text)
            for s in sentences:
                if re.search(r'\$[\d,]+|\d+%|\d{4}', s) and len(s) > 30 and len(s) < 300:
                    facts.append(s.strip())
        facts = facts[:30]  # Cap at 30

        # Deduplicate sources
        seen_urls = set()
        unique_sources = []
        for s in sources:
            url = s.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_sources.append(s)

        return {
            "summary": summary,
            "company_profile": {},
            "competitors": competitors[:10],
            "competitor_details": competitor_details,
            "market_data": market_data,
            "regulatory": [results.get("regulatory", "")][:1] if results.get("regulatory") else [],
            "trends": [],
            "pricing_analysis": {},
            "customer_evidence": [],
            "patent_landscape": {},
            "risks": [results.get("risks", "")][:1] if results.get("risks") else [],
            "facts": facts,
            "cited_facts": [],
            "sources": unique_sources,
            "rounds_completed": len(RESEARCH_STEPS),
            "tool_calls_made": len(RESEARCH_STEPS),
            "iterations": 1,
            "trust_score": 0.9 if len(unique_sources) >= 20 else 0.8 if len(unique_sources) >= 10 else 0.7 if len(unique_sources) >= 5 else 0.5,
            "failed": False,
            "failure_reason": "",
            "parse_quality": "gemini_grounded",
        }
