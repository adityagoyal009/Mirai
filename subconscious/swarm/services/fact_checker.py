"""
Fact Checker — validates factual claims from swarm agent reasoning
against REAL external sources instead of LLM-asking-LLM circular verification.

Verification sources:
  1. LLM extracts specific quantitative claims (acceptable use of LLM)
  2. Jina Grounding API (most authoritative, optional — requires JINA_API_KEY)
  3. OpenClaw-backed live web search
  4. SEC EDGAR + Yahoo Finance (free, no API key — public company data via HTTP)

Each claim is independently verified against external evidence.
"""

import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

import requests

from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger

logger = get_logger('mirofish.factcheck')


# ---------------------------------------------------------------------------
# Claim extraction (LLM call — acceptable: this is parsing, not verification)
# ---------------------------------------------------------------------------

_CLAIM_EXTRACTION_PROMPT = """You are a claim extractor. Given agent reasoning text about a company or market, extract ONLY specific, verifiable factual claims — especially quantitative ones.

Focus on:
- Market sizes (e.g., "$2B market", "TAM of $50 billion")
- Revenue / financial figures (e.g., "revenue of $100M", "ARR of $20M")
- Funding amounts (e.g., "raised $50M Series B", "total funding of $120M")
- Growth rates (e.g., "grew 40% YoY", "CAGR of 25%")
- Dates and timelines (e.g., "founded in 2019", "IPO in 2024")
- Company-specific facts (e.g., "500 employees", "operates in 30 countries")
- Regulatory or legal claims (e.g., "FDA approved", "SOC 2 compliant")

Return JSON: {"claims": [{"text": "exact claim text", "category": "market_size|revenue|funding|growth|date|company_fact|regulatory", "company": "company name if mentioned or null", "ticker": "stock ticker if known or null", "search_query": "best Google query to verify this"}]}

Extract at most 15 claims. Skip vague opinions or subjective assessments."""


def _extract_claims(agent_reasonings: List[str]) -> List[Dict[str, Any]]:
    """Use LLM to parse reasoning text into discrete, verifiable claims."""
    sample = "\n".join(f"- {r[:300]}" for r in agent_reasonings[:30])
    try:
        llm = LLMClient()
        messages = [
            {"role": "system", "content": _CLAIM_EXTRACTION_PROMPT},
            {"role": "user", "content": f"Agent Reasoning Samples:\n{sample}"},
        ]
        result = llm.chat_json(messages=messages, temperature=0.1, max_tokens=2000)
        claims = result.get("claims", [])
        logger.info(f"[FactCheck] Extracted {len(claims)} claims from agent reasoning")
        return claims[:15]
    except Exception as e:
        # FC-1 FIX: raise so verify() can return a failed=True result
        # (returning [] here causes trust_score=0.0 which is indistinguishable from "all contradicted")
        logger.error(f"[FactCheck] Claim extraction failed: {e}")
        raise


# ---------------------------------------------------------------------------
# Source 1: Live web search (OpenClaw-backed)
# ---------------------------------------------------------------------------

def _check_live_search(engine: Any, claim_text: str, search_query: str) -> Optional[Dict[str, Any]]:
    """Verify a claim against the live OpenClaw-backed search wrapper."""
    query = (search_query or claim_text or "").strip()
    if not query:
        return None
    try:
        results = engine.search(query, max_results=5, time_range="past 180 days")
        verification = _score_search_results(claim_text, results, source_label="OpenClaw Search")
        if verification:
            return verification
        if query != claim_text:
            fallback_results = engine.search(claim_text, max_results=5, time_range="past 180 days")
            return _score_search_results(claim_text, fallback_results, source_label="OpenClaw Search")
    except Exception as e:
        logger.debug(f"[FactCheck] Live search lookup failed: {e}")
    return None


# ---------------------------------------------------------------------------
# Source 3: SEC EDGAR — direct HTTP (free, no API key, no library)
# ---------------------------------------------------------------------------

