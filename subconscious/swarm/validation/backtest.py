"""
Backtesting Engine — runs historical startups through SwarmPredictor
and measures prediction accuracy against known outcomes.

Enhanced with per-dimension, per-zone, and per-model accuracy tracking,
plus prompt version correlation for calibration feedback loops.

Usage:
    python -m subconscious.swarm.validation.backtest [--agents 50] [--limit 10]
    python -m subconscious.swarm.validation.backtest --compare
"""

import json
import os
import sys
import time
import glob as glob_mod
import subprocess
import argparse
from collections import defaultdict
from typing import List, Dict, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from subconscious.swarm.validation.scraper import load_dataset, startup_to_exec_summary
from subconscious.swarm.services.swarm_predictor import SwarmPredictor, SCORE_DIMENSIONS
from subconscious.swarm.utils.logger import get_logger

# Prompt registry integration
try:
    from subconscious.swarm.utils.prompt_registry import get_all_hashes, get_snapshot
except ImportError:
    def get_all_hashes(): return {}
    def get_snapshot(): return {}

logger = get_logger('mirofish.validation.backtest')

OUTCOME_SCORES = {
    "success": 1.0,    # IPO/Unicorn/Profitable
    "acquired": 0.7,   # Acquired (depends on terms)
    "failed": 0.0,     # Shut down
}

RESULTS_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'validation_results.json')
BACKTEST_ARCHIVE_DIR = os.path.join(os.path.expanduser("~"), ".mirai", "backtest")

# All persona zones from persona_engine
ALL_ZONES = ["investor", "customer", "operator", "analyst", "contrarian", "wildcard"]


# ══════════════════════════════════════════════════════════════════
# Per-run metadata
# ══════════════════════════════════════════════════════════════════

