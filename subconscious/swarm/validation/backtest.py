"""
Backtesting Engine — runs historical startups through SwarmPredictor
and measures prediction accuracy against known outcomes.

Usage:
    python -m subconscious.swarm.validation.backtest [--agents 50] [--limit 10]
"""

import json
import os
import sys
import time
import argparse
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from subconscious.swarm.validation.scraper import load_dataset, startup_to_exec_summary
from subconscious.swarm.services.swarm_predictor import SwarmPredictor
from subconscious.swarm.utils.logger import get_logger

logger = get_logger('mirofish.validation.backtest')

OUTCOME_SCORES = {
    "success": 1.0,    # IPO/Unicorn/Profitable
    "acquired": 0.7,   # Acquired (depends on terms)
    "failed": 0.0,     # Shut down
}

RESULTS_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'validation_results.json')


def run_backtest(agents_per_run: int = 50, limit: int = 0) -> Dict[str, Any]:
    """
    Run backtesting on historical startups.

    Args:
        agents_per_run: Number of swarm agents per startup (50 for cost efficiency)
        limit: Max startups to test (0 = all)
    """
    dataset = load_dataset()
    if limit > 0:
        dataset = dataset[:limit]

    logger.info(f"[Backtest] Starting: {len(dataset)} startups, {agents_per_run} agents each")

    swarm = SwarmPredictor()
    results = []
    start_time = time.time()

    for i, startup in enumerate(dataset):
        company = startup.get('company', 'Unknown')
        outcome = startup.get('outcome', 'unknown')
        actual_score = OUTCOME_SCORES.get(outcome, 0.5)

        logger.info(f"[Backtest] {i+1}/{len(dataset)}: {company} ({outcome})")

        exec_summary = startup_to_exec_summary(startup)

        try:
            result = swarm.predict(
                exec_summary=exec_summary,
                research_context=f"Historical company: {company}. Actual outcome: HIDDEN (backtesting).",
                agent_count=agents_per_run,
            )

            predicted_score = result.median_overall / 10.0  # Normalize to 0-1
            predicted_verdict = result.verdict

            results.append({
                "company": company,
                "industry": startup.get('industry', ''),
                "outcome": outcome,
                "actual_score": actual_score,
                "predicted_score": round(predicted_score, 3),
                "predicted_verdict": predicted_verdict,
                "median_overall": result.median_overall,
                "avg_scores": result.avg_scores,
                "std_overall": result.std_overall,
                "agents_responded": result.total_agents,
                "models_used": result.models_used,
                "correct": (predicted_score >= 0.55 and actual_score >= 0.5) or
                          (predicted_score < 0.55 and actual_score < 0.5),
            })

            logger.info(
                f"  → Predicted: {predicted_verdict} ({result.median_overall:.1f}/10) | "
                f"Actual: {outcome} | {'CORRECT' if results[-1]['correct'] else 'WRONG'}"
            )

        except Exception as e:
            logger.error(f"  → Failed: {e}")
            results.append({
                "company": company, "outcome": outcome,
                "error": str(e), "correct": False,
            })

        # Save incrementally
        _save_results(results, start_time)

    return _compute_metrics(results, start_time)


def _save_results(results: List[Dict], start_time: float):
    """Save intermediate results."""
    output = {
        "results": results,
        "elapsed_seconds": round(time.time() - start_time, 1),
        "count": len(results),
    }
    os.makedirs(os.path.dirname(RESULTS_FILE), exist_ok=True)
    with open(RESULTS_FILE, 'w') as f:
        json.dump(output, f, indent=2)


def _compute_metrics(results: List[Dict], start_time: float) -> Dict[str, Any]:
    """Compute accuracy metrics from backtest results."""
    valid = [r for r in results if 'error' not in r]
    if not valid:
        return {"error": "No valid results"}

    total = len(valid)
    correct = sum(1 for r in valid if r['correct'])
    accuracy = round(correct / total * 100, 1)

    # Per-outcome accuracy
    by_outcome = {}
    for r in valid:
        o = r['outcome']
        if o not in by_outcome:
            by_outcome[o] = {"total": 0, "correct": 0}
        by_outcome[o]["total"] += 1
        if r['correct']:
            by_outcome[o]["correct"] += 1

    for o in by_outcome:
        by_outcome[o]["accuracy"] = round(
            by_outcome[o]["correct"] / by_outcome[o]["total"] * 100, 1
        )

    # Prediction distribution
    predictions = [r.get('median_overall', 5) for r in valid]
    avg_prediction = round(sum(predictions) / len(predictions), 2)

    metrics = {
        "total_startups": total,
        "accuracy_pct": accuracy,
        "correct": correct,
        "wrong": total - correct,
        "by_outcome": by_outcome,
        "avg_predicted_score": avg_prediction,
        "elapsed_seconds": round(time.time() - start_time, 1),
        "results": valid,
    }

    _save_results(valid, start_time)
    logger.info(f"[Backtest] Complete: {accuracy}% accuracy ({correct}/{total})")

    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mirai Backtest Engine")
    parser.add_argument("--agents", type=int, default=50, help="Agents per startup")
    parser.add_argument("--limit", type=int, default=0, help="Max startups (0=all)")
    args = parser.parse_args()

    metrics = run_backtest(agents_per_run=args.agents, limit=args.limit)
    print(json.dumps(metrics, indent=2, default=str))
