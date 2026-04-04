"""
OASIS Market Simulator — deep multi-round simulation of market reaction over 6 months.

Unlike the swarm (independent one-shot votes), OASIS runs interactive rounds where:
- Agents see previous round outcomes and remember their own prior stance
- Market events are injected between rounds
- Opinions evolve incrementally based on new information
- Final output: sentiment trajectory over time

When swarm agents are provided, OASIS selects 12 diverse panelists from the actual
swarm and seeds their scores from the swarm's evaluation — making OASIS a continuation
of the swarm rather than a disconnected simulation.
"""

import json
import random
import statistics
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
# Legacy Brave/SearXNG paths removed — OASIS now sources events via live web search

logger = get_logger('mirofish.oasis')

_NO_EVENT = "No significant market event this month."
SIMULATION_MODE = "deep"
SIMULATION_ROUNDS = 6
AGENTS_PER_ROUND = 12
HEADLINES_PER_ROUND = 8

_FRESHNESS_BY_MONTH = {
    1: "past 45 days",
    2: "past 90 days",
    3: "past 120 days",
    4: "past 180 days",
    5: "past 240 days",
    6: "past 365 days",
}

_SCORE_DIMENSION_LABELS = {
    "market_timing": "market timing",
    "competition_landscape": "competition landscape",
    "business_model_viability": "business model viability",
    "team_execution_signals": "team execution",
    "regulatory_news_environment": "regulatory exposure",
    "social_proof_demand": "customer demand",
    "pattern_match": "pattern match",
    "capital_efficiency": "capital efficiency",
    "scalability_potential": "scalability",
    "exit_potential": "exit potential",
}

