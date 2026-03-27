"""
Multi-Model Parallel Research Agent — Claude, GPT, and Gemini research simultaneously.

Each model focuses on a different aspect:
  Claude Opus: Market analysis & regulatory landscape
  GPT-5.4: Competitors & funding landscape
  Gemini 3.1 Pro: Recent news & market trends

Findings are merged and synthesized into a unified report.
"""

import json
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI

from .search_engine import SearchEngine
from .web_researcher import WebResearcher
from ..utils.logger import get_logger
from ..config import Config

logger = get_logger('mirofish.research_agent')

# Gateway config
GATEWAY_URL = Config.LLM_BASE_URL
GATEWAY_KEY = Config.LLM_API_KEY

# Models for parallel research
RESEARCH_MODELS = [
    {"model": "anthropic/claude-opus-4-6", "label": "Claude", "focus": "market_regulatory"},
    {"model": "openai-codex/gpt-5.4", "label": "GPT", "focus": "competitors_funding"},
    {"model": "google-gemini-cli/gemini-3.1-pro-preview", "label": "Gemini", "focus": "news_trends"},
]


@dataclass
class ResearchFindings:
    summary: str = ""
    competitors: List[str] = field(default_factory=list)
    competitor_details: List[Dict] = field(default_factory=list)
    market_data: Dict = field(default_factory=dict)
    trends: List[str] = field(default_factory=list)
    facts: List[str] = field(default_factory=list)
    sources: List[Dict] = field(default_factory=list)
    rounds_completed: int = 0


