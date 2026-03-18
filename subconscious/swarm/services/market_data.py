"""
Market Data Service — OpenBB-powered financial data for BI grounding.

Provides live financial data (stock prices, company fundamentals, economic
indicators, news) to ground BI predictions in reality rather than relying
solely on LLM training knowledge.

Usage:
    market = MarketDataService()
    data = market.get_company_overview("AAPL")
    # → {"name": "Apple Inc.", "sector": "Technology", "market_cap": ..., ...}
"""

import os
from typing import Dict, Any, List, Optional

from ..utils.logger import get_logger

logger = get_logger('mirofish.market_data')


class MarketDataService:
    """
    Wraps OpenBB SDK for financial data access.
    Gracefully degrades if OpenBB is not installed or data providers
    are not configured.
    """

    def __init__(self):
        self._obb = None
        self._available = None

    def _ensure_openbb(self):
        """Lazy-initialize OpenBB."""
        if self._obb is not None:
            return self._available

        try:
            from openbb import obb
            self._obb = obb
            self._available = True
            logger.info("[OpenBB] Initialized successfully")
        except ImportError:
            self._available = False
            logger.warning(
                "[OpenBB] Not installed. Run: pip install openbb"
            )
        except Exception as e:
            self._available = False
            logger.warning(f"[OpenBB] Init failed: {e}")

        return self._available

    def is_available(self) -> bool:
        """Check if OpenBB is available."""
        return self._ensure_openbb()

    def get_company_overview(self, symbol: str) -> Dict[str, Any]:
        """
        Get company fundamentals: name, sector, market cap, description, etc.
        """
        if not self._ensure_openbb():
            return {"error": "OpenBB not available", "symbol": symbol}

        try:
            result = self._obb.equity.profile(symbol=symbol)
            if hasattr(result, 'results') and result.results:
                data = result.results[0]
                return {
                    "symbol": symbol,
                    "name": getattr(data, 'name', ''),
                    "sector": getattr(data, 'sector', ''),
                    "industry": getattr(data, 'industry', ''),
                    "market_cap": getattr(data, 'market_cap', None),
                    "description": getattr(data, 'description', ''),
                    "country": getattr(data, 'country', ''),
                    "employees": getattr(data, 'employees', None),
                    "website": getattr(data, 'website', ''),
                    "ceo": getattr(data, 'ceo', ''),
                }
            return {"symbol": symbol, "error": "No data returned"}
        except Exception as e:
            logger.warning(f"[OpenBB] Company overview failed for {symbol}: {e}")
            return {"symbol": symbol, "error": str(e)}

    def get_stock_price(self, symbol: str) -> Dict[str, Any]:
        """Get current/recent stock price data."""
        if not self._ensure_openbb():
            return {"error": "OpenBB not available", "symbol": symbol}

        try:
            result = self._obb.equity.price.quote(symbol=symbol)
            if hasattr(result, 'results') and result.results:
                data = result.results[0]
                return {
                    "symbol": symbol,
                    "price": getattr(data, 'last_price', None),
                    "change": getattr(data, 'change', None),
                    "change_percent": getattr(data, 'change_percent', None),
                    "volume": getattr(data, 'volume', None),
                    "high": getattr(data, 'high', None),
                    "low": getattr(data, 'low', None),
                    "year_high": getattr(data, 'year_high', None),
                    "year_low": getattr(data, 'year_low', None),
                }
            return {"symbol": symbol, "error": "No price data"}
        except Exception as e:
            logger.warning(f"[OpenBB] Stock price failed for {symbol}: {e}")
            return {"symbol": symbol, "error": str(e)}

    def get_financial_metrics(self, symbol: str) -> Dict[str, Any]:
        """Get key financial ratios and metrics."""
        if not self._ensure_openbb():
            return {"error": "OpenBB not available", "symbol": symbol}

        try:
            result = self._obb.equity.fundamental.metrics(symbol=symbol)
            if hasattr(result, 'results') and result.results:
                data = result.results[0]
                return {
                    "symbol": symbol,
                    "pe_ratio": getattr(data, 'pe_ratio', None),
                    "pb_ratio": getattr(data, 'pb_ratio', None),
                    "revenue_growth": getattr(data, 'revenue_growth', None),
                    "eps": getattr(data, 'eps', None),
                    "dividend_yield": getattr(data, 'dividend_yield', None),
                    "debt_to_equity": getattr(data, 'debt_to_equity', None),
                    "roe": getattr(data, 'roe', None),
                    "roa": getattr(data, 'roa', None),
                }
            return {"symbol": symbol, "error": "No metrics data"}
        except Exception as e:
            logger.warning(f"[OpenBB] Financial metrics failed for {symbol}: {e}")
            return {"symbol": symbol, "error": str(e)}

    def search_company(self, query: str) -> List[Dict[str, Any]]:
        """Search for companies by name/ticker."""
        if not self._ensure_openbb():
            return []

        try:
            result = self._obb.equity.search(query=query)
            if hasattr(result, 'results') and result.results:
                return [
                    {
                        "symbol": getattr(r, 'symbol', ''),
                        "name": getattr(r, 'name', ''),
                    }
                    for r in result.results[:10]
                ]
            return []
        except Exception as e:
            logger.warning(f"[OpenBB] Company search failed for '{query}': {e}")
            return []

    def get_market_news(
        self, symbol: Optional[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get market news, optionally filtered by symbol."""
        if not self._ensure_openbb():
            return []

        try:
            if symbol:
                result = self._obb.news.company(symbol=symbol, limit=limit)
            else:
                result = self._obb.news.world(limit=limit)

            if hasattr(result, 'results') and result.results:
                return [
                    {
                        "title": getattr(r, 'title', ''),
                        "date": str(getattr(r, 'date', '')),
                        "url": getattr(r, 'url', ''),
                        "source": getattr(r, 'source', ''),
                        "text": getattr(r, 'text', '')[:500],
                    }
                    for r in result.results[:limit]
                ]
            return []
        except Exception as e:
            logger.warning(f"[OpenBB] Market news failed: {e}")
            return []

    def get_economic_indicators(self) -> Dict[str, Any]:
        """Get key macro economic indicators."""
        if not self._ensure_openbb():
            return {"error": "OpenBB not available"}

        indicators = {}
        # Try to fetch common indicators
        try:
            # GDP
            result = self._obb.economy.gdp.nominal(country="united_states")
            if hasattr(result, 'results') and result.results:
                latest = result.results[-1]
                indicators["gdp"] = {
                    "value": getattr(latest, 'value', None),
                    "date": str(getattr(latest, 'date', '')),
                }
        except Exception:
            pass

        try:
            # CPI / Inflation
            result = self._obb.economy.cpi(country="united_states")
            if hasattr(result, 'results') and result.results:
                latest = result.results[-1]
                indicators["cpi"] = {
                    "value": getattr(latest, 'value', None),
                    "date": str(getattr(latest, 'date', '')),
                }
        except Exception:
            pass

        return indicators

    def get_industry_context(
        self, company: str, industry: str
    ) -> Dict[str, Any]:
        """
        Gather financial context for a company/industry for BI research.
        Returns a combined dict of all available data.
        """
        context: Dict[str, Any] = {
            "company_query": company,
            "industry": industry,
            "data_sources": [],
        }

        # Search for the company ticker
        matches = self.search_company(company)
        if matches:
            symbol = matches[0]["symbol"]
            context["matched_symbol"] = symbol
            context["matched_name"] = matches[0].get("name", "")

            # Get overview
            overview = self.get_company_overview(symbol)
            if "error" not in overview:
                context["overview"] = overview
                context["data_sources"].append("company_profile")

            # Get price
            price = self.get_stock_price(symbol)
            if "error" not in price:
                context["stock_price"] = price
                context["data_sources"].append("stock_price")

            # Get metrics
            metrics = self.get_financial_metrics(symbol)
            if "error" not in metrics:
                context["financial_metrics"] = metrics
                context["data_sources"].append("financial_metrics")

            # Get news
            news = self.get_market_news(symbol=symbol, limit=5)
            if news:
                context["company_news"] = news
                context["data_sources"].append("company_news")
        else:
            context["note"] = f"No public ticker found for '{company}'"

            # Still try to get general industry news
            news = self.get_market_news(limit=5)
            if news:
                context["market_news"] = news
                context["data_sources"].append("market_news")

        return context