_ZONE_PROFILE_DEFAULTS = {
    "investor": {
        "lens": "portfolio construction, downside protection, and return potential",
        "influence": 1.15,
        "adaptability": 0.9,
        "attention_dims": ("business_model_viability", "capital_efficiency", "exit_potential"),
    },
    "customer": {
        "lens": "switching friction, budget fit, and concrete buyer value",
        "influence": 1.0,
        "adaptability": 1.0,
        "attention_dims": ("social_proof_demand", "competition_landscape", "business_model_viability"),
    },
    "operator": {
        "lens": "execution realism, scaling constraints, and implementation burden",
        "influence": 1.0,
        "adaptability": 0.95,
        "attention_dims": ("team_execution_signals", "scalability_potential", "capital_efficiency"),
    },
    "analyst": {
        "lens": "market structure, adoption evidence, and strategic positioning",
        "influence": 1.1,
        "adaptability": 1.0,
        "attention_dims": ("market_timing", "competition_landscape", "pattern_match"),
    },
    "contrarian": {
        "lens": "failure modes, hidden fragility, and adverse scenario pressure-testing",
        "influence": 0.95,
        "adaptability": 1.1,
        "attention_dims": ("regulatory_news_environment", "competition_landscape", "pattern_match"),
    },
    "wildcard": {
        "lens": "non-consensus reaction, narrative resonance, and overlooked edge cases",
        "influence": 0.75,
        "adaptability": 1.15,
        "attention_dims": ("social_proof_demand", "market_timing", "pattern_match"),
    },
    "synthetic": {
        "lens": "general market reaction and directional scenario sensitivity",
        "influence": 0.9,
        "adaptability": 1.0,
        "attention_dims": ("market_timing", "business_model_viability", "competition_landscape"),
    },
}


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
        startup_context = self._resolve_startup_context(exec_summary, extraction=extraction)
        research_data = self._parse_research_context(research_context)
        startup_brief = self._build_startup_brief(exec_summary, startup_context, research_data)

        if swarm_agents and len(swarm_agents) >= 12:
            agents = self._select_panelists_from_swarm(swarm_agents)
            panel_source = "swarm"
            logger.info(f"[OASIS] Selected {len(agents)} panelists from {len(swarm_agents)}-agent swarm")
        else:
            agents = self._create_panel(stage=stage, startup_context=startup_context)
            panel_source = "synthetic"
            if swarm_agents is not None:
                logger.info(f"[OASIS] Swarm too small ({len(swarm_agents) if swarm_agents else 0} agents), "
                           f"falling back to hardcoded panel")
        agents = self._attach_oasis_profiles(agents, startup_context, research_data)
        agent_lookup = {int(agent["id"]): agent for agent in agents}
        logger.info(
            f"[OASIS] Context company='{startup_context['company']}', "
            f"industry='{startup_context['industry']}', "
            f"product='{startup_context['product'][:60]}'"
        )

        timeline = []
        previous_events: List[Dict[str, Any]] = []
        previous_panel_summary = ""  # Fed into next round's agent prompts

        # Track each agent's running sentiment score (1-10 scale).
        # When sourced from swarm, seed with the agent's swarm overall score;
        # otherwise start at neutral 5.0.
        agent_scores = {}
        agent_histories: Dict[int, Dict[str, Any]] = {}
        for a in agents:
            if a.get('swarm_score') is not None:
                agent_scores[a['id']] = float(a['swarm_score'])
            else:
                agent_scores[a['id']] = 5.0
            agent_histories[a['id']] = {
                "agent_id": a['id'],
                "role": a.get("role", f"Agent {a['id']}"),
                "zone": a.get("zone", "synthetic"),
                "swarm_agent_id": a.get("swarm_agent_id"),
                "starting_score": round(agent_scores[a['id']], 2),
                "final_score": round(agent_scores[a['id']], 2),
                "total_delta": 0.0,
                "rounds": [],
                "profile": a.get("profile", {}),
            }

        if agent_scores:
            baseline_scores = list(agent_scores.values())
            baseline_weights = [
                float((agent_lookup.get(agent_id, {}).get("profile", {}) or {}).get("influence", 1.0) or 1.0)
                for agent_id in agent_scores.keys()
            ]
            baseline_avg_score = self._weighted_mean(baseline_scores, baseline_weights)
            baseline_sentiment = round((baseline_avg_score - 1) / 9 * 100)
            baseline_sentiment = max(0, min(100, baseline_sentiment))
        else:
            baseline_sentiment = 50

        previous_sentiment = baseline_sentiment

        for round_num in range(1, SIMULATION_ROUNDS + 1):
            month = round_num
            logger.info(f"[OASIS] Round {round_num}/{SIMULATION_ROUNDS} (Month {month})")

            # Source real market event for this month
            event_record = self._source_real_event(
                startup_brief, month, previous_events, previous_sentiment,
                startup_context=startup_context,
            )
            event_record["month"] = month
            previous_events.append(event_record)

            # Each agent evaluates with accumulated context + their own prior score
            round_context = self._build_round_context(
                council_verdict=council_verdict,
                month=month,
                latest_event=event_record,
                previous_events=previous_events[:-1],
                research_data=research_data,
                previous_panel_summary=previous_panel_summary,
            )
            for agent in agents:
                agent["memory_prompt"] = self._build_agent_memory_prompt(agent_histories.get(agent["id"], {}))

            scores_snapshot = dict(agent_scores)  # Immutable copy for this round
            votes = sorted(
                self._run_round(agents, startup_brief, round_context, scores_snapshot),
                key=lambda vote: vote.get("agent_id", 0),
            )

            # Update agent scores with adjustments (clamped 1-10)
            for v in votes:
                aid = v['agent_id']
                old_score = agent_scores[aid]
                profile = (agent_lookup.get(aid, {}).get("profile", {}) or {})
                adaptability = float(profile.get("adaptability", 1.0) or 1.0)
                influence = float(profile.get("influence", 1.0) or 1.0)
                effective_adjustment = round(float(v.get("adjustment", 0.0) or 0.0) * adaptability, 2)
                new_score = max(1.0, min(10.0, old_score + effective_adjustment))
                agent_scores[aid] = new_score
                v["score_before"] = round(old_score, 2)
                v["score_after"] = round(new_score, 2)
                v["zone"] = agent_histories.get(aid, {}).get("zone", "synthetic")
                v["raw_adjustment"] = round(float(v.get("adjustment", 0.0) or 0.0), 2)
                v["effective_adjustment"] = effective_adjustment
                v["influence"] = influence
                v["adaptability"] = adaptability

                history = agent_histories[aid]
                history["final_score"] = round(new_score, 2)
                history["total_delta"] = round(new_score - history["starting_score"], 2)
                history["rounds"].append({
                    "month": month,
                    "adjustment": round(float(v.get("adjustment", 0.0)), 2),
                    "raw_adjustment": round(float(v.get("raw_adjustment", 0.0) or 0.0), 2),
                    "effective_adjustment": effective_adjustment,
                    "influence": influence,
                    "adaptability": adaptability,
                    "score_before": round(old_score, 2),
                    "score_after": round(new_score, 2),
                    "reasoning": str(v.get("reasoning", "") or "").strip(),
                    "event": event_record.get("event", _NO_EVENT),
                    "event_kind": event_record.get("event_kind", "none"),
                    "event_source_title": event_record.get("source_title", ""),
                    "event_source_url": event_record.get("source_url", ""),
                })

            # Sentiment = average of all agent scores, mapped to 0-100%
            scores_list = list(agent_scores.values())
            score_weights = [
                float((agent_lookup.get(agent_id, {}).get("profile", {}) or {}).get("influence", 1.0) or 1.0)
                for agent_id in agent_scores.keys()
            ]
            avg_score = self._weighted_mean(scores_list, score_weights)
            sentiment_pct = round((avg_score - 1) / 9 * 100)  # 1->0%, 5.5->50%, 10->100%
            sentiment_pct = max(0, min(100, sentiment_pct))

            # Uncertainty quantification based on agent score variance
            std_dev = self._weighted_pstdev(scores_list, score_weights) if len(scores_list) > 1 else 0.0
            confidence_low = max(0, sentiment_pct - std_dev * 15)
            confidence_high = min(100, sentiment_pct + std_dev * 15)

            round_result = {
                "month": month,
                "event": event_record.get("event", _NO_EVENT),
                "event_kind": event_record.get("event_kind", "none"),
                "event_source_title": event_record.get("source_title", ""),
                "event_source_url": event_record.get("source_url", ""),
                "event_source_query": event_record.get("source_query", ""),
                "sentiment_pct": sentiment_pct,
                "confidence_low": round(confidence_low, 1),
                "confidence_high": round(confidence_high, 1),
                "std_dev": round(std_dev, 4),
                "sentiment_change": sentiment_pct - previous_sentiment,
                "avg_adjustment": round(statistics.mean(v.get("effective_adjustment", v.get("adjustment", 0.0)) for v in votes), 3) if votes else 0.0,
                "key_quote": self._select_key_quote(votes),
                "votes": len(votes),
                "round_votes": [
                    {
                        "agent_id": vote.get("agent_id"),
                        "role": vote.get("role", ""),
                        "zone": vote.get("zone", "synthetic"),
                        "adjustment": round(float(vote.get("adjustment", 0.0)), 2),
                        "raw_adjustment": round(float(vote.get("raw_adjustment", vote.get("adjustment", 0.0))), 2),
                        "effective_adjustment": round(float(vote.get("effective_adjustment", vote.get("adjustment", 0.0))), 2),
                        "influence": vote.get("influence", 1.0),
                        "adaptability": vote.get("adaptability", 1.0),
                        "score_before": vote.get("score_before"),
                        "score_after": vote.get("score_after"),
                        "reasoning": str(vote.get("reasoning", "") or "").strip(),
                    }
                    for vote in votes
                ],
            }
            timeline.append(round_result)
            previous_sentiment = sentiment_pct
            previous_panel_summary = self._build_panel_summary(votes, sentiment_pct)

            if on_round_complete:
                on_round_complete(round_result)

        # Compute trajectory relative to the pre-simulation baseline, not just month 1.
        start = baseline_sentiment
        end = timeline[-1]['sentiment_pct'] if timeline else 50
        delta = end - start
        decline_streak = self._max_consecutive_direction(timeline, direction="down")
        improve_streak = self._max_consecutive_direction(timeline, direction="up")
        if delta >= 8 or improve_streak >= 3:
            trajectory = "improving"
        elif delta <= -8 or decline_streak >= 3:
            trajectory = "declining"
        else:
            trajectory = "stable"

        # Compute overall uncertainty summary across all rounds
        uncertainty_band = {}
        if timeline:
            uncertainty_band = {
                "low": min(r["confidence_low"] for r in timeline),
                "high": max(r["confidence_high"] for r in timeline),
                "avg_std": round(statistics.mean(r["std_dev"] for r in timeline), 4),
            }

        panelists = self._build_panelists(agent_histories)
        debriefs = self._build_debriefs(panelists)

        return {
            "mode": SIMULATION_MODE,
            "timeline": timeline,
            "trajectory": trajectory,
            "start_sentiment": start,
            "month_1_sentiment": timeline[0]['sentiment_pct'] if timeline else start,
            "final_sentiment": end,
            "end_sentiment": end,
            "uncertainty_band": uncertainty_band,
            "rounds": len(timeline),
            "total_rounds": len(timeline),
            "agent_count": len(agents),
            "panel_source": panel_source,
            "material_event_count": sum(1 for item in timeline if item.get("event") != _NO_EVENT),
            "decline_streak": decline_streak,
            "improve_streak": improve_streak,
            "panelists": panelists,
            "debriefs": debriefs,
        }

    def _create_panel(self, stage: str = "", startup_context: Optional[Dict[str, str]] = None) -> List[Dict]:
        """Create a diverse panel of 12 agents for multi-round simulation,
        calibrated for the startup's stage."""
        s = (stage or "").lower().strip()
        startup_context = startup_context if isinstance(startup_context, dict) else {}
        industry = startup_context.get("industry", "").strip() or "this sector"
        target_market = startup_context.get("target_market", "").strip() or "the target market"
        product = startup_context.get("product", "").strip() or "the product"
        end_user = startup_context.get("end_user", "").strip() or "the end user"

        if s in ("idea", "pre-seed", "pre seed", "preseed", "seed", "mvp"):
            roles = [
                "Pre-seed/seed VC evaluating early-stage deals",
                f"Potential early adopter in {target_market}",
                f"Industry analyst covering emerging startups in {industry}",
                f"Competitor product manager watching the {product} category",
                f"Regulatory expert covering {industry}",
                f"Serial entrepreneur who bootstrapped similar {product} products",
                f"Target end-user ({end_user}) who would pilot this product",
                "Angel investor evaluating founder-market fit",
                f"Tech journalist covering {industry} startup launches",
                f"Domain expert with 20 years in {industry}",
                "Accelerator partner evaluating cohort candidates",
                "Impact investor evaluating early-stage social/environmental return",
            ]
        elif s in ("series a", "series-a", "revenue"):
            roles = [
                "Series A VC evaluating product-market fit",
                f"Potential enterprise customer in {target_market}",
                f"Industry analyst covering {industry}",
                f"Competitor product manager watching the {product} category",
                f"Regulatory expert covering {industry}",
                f"Serial entrepreneur who scaled similar {product} products to $5M ARR",
                f"Target end-user ({end_user}) who would use this product",
                "Growth investor evaluating Series A to B trajectory",
                f"Tech journalist covering the {industry} market",
                f"Domain expert with 20 years in {industry}",
                "Skeptical seed-stage VC questioning if Series A metrics are met",
                "Impact investor evaluating social/environmental return",
            ]
        elif s in ("series b", "series-b"):
            roles = [
                "Series B VC evaluating scaling efficiency",
                f"Enterprise customer in {target_market} evaluating long-term vendor commitment",
                f"Industry analyst covering growth-stage companies in {industry}",
                f"Competitor VP Product watching the {product} category",
                f"Regulatory expert covering {industry}",
                "Operating partner at a growth fund focused on unit economics",
                f"Power user ({end_user}) dependent on this product for daily operations",
                "Late-stage investor evaluating Series B to C trajectory",
                f"Business journalist covering the {industry} competitive landscape",
                f"Domain expert with 20 years in {industry}",
                "Skeptical PE partner focused on margin sustainability",
                "Impact investor evaluating governance and team scalability",
            ]
        elif s in ("series c", "series c+", "growth", "pre-ipo", "late stage", "series-c", "scaling"):
            roles = [
                "Late-stage growth equity investor",
                f"Enterprise customer in {target_market} evaluating vendor stability",
                f"Industry analyst covering market leaders in {industry}",
                f"Competitor VP Strategy watching the {product} category",
                f"Regulatory expert covering {industry}",
                "Public markets analyst evaluating IPO readiness",
                f"Large enterprise end-user ({end_user}) dependent on this product",
                "Crossover hedge fund evaluating pre-IPO opportunities",
                f"Business journalist covering the {industry} competitive landscape",
                f"Domain expert with 20 years in {industry}",
                "Skeptical PE partner focused on unit economics at scale",
                "ESG analyst evaluating governance and sustainability",
            ]
        else:
            # Default: early stage (safest default, avoids penalizing young startups)
            roles = [
                "Pre-seed/seed VC evaluating early-stage deals",
                f"Potential early adopter in {target_market}",
                f"Industry analyst covering emerging startups in {industry}",
                f"Competitor product manager watching the {product} category",
                f"Regulatory expert covering {industry}",
                f"Serial entrepreneur who bootstrapped similar {product} products",
                f"Target end-user ({end_user}) who would pilot this product",
                "Angel investor evaluating founder-market fit",
                f"Tech journalist covering {industry} startup launches",
                f"Domain expert with 20 years in {industry}",
                "Accelerator partner evaluating cohort candidates",
                "Impact investor evaluating early-stage social/environmental return",
            ]

        return [{"id": i, "role": role, "zone": self._infer_synthetic_zone(role)} for i, role in enumerate(roles)]

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
                "scores": getattr(agent, 'scores', {}) if isinstance(getattr(agent, 'scores', {}), dict) else {},
                "reasoning": getattr(agent, 'reasoning', ''),
                "confidence": getattr(agent, 'confidence', 0.0),
            })

        return panel

    def _infer_synthetic_zone(self, role: str) -> str:
        role_l = (role or "").lower()
        if any(token in role_l for token in ("competitor", "regulatory", "attorney", "privacy", "risk", "short seller", "compliance", "policy", "cyber", "platform", "forensic")):
            return "contrarian"
        if any(token in role_l for token in ("vc", "investor", "fund", "angel", "equity", "accelerator", "acquirer", "corp dev")):
            return "investor"
        if any(token in role_l for token in ("customer", "buyer", "procurement", "ciso", "budget holder", "end-user", "end user", "power user", "pilot this product")):
            return "customer"
        if any(token in role_l for token in ("founder", "entrepreneur", "cto", "cmo", "cfo", "coo", "chief", "vp ", "vp-", "operations", "product manager", "sales", "engineering", "partnerships")):
            return "operator"
        if any(token in role_l for token in ("analyst", "journalist", "reporter", "professor", "researcher", "economist", "futurist", "expert")):
            return "analyst"
        return "wildcard"

    def _top_dimension_names(
        self,
        scores: Dict[str, Any],
        *,
        reverse: bool,
        limit: int = 2,
    ) -> List[str]:
        numeric = []
        for key, value in (scores or {}).items():
            if key == "overall":
                continue
            if isinstance(value, (int, float)):
                numeric.append((key, float(value)))
        numeric.sort(key=lambda item: item[1], reverse=reverse)
        return [
            _SCORE_DIMENSION_LABELS.get(key, key.replace("_", " "))
            for key, _ in numeric[:limit]
        ]

    def _add_watchpoint(self, watchpoints: List[str], candidate: str, *, limit: int = 4) -> None:
        text = str(candidate or "").strip()
        if not text:
            return
        if any(text.lower() == existing.lower() for existing in watchpoints):
            return
        if len(watchpoints) < limit:
            watchpoints.append(text)

    def _collect_zone_watchpoints(
        self,
        zone: str,
        startup_context: Dict[str, str],
        research_data: Dict[str, Any],
        scores: Dict[str, Any],
    ) -> List[str]:
        watchpoints: List[str] = []
        for label in self._top_dimension_names(scores, reverse=False, limit=2):
            self._add_watchpoint(watchpoints, f"Weakest prior score signal: {label}")

        risks = research_data.get("risks", [])
        if isinstance(risks, list):
            for item in risks[:2]:
                self._add_watchpoint(watchpoints, str(item))

        if zone == "contrarian":
            regulatory = research_data.get("regulatory", [])
            if isinstance(regulatory, list):
                for item in regulatory[:2]:
                    self._add_watchpoint(watchpoints, str(item))
            patents = research_data.get("patents", {})
            if isinstance(patents, dict):
                fto = str(patents.get("freedom_to_operate", "") or "").strip()
                if fto and fto.lower() != "not found":
                    self._add_watchpoint(watchpoints, f"IP/FTO: {fto}")
        elif zone in {"investor", "analyst"}:
            market_data = research_data.get("market_data", {})
            if isinstance(market_data, dict):
                growth = str(market_data.get("growth_rate", "") or "").strip()
                source = str(market_data.get("source", "") or "").strip()
                if growth:
                    suffix = f" [{source}]" if source else ""
                    self._add_watchpoint(watchpoints, f"Market growth context: {growth}{suffix}")
            pricing = research_data.get("pricing_analysis", {})
            if isinstance(pricing, dict):
                assessment = str(pricing.get("assessment", "") or "").strip()
                if assessment:
                    self._add_watchpoint(watchpoints, f"Pricing position: {assessment}")
        elif zone == "customer":
            trigger = startup_context.get("switching_trigger", "").strip()
            substitute = startup_context.get("current_substitute", "").strip()
            if trigger:
                self._add_watchpoint(watchpoints, f"Buyer switching trigger: {trigger}")
            if substitute:
                self._add_watchpoint(watchpoints, f"Current substitute: {substitute}")
            customer_evidence = research_data.get("customer_evidence", [])
            if isinstance(customer_evidence, list):
                for item in customer_evidence[:1]:
                    self._add_watchpoint(watchpoints, str(item))
        elif zone == "operator":
            traction = str((research_data.get("company_profile", {}) or {}).get("traction", "") or "").strip()
            if traction:
                self._add_watchpoint(watchpoints, f"Traction signal: {traction}")
            trends = research_data.get("trends", [])
            if isinstance(trends, list):
                for item in trends[:1]:
                    self._add_watchpoint(watchpoints, str(item))
        else:
            trends = research_data.get("trends", [])
            if isinstance(trends, list):
                for item in trends[:2]:
                    self._add_watchpoint(watchpoints, str(item))

        company = startup_context.get("company", "the company")
        if not watchpoints:
            self._add_watchpoint(watchpoints, f"Keep reassessing whether {company} can defend its position as new market signals arrive.")
        return watchpoints

    def _baseline_stance(self, score: Optional[float]) -> str:
        if score is None:
            return "neutral"
        score_f = float(score)
        if score_f >= 7.5:
            return "strongly bullish"
        if score_f >= 6.0:
            return "cautiously bullish"
        if score_f <= 3.5:
            return "strongly bearish"
        if score_f <= 5.0:
            return "cautiously bearish"
        return "mixed"

    def _build_initial_thesis(
        self,
        agent: Dict[str, Any],
        startup_context: Dict[str, str],
    ) -> str:
        reasoning = str(agent.get("reasoning", "") or "").strip()
        if reasoning:
            sentence = reasoning.split(".")[0].strip()
            if sentence:
                return sentence[:220]
        company = startup_context.get("company", "the startup")
        product = startup_context.get("product", "the product").strip() or "the product"
        target_market = startup_context.get("target_market", "the target market").strip() or "the target market"
        zone = str(agent.get("zone", "synthetic") or "synthetic")
        if zone == "investor":
            return f"Started by testing whether {company} can compound into a venture-scale outcome with disciplined capital use."
        if zone == "customer":
            return f"Started by asking whether {target_market} would actually switch to {product}."
        if zone == "operator":
            return f"Started by pressure-testing whether the team can execute {product} reliably in the real world."
        if zone == "analyst":
            return f"Started by mapping whether {company} has a durable place in the {startup_context.get('industry', 'market')} landscape."
        if zone == "contrarian":
            return f"Started by hunting for the failure mode that could break {company}'s thesis."
        return f"Started with a general market read on how {company} might be received."

    def _build_oasis_profile(
        self,
        agent: Dict[str, Any],
        startup_context: Dict[str, str],
        research_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        zone = str(agent.get("zone", "synthetic") or "synthetic")
        defaults = _ZONE_PROFILE_DEFAULTS.get(zone, _ZONE_PROFILE_DEFAULTS["synthetic"])
        swarm_score = agent.get("swarm_score")
        confidence = float(agent.get("confidence", 0.0) or 0.0)
        scores = agent.get("scores", {}) if isinstance(agent.get("scores", {}), dict) else {}
        strengths = self._top_dimension_names(scores, reverse=True, limit=2)
        weaknesses = self._top_dimension_names(scores, reverse=False, limit=2)
        stance = self._baseline_stance(float(swarm_score)) if swarm_score is not None else "neutral"
        extremeness = min(1.0, abs((float(swarm_score or 5.0) - 5.5) / 4.5))
        influence = defaults["influence"] + (0.08 * extremeness) + (0.05 * confidence)
        adaptability = defaults["adaptability"] + (0.18 * (1.0 - extremeness))
        influence = round(max(0.7, min(1.35, influence)), 2)
        adaptability = round(max(0.75, min(1.25, adaptability)), 2)
        watchpoints = self._collect_zone_watchpoints(zone, startup_context, research_data, scores)
        initial_thesis = self._build_initial_thesis(agent, startup_context)
        return {
            "lens": defaults["lens"],
            "baseline_stance": stance,
            "influence": influence,
            "adaptability": adaptability,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "watchpoints": watchpoints,
            "attention_dims": [
                _SCORE_DIMENSION_LABELS.get(key, key.replace("_", " "))
                for key in defaults["attention_dims"]
            ],
            "initial_thesis": initial_thesis,
        }

    def _attach_oasis_profiles(
        self,
        agents: List[Dict[str, Any]],
        startup_context: Dict[str, str],
        research_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        profiled: List[Dict[str, Any]] = []
        for agent in agents:
            enriched = dict(agent)
            enriched["zone"] = str(enriched.get("zone", "") or self._infer_synthetic_zone(enriched.get("role", "")))
            enriched["profile"] = self._build_oasis_profile(enriched, startup_context, research_data)
            profiled.append(enriched)
        return profiled

    def _profile_summary(self, profile: Dict[str, Any]) -> str:
        if not isinstance(profile, dict):
            return ""
        bits = [
            f"stance: {profile.get('baseline_stance', 'neutral')}",
            f"influence: {profile.get('influence', 1.0)}x",
            f"adaptability: {profile.get('adaptability', 1.0)}x",
        ]
        strengths = profile.get("strengths", [])
        if isinstance(strengths, list) and strengths:
            bits.append("strengths: " + ", ".join(str(strength) for strength in strengths))
        return " | ".join(bits)

    def _build_agent_memory_prompt(self, history: Dict[str, Any]) -> str:
        rounds = history.get("rounds", []) if isinstance(history, dict) else []
        if not rounds:
            return "YOUR MEMORY:\n- This is the first simulated month. Start from your opening thesis and watchpoints."

        recent = rounds[-2:]
        lines = ["YOUR MEMORY:"]
        for item in recent:
            lines.append(
                f"- Month {item.get('month', '?')}: "
                f"{item.get('event', _NO_EVENT)} -> {item.get('score_before', '?')} to {item.get('score_after', '?')} "
                f"(effective {item.get('effective_adjustment', 0)})."
            )
        strongest = max(rounds, key=lambda item: abs(float(item.get("effective_adjustment", 0.0) or 0.0)))
        lines.append(
            f"- Biggest turning point so far: month {strongest.get('month', '?')} "
            f"when {strongest.get('event', _NO_EVENT)} drove {strongest.get('effective_adjustment', 0)}."
        )
        return "\n".join(lines)

    def _build_memory_snapshot(self, rounds: List[Dict[str, Any]]) -> List[str]:
        if not rounds:
            return []
        recent = rounds[-2:]
        snapshot = []
        for item in recent:
            snapshot.append(
                f"Month {item.get('month', '?')}: {item.get('score_before', '?')} -> {item.get('score_after', '?')} "
                f"on {item.get('event_kind', 'none')} event"
            )
        return snapshot

    def _weighted_mean(self, values: List[float], weights: List[float]) -> float:
        if not values:
            return 5.0
        weight_total = sum(weights) or float(len(values))
        return sum(v * w for v, w in zip(values, weights)) / weight_total

    def _weighted_pstdev(self, values: List[float], weights: List[float]) -> float:
        if len(values) < 2:
            return 0.0
        mean = self._weighted_mean(values, weights)
        weight_total = sum(weights) or float(len(values))
        variance = sum(w * ((v - mean) ** 2) for v, w in zip(values, weights)) / weight_total
        return variance ** 0.5

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
        end_user = str(extraction.get("end_user", "") or "").strip()
        economic_buyer = str(extraction.get("economic_buyer", "") or "").strip()
        switching_trigger = str(extraction.get("switching_trigger", "") or "").strip()
        current_substitute = str(extraction.get("current_substitute", "") or "").strip()

        if company and industry:
            return {
                "company": company,
                "industry": industry,
                "product": product,
                "target_market": target_market,
                "business_model": business_model,
                "end_user": end_user,
                "economic_buyer": economic_buyer,
                "switching_trigger": switching_trigger,
                "current_substitute": current_substitute,
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
            "end_user": end_user,
            "economic_buyer": economic_buyer,
            "switching_trigger": switching_trigger,
            "current_substitute": current_substitute,
        }

    def _parse_research_context(self, research_context: Any) -> Dict[str, Any]:
        if isinstance(research_context, dict):
            return research_context
        if not research_context:
            return {}
        if isinstance(research_context, str):
            try:
                parsed = json.loads(research_context)
                return parsed if isinstance(parsed, dict) else {"summary": research_context}
            except Exception:
                return {"summary": research_context}
        return {}

    def _build_startup_brief(
        self,
        exec_summary: str,
        startup_context: Dict[str, str],
        research_data: Dict[str, Any],
    ) -> str:
        company = startup_context.get("company", "startup")
        lines = [
            "STARTUP PROFILE:",
            f"- Company: {company}",
            f"- Industry: {startup_context.get('industry', 'Not specified') or 'Not specified'}",
            f"- Product: {startup_context.get('product', 'Not specified') or 'Not specified'}",
            f"- Target market: {startup_context.get('target_market', 'Not specified') or 'Not specified'}",
            f"- Business model: {startup_context.get('business_model', 'Not specified') or 'Not specified'}",
            f"- End user: {startup_context.get('end_user', 'Not specified') or 'Not specified'}",
            f"- Economic buyer: {startup_context.get('economic_buyer', 'Not specified') or 'Not specified'}",
            f"- Switching trigger: {startup_context.get('switching_trigger', 'Not specified') or 'Not specified'}",
            f"- Current substitute: {startup_context.get('current_substitute', 'Not specified') or 'Not specified'}",
        ]

        if exec_summary:
            lines.extend(["", "FOUNDER NARRATIVE:", str(exec_summary)])

        summary = str(research_data.get("summary", "") or "").strip()
        if summary:
            lines.extend(["", "RESEARCH SUMMARY:", summary])

        company_profile = research_data.get("company_profile", {})
        if isinstance(company_profile, dict) and company_profile:
            lines.extend([
                "",
                "COMPANY FACTS:",
                f"- Description: {company_profile.get('description', 'Not found')}",
                f"- Pricing: {company_profile.get('pricing', 'Not found')}",
                f"- Traction: {company_profile.get('traction', 'Not found')}",
                f"- HQ: {company_profile.get('hq_location', 'Not found')}",
                f"- Employees: {company_profile.get('employee_count', 'Not found')}",
            ])

        market_data = research_data.get("market_data", {})
        if isinstance(market_data, dict) and market_data:
            lines.extend([
                "",
                "MARKET DATA:",
                f"- TAM: {market_data.get('tam', 'Not found')}",
                f"- SAM: {market_data.get('sam', 'Not found')}",
                f"- Growth: {market_data.get('growth_rate', 'Not found')}",
                f"- Source: {market_data.get('source', 'Not found')}",
            ])

        competitors = research_data.get("competitors", [])
        if isinstance(competitors, list) and competitors:
            lines.extend([
                "",
                "COMPETITORS:",
                *(f"- {str(name)}" for name in competitors[:8]),
            ])

        pricing_analysis = research_data.get("pricing_analysis", {})
        if isinstance(pricing_analysis, dict) and pricing_analysis:
            lines.extend([
                "",
                "PRICING ANALYSIS:",
                f"- Startup pricing: {pricing_analysis.get('startup_pricing', 'Not found')}",
                f"- Competitor pricing: {pricing_analysis.get('competitor_pricing', 'Not found')}",
                f"- Assessment: {pricing_analysis.get('assessment', 'Not found')}",
            ])

        patents = research_data.get("patents", {})
        if isinstance(patents, dict) and patents:
            lines.extend([
                "",
                "PATENTS:",
                f"- Total families: {patents.get('total_families', 0)}",
                f"- Active: {patents.get('active', 0)}",
                f"- Pending: {patents.get('pending', 0)}",
                f"- Freedom to operate: {patents.get('freedom_to_operate', 'Not found')}",
            ])

        regulatory = research_data.get("regulatory", [])
        if isinstance(regulatory, list) and regulatory:
            lines.extend(["", "REGULATORY:"] + [f"- {str(item)}" for item in regulatory[:5]])

        customer_evidence = research_data.get("customer_evidence", [])
        if isinstance(customer_evidence, list) and customer_evidence:
            lines.extend(["", "CUSTOMER EVIDENCE:"] + [f"- {str(item)}" for item in customer_evidence[:5]])

        risks = research_data.get("risks", [])
        if isinstance(risks, list) and risks:
            lines.extend(["", "KNOWN RISKS:"] + [f"- {str(item)}" for item in risks[:5]])

        return "\n".join(lines)

    def _headline_queries(self, startup_context: Dict[str, str]) -> List[str]:
        """Build multiple grounded search queries instead of a single company/industry string."""
        company = startup_context.get("company", "").strip()
        industry = startup_context.get("industry", "").strip()
        product = startup_context.get("product", "").strip()
        target_market = startup_context.get("target_market", "").strip()
        business_model = startup_context.get("business_model", "").strip()
        end_user = startup_context.get("end_user", "").strip()
        economic_buyer = startup_context.get("economic_buyer", "").strip()
        switching_trigger = startup_context.get("switching_trigger", "").strip()
        current_substitute = startup_context.get("current_substitute", "").strip()

        queries = []
        if company and company.lower() != "startup":
            queries.append(f"\"{company}\" news")
            if product:
                queries.append(f"\"{company}\" {product} news")
            if target_market:
                queries.append(f"\"{company}\" {target_market} customer partnership news")
            if end_user:
                queries.append(f"\"{company}\" {end_user} deployment news")
        if industry and target_market:
            queries.append(f"{industry} {target_market} market news")
        if industry and economic_buyer:
            queries.append(f"{industry} {economic_buyer} budget spending news")
        if industry and switching_trigger:
            queries.append(f"{industry} {switching_trigger} news")
        if industry and current_substitute:
            queries.append(f"{industry} replacing {current_substitute} software trend")
        if product and business_model:
            queries.append(f"{product} {business_model} adoption news")
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
        return deduped[:8]

    # ── real headline sourcing ────────────────────────────────────

    def _fetch_real_headlines(
        self,
        startup_context: Dict[str, str],
        *,
        month: int,
        previous_events: Optional[List[Dict[str, Any]]] = None,
        max_headlines: int = HEADLINES_PER_ROUND,
    ) -> List[Dict[str, str]]:
        """Fetch real news headlines via live web search.

        Returns a list of headline dicts (may be empty if search unavailable).
        """
        freshness = _FRESHNESS_BY_MONTH.get(month, "past 365 days")
        cache_key = (
            startup_context.get("company", "").strip().lower(),
            startup_context.get("industry", "").strip().lower(),
            startup_context.get("product", "").strip().lower(),
            startup_context.get("target_market", "").strip().lower(),
            startup_context.get("business_model", "").strip().lower(),
            freshness,
            max_headlines,
        )
        cached = self._headline_cache.get(cache_key)
        target_pool = max(max_headlines * 2, 12)
        used_keys = {
            (
                str(item.get("source_title", "") or "").strip().lower(),
                str(item.get("source_url", "") or "").strip().lower(),
            )
            for item in (previous_events or [])
            if isinstance(item, dict)
        }
        if cached is not None:
            return [
                dict(item) for item in cached
                if (
                    str(item.get("title", "") or "").strip().lower(),
                    str(item.get("url", "") or "").strip().lower(),
                ) not in used_keys
            ][:max_headlines]

        try:
            from .gateway_client import web_search
            collected: List[Dict[str, str]] = []
            seen = set()
            for query in self._headline_queries(startup_context):
                results = web_search(query, count=min(5, max_headlines), freshness=freshness)
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
                    if len(collected) >= target_pool:
                        break
                if len(collected) >= target_pool:
                    break
            if collected:
                self._headline_cache[cache_key] = collected[:]
                logger.info(
                    f"[OASIS] Web search returned {len(collected)} headlines across "
                    f"{len(self._headline_queries(startup_context))} queries for month {month}"
                )
                return [
                    dict(item) for item in collected
                    if (
                        str(item.get("title", "") or "").strip().lower(),
                        str(item.get("url", "") or "").strip().lower(),
                    ) not in used_keys
                ][:max_headlines]
        except Exception as e:
            logger.warning(f"[OASIS] Web search for headlines failed (non-fatal): {e}")

        self._headline_cache[cache_key] = []
        return []

    # ── grounded event generation (replaces _generate_event) ─────

    def _source_real_event(
        self,
        startup_brief: str,
        month: int,
        previous_events: List[Dict[str, Any]],
        current_sentiment: int,
        *,
        startup_context: Dict[str, str],
    ) -> Dict[str, Any]:
        """Source a market event grounded in REAL news data.

        Pipeline:
        1. Fetch real headlines via live web search.
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
        headlines = self._fetch_real_headlines(
            startup_context,
            month=month,
            previous_events=previous_events,
            max_headlines=HEADLINES_PER_ROUND,
        )

        # --- No headlines → no fabrication ---
        if not headlines:
            logger.info(
                f"[OASIS] Month {month}: no real headlines found — "
                "returning 'no event' (NOT fabricating)"
            )
            return {
                "event": _NO_EVENT,
                "source_title": "",
                "source_url": "",
                "source_query": "",
                "event_kind": "none",
            }

        # --- LLM summarization grounded in real data ---
        headline_block = "\n".join(
            (
                f"  - TITLE: {item.get('title', '')}\n"
                f"    QUERY: {item.get('query', '')}\n"
                f"    URL: {item.get('url', '')}\n"
                f"    DESCRIPTION: {item.get('description', '')}"
            )
            for item in headlines
        )
        previous_sources = "\n".join(
            f"  - {item.get('source_title', '')} | {item.get('source_url', '')}"
            for item in previous_events
            if isinstance(item, dict) and (item.get("source_title") or item.get("source_url"))
        ) or "  - None yet"
        prompt = (
            f"You are summarizing real market news for a startup simulation.\n\n"
            f"{startup_brief}\n\n"
            f"COMPANY: {company_name}\n"
            f"INDUSTRY: {industry}\n"
            f"PRODUCT: {product or 'Not specified'}\n"
            f"TARGET MARKET: {target_market or 'Not specified'}\n"
            f"BUSINESS MODEL: {business_model or 'Not specified'}\n"
            f"MONTH: {month} of {SIMULATION_ROUNDS}\n"
            f"CURRENT MARKET SENTIMENT: {current_sentiment}%\n"
            f"PREVIOUS EVENTS:\n"
            + "\n".join(
                f"  Month {i+1}: {item.get('event', _NO_EVENT)}"
                for i, item in enumerate(previous_events)
                if isinstance(item, dict)
            )
            + "\n\n"
            f"ALREADY USED HEADLINES (do not reuse these stories):\n{previous_sources}\n\n"
            f"REAL NEWS HEADLINES (sourced just now):\n{headline_block}\n\n"
            f"Given these REAL news headlines about {company_name}/{industry}, "
            f"summarize the single most impactful event for this startup's trajectory. "
            f"If none are directly relevant, return '{_NO_EVENT}'.\n\n"
            f"RULES:\n"
            f"- Must be grounded in the headlines above — do NOT invent facts\n"
            f"- Do not reuse a headline/story already used in previous months\n"
            f"- Choose the headline with the clearest impact on adoption, regulation, competition, funding, pricing, or customer demand\n"
            f"- Return JSON only with keys: event, source_title, source_url, source_query, event_kind\n"
            f"- event_kind must be one of company, customer, competition, funding, regulatory, pricing, macro, market, product, none\n\n"
            f"Event for month {month}:"
        )
        response = self.llm.chat(
            [{"role": "user", "content": prompt}], max_tokens=120,
        )

        payload = self._parse_event_payload(response or "")
        if not payload:
            fallback = headlines[0]
            event = (response or fallback.get("title") or _NO_EVENT).strip()
            payload = {
                "event": event,
                "source_title": fallback.get("title", ""),
                "source_url": fallback.get("url", ""),
                "source_query": fallback.get("query", ""),
                "event_kind": "market" if event != _NO_EVENT else "none",
            }

        event = str(payload.get("event", _NO_EVENT) or _NO_EVENT).strip()
        if event == _NO_EVENT:
            payload["event_kind"] = "none"
            payload["source_title"] = ""
            payload["source_url"] = ""
            payload["source_query"] = ""

        source_tag = "real-data-grounded" if event != _NO_EVENT else "no-event"
        logger.info(f"[OASIS] Month {month} event [{source_tag}]: {event[:160]}")

        return payload

    def _run_round(self, agents: List[Dict], startup_brief: str,
                   context: str, agent_scores: Dict[int, float]) -> List[Dict]:
        """Run all agents for one round, returning incremental adjustments."""
        results = []

        def evaluate_agent(agent):
            prior_score = agent_scores[agent['id']]
            profile = agent.get("profile", {}) if isinstance(agent.get("profile", {}), dict) else {}
            profile_lines = [
                "YOUR PANELIST PROFILE:",
                f"- Zone: {agent.get('zone', 'synthetic')}",
                f"- Lens: {profile.get('lens', 'general market reaction')}",
                f"- Baseline stance: {profile.get('baseline_stance', 'neutral')}",
                f"- Influence weight: {profile.get('influence', 1.0)}x",
                f"- Adaptability: {profile.get('adaptability', 1.0)}x",
                f"- Opening thesis: {profile.get('initial_thesis', 'Not set')}",
            ]
            strengths = profile.get("strengths", [])
            if isinstance(strengths, list) and strengths:
                profile_lines.append(f"- Strongest prior score signals: {', '.join(str(item) for item in strengths)}")
            weaknesses = profile.get("weaknesses", [])
            if isinstance(weaknesses, list) and weaknesses:
                profile_lines.append(f"- Weakest prior score signals: {', '.join(str(item) for item in weaknesses)}")
            watchpoints = profile.get("watchpoints", [])
            if isinstance(watchpoints, list) and watchpoints:
                profile_lines.append(f"- Watchpoints: {' | '.join(str(item) for item in watchpoints)}")
            profile_block = "\n".join(profile_lines)
            memory_block = agent.get("memory_prompt", "YOUR MEMORY:\n- No prior rounds yet.")
            prompt = (
                f"You are: {agent['role']}\n\n"
                f"{startup_brief}\n\n"
                f"{context}\n\n"
                f"{profile_block}\n\n"
                f"{memory_block}\n\n"
                f"Your current confidence in this startup is {prior_score:.1f}/10.\n\n"
                f"Based on this month's event and the full accumulated context, how does your confidence CHANGE?\n\n"
                f"Reply with a number from -3 to +3 (in 0.5 increments) followed by a one-sentence reason.\n"
                f"Examples:\n"
                f"  +1.5 This regulation creates a real adoption tailwind for their specific buyer.\n"
                f"  -1.0 This competitor funding event makes their moat meaningfully weaker.\n"
                f"  0 This event is neutral for their specific positioning.\n"
                f"  +0.5 Positive signal but not enough to materially change outlook.\n\n"
                f"Score hard only when the event materially changes the thesis. Anchor on evidence, not personality.\n\n"
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
                    # Clamp to [-3, +3]
                    adjustment = max(-3.0, min(3.0, adjustment))
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

    def _parse_event_payload(self, raw: str) -> Dict[str, Any]:
        raw = (raw or "").strip()
        if not raw:
            return {}

        start = raw.find("{")
        end = raw.rfind("}")
        payload = raw[start:end + 1] if start >= 0 and end > start else raw
        try:
            parsed = json.loads(payload)
            if isinstance(parsed, dict):
                return {
                    "event": str(parsed.get("event", _NO_EVENT) or _NO_EVENT).strip(),
                    "source_title": str(parsed.get("source_title", "") or "").strip(),
                    "source_url": str(parsed.get("source_url", "") or "").strip(),
                    "source_query": str(parsed.get("source_query", "") or "").strip(),
                    "event_kind": str(parsed.get("event_kind", "none") or "none").strip().lower(),
                }
        except Exception:
            return {}
        return {}

    def _build_round_context(
        self,
        *,
        council_verdict: str,
        month: int,
        latest_event: Dict[str, Any],
        previous_events: List[Dict[str, Any]],
        research_data: Dict[str, Any],
        previous_panel_summary: str,
    ) -> str:
        lines = [
            "OASIS DEEP MARKET SIMULATION CONTEXT:",
            f"- Council verdict baseline: {council_verdict}",
            f"- Current month: {month} of {SIMULATION_ROUNDS}",
            "",
            "CURRENT MONTH EVENT:",
            f"- Event: {latest_event.get('event', _NO_EVENT)}",
            f"- Type: {latest_event.get('event_kind', 'none')}",
            f"- Source title: {latest_event.get('source_title', 'Not available') or 'Not available'}",
            f"- Source URL: {latest_event.get('source_url', 'Not available') or 'Not available'}",
        ]

        if previous_events:
            lines.extend(["", "TIMELINE SO FAR:"])
            for item in previous_events:
                if isinstance(item, dict):
                    lines.append(f"- Month {item.get('month', '?')}: {item.get('event', _NO_EVENT)}")

        summary = str(research_data.get("summary", "") or "").strip()
        if summary:
            lines.extend(["", "RESEARCH SUMMARY:", summary])

        regulatory = research_data.get("regulatory", [])
        if isinstance(regulatory, list) and regulatory:
            lines.extend(["", "REGULATORY FACTS:"] + [f"- {str(item)}" for item in regulatory[:4]])

        patents = research_data.get("patents", {})
        if isinstance(patents, dict) and patents:
            lines.extend([
                "",
                "PATENT FACTS:",
                f"- Total families: {patents.get('total_families', 0)}",
                f"- Active: {patents.get('active', 0)}",
                f"- Pending: {patents.get('pending', 0)}",
                f"- Freedom to operate: {patents.get('freedom_to_operate', 'Not found')}",
            ])

        pricing = research_data.get("pricing_analysis", {})
        if isinstance(pricing, dict) and pricing:
            lines.extend([
                "",
                "PRICING FACTS:",
                f"- Startup pricing: {pricing.get('startup_pricing', 'Not found')}",
                f"- Competitor pricing: {pricing.get('competitor_pricing', 'Not found')}",
                f"- Assessment: {pricing.get('assessment', 'Not found')}",
            ])

        customer_evidence = research_data.get("customer_evidence", [])
        if isinstance(customer_evidence, list) and customer_evidence:
            lines.extend(["", "CUSTOMER SIGNALS:"] + [f"- {str(item)}" for item in customer_evidence[:4]])

        risks = research_data.get("risks", [])
        if isinstance(risks, list) and risks:
            lines.extend(["", "KNOWN RISKS:"] + [f"- {str(item)}" for item in risks[:4]])

        if previous_panel_summary:
            lines.extend(["", previous_panel_summary])

        return "\n".join(lines)

    def _select_key_quote(self, votes: List[Dict[str, Any]]) -> str:
        if not votes:
            return ""
        strongest = max(
            votes,
            key=lambda vote: (abs(float(vote.get("effective_adjustment", vote.get("adjustment", 0.0)))), len(str(vote.get("reasoning", "")))),
        )
        return str(strongest.get("reasoning", "")).strip()[:220]

    def _build_panelists(self, agent_histories: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
        panelists = []
        for history in agent_histories.values():
            rounds = history.get("rounds", [])
            strongest_positive = None
            strongest_negative = None
            if rounds:
                strongest_positive = max(rounds, key=lambda item: float(item.get("adjustment", 0.0)))
                strongest_negative = min(rounds, key=lambda item: float(item.get("adjustment", 0.0)))
            panelists.append({
                "agent_id": history.get("agent_id"),
                "role": history.get("role", ""),
                "zone": history.get("zone", "synthetic"),
                "swarm_agent_id": history.get("swarm_agent_id"),
                "starting_score": round(float(history.get("starting_score", 5.0) or 5.0), 2),
                "final_score": round(float(history.get("final_score", 5.0) or 5.0), 2),
                "total_delta": round(float(history.get("total_delta", 0.0) or 0.0), 2),
                "rounds": rounds,
                "profile": history.get("profile", {}),
                "profile_summary": self._profile_summary(history.get("profile", {})),
                "memory_snapshot": self._build_memory_snapshot(rounds),
                "strongest_positive_month": strongest_positive.get("month") if strongest_positive else None,
                "strongest_negative_month": strongest_negative.get("month") if strongest_negative else None,
            })
        panelists.sort(key=lambda item: (item.get("final_score", 0), item.get("total_delta", 0)), reverse=True)
        return panelists

    def _build_debriefs(self, panelists: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not panelists:
            return []

        selected: List[Tuple[str, Dict[str, Any]]] = []
        selected.append(("Strongest Bull", max(panelists, key=lambda item: float(item.get("final_score", 0.0)))))
        selected.append(("Strongest Bear", min(panelists, key=lambda item: float(item.get("final_score", 0.0)))))
        selected.append(("Most Changed", max(panelists, key=lambda item: abs(float(item.get("total_delta", 0.0))))))

        debriefs: List[Dict[str, Any]] = []
        seen = set()
        for label, panelist in selected:
            agent_id = panelist.get("agent_id")
            if agent_id in seen:
                continue
            seen.add(agent_id)
            rounds = panelist.get("rounds", [])
            turning_points = sorted(
                rounds,
                key=lambda item: abs(float(item.get("adjustment", 0.0))),
                reverse=True,
            )[:2]
            strongest_reason = ""
            if turning_points:
                strongest_reason = str(turning_points[0].get("reasoning", "") or "").strip()

            delta = float(panelist.get("total_delta", 0.0) or 0.0)
            direction = "rose" if delta > 0.25 else "fell" if delta < -0.25 else "stayed near baseline"
            summary = (
                f"Started at {panelist.get('starting_score', 5.0)}/10 and ended at "
                f"{panelist.get('final_score', 5.0)}/10, so conviction {direction}. "
            )
            if turning_points:
                top = turning_points[0]
                summary += (
                    f"The biggest turning point was month {top.get('month', '?')} when "
                    f"{top.get('event', _NO_EVENT)} drove a {top.get('effective_adjustment', top.get('adjustment', 0))} change."
                )
            elif strongest_reason:
                summary += strongest_reason
            else:
                summary += "No single month materially changed this panelist's thesis."

            debriefs.append({
                "label": label,
                "agent_id": agent_id,
                "role": panelist.get("role", ""),
                "zone": panelist.get("zone", "synthetic"),
                "starting_score": panelist.get("starting_score", 5.0),
                "final_score": panelist.get("final_score", 5.0),
                "total_delta": panelist.get("total_delta", 0.0),
                "summary": summary,
                "strongest_reason": strongest_reason,
                "profile_summary": panelist.get("profile_summary", ""),
                "watchpoints": (panelist.get("profile", {}) or {}).get("watchpoints", []),
                "turning_points": [
                    {
                        "month": item.get("month"),
                        "adjustment": item.get("adjustment"),
                        "effective_adjustment": item.get("effective_adjustment", item.get("adjustment")),
                        "event": item.get("event", _NO_EVENT),
                        "event_kind": item.get("event_kind", "none"),
                        "reasoning": item.get("reasoning", ""),
                    }
                    for item in turning_points
                ],
            })

        return debriefs

    def _max_consecutive_direction(self, timeline: List[Dict[str, Any]], *, direction: str) -> int:
        best = 0
        current = 0
        for item in timeline:
            change = float(item.get("sentiment_change", 0) or 0)
            matched = change > 0 if direction == "up" else change < 0
            if matched:
                current += 1
                best = max(best, current)
            else:
                current = 0
        return best

    def _build_panel_summary(self, votes: List[Dict], sentiment_pct: int) -> str:
        """Build a text summary of panel opinions for inter-agent visibility."""
        if not votes:
            return ""

        bullish = [v for v in votes if float(v.get('effective_adjustment', v['adjustment'])) > 0]
        bearish = [v for v in votes if float(v.get('effective_adjustment', v['adjustment'])) < 0]
        neutral = [v for v in votes if float(v.get('effective_adjustment', v['adjustment'])) == 0]

        bullish.sort(key=lambda v: v.get('effective_adjustment', v['adjustment']), reverse=True)
        bearish.sort(key=lambda v: v.get('effective_adjustment', v['adjustment']))

        lines = [
            f"PANEL CONSENSUS FROM LAST ROUND ({len(votes)} analysts):",
            f"  Overall sentiment: {sentiment_pct}%",
            f"  Breakdown: {len(bullish)} bullish, {len(bearish)} bearish, {len(neutral)} neutral",
        ]

        if bullish:
            lines.append("  Strongest bull case:")
            for v in bullish[:2]:
                reason = v['reasoning'][:120].strip()
                lines.append(
                    f"    - {v['role']} ({v.get('effective_adjustment', v['adjustment'])}, "
                    f"influence {v.get('influence', 1.0)}x): {reason}"
                )

        if bearish:
            lines.append("  Strongest bear case:")
            for v in bearish[:2]:
                reason = v['reasoning'][:120].strip()
                lines.append(
                    f"    - {v['role']} ({v.get('effective_adjustment', v['adjustment'])}, "
                    f"influence {v.get('influence', 1.0)}x): {reason}"
                )

        if len(bullish) > len(bearish) * 2 and bearish:
            lines.append("  NOTE: The bearish minority raised concerns worth considering.")
        elif len(bearish) > len(bullish) * 2 and bullish:
            lines.append("  NOTE: The bullish minority identified opportunities worth considering.")

        return "\n".join(lines)