class ResearchAgent:
    """Multi-model parallel research agent."""

    def __init__(self):
        self.search = SearchEngine()
        self.web = WebResearcher()
        self._searxng_available = self.search.is_available()

    def research(self, company: str, industry: str, product: str = "",
                 target_market: str = "", on_progress=None) -> ResearchFindings:
        """Run parallel research across 3 models."""
        if not self._searxng_available:
            logger.warning("[Research] SearXNG not available — using LLM knowledge only")

        findings = ResearchFindings()
        all_model_findings: Dict[str, Dict] = {}

        # ── Round 1: Parallel research across 3 models ──
        if on_progress:
            on_progress(1, "Researching in parallel...")

        def research_with_model(model_cfg):
            """One model's research thread."""
            model_id = model_cfg["model"]
            label = model_cfg["label"]
            focus = model_cfg["focus"]

            try:
                client = OpenAI(api_key=GATEWAY_KEY, base_url=GATEWAY_URL)

                # Generate queries based on focus area
                queries = self._generate_queries(client, model_id, company, industry, product, focus)
                if on_progress:
                    on_progress(1, f"Searching {len(queries)} queries...")

                # Search + crawl
                model_findings = []
                urls_visited = set()
                for query in queries[:4]:
                    self._search_and_crawl(query, model_findings, urls_visited)

                # Model synthesizes its own findings
                if on_progress:
                    on_progress(1, f"Synthesizing findings...")

                synthesis = self._model_synthesize(client, model_id, label, focus,
                                                    model_findings, company, industry)
                return label, synthesis, model_findings

            except Exception as e:
                logger.warning(f"[Research] {label} research failed: {e}")
                return label, {}, []

        # Run all 3 models in parallel
        logger.info("[Research] Starting parallel research: Claude (market), GPT (competitors), Gemini (news)")
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(research_with_model, m) for m in RESEARCH_MODELS]
            for future in as_completed(futures):
                try:
                    label, synthesis, raw_findings = future.result()
                    all_model_findings[label] = {
                        "synthesis": synthesis,
                        "raw": raw_findings,
                    }
                    logger.info(f"[Research] {label} complete: {len(raw_findings)} findings")
                except Exception as e:
                    logger.warning(f"[Research] Model thread failed: {e}")

        findings.rounds_completed = 1

        # ── Round 2: LLM-generated follow-up queries ──
        if on_progress:
            on_progress(2, "Analyzing gaps, generating follow-up queries...")

        gaps = self._identify_gaps(all_model_findings, company, industry)
        if gaps and self._searxng_available:
            extra_findings = []
            urls_visited = set()
            for query in gaps[:3]:
                if on_progress:
                    on_progress(2, f"Following up: {query[:40]}...")
                self._search_and_crawl(query, extra_findings, urls_visited)

            if extra_findings:
                all_model_findings["FollowUp"] = {"synthesis": {}, "raw": extra_findings}

        findings.rounds_completed = 2

        # ── Round 3: Competitor deep-dive ──
        competitors_found = []
        for label, data in all_model_findings.items():
            synth = data.get("synthesis", {})
            competitors_found.extend(synth.get("competitors", []))
        competitors_found = list(set(c for c in competitors_found if isinstance(c, str)))[:5]

        if competitors_found and self._searxng_available:
            if on_progress:
                on_progress(3, f"Deep-diving {len(competitors_found)} competitors...")
            comp_findings = []
            urls_visited = set()
            for comp in competitors_found[:3]:
                self._search_and_crawl(f"{comp} company funding revenue valuation", comp_findings, urls_visited, max_results=2, max_crawl=1)
            if comp_findings:
                all_model_findings["CompetitorDeepDive"] = {"synthesis": {}, "raw": comp_findings}

        findings.rounds_completed = 3

        # ── Final: Merge all findings ──
        if on_progress:
            on_progress(4, "Merging all research findings...")

        merged = self._merge_findings(all_model_findings, company, industry)
        findings.summary = merged.get("summary", "")
        findings.competitors = merged.get("competitors", competitors_found)
        findings.competitor_details = merged.get("competitor_details", [])
        findings.market_data = merged.get("market_data", {})
        findings.trends = merged.get("trends", [])
        findings.facts = merged.get("facts", [])

        # Collect all sources
        for label, data in all_model_findings.items():
            for f in data.get("raw", []):
                if f.get("source"):
                    findings.sources.append({"url": f["source"], "title": f.get("title", ""), "model": label})

        logger.info(f"[Research] Complete: {len(findings.facts)} facts, {len(findings.competitors)} competitors, {len(findings.sources)} sources from {len(all_model_findings)} models")
        return findings

    def _generate_queries(self, client, model_id, company, industry, product, focus):
        """LLM generates research queries based on focus area."""
        try:
            resp = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": (
                    f"Company: {company}\nIndustry: {industry}\nProduct: {product[:100]}\n\n"
                    f"Generate 4 web search queries to thoroughly research this startup. Cover:\n"
                    f"1. Market size, TAM, growth trends\n"
                    f"2. Competitors, their funding, and positioning\n"
                    f"3. Regulatory landscape and recent policy changes\n"
                    f"4. Recent news, analyst opinions, and market signals\n\n"
                    f"Return ONLY a JSON array of 4 search query strings. No other text."
                )}],
                max_tokens=200,
            )
            text = resp.choices[0].message.content or "[]"
            match = re.search(r'\[.*\]', text, re.DOTALL)
            if match:
                queries = json.loads(match.group())
                return [str(q) for q in queries if isinstance(q, str)][:4]
        except Exception as e:
            logger.warning(f"[Research] Query generation failed for {model_id}: {e}")

        # Fallback — all models get the same broad queries
        return [
            f"{industry} market size TAM growth 2025 2026",
            f"{company} competitors {industry} startups",
            f"{industry} regulatory trends news 2026",
            f"{industry} funding landscape startups",
        ]

    def _search_and_crawl(self, query, findings, visited, max_results=3, max_crawl=2):
        """Search SearXNG + crawl pages."""
        try:
            results = self.search.search(query, max_results=max_results)
            crawled = 0
            for r in results:
                url = r.get("url", "")
                if not url or url in visited or crawled >= max_crawl:
                    continue
                visited.add(url)
                content = None
                if self.web._get_crawl4ai():
                    content = self.web._crawl4ai_extract(url)
                if content and len(content) > 100:
                    findings.append({"source": url, "title": r.get("title", ""), "content": content[:6000], "query": query})
                    crawled += 1
                elif r.get("content"):
                    findings.append({"source": url, "title": r.get("title", ""), "content": r["content"][:1500], "query": query})
                    crawled += 1
        except Exception as e:
            logger.warning(f"[Research] Search failed for '{query[:40]}': {e}")

    def _model_synthesize(self, client, model_id, label, focus, findings, company, industry):
        """One model synthesizes its findings."""
        if not findings:
            return {"summary": "", "competitors": [], "facts": []}

        content_text = "\n\n".join(f"[{f['title']}]\n{f['content'][:600]}" for f in findings[:8])

        try:
            resp = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": (
                    f"Synthesize these research findings about {company} ({industry}).\n\n"
                    f"FINDINGS:\n{content_text}\n\n"
                    f"Return JSON: {{\"summary\": \"200 words\", \"competitors\": [\"name1\", ...], "
                    f"\"facts\": [\"specific fact with number\", ...], \"trends\": [\"trend\", ...]}}\n"
                    f"Only include data from the findings above. Return ONLY valid JSON."
                )}],
                max_tokens=800,
            )
            text = resp.choices[0].message.content or "{}"
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception as e:
            logger.warning(f"[Research] {label} synthesis failed: {e}")

        return {"summary": "", "competitors": [], "facts": []}

    def _identify_gaps(self, all_findings, company, industry):
        """LLM identifies what's still missing."""
        summaries = []
        for label, data in all_findings.items():
            synth = data.get("synthesis", {})
            if synth.get("summary"):
                summaries.append(f"{label}: {synth['summary'][:200]}")

        if not summaries:
            return [f"{industry} market size TAM", f"{company} competitors funding"]

        try:
            client = OpenAI(api_key=GATEWAY_KEY, base_url=GATEWAY_URL)
            resp = client.chat.completions.create(
                model="anthropic/claude-sonnet-4-6",  # Use fast model for gap analysis
                messages=[{"role": "user", "content": (
                    f"Research so far on {company} ({industry}):\n"
                    + "\n".join(summaries)
                    + "\n\nWhat specific data is still missing? "
                    f"Generate 3 targeted search queries to fill the gaps. "
                    f"Return ONLY a JSON array of 3 query strings."
                )}],
                max_tokens=200,
            )
            text = resp.choices[0].message.content or "[]"
            match = re.search(r'\[.*\]', text, re.DOTALL)
            if match:
                return [str(q) for q in json.loads(match.group())][:3]
        except Exception as e:
            logger.warning(f"[Research] Gap analysis failed: {e}")

        return []

    def _merge_findings(self, all_findings, company, industry):
        """Merge findings from all models into unified report."""
        all_summaries = []
        all_competitors = []
        all_facts = []
        all_trends = []

        for label, data in all_findings.items():
            synth = data.get("synthesis", {})
            if synth.get("summary"):
                all_summaries.append(f"[{label}] {synth['summary']}")
            all_competitors.extend(synth.get("competitors", []))
            all_facts.extend(synth.get("facts", []))
            all_trends.extend(synth.get("trends", []))

        # Deduplicate
        competitors = list(set(c for c in all_competitors if isinstance(c, str)))
        facts = list(dict.fromkeys(str(f) for f in all_facts if f))[:15]
        trends = list(dict.fromkeys(str(t) for t in all_trends if t))[:8]

        # Merge summaries
        summary = "\n\n".join(all_summaries) if all_summaries else ""

        return {
            "summary": summary,
            "competitors": competitors,
            "facts": facts,
            "trends": trends,
            "market_data": {},
        }
