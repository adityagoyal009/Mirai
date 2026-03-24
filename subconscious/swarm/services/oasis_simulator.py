"""
OASIS Market Simulator — multi-round simulation of market reaction over 6 months.

Unlike the swarm (independent one-shot votes), OASIS runs interactive rounds where:
- Agents see previous round outcomes and remember their own prior stance
- Market events are injected between rounds
- Opinions evolve incrementally based on new information
- Final output: sentiment trajectory over time
"""

from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from ..config import Config

logger = get_logger('mirofish.oasis')

SIMULATION_ROUNDS = 6  # 6 months
AGENTS_PER_ROUND = 12  # Small focused group


class OasisSimulator:
    """Runs multi-round market reaction simulation."""

    def __init__(self):
        self.llm = LLMClient()

    def simulate(self, exec_summary: str, research_context: str,
                 council_verdict: str, on_round_complete=None) -> Dict[str, Any]:
        """
        Simulate market reaction over 6 months.

        Returns timeline of sentiment + key events per month.
        """
        agents = self._create_panel()

        timeline = []
        previous_events = []
        previous_sentiment = 50  # Start neutral
        previous_panel_summary = ""  # Fed into next round's agent prompts

        # Track each agent's running sentiment score (1-10 scale, start at 5)
        agent_scores = {a['id']: 5.0 for a in agents}

        for round_num in range(1, SIMULATION_ROUNDS + 1):
            month = round_num
            logger.info(f"[OASIS] Round {round_num}/6 (Month {month})")

            # Generate market event for this month
            event = self._generate_event(
                exec_summary, month, previous_events, previous_sentiment
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

            votes = self._run_round(agents, exec_summary, round_context, agent_scores)

            # Update agent scores with adjustments (clamped 1-10)
            for v in votes:
                aid = v['agent_id']
                old_score = agent_scores[aid]
                new_score = max(1.0, min(10.0, old_score + v['adjustment']))
                agent_scores[aid] = new_score

            # Sentiment = average of all agent scores, mapped to 0-100%
            avg_score = sum(agent_scores.values()) / len(agent_scores)
            sentiment_pct = round((avg_score - 1) / 9 * 100)  # 1->0%, 5.5->50%, 10->100%
            sentiment_pct = max(0, min(100, sentiment_pct))

            round_result = {
                "month": month,
                "event": event,
                "sentiment_pct": sentiment_pct,
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

        return {
            "timeline": timeline,
            "trajectory": trajectory,
            "start_sentiment": start,
            "end_sentiment": end,
            "total_rounds": len(timeline),
        }

    def _create_panel(self) -> List[Dict]:
        """Create a diverse panel of 12 agents for multi-round simulation."""
        roles = [
            "Seed VC evaluating this deal",
            "Potential enterprise customer in the target market",
            "Industry analyst covering this sector",
            "Competitor product manager watching this space",
            "Regulatory expert in this industry",
            "Serial entrepreneur who built similar products",
            "Target end-user who would use this product",
            "Growth investor looking at Series A candidates",
            "Tech journalist covering this market",
            "Domain expert with 20 years in this field",
            "Skeptical PE partner focused on unit economics",
            "Impact investor evaluating social/environmental return",
        ]
        return [{"id": i, "role": role} for i, role in enumerate(roles)]

    def _generate_event(self, exec_summary: str, month: int,
                        previous_events: List[str], current_sentiment: int) -> str:
        """LLM generates a realistic market event for this month."""
        prompt = (
            f"You are simulating market dynamics for a startup.\n\n"
            f"STARTUP: {exec_summary[:300]}\n\n"
            f"MONTH: {month} of 6\n"
            f"CURRENT MARKET SENTIMENT: {current_sentiment}%\n"
            f"PREVIOUS EVENTS:\n"
            + "\n".join(f"  Month {i+1}: {e}" for i, e in enumerate(previous_events))
            + "\n\n"
            f"Generate ONE realistic market event for month {month} that would affect this startup. "
            f"Examples: competitor raises funding, new regulation passed, key hire joins, pilot customer churns, "
            f"market report published, partnership announced.\n\n"
            f"RULES:\n"
            f"- Be specific to this startup's industry\n"
            f"- Events should be plausible and incremental, not dramatic or catastrophic\n"
            f"- Most events should be moderately positive or moderately negative, not extreme\n"
            f"- Avoid alternating wildly between very good and very bad events\n"
            f"- One sentence only\n\n"
            f"Event for month {month}:"
        )
        response = self.llm.chat([{"role": "user", "content": prompt}], max_tokens=100)
        return (response or "No significant market event this month.").strip()

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
