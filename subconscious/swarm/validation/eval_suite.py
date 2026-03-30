"""
Mirai Evaluation Suite — LLM-as-judge metrics for research quality assessment.
No external eval frameworks. Uses gateway LLM + hallucination_guard.
"""
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from openai import OpenAI
from ..config import Config
from ..services.hallucination_guard import check_faithfulness

logger = logging.getLogger("mirai.eval_suite")

THRESHOLDS = {
    "faithfulness": 0.7,
    "relevancy": 0.7,
    "hallucination": 0.3,
    "council_grounding": 0.7,
    "persona_adherence": 0.7,
}


def _llm_judge(criteria: str, context: str, output: str) -> float:
    """Score 0-1 using LLM as judge via Mirai gateway."""
    try:
        client = OpenAI(api_key=Config.LLM_API_KEY, base_url=Config.LLM_BASE_URL)
        resp = client.chat.completions.create(
            model="anthropic/claude-sonnet-4-6",
            messages=[{"role": "user", "content": (
                f"You are evaluating AI output quality. Score 0-10 on this criterion:\n\n"
                f"CRITERION: {criteria}\n\n"
                f"CONTEXT: {context[:2000]}\n\n"
                f"OUTPUT TO EVALUATE: {output[:2000]}\n\n"
                f"Return ONLY a single number 0-10. Nothing else."
            )}],
            max_tokens=10,
            temperature=0.0,
        )
        score = float(resp.choices[0].message.content.strip().split()[0])
        return min(max(score / 10.0, 0.0), 1.0)
    except Exception as e:
        logger.warning(f"[Eval] LLM judge failed: {e}")
        return 0.5


class MiraiEvalSuite:
    def __init__(self):
        self._results = []

    def evaluate_synthesis(self, synthesis: str, raw_sources: List[str], query: str = "") -> Dict:
        """Evaluate research synthesis quality."""
        # Faithfulness via hallucination_guard (no LLM call needed)
        faith_result = check_faithfulness(synthesis, raw_sources)
        faithfulness = faith_result.get("faithfulness", 0.5)

        # Relevancy via LLM judge
        relevancy = _llm_judge(
            "Does this research synthesis directly address the research topic and provide actionable findings?",
            query, synthesis
        )

        # Hallucination = inverse faithfulness
        hallucination = 1.0 - faithfulness

        result = {
            "faithfulness": round(faithfulness, 4),
            "relevancy": round(relevancy, 4),
            "hallucination": round(hallucination, 4),
            "pass": (faithfulness >= THRESHOLDS["faithfulness"] and
                     relevancy >= THRESHOLDS["relevancy"] and
                     hallucination <= THRESHOLDS["hallucination"]),
            "details": faith_result.get("claims", [])[:5],
        }
        self._results.append({"type": "synthesis", "timestamp": datetime.utcnow().isoformat(), **result})
        return result

    def evaluate_council_scoring(self, scores: Dict, research_context: str) -> Dict:
        """Evaluate whether council dimension scores are grounded in research."""
        scores_str = json.dumps(scores, indent=2) if isinstance(scores, dict) else str(scores)
        grounding = _llm_judge(
            "Are these dimension scores justified by specific facts from the research context? Each score should have evidence.",
            research_context, scores_str
        )
        result = {
            "council_grounding": round(grounding, 4),
            "pass": grounding >= THRESHOLDS["council_grounding"],
        }
        self._results.append({"type": "council", "timestamp": datetime.utcnow().isoformat(), **result})
        return result

    def evaluate_agent_reasoning(self, reasoning: str, persona: str, exec_summary: str = "") -> Dict:
        """Evaluate whether agent reasoning stayed within persona domain."""
        adherence = _llm_judge(
            "Did this agent stay within their specific domain expertise? A VC should discuss investment, a doctor should discuss health impacts, etc.",
            f"Persona: {persona}\nStartup: {exec_summary[:500]}", reasoning
        )
        result = {
            "persona_adherence": round(adherence, 4),
            "pass": adherence >= THRESHOLDS["persona_adherence"],
        }
        self._results.append({"type": "agent", "timestamp": datetime.utcnow().isoformat(), **result})
        return result

    def run_backtest_eval(self, backtest_results: List[Dict]) -> Dict:
        """Run evaluation across a backtest run."""
        synthesis_scores, council_scores, agent_scores = [], [], []
        for r in backtest_results:
            if r.get("research_summary") and r.get("raw_sources"):
                s = self.evaluate_synthesis(r["research_summary"], r["raw_sources"], r.get("query", ""))
                synthesis_scores.append(s)
            if r.get("dimension_scores") and r.get("research_context"):
                c = self.evaluate_council_scoring(r["dimension_scores"], r["research_context"])
                council_scores.append(c)
        avg = lambda scores, key: sum(s[key] for s in scores) / max(len(scores), 1)
        return {
            "synthesis_avg_faithfulness": round(avg(synthesis_scores, "faithfulness"), 4) if synthesis_scores else None,
            "synthesis_avg_relevancy": round(avg(synthesis_scores, "relevancy"), 4) if synthesis_scores else None,
            "council_avg_grounding": round(avg(council_scores, "council_grounding"), 4) if council_scores else None,
            "total_evaluated": len(synthesis_scores) + len(council_scores) + len(agent_scores),
            "pass_rate": round(sum(1 for s in self._results if s.get("pass")) / max(len(self._results), 1), 4),
        }

    def report(self) -> str:
        """Generate a human-readable summary of all evaluations run so far."""
        if not self._results:
            return "No evaluations run yet."
        lines = [f"Mirai Eval Report ({len(self._results)} evaluations)"]
        by_type = {}
        for r in self._results:
            by_type.setdefault(r["type"], []).append(r)
        for t, items in by_type.items():
            passed = sum(1 for i in items if i.get("pass"))
            lines.append(f"  {t}: {passed}/{len(items)} passed")
        return "\n".join(lines)