def _check_sec_edgar(company: Optional[str], ticker: Optional[str], category: str) -> Optional[Dict[str, Any]]:
    """Search SEC EDGAR directly via free JSON API. No library needed."""
    if category not in ("revenue", "funding", "market_size", "company_fact"):
        return None
    query = ticker or company
    if not query:
        return None
    try:
        import time
        time.sleep(0.1)  # SEC rate limit: 10 req/sec
        resp = requests.get(
            "https://efts.sec.gov/LATEST/search-index",
            params={"q": query, "dateRange": "custom", "startdt": "2024-01-01", "forms": "10-K,10-Q"},
            headers={"User-Agent": "Mirai/1.0 mirai@example.com"},
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        hits = resp.json().get("hits", {}).get("hits", [])
        if hits:
            filing = hits[0].get("_source", {})
            return {
                "status": "UNVERIFIED",
                "source": "sec_edgar",
                "source_url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company={query}&type=10-K&dateb=&owner=include&count=5",
                "evidence": f"SEC filing: {filing.get('form_type', 'N/A')} filed {filing.get('file_date', 'N/A')} by {filing.get('entity_name', query)}",
            }
    except Exception as e:
        logger.debug(f"[FactCheck] SEC EDGAR lookup failed: {e}")
    return None


# ---------------------------------------------------------------------------
# Source 4: Yahoo Finance — direct HTTP (free, no API key, no library)
# ---------------------------------------------------------------------------

def _check_yahoo_finance(claim_text: str, company: Optional[str], ticker: Optional[str], category: str) -> Optional[Dict[str, Any]]:
    """Query Yahoo Finance directly via public JSON API. No library needed."""
    symbol = ticker
    if not symbol:
        # Try company name as ticker guess
        symbol = company.upper().replace(" ", "").replace(",", "")[:5] if company else None
    if not symbol:
        return None
    try:
        resp = requests.get(
            f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}",
            params={"modules": "financialData,defaultKeyStatistics,summaryDetail"},
            headers={"User-Agent": "Mozilla/5.0 (Mirai/1.0)"},
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        results = resp.json().get("quoteSummary", {}).get("result", [])
        if not results:
            return None
        data = results[0]
        financial = data.get("financialData", {})
        summary = data.get("summaryDetail", {})
        stats = data.get("defaultKeyStatistics", {})

        info = {}
        for key, section, field in [
            ("totalRevenue", financial, "totalRevenue"),
            ("marketCap", summary, "marketCap"),
            ("revenueGrowth", financial, "revenueGrowth"),
            ("fullTimeEmployees", financial, "fullTimeEmployees"),
            ("regularMarketPrice", summary, "regularMarketPrice"),
        ]:
            val = section.get(field, {})
            info[key] = val.get("raw") if isinstance(val, dict) else val

        company_name = data.get("quoteType", {}).get("shortName", symbol)

        # If no meaningful data returned, skip
        if not info.get("regularMarketPrice") and not info.get("totalRevenue"):
            return None

        # Extract numbers from claim and compare
        claim_numbers = _extract_numbers(claim_text)
        if not claim_numbers:
            # No numbers to verify, but filing exists
            return {
                "status": "UNVERIFIED", "source": "yahoo_finance",
                "source_url": f"https://finance.yahoo.com/quote/{symbol}",
                "evidence": f"Company found: {company_name}. Revenue: {_format_number(info.get('totalRevenue'))}, Market Cap: {_format_number(info.get('marketCap'))}",
            }

        # Try to match claim numbers against financial data
        for claim_num in claim_numbers:
            for metric_name, metric_val in info.items():
                if metric_val is None:
                    continue
                try:
                    ratio = claim_num / float(metric_val) if float(metric_val) != 0 else 999
                    if 0.85 <= ratio <= 1.15:  # 15% tolerance
                        return {
                            "status": "VERIFIED", "source": "yahoo_finance",
                            "source_url": f"https://finance.yahoo.com/quote/{symbol}",
                            "evidence": f"{metric_name}: {_format_number(metric_val)} matches claim ({_format_number(claim_num)})",
                        }
                    elif 0.5 <= ratio <= 2.0:
                        pass  # Close but not matching
                    elif ratio < 0.5 or ratio > 2.0:
                        return {
                            "status": "CONTRADICTED", "source": "yahoo_finance",
                            "source_url": f"https://finance.yahoo.com/quote/{symbol}",
                            "evidence": f"Claim says {_format_number(claim_num)} but {metric_name} is {_format_number(metric_val)}",
                        }
                except (ValueError, ZeroDivisionError):
                    continue

        return None
    except Exception as e:
        logger.debug(f"[FactCheck] Yahoo Finance lookup failed: {e}")
    return None


# ---------------------------------------------------------------------------
# Shared search-result scoring logic (used by live search handlers)
# ---------------------------------------------------------------------------

def _score_search_results(claim_text: str, results: List[Dict[str, Any]], source_label: str) -> Optional[Dict[str, Any]]:
    """
    Score a list of search results against a claim.
    Used by live search handlers.

    Returns the best matching result as a verification dict, or None.
    """
    claim_numbers = _extract_numbers(claim_text)
    claim_lower = claim_text.lower()

    best_match = None
    best_score = 0.0

    for r in results:
        content = (r.get("content", "") or "").lower()
        title = (r.get("title", "") or "").lower()
        combined = f"{title} {content}"
        url = r.get("url", "")
        domain = _extract_domain(url)
        credibility = r.get("credibility_weight", 1.0)

        score = 0.0

        # Check if key numbers from the claim appear in the result
        result_numbers = _extract_numbers(combined)
        for cn in claim_numbers:
            for rn in result_numbers:
                if _numbers_close(cn, rn, tolerance=0.15):
                    score += 3.0  # Strong: matching number
                    break
                elif _numbers_close(cn, rn, tolerance=0.5):
                    score += 1.0  # Weak: roughly similar magnitude
                    break

        # Check for key terms overlap
        claim_keywords = set(re.findall(r'\b[a-z]{4,}\b', claim_lower))
        result_keywords = set(re.findall(r'\b[a-z]{4,}\b', combined))
        overlap = claim_keywords & result_keywords
        if len(overlap) >= 3:
            score += 1.0
        if len(overlap) >= 5:
            score += 1.0

        # Credibility boost
        score *= credibility

        if score > best_score:
            best_score = score
            best_match = {
                "url": url,
                "domain": domain,
                "content_snippet": (r.get("content", "") or "")[:200],
                "title": r.get("title", ""),
                "score": score,
            }

    if not best_match or best_score < 1.0:
        return None

    # Determine status based on match quality
    if best_score >= 3.0:
        status = "VERIFIED"
    else:
        status = "UNVERIFIED"

    # Check for contradictions: if result numbers exist but differ significantly
    if claim_numbers and best_match:
        combined_text = best_match.get("content_snippet", "").lower()
        result_nums = _extract_numbers(combined_text)
        for cn in claim_numbers:
            for rn in result_nums:
                if cn > 0 and rn > 0:
                    ratio = max(cn, rn) / min(cn, rn)
                    if 2.0 < ratio < 100:
                        status = "CONTRADICTED"
                        break

    return {
        "source": f"{source_label} ({best_match['domain']})",
        "source_url": best_match["url"],
        "status": status,
        "evidence": best_match["content_snippet"],
    }


# ---------------------------------------------------------------------------
# Number extraction and comparison helpers
# ---------------------------------------------------------------------------

def _extract_numbers(text: str) -> List[float]:
    """Extract numeric values from text, handling $2B, 40%, $50M, etc."""
    numbers = []

    # Match patterns like $2.5B, $50M, $100K, 2.5 billion, etc.
    money_patterns = re.findall(
        r'\$\s*([\d,.]+)\s*(trillion|billion|million|bn|bil|mil|[tbmk])\b',
        text, re.IGNORECASE
    )
    for val_str, suffix in money_patterns:
        try:
            val = float(val_str.replace(",", ""))
            suffix_lower = suffix.lower()
            if suffix_lower in ("t", "trillion"):
                val *= 1_000_000_000_000
            elif suffix_lower in ("b", "bn", "bil", "billion"):
                val *= 1_000_000_000
            elif suffix_lower in ("m", "mil", "million"):
                val *= 1_000_000
            elif suffix_lower in ("k",):
                val *= 1_000
            numbers.append(val)
        except ValueError:
            pass

    # Match plain numbers with $ prefix
    plain_dollar = re.findall(r'\$([\d,.]+)\b', text)
    for val_str in plain_dollar:
        try:
            val = float(val_str.replace(",", ""))
            if val not in numbers:
                numbers.append(val)
        except ValueError:
            pass

    # Match percentages
    pct_patterns = re.findall(r'([\d,.]+)\s*%', text)
    for val_str in pct_patterns:
        try:
            numbers.append(float(val_str.replace(",", "")))
        except ValueError:
            pass

    # Match plain large numbers (with commas)
    large_nums = re.findall(r'\b([\d,]+(?:\.\d+)?)\s*(?:billion|million|trillion)\b', text, re.IGNORECASE)
    for val_str in large_nums:
        try:
            val = float(val_str.replace(",", ""))
            # Handle standalone: "2.5 billion" (non-$ prefixed)
            idx = text.lower().find(val_str.lower())
            if idx >= 0:
                after = text[idx + len(val_str):idx + len(val_str) + 15].lower().strip()
                if after.startswith("trillion"):
                    val *= 1_000_000_000_000
                elif after.startswith("billion"):
                    val *= 1_000_000_000
                elif after.startswith("million"):
                    val *= 1_000_000
            if val not in numbers:
                numbers.append(val)
        except ValueError:
            pass

    return numbers


def _numbers_close(a: float, b: float, tolerance: float = 0.15) -> bool:
    """Check if two numbers are within a tolerance ratio of each other."""
    if a == 0 and b == 0:
        return True
    if a == 0 or b == 0:
        return False
    ratio = max(a, b) / min(a, b)
    return ratio <= (1.0 + tolerance)


def _format_number(val: float) -> str:
    """Format a large number with human-readable suffix."""
    if val >= 1_000_000_000_000:
        return f"${val / 1_000_000_000_000:.1f}T"
    elif val >= 1_000_000_000:
        return f"${val / 1_000_000_000:.1f}B"
    elif val >= 1_000_000:
        return f"${val / 1_000_000:.1f}M"
    elif val >= 1_000:
        return f"${val / 1_000:.1f}K"
    else:
        return f"${val:,.0f}"


def _extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        from urllib.parse import urlparse
        hostname = urlparse(url).hostname or ""
        if hostname.startswith("www."):
            hostname = hostname[4:]
        return hostname
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Main verification pipeline
# ---------------------------------------------------------------------------

class VerifiedFactChecker:
    """
    Real fact verification that cross-references claims against external sources
    instead of asking another LLM to judge (circular verification).

    Sources (checked in order, first definitive result wins):
      0. Jina Grounding API (if JINA_API_KEY is set — most authoritative)
      1. OpenClaw-backed live search
      2. SEC EDGAR filings (direct HTTP, no library needed)
      3. Yahoo Finance stock/revenue/market cap data (direct HTTP, no library needed)
    """

    def __init__(self):
        self._search_engine = None

    def _get_search_engine(self):
        if self._search_engine is None:
            from .search_engine import SearchEngine

            self._search_engine = SearchEngine()
        return self._search_engine

    def _check_jina_grounding(self, claim_text: str) -> Optional[Dict]:
        """Use Jina's grounding API for factuality verification."""
        api_key = os.environ.get('JINA_API_KEY', '')
        if not api_key:
            return None
        try:
            resp = requests.get(
                f"https://g.jina.ai/{requests.utils.quote(claim_text)}",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Accept": "application/json",
                },
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                factuality = data.get("data", {}).get("factuality", -1)
                result = data.get("data", {}).get("result", "")
                references = data.get("data", {}).get("references", [])
                if factuality >= 0:
                    status = "VERIFIED" if factuality > 0.7 else ("CONTRADICTED" if factuality < 0.3 else "UNVERIFIED")
                    return {
                        "status": status,
                        "source": "jina_grounding",
                        "source_url": references[0].get("url", "") if references else "",
                        "evidence": result[:200],
                        "factuality_score": factuality,
                    }
        except Exception as e:
            logger.warning(f"[FactCheck] Jina grounding failed: {e}")
        return None

    def verify(
        self,
        agent_reasonings: List[str],
        research_context: str = "",
    ) -> Dict[str, Any]:
        """
        Extract and verify factual claims from agent reasoning.

        Args:
            agent_reasonings: List of reasoning text strings from swarm agents.
            research_context: Original research data (used for context, not as
                              the verification source -- that would be circular).

        Returns:
            Dict with claims list, trust_score, and counts.
        """
        if not agent_reasonings:
            return self._empty_result()

        # Step 1: Extract discrete claims using LLM (parsing, not verification)
        try:
            raw_claims = _extract_claims(agent_reasonings)
        except Exception as e:
            # FC-1 FIX: return a distinct failed result so callers don't mistake
            # this for "all claims contradicted" (trust_score=0.0)
            logger.error(f"[FactCheck] Claim extraction failed — returning failed fact-check: {e}")
            return self._failed_result(str(e))
        if not raw_claims:
            logger.info("[FactCheck] No verifiable claims extracted")
            return self._empty_result()

        # Step 2: Verify each claim against external sources (parallel)
        verified_claims = []
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {
                pool.submit(self._verify_single_claim, claim): claim
                for claim in raw_claims
            }
            for future in as_completed(futures):
                claim = futures[future]
                try:
                    result = future.result()
                    verified_claims.append(result)
                except Exception as e:
                    logger.debug(f"[FactCheck] Claim verification error: {e}")
                    verified_claims.append({
                        "text": claim.get("text", ""),
                        "status": "UNVERIFIED",
                        "source": None,
                        "source_url": None,
                        "evidence": f"Verification error: {e}",
                    })

        # Step 3: Aggregate results
        return self._aggregate(verified_claims)

    def _verify_single_claim(self, claim: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify a single claim against all available external sources.
        Returns the first definitive result, or UNVERIFIED if none match.

        Pipeline order:
          0. Jina Grounding (most authoritative, if JINA_API_KEY is set)
          1. OpenClaw-backed live search
          2. SEC EDGAR + Yahoo Finance (for public company financial claims)
        """
        claim_text = claim.get("text", "")
        category = claim.get("category", "")
        company = claim.get("company")
        ticker = claim.get("ticker")
        search_query = claim.get("search_query", "")

        result = {
            "text": claim_text,
            "status": "UNVERIFIED",
            "source": None,
            "source_url": None,
            "evidence": None,
        }

        # --- Source 0: Jina Grounding (most authoritative, if API key set) ---
        jina = self._check_jina_grounding(claim_text)
        if jina and jina["status"] in ("VERIFIED", "CONTRADICTED"):
            result.update({
                "status": jina["status"],
                "source": jina["source"],
                "source_url": jina["source_url"],
                "evidence": jina["evidence"],
            })
            logger.debug(f"[FactCheck] Jina: '{claim_text[:60]}' -> {jina['status']}")
            return result

        # --- Source 1: OpenClaw-backed live search ---
        live_search = _check_live_search(self._get_search_engine(), claim_text, search_query)
        if live_search and live_search["status"] in ("VERIFIED", "CONTRADICTED"):
            result.update({
                "status": live_search["status"],
                "source": live_search["source"],
                "source_url": live_search["source_url"],
                "evidence": live_search["evidence"],
            })
            logger.debug(f"[FactCheck] LiveSearch: '{claim_text[:60]}' -> {live_search['status']}")
            return result

        if live_search:
            result["source"] = live_search["source"]
            result["source_url"] = live_search["source_url"]
            result["evidence"] = live_search["evidence"]

        # --- Source 2: SEC EDGAR (filings for public companies, direct HTTP) ---
        edgar = _check_sec_edgar(company, ticker, category)
        if edgar:
            if result["source"] is None:
                result["source"] = edgar["source"]
                result["source_url"] = edgar["source_url"]
                result["evidence"] = edgar["evidence"]

        # --- Source 3: Yahoo Finance (stock/revenue/market cap, direct HTTP) ---
        yf_result = _check_yahoo_finance(claim_text, company, ticker, category)
        if yf_result:
            if yf_result["status"] in ("VERIFIED", "CONTRADICTED"):
                result.update({
                    "status": yf_result["status"],
                    "source": yf_result["source"],
                    "source_url": yf_result["source_url"],
                    "evidence": yf_result["evidence"],
                })
                logger.debug(f"[FactCheck] Yahoo Finance: '{claim_text[:60]}' -> {yf_result['status']}")
                return result
            # Use as supplementary evidence if nothing better
            if result["source"] is None:
                result["source"] = yf_result["source"]
                result["source_url"] = yf_result["source_url"]
                result["evidence"] = yf_result["evidence"]

        return result

    def _aggregate(self, claims: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate individual claim results into a summary report."""
        verified = sum(1 for c in claims if c["status"] == "VERIFIED")
        unverified = sum(1 for c in claims if c["status"] == "UNVERIFIED")
        contradicted = sum(1 for c in claims if c["status"] == "CONTRADICTED")
        total = max(len(claims), 1)

        trust_score = round(verified / total, 2)
        critical_contradictions = [
            c["text"] for c in claims if c["status"] == "CONTRADICTED"
        ]

        logger.info(
            f"[FactCheck] Results: {verified} verified, {unverified} unverified, "
            f"{contradicted} contradicted (trust_score={trust_score})"
        )

        return {
            "claims": claims,
            "trust_score": trust_score,
            "confidence_impact": trust_score,
            "verified_count": verified,
            "unverified_count": unverified,
            "contradicted_count": contradicted,
            # Legacy keys -- callers read these
            "verified": verified,
            "unverified": unverified,
            "contradicted": contradicted,
            "critical_contradictions": critical_contradictions[:5],
        }

    @staticmethod
    def _empty_result() -> Dict[str, Any]:
        return {
            "claims": [],
            "trust_score": 0.0,
            "confidence_impact": 0.0,
            "verified_count": 0,
            "unverified_count": 0,
            "contradicted_count": 0,
            "verified": 0,
            "unverified": 0,
            "contradicted": 0,
            "critical_contradictions": [],
        }

    @staticmethod
    def _failed_result(reason: str = "") -> Dict[str, Any]:
        """FC-1 FIX: Distinct result for when the fact-checker itself failed to run.
        trust_score=None distinguishes this from 'all claims contradicted' (trust_score=0.0)."""
        return {
            "claims": [],
            "trust_score": None,  # None = fact-check didn't run (not "0% trustworthy")
            "confidence_impact": 0.0,
            "verified_count": 0,
            "unverified_count": 0,
            "contradicted_count": 0,
            "verified": 0,
            "unverified": 0,
            "contradicted": 0,
            "critical_contradictions": [],
            "failed": True,
            "failure_reason": reason,
        }


# ---------------------------------------------------------------------------
# Backward-compatible module-level function (preserves existing call sites)
# ---------------------------------------------------------------------------

_checker = VerifiedFactChecker()


def check_facts(agent_reasonings: List[str], research_context: str) -> Dict[str, Any]:
    """
    Backward-compatible entry point.

    Called by:
      - swarm_predictor.py: check_facts(reasonings, research_context)
      - business_intel.py:  check_facts(research_claims, exec_summary)

    Delegates to VerifiedFactChecker which uses only FREE external sources.
    """
    return _checker.verify(agent_reasonings, research_context)
