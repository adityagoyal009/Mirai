"""Shared final-verdict blending for REST and interactive analysis paths."""

from typing import Any, Dict, List, Optional


_VERDICT_TO_SCORE = {
    "Strong Miss": 1.5,
    "Likely Miss": 3.5,
    "Mixed Signal": 5.5,
    "Uncertain": 5.5,
    "Likely Hit": 7.5,
    "Strong Hit": 9.0,
}


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, low: float = 1.0, high: float = 10.0) -> float:
    return max(low, min(high, value))


def _verdict_to_numeric(verdict: str, default: float = 5.5) -> float:
    return _VERDICT_TO_SCORE.get(verdict, default)


def _numeric_to_verdict(score: float) -> str:
    if score >= 8.5:
        return "Strong Hit"
    if score >= 6.8:
        return "Likely Hit"
    if score >= 5.0:
        return "Mixed Signal"
    if score >= 3.2:
        return "Likely Miss"
    return "Strong Miss"


def _max_consecutive_declines(timeline: List[Dict[str, Any]]) -> int:
    consecutive = 0
    max_consecutive = 0
    for entry in timeline:
        if _coerce_float(entry.get("sentiment_change", entry.get("change", 0))) < 0:
            consecutive += 1
            max_consecutive = max(max_consecutive, consecutive)
        else:
            consecutive = 0
    return max_consecutive


def _swarm_numeric_score(swarm: Dict[str, Any], fallback: float) -> float:
    avg_scores = swarm.get("avg_scores", {})
    avg_overall = 0.0
    if isinstance(avg_scores, dict):
        avg_overall = _coerce_float(avg_scores.get("overall"), 0.0)

    median_overall = _coerce_float(swarm.get("median_overall"), 0.0)
    if avg_overall <= 0:
        avg_overall = median_overall
    if median_overall <= 0:
        median_overall = avg_overall
    if avg_overall <= 0 and median_overall <= 0:
        return fallback

    positive_pct = _coerce_float(swarm.get("positive_pct"), 50.0)
    vote_pull = max(-1.0, min(1.0, (positive_pct - 50.0) / 50.0))
    blended = (median_overall * 0.6) + (avg_overall * 0.4) + (vote_pull * 0.5)
    return round(_clamp(blended), 2)


def finalize_prediction(
    council_prediction: Dict[str, Any],
    *,
    swarm: Optional[Dict[str, Any]] = None,
    oasis: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Blend council, swarm, and OASIS signals into the final investor-facing view."""
    council_verdict = council_prediction.get("verdict", "Unknown")
    council_confidence = _coerce_float(council_prediction.get("confidence"), 0.0)
    council_score = _coerce_float(
        council_prediction.get("overall_score", council_prediction.get("composite_score")),
        0.0,
    )
    if council_score <= 0:
        council_score = _verdict_to_numeric(council_verdict)

    final_verdict = council_verdict if council_verdict not in ("", "Unknown", None) else _numeric_to_verdict(council_score)
    final_confidence = council_confidence
    final_score = round(_clamp(council_score), 2)
    warnings: List[str] = []

    swarm_verdict = council_verdict
    swarm_confidence = council_confidence
    swarm_score = council_score
    verdict_blended = False

    if isinstance(swarm, dict) and swarm:
        swarm_verdict = swarm.get("verdict", council_verdict)
        swarm_confidence = _coerce_float(swarm.get("avg_confidence"), council_confidence)
        swarm_score = _swarm_numeric_score(swarm, council_score)

        std_overall = _coerce_float(swarm.get("std_overall"), 0.0)
        council_weight = max(council_confidence, 0.15)
        swarm_weight = max(swarm_confidence, 0.15) * (1.0 - min(std_overall, 3.0) / 8.0)

        if (council_weight + swarm_weight) > 0:
            final_score = round(
                _clamp(
                    ((council_score * council_weight) + (swarm_score * swarm_weight))
                    / (council_weight + swarm_weight)
                ),
                2,
            )
            disagreement = abs(council_score - swarm_score)
            confidence_penalty = min(0.2, disagreement / 20.0)
            final_confidence = round(
                max(
                    0.1,
                    min(
                        1.0,
                        (
                            (council_confidence * council_weight)
                            + (swarm_confidence * swarm_weight)
                        ) / (council_weight + swarm_weight) - confidence_penalty,
                    ),
                ),
                2,
            )
            final_verdict = _numeric_to_verdict(final_score)
            verdict_blended = True

            if disagreement >= 2.0:
                warnings.append(
                    f"Council ({council_verdict}, {council_score:.1f}/10) and Swarm "
                    f"({swarm_verdict}, {swarm_score:.1f}/10) strongly disagree."
                )

    trajectory = ""
    oasis_adjusted = False
    if isinstance(oasis, dict) and oasis:
        trajectory = oasis.get("trajectory", "stable")
        start = _coerce_float(oasis.get("start_sentiment", oasis.get("startSentiment")), 50.0)
        end = _coerce_float(oasis.get("final_sentiment", oasis.get("end_sentiment", oasis.get("endSentiment"))), 50.0)
        delta = end - start
        confidence_low = final_confidence < 0.75

        if trajectory in ("declining", "improving") and trajectory != "stable":
            warnings.append(f"OASIS projects {trajectory} trajectory — monitor closely.")

        if trajectory == "declining" and final_score >= 5.0:
            if confidence_low or _max_consecutive_declines(oasis.get("timeline", []) or []) >= 2:
                penalty = 1.0 if delta <= -20 else 0.6
                final_score = round(_clamp(final_score - penalty), 2)
                final_verdict = _numeric_to_verdict(final_score)
                oasis_adjusted = True
        elif trajectory == "improving" and final_score <= 6.2:
            if confidence_low:
                boost = 1.0 if delta >= 20 else 0.6
                final_score = round(_clamp(final_score + boost), 2)
                final_verdict = _numeric_to_verdict(final_score)
                oasis_adjusted = True

    return {
        "council_verdict": council_verdict,
        "council_confidence": council_confidence,
        "council_score": round(_clamp(council_score), 2),
        "swarm_verdict": swarm_verdict,
        "swarm_confidence": swarm_confidence,
        "swarm_score": round(_clamp(swarm_score), 2),
        "final_verdict": final_verdict,
        "final_confidence": final_confidence,
        "composite_score": final_score,
        "trajectory": trajectory or "stable",
        "verdict_blended": verdict_blended,
        "oasis_adjusted": oasis_adjusted,
        "warnings": warnings,
    }
