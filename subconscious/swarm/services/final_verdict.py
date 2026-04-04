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
    # Keep swarm numeric output relatively conservative; its highest value is often
    # objection discovery and lane-specific reasoning, not precise score calibration.
    blended = (median_overall * 0.7) + (avg_overall * 0.3) + (vote_pull * 0.25)
    return round(_clamp(blended), 2)


def finalize_prediction(
    council_prediction: Dict[str, Any],
    *,
    swarm: Optional[Dict[str, Any]] = None,
    oasis: Optional[Dict[str, Any]] = None,
    research_quality: Optional[Dict[str, Any]] = None,
    risk_panel: Optional[Dict[str, Any]] = None,
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
    risk_panel_penalty = 0.0
    risk_panel_high_severity_count = 0
    risk_panel_dimension_penalties: Dict[str, float] = {}
    risk_adjusted_dimensions: List[Dict[str, Any]] = []

    if isinstance(swarm, dict) and swarm:
        swarm_verdict = swarm.get("verdict", council_verdict)
        swarm_confidence = _coerce_float(swarm.get("avg_confidence"), council_confidence)
        swarm_score = _swarm_numeric_score(swarm, council_score)

        std_overall = _coerce_float(swarm.get("std_overall"), 0.0)
        # Numeric score should lean on the more calibrated council layer, with swarm
        # serving as a secondary adjustment whose impact shrinks when disagreement rises.
        council_weight = 0.78 * max(council_confidence, 0.4)
        swarm_weight = 0.22 * max(swarm_confidence, 0.25) * max(0.2, 1.0 - min(std_overall, 3.0) / 4.5)

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

    research_quality_score: Optional[float] = None
    if isinstance(research_quality, dict) and research_quality:
        research_quality_score = _coerce_float(research_quality.get("overall_score"), -1.0)
        if research_quality_score >= 0:
            low_coverage_dimensions = research_quality.get("low_coverage_dimensions", []) or []
            missing_evidence_flags = research_quality.get("missing_evidence_flags", []) or []
            quality_penalty = 0.0

            if research_quality_score < 0.75:
                quality_penalty += min(0.35, (0.75 - research_quality_score) * 0.6)
            if len(low_coverage_dimensions) >= 3:
                quality_penalty += 0.08
            elif len(low_coverage_dimensions) >= 1:
                quality_penalty += 0.04
            if "research_parse_degraded" in missing_evidence_flags:
                quality_penalty += 0.07
            if "low_faithfulness" in missing_evidence_flags:
                quality_penalty += 0.08

            if quality_penalty > 0:
                final_confidence = round(max(0.1, final_confidence - min(0.4, quality_penalty)), 2)
                warnings.append(
                    f"Research quality is {research_quality_score:.2f}/1.00 — confidence reduced because evidence coverage is uneven."
                )

            if low_coverage_dimensions:
                warnings.append(
                    "Low research coverage in: " + ", ".join(low_coverage_dimensions[:4]) + "."
                )

    if isinstance(risk_panel, dict) and risk_panel:
        risk_panel_penalty = _coerce_float(risk_panel.get("overall_penalty"), 0.0)
        penalties = risk_panel.get("dimension_penalties", {})
        if isinstance(penalties, dict):
            risk_panel_dimension_penalties = {
                str(key): round(_coerce_float(value, 0.0), 2)
                for key, value in penalties.items()
                if _coerce_float(value, 0.0) > 0
            }

        findings = risk_panel.get("findings", [])
        if isinstance(findings, list):
            material_findings = [
                finding for finding in findings
                if isinstance(finding, dict) and finding.get("status") == "risk_found"
            ]
            insufficient_count = sum(
                1 for finding in findings
                if isinstance(finding, dict) and finding.get("status") == "insufficient_evidence"
            )
            risk_panel_high_severity_count = sum(
                1 for finding in material_findings if finding.get("severity") == "high"
            )

            if risk_panel_penalty > 0:
                final_score = round(_clamp(final_score - min(1.2, risk_panel_penalty)), 2)
                final_verdict = _numeric_to_verdict(final_score)
                top_labels = [
                    str(finding.get("label", finding.get("domain", "risk")))
                    for finding in material_findings[:3]
                ]
                if top_labels:
                    warnings.append(
                        "Risk panel flagged material issues in: " + ", ".join(top_labels) + "."
                    )
            if insufficient_count >= 2:
                final_confidence = round(max(0.1, final_confidence - min(0.15, insufficient_count * 0.03)), 2)
                warnings.append(
                    f"Risk panel reported {insufficient_count} domains with insufficient evidence."
                )

        raw_dimensions = council_prediction.get("dimensions", [])
        if isinstance(raw_dimensions, list):
            for dimension in raw_dimensions:
                if not isinstance(dimension, dict):
                    continue
                name = str(dimension.get("name", "") or "")
                base_score = _coerce_float(dimension.get("score"), 0.0)
                penalty = _coerce_float(risk_panel_dimension_penalties.get(name), 0.0)
                adjusted_score = round(_clamp(base_score - penalty), 2) if base_score > 0 else 0.0
                risk_adjusted_dimensions.append({
                    "name": name,
                    "score": round(base_score, 2),
                    "risk_penalty": round(penalty, 2),
                    "risk_adjusted_score": adjusted_score,
                    "reasoning": dimension.get("reasoning", ""),
                })

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
        "research_quality_score": research_quality_score,
        "risk_panel_penalty": round(risk_panel_penalty, 2),
        "risk_panel_high_severity_count": risk_panel_high_severity_count,
        "risk_panel_dimension_penalties": risk_panel_dimension_penalties,
        "risk_adjusted_dimensions": risk_adjusted_dimensions,
        "warnings": warnings,
    }