def _get_git_commit() -> str:
    """Get short git commit hash, or 'unknown' if not in a repo."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=os.path.join(os.path.dirname(__file__), '..', '..', '..'),
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except Exception:
        return "unknown"


def _build_run_metadata() -> Dict[str, Any]:
    """Build metadata dict for this backtest run."""
    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "git_commit": _get_git_commit(),
        "prompt_hashes": get_all_hashes(),
        "prompt_snapshot": get_snapshot(),
    }


# ══════════════════════════════════════════════════════════════════
# Per-company breakdown builder
# ══════════════════════════════════════════════════════════════════

def _build_company_result(
    company: str,
    industry: str,
    outcome: str,
    actual_score: float,
    result,  # SwarmResult
) -> Dict[str, Any]:
    """
    Build an enhanced per-company result dict from a SwarmResult.
    Includes dimension_scores, swarm_stats with per-zone accuracy.
    """
    predicted_score = result.median_overall / 10.0  # Normalize to 0-1
    predicted_verdict = result.verdict

    correct = (predicted_score >= 0.55 and actual_score >= 0.5) or \
              (predicted_score < 0.55 and actual_score < 0.5)

    # Per-dimension scores from swarm averages
    dimension_scores = dict(result.avg_scores)

    # Per-zone accuracy: did each zone's majority vote match the actual outcome?
    actual_positive = actual_score >= 0.5
    zone_accuracy = {}
    zone_votes = defaultdict(lambda: {"hit": 0, "miss": 0})

    for agent in result.agent_results:
        z = getattr(agent, 'zone', 'wildcard')
        if agent.overall >= 5.5:
            zone_votes[z]["hit"] += 1
        else:
            zone_votes[z]["miss"] += 1

    for z, votes in zone_votes.items():
        total_z = votes["hit"] + votes["miss"]
        if total_z == 0:
            continue
        zone_majority_hit = votes["hit"] >= votes["miss"]
        zone_accuracy[z] = (zone_majority_hit == actual_positive)

    # Per-model tracking
    model_votes = defaultdict(lambda: {"hit": 0, "miss": 0})
    for agent in result.agent_results:
        m = getattr(agent, 'model_used', 'unknown')
        if agent.overall >= 5.5:
            model_votes[m]["hit"] += 1
        else:
            model_votes[m]["miss"] += 1

    per_model_majority = {}
    for m, votes in model_votes.items():
        total_m = votes["hit"] + votes["miss"]
        if total_m == 0:
            continue
        model_majority_hit = votes["hit"] >= votes["miss"]
        per_model_majority[m] = (model_majority_hit == actual_positive)

    return {
        "company": company,
        "industry": industry,
        "actual_outcome": outcome,
        "actual_score": actual_score,
        "predicted_verdict": predicted_verdict,
        "predicted_score": round(predicted_score, 3),
        "correct": correct,
        "dimension_scores": {k: round(v, 2) for k, v in dimension_scores.items()},
        "swarm_stats": {
            "positive_pct": round(result.positive_pct, 1),
            "total_agents": result.total_agents,
            "zone_accuracy": zone_accuracy,
            "model_accuracy": per_model_majority,
        },
        "median_overall": result.median_overall,
        "avg_scores": result.avg_scores,
        "std_overall": result.std_overall,
        "agents_responded": result.total_agents,
        "models_used": result.models_used,
    }


# ══════════════════════════════════════════════════════════════════
# Summary statistics
# ══════════════════════════════════════════════════════════════════

def compute_summary_statistics(results: List[Dict]) -> Dict[str, Any]:
    """
    Compute comprehensive summary statistics from backtest results.

    Returns:
        Dict with overall_accuracy, false_positive_rate, false_negative_rate,
        per_dimension_accuracy, per_zone_accuracy, per_model_accuracy,
        and deliberation_impact.
    """
    valid = [r for r in results if 'error' not in r]
    if not valid:
        return {"error": "No valid results"}

    total = len(valid)
    correct = sum(1 for r in valid if r['correct'])
    overall_accuracy = round(correct / total, 3)

    # False positive: predicted positive but actually failed
    actual_failures = [r for r in valid if r.get('actual_score', 0) < 0.5]
    false_positives = sum(1 for r in actual_failures if r.get('predicted_score', 0) >= 0.55)
    fp_rate = round(false_positives / len(actual_failures), 3) if actual_failures else 0

    # False negative: predicted negative but actually succeeded
    actual_successes = [r for r in valid if r.get('actual_score', 0) >= 0.5]
    false_negatives = sum(1 for r in actual_successes if r.get('predicted_score', 0) < 0.55)
    fn_rate = round(false_negatives / len(actual_successes), 3) if actual_successes else 0

    # Per-dimension accuracy: for each scoring dimension, would that dimension
    # alone have correctly predicted the outcome?
    per_dimension_accuracy = {}
    for dim in SCORE_DIMENSIONS:
        dim_valid = [r for r in valid if dim in r.get('dimension_scores', {})]
        if not dim_valid:
            continue
        dim_correct = 0
        for r in dim_valid:
            dim_score = r['dimension_scores'][dim]
            predicted_positive = dim_score >= 5.5
            actual_positive = r.get('actual_score', 0) >= 0.5
            if predicted_positive == actual_positive:
                dim_correct += 1
        per_dimension_accuracy[dim] = round(dim_correct / len(dim_valid), 3)

    # Per-zone accuracy: aggregate zone correctness across all companies
    zone_correct = defaultdict(int)
    zone_total = defaultdict(int)
    for r in valid:
        zone_acc = r.get('swarm_stats', {}).get('zone_accuracy', {})
        for zone, was_correct in zone_acc.items():
            zone_total[zone] += 1
            if was_correct:
                zone_correct[zone] += 1

    per_zone_accuracy = {}
    for zone in zone_total:
        per_zone_accuracy[zone] = round(zone_correct[zone] / zone_total[zone], 3)

    # Per-model accuracy
    model_correct = defaultdict(int)
    model_total = defaultdict(int)
    for r in valid:
        model_acc = r.get('swarm_stats', {}).get('model_accuracy', {})
        for model, was_correct in model_acc.items():
            model_total[model] += 1
            if was_correct:
                model_correct[model] += 1

    per_model_accuracy = {}
    for model in model_total:
        per_model_accuracy[model] = round(model_correct[model] / model_total[model], 3)

    # Deliberation impact: compare swarm-weighted consensus accuracy vs raw median
    weighted_correct = 0
    unweighted_correct = 0
    delib_count = 0
    for r in valid:
        swarm_pct = r.get('swarm_stats', {}).get('positive_pct')
        if swarm_pct is not None:
            delib_count += 1
            actual_positive = r.get('actual_score', 0) >= 0.5
            # Weighted: using swarm positive_pct (includes deliberation weights)
            swarm_positive = swarm_pct >= 55
            if swarm_positive == actual_positive:
                weighted_correct += 1
            # Unweighted: just using raw predicted_score
            raw_positive = r.get('predicted_score', 0) >= 0.55
            if raw_positive == actual_positive:
                unweighted_correct += 1

    deliberation_impact = {}
    if delib_count > 0:
        deliberation_impact = {
            "weighted_accuracy": round(weighted_correct / delib_count, 3),
            "unweighted_accuracy": round(unweighted_correct / delib_count, 3),
            "sample_size": delib_count,
        }

    return {
        "overall_accuracy": overall_accuracy,
        "total_evaluated": total,
        "correct": correct,
        "wrong": total - correct,
        "false_positive_rate": fp_rate,
        "false_negative_rate": fn_rate,
        "per_dimension_accuracy": per_dimension_accuracy,
        "per_zone_accuracy": per_zone_accuracy,
        "per_model_accuracy": per_model_accuracy,
        "deliberation_impact": deliberation_impact,
    }


# ══════════════════════════════════════════════════════════════════
# Persistence
# ══════════════════════════════════════════════════════════════════

def _save_results(results: List[Dict], start_time: float):
    """Save intermediate results."""
    output = {
        "results": results,
        "elapsed_seconds": round(time.time() - start_time, 1),
        "count": len(results),
    }
    os.makedirs(os.path.dirname(RESULTS_FILE), exist_ok=True)
    with open(RESULTS_FILE, 'w') as f:
        json.dump(output, f, indent=2, default=str)


def save_run_archive(results: List[Dict], summary: Dict[str, Any], elapsed: float) -> str:
    """
    Save a complete run to ~/.mirai/backtest/run_{timestamp}.json.
    Returns the path to the saved file.
    """
    os.makedirs(BACKTEST_ARCHIVE_DIR, exist_ok=True)

    run_data = {
        **_build_run_metadata(),
        "results": results,
        "summary": summary,
        "elapsed_seconds": round(elapsed, 1),
    }

    ts = time.strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(BACKTEST_ARCHIVE_DIR, f"run_{ts}.json")
    with open(filepath, "w") as f:
        json.dump(run_data, f, indent=2, default=str)

    return filepath


def load_previous_runs(max_runs: int = 10) -> List[Dict]:
    """Load previous run archives, sorted newest first."""
    pattern = os.path.join(BACKTEST_ARCHIVE_DIR, "run_*.json")
    files = sorted(glob_mod.glob(pattern), reverse=True)
    runs = []
    for fpath in files[:max_runs]:
        try:
            with open(fpath) as f:
                run = json.load(f)
                run["_filepath"] = fpath
                runs.append(run)
        except (json.JSONDecodeError, IOError):
            continue
    return runs


# ══════════════════════════════════════════════════════════════════
# Comparison mode
# ══════════════════════════════════════════════════════════════════

def print_comparison(current_summary: Optional[Dict] = None):
    """
    Compare the last two runs and print a diff.
    If current_summary is provided, compare it against the most recent archived run.
    """
    runs = load_previous_runs(max_runs=5)

    if current_summary and runs:
        new_summary = current_summary
        old_summary = runs[0].get("summary", {})
        old_label = os.path.basename(runs[0].get("_filepath", "previous"))
        new_label = "current run"

        old_hashes = runs[0].get("prompt_hashes", {})
        new_hashes = get_all_hashes()
    elif len(runs) >= 2:
        new_summary = runs[0].get("summary", {})
        old_summary = runs[1].get("summary", {})
        new_label = os.path.basename(runs[0].get("_filepath", "newer"))
        old_label = os.path.basename(runs[1].get("_filepath", "older"))

        old_hashes = runs[1].get("prompt_hashes", {})
        new_hashes = runs[0].get("prompt_hashes", {})
    else:
        logger.info("[Backtest] No previous runs to compare.")
        return

    # Prompt changes
    changed_prompts = []
    for name in set(list(old_hashes.keys()) + list(new_hashes.keys())):
        old_h = old_hashes.get(name, "<missing>")
        new_h = new_hashes.get(name, "<missing>")
        if old_h != new_h:
            changed_prompts.append(name)

    print(f"\n{'='*60}")
    print(f"  COMPARISON: {old_label} -> {new_label}")
    print(f"{'='*60}")

    if changed_prompts:
        print(f"  Prompt changes: {', '.join(changed_prompts)}")
        for name in changed_prompts:
            print(f"    {name}: {old_hashes.get(name, '<new>')[:8]} -> {new_hashes.get(name, '<removed>')[:8]}")
    else:
        print("  Prompts: unchanged")

    # Overall accuracy
    old_acc = old_summary.get("overall_accuracy", 0)
    new_acc = new_summary.get("overall_accuracy", 0)
    delta = new_acc - old_acc
    sign = "+" if delta >= 0 else ""
    print(f"\n  Accuracy: {old_acc*100:.0f}% -> {new_acc*100:.0f}% ({sign}{delta*100:.0f}%)")

    # FP/FN
    old_fp = old_summary.get("false_positive_rate", 0)
    new_fp = new_summary.get("false_positive_rate", 0)
    delta_fp = new_fp - old_fp
    sign_fp = "+" if delta_fp >= 0 else ""
    print(f"  False positive rate: {old_fp*100:.0f}% -> {new_fp*100:.0f}% ({sign_fp}{delta_fp*100:.0f}%)")

    old_fn = old_summary.get("false_negative_rate", 0)
    new_fn = new_summary.get("false_negative_rate", 0)
    delta_fn = new_fn - old_fn
    sign_fn = "+" if delta_fn >= 0 else ""
    print(f"  False negative rate: {old_fn*100:.0f}% -> {new_fn*100:.0f}% ({sign_fn}{delta_fn*100:.0f}%)")

    # Best/worst dimensions
    dim_acc = new_summary.get("per_dimension_accuracy", {})
    if dim_acc:
        best_dim = max(dim_acc, key=dim_acc.get)
        worst_dim = min(dim_acc, key=dim_acc.get)
        print(f"  Best dimension: {best_dim} ({dim_acc[best_dim]*100:.0f}%)")
        print(f"  Worst dimension: {worst_dim} ({dim_acc[worst_dim]*100:.0f}%)")

    # Best/worst zones
    zone_acc = new_summary.get("per_zone_accuracy", {})
    if zone_acc:
        best_zone = max(zone_acc, key=zone_acc.get)
        worst_zone = min(zone_acc, key=zone_acc.get)
        print(f"  Most accurate zone: {best_zone} ({zone_acc[best_zone]*100:.0f}%)")
        if best_zone != worst_zone:
            print(f"  Least accurate zone: {worst_zone} ({zone_acc[worst_zone]*100:.0f}%)")

    # Deliberation
    delib = new_summary.get("deliberation_impact", {})
    if delib:
        print(f"  Deliberation: weighted={delib.get('weighted_accuracy', 0)*100:.0f}% "
              f"vs unweighted={delib.get('unweighted_accuracy', 0)*100:.0f}%")

    print()


# ══════════════════════════════════════════════════════════════════
# Main backtest runner
# ══════════════════════════════════════════════════════════════════

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
    logger.info(f"[Backtest] Git commit: {_get_git_commit()}")
    logger.info(f"[Backtest] Prompt hashes: {get_all_hashes()}")

    swarm = SwarmPredictor()
    results = []
    start_time = time.time()

    for i, startup in enumerate(dataset):
        company = startup.get('company', 'Unknown')
        outcome = startup.get('outcome', 'unknown')
        actual_score = OUTCOME_SCORES.get(outcome, 0.5)
        industry = startup.get('industry', '')

        logger.info(f"[Backtest] {i+1}/{len(dataset)}: {company} ({outcome})")

        exec_summary = startup_to_exec_summary(startup)

        try:
            result = swarm.predict(
                exec_summary=exec_summary,
                research_context=f"Historical company: {company}. Actual outcome: HIDDEN (backtesting).",
                agent_count=agents_per_run,
            )

            company_result = _build_company_result(
                company=company,
                industry=industry,
                outcome=outcome,
                actual_score=actual_score,
                result=result,
            )
            results.append(company_result)

            logger.info(
                f"  -> Predicted: {company_result['predicted_verdict']} "
                f"({result.median_overall:.1f}/10) | "
                f"Actual: {outcome} | "
                f"{'CORRECT' if company_result['correct'] else 'WRONG'}"
            )

        except Exception as e:
            logger.error(f"  -> Failed: {e}")
            results.append({
                "company": company, "actual_outcome": outcome,
                "actual_score": actual_score,
                "error": str(e), "correct": False,
            })

        # Save incrementally
        _save_results(results, start_time)

    elapsed = time.time() - start_time

    # Compute legacy metrics for backward compat
    metrics = _compute_metrics(results, start_time)

    # Compute enhanced summary statistics
    summary = compute_summary_statistics(results)
    metrics["summary"] = summary

    # Save archived run
    archive_path = save_run_archive(results, summary, elapsed)
    logger.info(f"[Backtest] Run archived to: {archive_path}")

    # Print summary
    _print_summary(summary)

    # Print comparison with previous runs
    print_comparison(current_summary=summary)

    return metrics


def _compute_metrics(results: List[Dict], start_time: float) -> Dict[str, Any]:
    """Compute accuracy metrics from backtest results (backward compat)."""
    valid = [r for r in results if 'error' not in r]
    if not valid:
        return {"error": "No valid results"}

    total = len(valid)
    correct = sum(1 for r in valid if r['correct'])
    accuracy = round(correct / total * 100, 1)

    # Per-outcome accuracy
    by_outcome = {}
    for r in valid:
        o = r.get('actual_outcome', r.get('outcome', 'unknown'))
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


def _print_summary(summary: Dict[str, Any]):
    """Print enhanced summary statistics."""
    if "error" in summary:
        print(f"\n  Summary error: {summary['error']}")
        return

    print(f"\n{'='*60}")
    print(f"  BACKTEST SUMMARY STATISTICS")
    print(f"{'='*60}")
    print(f"  Overall accuracy:      {summary['overall_accuracy']*100:.1f}% "
          f"({summary['correct']}/{summary['total_evaluated']})")
    print(f"  False positive rate:   {summary['false_positive_rate']*100:.1f}%")
    print(f"  False negative rate:   {summary['false_negative_rate']*100:.1f}%")

    dim_acc = summary.get("per_dimension_accuracy", {})
    if dim_acc:
        print(f"\n  Per-dimension accuracy:")
        for dim, acc in sorted(dim_acc.items(), key=lambda x: -x[1]):
            bar = "#" * int(acc * 20)
            print(f"    {dim:20s} {acc*100:5.1f}%  {bar}")

    zone_acc = summary.get("per_zone_accuracy", {})
    if zone_acc:
        print(f"\n  Per-zone accuracy:")
        for zone, acc in sorted(zone_acc.items(), key=lambda x: -x[1]):
            bar = "#" * int(acc * 20)
            print(f"    {zone:20s} {acc*100:5.1f}%  {bar}")

    model_acc = summary.get("per_model_accuracy", {})
    if model_acc:
        print(f"\n  Per-model accuracy:")
        for model, acc in sorted(model_acc.items(), key=lambda x: -x[1]):
            print(f"    {model:30s} {acc*100:5.1f}%")

    delib = summary.get("deliberation_impact", {})
    if delib:
        print(f"\n  Deliberation impact (n={delib.get('sample_size', 0)}):")
        print(f"    Weighted accuracy:   {delib.get('weighted_accuracy', 0)*100:.1f}%")
        print(f"    Unweighted accuracy: {delib.get('unweighted_accuracy', 0)*100:.1f}%")

    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mirai Backtest Engine")
    parser.add_argument("--agents", type=int, default=50, help="Agents per startup")
    parser.add_argument("--limit", type=int, default=0, help="Max startups (0=all)")
    parser.add_argument("--compare", action="store_true", help="Compare last two runs")
    args = parser.parse_args()

    if args.compare:
        print_comparison()
    else:
        metrics = run_backtest(agents_per_run=args.agents, limit=args.limit)
        print(json.dumps(metrics, indent=2, default=str))
