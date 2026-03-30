"""
OASIS Market Simulator — multi-round simulation of market reaction over 4 months.

Unlike the swarm (independent one-shot votes), OASIS runs interactive rounds where:
- Agents see previous round outcomes and remember their own prior stance
- Market events are injected between rounds
- Opinions evolve incrementally based on new information
- Final output: sentiment trajectory over time

When swarm agents are provided, OASIS selects 12 diverse panelists from the actual
swarm and seeds their scores from the swarm's evaluation — making OASIS a continuation
of the swarm rather than a disconnected simulation.
"""

import random
import statistics
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from ..config import Config
# Legacy Brave/SearXNG paths removed — OASIS now sources events via OpenClaw-backed search

logger = get_logger('mirofish.oasis')

_NO_EVENT = "No significant market event this month."

SIMULATION_ROUNDS = 4  # 4 months (reduced from 6 — trajectory stable by month 3-4)
AGENTS_PER_ROUND = 12  # Small focused group


class OasisSimulator:
    """Runs multi-round market reaction simulation."""

    def __init__(self):
        self.llm = LLMClient()
        self._headline_cache: Dict[Tuple[str, ...], List[Dict[str, str]]] = {}

    def simulate(self, exec_summary: str, research_context: str,
                 council_verdict: str, on_round_complete=None,
                 swarm_agents: Optional[List] = None,
                 stage: str = "",
                 extraction: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Simulate market reaction over the configured number of rounds.

        Args:
            swarm_agents: Optional list of SwarmAgent objects from the swarm predictor.
                          When provided, 12 diverse panelists are selected from the swarm
                          and their swarm scores seed the OASIS starting scores.

        Returns timeline of sentiment + key events per month.
        """
        if swarm_agents and len(swarm_agents) >= 12:
            agents = self._select_panelists_from_swarm(swarm_agents)
            logger.info(f"[OASIS] Selected {len(agents)} panelists from {len(swarm_agents)}-agent swarm")
        else:
            agents = self._create_panel(stage=stage)
            if swarm_agents is not None:
                logger.info(f"[OASIS] Swarm too small ({len(swarm_agents) if swarm_agents else 0} agents), "
                           f"falling back to hardcoded panel")

        startup_context = self._resolve_startup_context(exec_summary, extraction=extraction)
        logger.info(
            f"[OASIS] Context company='{startup_context['company']}', "
            f"industry='{startup_context['industry']}', "
            f"product='{startup_context['product'][:60]}'"
        )

        timeline = []
        previous_events = []
        previous_sentiment = 50  # Start neutral
        previous_panel_summary = ""  # Fed into next round's agent prompts

        # Track each agent's running sentiment score (1-10 scale).
        # When sourced from swarm, seed with the agent's swarm overall score;
        # otherwise start at neutral 5.0.
        agent_scores = {}
        for a in agents:
            if a.get('swarm_score') is not None:
                agent_scores[a['id']] = float(a['swarm_score'])
            else:
                agent_scores[a['id']] = 5.0

        for round_num in range(1, SIMULATION_ROUNDS + 1):
            month = round_num
            logger.info(f"[OASIS] Round {round_num}/{SIMULATION_ROUNDS} (Month {month})")

            # Source real market event for this month
            event = self._source_real_event(
                exec_summary, month, previous_events, previous_sentiment,
                startup_context=startup_context,
            )
            previous_events.append(event)

            # Each agent evaluates with accumulated context + their own prior score
            round_context = (
                f"{research_context}\n\n"
                f"COUNCIL VERDICT: {council_verdict}\n\n"
                f"TIMELINE SO FAR:\n"
                + "\n".join(f"Month {i+1}: {e}" for i, e in enumerate(previous_events))
                + f"\n\nCURRENT MONTH: {month}\n"
                f"LATEST EVENT: {event}\n"
            )

            if previous_panel_summary:
                round_context += f"\n{previous_panel_summary}\n"

            scores_snapshot = dict(agent_scores)  # Immutable copy for this round
            votes = self._run_round(agents, exec_summary, round_context, scores_snapshot)

            # Update agent scores with adjustments (clamped 1-10)
            for v in votes:
                aid = v['agent_id']
                old_score = agent_scores[aid]
                new_score = max(1.0, min(10.0, old_score + v['adjustment']))
                agent_scores[aid] = new_score

            # Sentiment = average of all agent scores, mapped to 0-100%
            scores_list = list(agent_scores.values())
            avg_score = sum(scores_list) / len(scores_list)
            sentiment_pct = round((avg_score - 1) / 9 * 100)  # 1->0%, 5.5->50%, 10->100%
            sentiment_pct = max(0, min(100, sentiment_pct))

            # Uncertainty quantification based on agent score variance
            std_dev = statistics.pstdev(scores_list) if len(scores_list) > 1 else 0.0
            confidence_low = max(0, sentiment_pct - std_dev * 15)
            confidence_high = min(100, sentiment_pct + std_dev * 15)

            round_result = {
                "month": month,
                "event": event,
                "sentiment_pct": sentiment_pct,
                "confidence_low": round(confidence_low, 1),
                "confidence_high": round(confidence_high, 1),
                "std_dev": round(std_dev, 4),
                "sentiment_change": sentiment_pct - previous_sentiment,
                "key_quote": votes[0]['reasoning'][:150] if votes else "",
                "votes": len(votes),
            }
            timeline.append(round_result)
            previous_sentiment = sentiment_pct
            previous_panel_summary = self._build_panel_summary(votes, sentiment_pct)

            if on_round_complete:
                on_round_complete(round_result)

        # Compute trajectory
        start = timeline[0]['sentiment_pct'] if timeline else 50
        end = timeline[-1]['sentiment_pct'] if timeline else 50
        trajectory = "improving" if end > start + 10 else "declining" if end < start - 10 else "stable"

        # Compute overall uncertainty summary across all rounds
        uncertainty_band = {}
        if timeline:
            uncertainty_band = {
                "low": min(r["confidence_low"] for r in timeline),
                "high": max(r["confidence_high"] for r in timeline),
                "avg_std": round(statistics.mean(r["std_dev"] for r in timeline), 4),
            }

        return {
            "timeline": timeline,
            "trajectory": trajectory,
            "start_sentiment": start,
            "final_sentiment": end,
            "uncertainty_band": uncertainty_band,
            "total_rounds": len(timeline),
        }

    def _create_panel(self, stage: str = "") -> List[Dict]:
        """Create a diverse panel of 12 agents for multi-round simulation,
        calibrated for the startup's stage."""
        s = (stage or "").lower().strip()

        if s in ("idea", "pre-seed", "pre seed", "preseed", "seed", "mvp"):
            roles = [
                "Pre-seed/seed VC evaluating early-stage deals",
                "Potential early adopter in the target market",
                "Industry analyst covering emerging startups in this sector",
                "Competitor product manager watching this space",
                "Regulatory expert in this industry",
                "Serial entrepreneur who bootstrapped similar products",
                "Target end-user who would pilot this product",
                "Angel investor evaluating founder-market fit",
                "Tech journalist covering startup launches",
                "Domain expert with 20 years in this field",
                "Accelerator partner evaluating cohort candidates",
                "Impact investor evaluating early-stage social/environmental return",
            ]
        elif s in ("series a", "series-a", "revenue"):
            roles = [
                "Series A VC evaluating product-market fit",
                "Potential enterprise customer in the target market",
                "Industry analyst covering this sector",
                "Competitor product manager watching this space",
                "Regulatory expert in this industry",
                "Serial entrepreneur who scaled similar products to $5M ARR",
                "Target end-user who would use this product",
                "Growth investor evaluating Series A to B trajectory",
                "Tech journalist covering this market",
                "Domain expert with 20 years in this field",
                "Skeptical seed-stage VC questioning if Series A metrics are met",
                "Impact investor evaluating social/environmental return",
            ]
        elif s in ("series b", "series-b"):
            roles = [
                "Series B VC evaluating scaling efficiency",
                "Enterprise customer evaluating long-term vendor commitment",
                "Industry analyst covering growth-stage companies in this sector",
                "Competitor VP Product watching this space",
                "Regulatory expert in this industry",
                "Operating partner at a growth fund focused on unit economics",
                "Power user dependent on this product for daily operations",
                "Late-stage investor evaluating Series B to C trajectory",
                "Business journalist covering the competitive landscape",
                "Domain expert with 20 years in this field",
                "Skeptical PE partner focused on margin sustainability",
                "Impact investor evaluating governance and team scalability",
            ]
        elif s in ("series c", "series c+", "growth", "pre-ipo", "late stage", "series-c", "scaling"):
            roles = [
                "Late-stage growth equity investor",
                "Enterprise customer evaluating vendor stability",
                "Industry analyst covering market leaders in this sector",
                "Competitor VP Strategy watching this space",
                "Regulatory expert in this industry",
                "Public markets analyst evaluating IPO readiness",
                "Large enterprise end-user dependent on this product",
                "Crossover hedge fund evaluating pre-IPO opportunities",
                "Business journalist covering the competitive landscape",
                "Domain expert with 20 years in this field",
                "Skeptical PE partner focused on unit economics at scale",
                "ESG analyst evaluating governance and sustainability",
            ]
        else:
            # Default: early stage (safest default, avoids penalizing young startups)
            roles = [
                "Pre-seed/seed VC evaluating early-stage deals",
                "Potential early adopter in the target market",
                "Industry analyst covering emerging startups in this sector",
                "Competitor product manager watching this space",
                "Regulatory expert in this industry",
                "Serial entrepreneur who bootstrapped similar products",
                "Target end-user who would pilot this product",
                "Angel investor evaluating founder-market fit",
                "Tech journalist covering startup launches",
                "Domain expert with 20 years in this field",
                "Accelerator partner evaluating cohort candidates",
                "Impact investor evaluating early-stage social/environmental return",
            ]

        return [{"id": i, "role": role} for i, role in enumerate(roles)]

    def _select_panelists_from_swarm(self, swarm_agents: List) -> List[Dict]:
        """Select 12 diverse panelists from the actual swarm agents.

        Selection strategy:
          1. Strongest bull (highest overall score)
          2. Strongest bear (lowest overall score)
          3-4. Two from Investor zone (random)
          5-6. Two from Analyst zone (random)
          7. One from Customer zone
          8. One from Operator zone
          9. One from Contrarian zone
          10. One from Wild Card zone
          11. Most internally conflicted (highest per-dimension score variance)
          12. One random remaining agent

        Each panelist dict carries:
          - id: sequential int for OASIS tracking
          - role: the agent's persona description from the swarm
          - swarm_score: the agent's overall score from the swarm (seeds OASIS)
          - zone: the agent's zone from the swarm
          - swarm_agent_id: original swarm agent_id for traceability
        """
        used_ids = set()
        selected = []

        def _pick(agent):
            """Add an agent to the panel if not already picked."""
            aid = getattr(agent, 'agent_id', None) or id(agent)
            if aid in used_ids:
                return False
            used_ids.add(aid)
            selected.append(agent)
            return True

        def _agents_in_zone(zone: str):
            return [a for a in swarm_agents
                    if getattr(a, 'zone', 'wildcard') == zone
                    and (getattr(a, 'agent_id', None) or id(a)) not in used_ids]

        def _pick_random_from_zone(zone: str, count: int):
            pool = _agents_in_zone(zone)
            for a in random.sample(pool, min(count, len(pool))):
                _pick(a)

        # 1. Strongest bull (highest overall score)
        sorted_by_score = sorted(swarm_agents, key=lambda a: getattr(a, 'overall', 5.0), reverse=True)
        _pick(sorted_by_score[0])

        # 2. Strongest bear (lowest overall score)
        _pick(sorted_by_score[-1])

        # 3-4. Two from Investor zone
        _pick_random_from_zone('investor', 2)

        # 5-6. Two from Analyst zone
        _pick_random_from_zone('analyst', 2)

        # 7. One from Customer zone
        _pick_random_from_zone('customer', 1)

        # 8. One from Operator zone
        _pick_random_from_zone('operator', 1)

        # 9. One from Contrarian zone
        _pick_random_from_zone('contrarian', 1)

        # 10. One from Wild Card zone
        _pick_random_from_zone('wildcard', 1)

        # 11. Most internally conflicted (highest per-dimension score variance)
        remaining = [a for a in swarm_agents
                     if (getattr(a, 'agent_id', None) or id(a)) not in used_ids]
        if remaining:
            def _dim_variance(agent):
                scores = getattr(agent, 'scores', {})
                dims = [v for k, v in scores.items() if k != 'overall' and isinstance(v, (int, float))]
                if len(dims) < 2:
                    return 0.0
                mean = sum(dims) / len(dims)
                return sum((d - mean) ** 2 for d in dims) / len(dims)

            most_conflicted = max(remaining, key=_dim_variance)
            _pick(most_conflicted)

        # 12. One random remaining agent
        remaining = [a for a in swarm_agents
                     if (getattr(a, 'agent_id', None) or id(a)) not in used_ids]
        if remaining:
            _pick(random.choice(remaining))

        # If any zone was empty and we have fewer than 12, backfill from remaining
        remaining = [a for a in swarm_agents
                     if (getattr(a, 'agent_id', None) or id(a)) not in used_ids]
        while len(selected) < AGENTS_PER_ROUND and remaining:
            agent = random.choice(remaining)
            _pick(agent)
            remaining = [a for a in remaining
                         if (getattr(a, 'agent_id', None) or id(a)) not in used_ids]

        # Convert SwarmAgent objects to OASIS panel dicts
        panel = []
        for i, agent in enumerate(selected):
            panel.append({
                "id": i,
                "role": getattr(agent, 'persona', f"Swarm Agent #{getattr(agent, 'agent_id', i)}"),
                "swarm_score": getattr(agent, 'overall', 5.0),
                "zone": getattr(agent, 'zone', 'wildcard'),
                "swarm_agent_id": getattr(agent, 'agent_id', i),
            })

        return panel

    # ── startup context resolution ───────────────────────────────

    def _resolve_startup_context(
        self,
        exec_summary: str,
        *,
        extraction: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """Resolve company context for OASIS without discarding structured fields."""
        extraction = extraction if isinstance(extraction, dict) else {}

        company = str(extraction.get("company", "") or "").strip()
        industry = str(extraction.get("industry", "") or "").strip()
        product = str(extraction.get("product", "") or "").strip()
        target_market = str(extraction.get("target_market", "") or "").strip()
        business_model = str(extraction.get("business_model", "") or "").strip()

        if company and industry:
            return {
                "company": company,
                "industry": industry,
                "product": product,
                "target_market": target_market,
                "business_model": business_model,
            }

        prompt = (
            "Extract the company name, industry, product, target market, and business model "
            "from this startup summary. Reply with EXACTLY five lines — nothing else:\n"
            "COMPANY: <name>\n"
            "INDUSTRY: <industry>\n"
            "PRODUCT: <product>\n"
            "TARGET MARKET: <target market>\n"
            "BUSINESS MODEL: <business model>\n\n"
            f"Summary:\n{exec_summary[:500]}"
        )
        response = (
            self.llm.chat([{"role": "user", "content": prompt}], max_tokens=60) or ""
        ).strip()

        company = company or ""
        industry = industry or ""
        for line in response.splitlines():
            raw = line.strip()
            line_upper = raw.upper()
            if line_upper.startswith("COMPANY:"):
                company = raw[len("COMPANY:"):].strip()
            elif line_upper.startswith("INDUSTRY:"):
                industry = raw[len("INDUSTRY:"):].strip()
            elif line_upper.startswith("PRODUCT:") and not product:
                product = raw[len("PRODUCT:"):].strip()
            elif line_upper.startswith("TARGET MARKET:") and not target_market:
                target_market = raw[len("TARGET MARKET:"):].strip()
            elif line_upper.startswith("BUSINESS MODEL:") and not business_model:
                business_model = raw[len("BUSINESS MODEL:"):].strip()

        if not company:
            logger.warning(
                "[OASIS] Could not extract company name from exec summary — "
                "falling back to generic 'startup'. OASIS web searches will NOT be company-specific."
            )
            company = "startup"
        if not industry:
            logger.warning(
                "[OASIS] Could not extract industry from exec summary — "
                "falling back to generic 'technology'. OASIS market simulation will use generic tech trends."
            )
            industry = "technology"

        return {
            "company": company,
            "industry": industry,
            "product": product,
            "target_market": target_market,
            "business_model": business_model,
        }

    def _headline_queries(self, startup_context: Dict[str, str]) -> List[str]:
        """Build multiple grounded search queries instead of a single company/industry string."""
        company = startup_context.get("company", "").strip()
        industry = startup_context.get("industry", "").strip()
        product = startup_context.get("product", "").strip()
        target_market = startup_context.get("target_market", "").strip()
        business_model = startup_context.get("business_model", "").strip()

        queries = []
        if company and company.lower() != "startup":
            queries.append(f"\"{company}\" news")
            if product:
                queries.append(f"\"{company}\" {product} news")
            if target_market:
                queries.append(f"\"{company}\" {target_market} customer partnership news")
        if industry and target_market:
            queries.append(f"{industry} {target_market} market news")
        if industry and product:
            queries.append(f"{industry} {product} market adoption news")
        if industry and business_model:
            queries.append(f"{industry} {business_model} pricing regulation news")
        if industry:
            queries.append(f"{industry} startup funding regulation news")

        deduped = []
        seen = set()
        for query in queries:
            norm = " ".join(query.lower().split())
            if norm and norm not in seen:
                seen.add(norm)
                deduped.append(query)
        return deduped[:5]

    # ── real headline sourcing ────────────────────────────────────

    def _fetch_real_headlines(
        self, startup_context: Dict[str, str], max_headlines: int = 6,
    ) -> List[Dict[str, str]]:
        """Fetch real news headlines via OpenClaw-backed web search.

        Returns a list of headline dicts (may be empty if search unavailable).
        """
        cache_key = (
            startup_context.get("company", "").strip().lower(),
            startup_context.get("industry", "").strip().lower(),
            startup_context.get("product", "").strip().lower(),
            startup_context.get("target_market", "").strip().lower(),
            startup_context.get("business_model", "").strip().lower(),
            max_headlines,
        )
        cached = self._headline_cache.get(cache_key)
        if cached is not None:
            return [dict(item) for item in cached]

        try:
            from .gateway_client import web_search
            collected: List[Dict[str, str]] = []
            seen = set()
            for query in self._headline_queries(startup_context):
                results = web_search(query, count=min(4, max_headlines), freshness="past 120 days")
                for result in results:
                    title = str(result.get("title", "") or "").strip()
                    url = str(result.get("url", "") or "").strip()
                    if not title:
                        continue
                    dedupe_key = (title.lower(), url.lower())
                    if dedupe_key in seen:
                        continue
                    seen.add(dedupe_key)
                    collected.append({
                        "title": title,
                        "url": url,
                        "description": str(result.get("description", "") or "").strip(),
                        "query": query,
                    })
                    if len(collected) >= max_headlines:
                        break
                if len(collected) >= max_headlines:
                    break
            if collected:
                self._headline_cache[cache_key] = collected[:max_headlines]
                logger.info(
                    f"[OASIS] Web search returned {len(collected)} headlines across "
                    f"{len(self._headline_queries(startup_context))} queries"
                )
                return [dict(item) for item in collected[:max_headlines]]
        except Exception as e:
            logger.warning(f"[OASIS] Web search for headlines failed (non-fatal): {e}")

        self._headline_cache[cache_key] = []
        return []

    # ── grounded event generation (replaces _generate_event) ─────

    def _source_real_event(
        self,
        exec_summary: str,
        month: int,
        previous_events: List[str],
        current_sentiment: int,
        *,
        startup_context: Dict[str, str],
    ) -> str:
        """Source a market event grounded in REAL news data.

        Pipeline:
        1. Fetch real headlines via OpenClaw-backed live search.
        2. Ask the LLM to summarize the most impactful headline into a
           single event sentence.
        3. If no headlines are found, return a "no event" marker — never
           fabricate.

        Accepts the same positional parameters as the old _generate_event()
        plus structured startup context.
        """
        company_name = startup_context.get("company", "startup")
        industry = startup_context.get("industry", "technology")
        product = startup_context.get("product", "")
        target_market = startup_context.get("target_market", "")
        business_model = startup_context.get("business_model", "")
        headlines = self._fetch_real_headlines(startup_context)

        # --- No headlines → no fabrication ---
        if not headlines:
            logger.info(
                f"[OASIS] Month {month}: no real headlines found — "
                "returning 'no event' (NOT fabricating)"
            )
            return _NO_EVENT

        # --- LLM summarization grounded in real data ---
        headline_block = "\n".join(
            f"  - {item.get('title', '')} | Query: {item.get('query', '')} | URL: {item.get('url', '')}"
            for item in headlines
        )
        prompt = (
            f"You are summarizing real market news for a startup simulation.\n\n"
            f"STARTUP: {exec_summary[:300]}\n"
            f"COMPANY: {company_name}\n"
            f"INDUSTRY: {industry}\n"
            f"PRODUCT: {product or 'Not specified'}\n"
            f"TARGET MARKET: {target_market or 'Not specified'}\n"
            f"BUSINESS MODEL: {business_model or 'Not specified'}\n"
            f"MONTH: {month} of {SIMULATION_ROUNDS}\n"
            f"CURRENT MARKET SENTIMENT: {current_sentiment}%\n"
            f"PREVIOUS EVENTS:\n"
            + "\n".join(f"  Month {i+1}: {e}" for i, e in enumerate(previous_events))
            + "\n\n"
            f"REAL NEWS HEADLINES (sourced just now):\n{headline_block}\n\n"
            f"Given these REAL news headlines about {company_name}/{industry}, "
            f"summarize the single most impactful event for this startup's trajectory. "
            f"If none are directly relevant, say '{_NO_EVENT}'\n\n"
            f"RULES:\n"
            f"- One sentence only\n"
            f"- Must be grounded in the headlines above — do NOT invent facts\n"
            f"- Reference the actual news when possible\n\n"
            f"Event for month {month}:"
        )
        response = self.llm.chat(
            [{"role": "user", "content": prompt}], max_tokens=120,
        )
        event = (response or _NO_EVENT).strip()

        source_tag = "real-data-grounded"
        if event == _NO_EVENT:
            source_tag = "no-event"
        logger.info(f"[OASIS] Month {month} event [{source_tag}]: {event[:120]}")

        return event

    def _run_round(self, agents: List[Dict], exec_summary: str,
                   context: str, agent_scores: Dict[int, float]) -> List[Dict]:
        """Run all agents for one round, returning incremental adjustments."""
        results = []

        def evaluate_agent(agent):
            prior_score = agent_scores[agent['id']]
            prompt = (
                f"You are: {agent['role']}\n\n"
                f"STARTUP:\n{exec_summary[:300]}\n\n"
                f"{context}\n\n"
                f"Your current confidence in this startup is {prior_score:.1f}/10.\n\n"
                f"Based on this month's event and accumulated context, how does your confidence CHANGE?\n\n"
                f"Reply with a number from -2 to +2 (in 0.5 increments) followed by a one-sentence reason.\n"
                f"Examples:\n"
                f"  +1.0 This regulation creates genuine tailwind for their market.\n"
                f"  -0.5 Minor competitive threat but doesn't change fundamentals.\n"
                f"  0 This event is neutral for their specific positioning.\n"
                f"  +0.5 Positive signal but not enough to materially change outlook.\n\n"
                f"Your adjustment and reason:"
            )
            response = (self.llm.chat([{"role": "user", "content": prompt}], max_tokens=100) or "0 No change.").strip()

            # Parse adjustment from response
            adjustment = 0.0
            try:
                # Look for a number at the start like "+1.0", "-0.5", "0"
                import re
                match = re.match(r'^([+-]?\d+(?:\.\d+)?)', response.strip())
                if match:
                    adjustment = float(match.group(1))
                    # Clamp to [-2, +2]
                    adjustment = max(-2.0, min(2.0, adjustment))
                else:
                    # Fallback: look for improved/worsened keywords
                    lower = response.lower()
                    if 'improved' in lower or 'positive' in lower or 'tailwind' in lower:
                        adjustment = 0.5
                    elif 'worsened' in lower or 'negative' in lower or 'threat' in lower:
                        adjustment = -0.5
            except (ValueError, TypeError):
                pass

            return {
                "agent_id": agent['id'],
                "role": agent['role'],
                "adjustment": adjustment,
                "sentiment": 1 if adjustment > 0 else (-1 if adjustment < 0 else 0),
                "reasoning": response,
            }

        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = [pool.submit(evaluate_agent, a) for a in agents]
            for f in as_completed(futures):
                try:
                    results.append(f.result())
                except Exception as e:
                    logger.warning(f"[OASIS] Agent failed: {e}")

        return results

    def _build_panel_summary(self, votes: List[Dict], sentiment_pct: int) -> str:
        """Build a text summary of panel opinions for inter-agent visibility."""
        if not votes:
            return ""

        bullish = [v for v in votes if v['adjustment'] > 0]
        bearish = [v for v in votes if v['adjustment'] < 0]
        neutral = [v for v in votes if v['adjustment'] == 0]

        bullish.sort(key=lambda v: v['adjustment'], reverse=True)
        bearish.sort(key=lambda v: v['adjustment'])

        lines = [
            f"PANEL CONSENSUS FROM LAST ROUND ({len(votes)} analysts):",
            f"  Overall sentiment: {sentiment_pct}%",
            f"  Breakdown: {len(bullish)} bullish, {len(bearish)} bearish, {len(neutral)} neutral",
        ]

        if bullish:
            lines.append("  Strongest bull case:")
            for v in bullish[:2]:
                reason = v['reasoning'][:120].strip()
                lines.append(f"    - {v['role']}: {reason}")

        if bearish:
            lines.append("  Strongest bear case:")
            for v in bearish[:2]:
                reason = v['reasoning'][:120].strip()
                lines.append(f"    - {v['role']}: {reason}")

        if len(bullish) > len(bearish) * 2 and bearish:
            lines.append("  NOTE: The bearish minority raised concerns worth considering.")
        elif len(bearish) > len(bullish) * 2 and bullish:
            lines.append("  NOTE: The bullish minority identified opportunities worth considering.")

        return "\n".join(lines)
