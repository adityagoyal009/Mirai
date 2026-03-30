"""Shared final-verdict blending for REST and interactive analysis paths."""

from typing import Any, Dict, List, Optional


_VERDICT_TO_SCORE = {
    "Strong Miss": 1,
    "Likely Miss": 2,
    "Mixed Signal": 3,
    "Uncertain": 3,
    "Likely Hit": 4,
    "Strong Hit": 5,
}

_SCORE_TO_NUMERIC = {
    1: 2.0,
    2: 4.0,
    3: 5.5,
    4: 7.5,
    5: 9.5,
}


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _ordinal_to_verdict(score: float) -> str:
    if score >= 4.5:
        return "Strong Hit"
    if score >= 3.5:
        return "Likely Hit"
    if score >= 2.5:
        return "Mixed Signal"
    if score >= 1.5:
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

    final_verdict = council_verdict
    final_confidence = council_confidence
    final_score = council_score
    warnings: List[str] = []

    council_ordinal = _VERDICT_TO_SCORE.get(council_verdict, 3)
    swarm_verdict = council_verdict
    swarm_confidence = council_confidence
    verdict_blended = False

    if isinstance(swarm, dict) and swarm:
        swarm_verdict = swarm.get("verdict", council_verdict)
        swarm_confidence = _coerce_float(swarm.get("avg_confidence"), council_confidence)
        swarm_ordinal = _VERDICT_TO_SCORE.get(swarm_verdict, council_ordinal)
        council_weight = max(council_confidence, 0.1)
        swarm_weight = max(swarm_confidence, 0.1)
        blended = (
            (council_ordinal * council_weight) + (swarm_ordinal * swarm_weight)
        ) / (council_weight + swarm_weight)

        final_verdict = _ordinal_to_verdict(blended)
        final_confidence = round(
            ((council_weight * council_confidence) + (swarm_weight * swarm_confidence))
            / (council_weight + swarm_weight),
            2,
        )
        final_score = _SCORE_TO_NUMERIC.get(_VERDICT_TO_SCORE.get(final_verdict, 3), council_score)
        verdict_blended = True

        if abs(council_ordinal - swarm_ordinal) >= 3:
            warnings.append(
                f"Council ({council_verdict}) and Swarm ({swarm_verdict}) strongly disagree. "
                f"Final verdict '{final_verdict}' is a confidence-weighted blend."
            )

    trajectory = ""
    oasis_adjusted = False
    if isinstance(oasis, dict) and oasis:
        trajectory = oasis.get("trajectory", "stable")
        confidence_low = final_confidence < 0.7

        if trajectory in ("declining", "improving") and trajectory != "stable":
            warnings.append(f"OASIS projects {trajectory} trajectory — monitor closely.")

        if trajectory == "declining" and final_verdict in ("Likely Hit", "Strong Hit"):
            if confidence_low and _max_consecutive_declines(oasis.get("timeline", []) or []) >= 2:
                final_verdict = "Mixed Signal"
                final_score = _SCORE_TO_NUMERIC[_VERDICT_TO_SCORE[final_verdict]]
                oasis_adjusted = True
        elif trajectory == "improving" and final_verdict in ("Likely Miss", "Mixed Signal"):
            if confidence_low:
                upgrade_map = {
                    "Likely Miss": "Mixed Signal",
                    "Mixed Signal": "Likely Hit",
                }
                final_verdict = upgrade_map.get(final_verdict, final_verdict)
                final_score = _SCORE_TO_NUMERIC[_VERDICT_TO_SCORE[final_verdict]]
                oasis_adjusted = True

    if not verdict_blended and not oasis_adjusted:
        final_score = council_score

    return {
        "council_verdict": council_verdict,
        "council_confidence": council_confidence,
        "council_score": council_score,
        "swarm_verdict": swarm_verdict,
        "swarm_confidence": swarm_confidence,
        "final_verdict": final_verdict,
        "final_confidence": final_confidence,
        "composite_score": final_score,
        "trajectory": trajectory or "stable",
        "verdict_blended": verdict_blended,
        "oasis_adjusted": oasis_adjusted,
        "warnings": warnings,
    }
