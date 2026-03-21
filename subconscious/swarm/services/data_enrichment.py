"""
Data Enrichment — auto-enriches startup data from public sources
before feeding to the swarm for prediction.

Sources: Web search, app stores, patent databases, press coverage.
"""

import json
import os
from typing import Dict, Any, Optional, List

import requests

from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from ..config import Config

logger = get_logger('mirofish.enrichment')

_TIMEOUT = 10


class DataEnrichment:
    """Auto-enriches startup data from public sources."""

    def __init__(self):
        self._searxng_url = Config.SEARXNG_URL
        self._llm = None

    def _get_llm(self) -> LLMClient:
        if self._llm is None:
            self._llm = LLMClient()
        return self._llm

    def enrich(self, company: str, industry: str, product: str,
               target_market: str = "", team: str = "") -> Dict[str, Any]:
        """
        Run all enrichment steps. Returns dict of enriched data.
        Each step fails gracefully — partial enrichment is fine.
        """
        result = {"company": company, "sources": []}

        # 1. Web presence
        web_info = self._search_web(company, industry)
        if web_info:
            result["web_presence"] = web_info
            result["sources"].append("web_search")

        # 2. Competitor landscape
        competitors = self._find_competitors(company, industry, product)
        if competitors:
            result["competitors"] = competitors
            result["sources"].append("competitor_search")

        # 3. Press coverage + sentiment
        press = self._search_press(company)
        if press:
            result["press_coverage"] = press
            result["sources"].append("press")

        # 4. Market data (if OpenBB available)
        market = self._get_market_data(company, industry)
        if market:
            result["market_data"] = market
            result["sources"].append("market_data")

        logger.info(f"[Enrichment] {company}: {len(result['sources'])} sources enriched")
        return result

    def _search_web(self, company: str, industry: str) -> Optional[Dict]:
        """Search for company website and key info."""
        try:
            resp = requests.get(
                f"{self._searxng_url}/search",
                params={"q": f"{company} {industry} company", "format": "json", "categories": "general"},
                timeout=_TIMEOUT,
            )
            if resp.status_code != 200:
                return None

            results = resp.json().get("results", [])[:5]
            if not results:
                return None

            return {
                "top_results": [{"title": r.get("title", ""), "url": r.get("url", ""),
                                 "snippet": r.get("content", "")[:200]} for r in results],
                "website": results[0].get("url", "") if results else "",
            }
        except Exception as e:
            logger.debug(f"[Enrichment] Web search failed: {e}")
            return None

    def _find_competitors(self, company: str, industry: str, product: str) -> Optional[List[Dict]]:
        """Find competitors via web search."""
        try:
            query = f"{industry} competitors alternatives to {product}"
            resp = requests.get(
                f"{self._searxng_url}/search",
                params={"q": query, "format": "json"},
                timeout=_TIMEOUT,
            )
            if resp.status_code != 200:
                return None

            results = resp.json().get("results", [])[:8]
            if not results:
                return None

            # Use LLM to extract competitor names from search results
            snippets = "\n".join(f"- {r.get('title', '')}: {r.get('content', '')[:150]}" for r in results)
            try:
                llm = self._get_llm()
                extracted = llm.chat_json(
                    messages=[
                        {"role": "system", "content": "Extract competitor company names from these search results. Return JSON: {\"competitors\": [{\"name\": \"...\", \"description\": \"brief\"}]}"},
                        {"role": "user", "content": snippets},
                    ],
                    temperature=0.2, max_tokens=500,
                )
                return extracted.get("competitors", [])[:10]
            except Exception:
                return [{"name": r.get("title", "")[:50], "description": r.get("content", "")[:100]} for r in results[:5]]

        except Exception as e:
            logger.debug(f"[Enrichment] Competitor search failed: {e}")
            return None

    def _search_press(self, company: str) -> Optional[Dict]:
        """Search for press coverage and analyze sentiment."""
        try:
            resp = requests.get(
                f"{self._searxng_url}/search",
                params={"q": f"{company} startup news funding", "format": "json",
                         "categories": "news", "time_range": "year"},
                timeout=_TIMEOUT,
            )
            if resp.status_code != 200:
                return None

            results = resp.json().get("results", [])[:5]
            if not results:
                return None

            articles = [{"title": r.get("title", ""), "url": r.get("url", ""),
                         "snippet": r.get("content", "")[:200]} for r in results]

            return {
                "article_count": len(articles),
                "articles": articles,
            }
        except Exception as e:
            logger.debug(f"[Enrichment] Press search failed: {e}")
            return None

    def _get_market_data(self, company: str, industry: str) -> Optional[Dict]:
        """Get market data via OpenBB if available."""
        try:
            from .market_data import MarketDataService
            svc = MarketDataService()
            data = svc.get_industry_context(company, industry)
            return data if data else None
        except Exception:
            return None

    def format_for_research(self, enrichment: Dict) -> str:
        """Format enrichment data as research context for swarm agents."""
        lines = []

        if enrichment.get("web_presence"):
            wp = enrichment["web_presence"]
            if wp.get("website"):
                lines.append(f"Company website: {wp['website']}")

        if enrichment.get("competitors"):
            comps = enrichment["competitors"]
            lines.append(f"Competitors ({len(comps)}):")
            for c in comps[:5]:
                lines.append(f"  - {c.get('name', '?')}: {c.get('description', '')[:80]}")

        if enrichment.get("press_coverage"):
            press = enrichment["press_coverage"]
            lines.append(f"Press coverage: {press.get('article_count', 0)} recent articles")
            for a in press.get("articles", [])[:3]:
                lines.append(f"  - {a.get('title', '')[:60]}")

        if enrichment.get("market_data"):
            lines.append(f"Market data available: {list(enrichment['market_data'].keys())}")

        return "\n".join(lines) if lines else ""
