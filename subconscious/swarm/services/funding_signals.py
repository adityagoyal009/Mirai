"""
Funding Signals — searches for real-time funding rounds, acquisitions,
and competitive moves via SearXNG news search.
"""

import re
from typing import List, Dict, Optional
from .search_engine import SearchEngine
from ..utils.logger import get_logger

logger = get_logger('mirofish.funding')


class FundingSignals:
    """Fetches live funding/market signals from web search."""

    def __init__(self):
        self._search = SearchEngine()

    def search_funding(self, company_name: str, industry: str = "") -> Dict:
        """Search for funding rounds, valuations, and investor activity."""
        if not self._search.is_available():
            logger.warning("[Funding] SearXNG not available — skipping funding signals")
            return {"available": False, "signals": []}

        signals = []

        # Search for company-specific funding
        if company_name:
            results = self._search.search_news(
                f'"{company_name}" funding OR raised OR series OR valuation',
                max_results=10
            )
            for r in results:
                signal = self._extract_funding_signal(r)
                if signal:
                    signals.append(signal)

        # Search for industry funding trends
        if industry:
            results = self._search.search_news(
                f'{industry} startup funding 2026 raised',
                max_results=10
            )
            for r in results:
                signal = self._extract_funding_signal(r)
                if signal:
                    signal['type'] = 'industry_trend'
                    signals.append(signal)

        # Search for competitor funding
        if company_name and industry:
            results = self._search.search_news(
                f'{industry} competitor funding series seed 2026',
                max_results=5
            )
            for r in results:
                signal = self._extract_funding_signal(r)
                if signal:
                    signal['type'] = 'competitor'
                    signals.append(signal)

        # Search for acquisitions in the space
        if industry:
            results = self._search.search_news(
                f'{industry} acquisition acquired startup 2026',
                max_results=5
            )
            for r in results:
                signals.append({
                    'type': 'acquisition',
                    'title': r.get('title', ''),
                    'url': r.get('url', ''),
                    'snippet': r.get('content', '')[:200],
                    'date': r.get('publishedDate', ''),
                })

        logger.info(f"[Funding] Found {len(signals)} signals for {company_name or industry}")
        return {
            "available": True,
            "signal_count": len(signals),
            "signals": signals[:20],
        }

    def _extract_funding_signal(self, result: dict) -> Optional[Dict]:
        """Extract structured funding info from a search result."""
        title = result.get('title', '')
        content = result.get('content', '')
        text = f"{title} {content}"

        # Try to extract funding amount
        amount = None
        amount_match = re.search(
            r'\$(\d+(?:\.\d+)?)\s*(million|billion|M|B|mn|bn)',
            text, re.IGNORECASE
        )
        if amount_match:
            num = float(amount_match.group(1))
            unit = amount_match.group(2).lower()
            if unit in ('billion', 'b', 'bn'):
                num *= 1000
            amount = f"${num:.0f}M"

        # Try to extract round type
        round_type = None
        for rt in ['Series A', 'Series B', 'Series C', 'Series D', 'Seed', 'Pre-seed', 'IPO', 'SPAC']:
            if rt.lower() in text.lower():
                round_type = rt
                break

        if not amount and not round_type:
            return None

        return {
            'type': 'funding_round',
            'title': title[:120],
            'url': result.get('url', ''),
            'amount': amount,
            'round': round_type,
            'snippet': content[:200] if content else '',
            'date': result.get('publishedDate', ''),
        }

    def format_for_prompt(self, signals_data: Dict) -> str:
        """Format signals as context for LLM prompts."""
        if not signals_data.get('available') or not signals_data.get('signals'):
            return ""

        lines = ["Recent funding & market signals:"]
        for s in signals_data['signals'][:10]:
            parts = []
            if s.get('amount'):
                parts.append(s['amount'])
            if s.get('round'):
                parts.append(s['round'])
            detail = ' | '.join(parts)
            prefix = f"[{detail}] " if detail else ""
            lines.append(f"- {prefix}{s.get('title', '')}")

        return '\n'.join(lines)
