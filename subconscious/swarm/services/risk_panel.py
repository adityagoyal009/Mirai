"""
Deterministic risk panel for post-swarm diligence.

This complements the randomized contrarian swarm lane with fixed, domain-specific
risk reviewers that consume structured research, council, and swarm output.
"""

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..config import Config
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger

logger = get_logger("mirofish.risk_panel")

_MAX_WORKERS = 6
_MAX_OVERALL_PENALTY = 1.2
_SEVERITY_WEIGHTS = {
    "low": 0.10,
    "medium": 0.22,
    "high": 0.40,
}

_RISK_PANEL_SPECS: List[Dict[str, Any]] = [
    {
        "domain": "ip_risk",
        "label": "IP Attorney",
        "focus": (
            "Patent infringement exposure, freedom-to-operate issues, prior art overlap, "
            "trade secret leakage, and whether the company has defensible IP at all."
        ),
        "affects_dimensions": ["competition_landscape", "pattern_match"],
        "research_keys": [
            "company_profile", "competitors", "competitor_details",
            "patent_landscape", "patents", "facts", "sources",
        ],
        "condition": "always",
    },
    {
        "domain": "regulatory_risk",
        "label": "Regulatory Expert",
        "focus": (
            "Licensing requirements, compliance burden, pending regulation, cross-border "
            "constraints, and whether regulation creates a blocker or a tailwind."
        ),
        "affects_dimensions": ["regulatory_news_environment", "market_timing"],
        "research_keys": [
            "company_profile", "regulatory", "trends", "facts", "sources",
        ],
        "condition": "always",
    },
    {
        "domain": "competition_risk",
        "label": "Competition Analyst",
        "focus": (
            "Incumbent response, big-tech build risk, market concentration, moat durability, "
            "and how easily the startup can be out-distributed or copied."
        ),
        "affects_dimensions": ["competition_landscape", "scalability_potential"],
        "research_keys": [
            "company_profile", "competitors", "competitor_details",
            "pricing_analysis", "market_data", "facts", "sources",
        ],
        "condition": "always",
    },
    {
        "domain": "unit_economics_risk",
        "label": "Unit Economics Auditor",
        "focus": (
            "Pricing power, margin durability, CAC/LTV realism, burn survivability, "
            "services leakage, and whether the business can scale economically."
        ),
        "affects_dimensions": ["business_model_viability", "capital_efficiency"],
        "research_keys": [
            "company_profile", "pricing_analysis", "market_data",
            "financial_data", "financials", "traction_breakdown",
            "customer_evidence", "facts",
        ],
        "condition": "always",
    },
    {
        "domain": "platform_dependency_risk",
        "label": "Platform Risk Analyst",
        "focus": (
            "Dependency on third-party APIs, cloud providers, app stores, distribution gates, "
            "or infrastructure chokepoints that can compress margins or kill growth."
        ),
        "affects_dimensions": ["business_model_viability", "scalability_potential"],
        "research_keys": [
            "company_profile", "competitor_details", "pricing_analysis",
            "risks", "facts", "sources",
        ],
        "condition": "always",
    },
    {
        "domain": "technical_diligence_risk",
        "label": "Technical Due Diligence",
        "focus": (
            "Scalability bottlenecks, implementation fragility, security posture, hiring difficulty, "
            "architecture maturity, and whether the product can actually deliver at scale."
        ),
        "affects_dimensions": ["team_execution_signals", "scalability_potential"],
        "research_keys": [
            "company_profile", "team", "customer_evidence", "risks", "facts", "sources",
        ],
        "condition": "always",
    },
    {
        "domain": "market_timing_risk",
        "label": "Market Timing Analyst",
        "focus": (
            "Hype-cycle timing, adoption readiness, macro pressure, procurement timing, "
            "and whether the startup is too early, too late, or selling into a frozen budget."
        ),
        "affects_dimensions": ["market_timing", "social_proof_demand"],
        "research_keys": [
            "market_data", "trends", "customer_evidence", "competitor_details", "facts",
        ],
        "condition": "always",
    },
    {
        "domain": "team_risk",
        "label": "Team Risk Assessor",
        "focus": (
            "Founder-market fit gaps, missing functions, key-person risk, prior execution proof, "
            "board quality, and whether the team profile matches the ambition."
        ),
        "affects_dimensions": ["team_execution_signals", "pattern_match"],
        "research_keys": [
            "company_profile", "team", "board_members", "deal_history",
            "founder_inputs", "facts", "sources",
        ],
        "condition": "always",
    },
    {
        "domain": "customer_concentration_risk",
        "label": "Customer Concentration Auditor",
        "focus": (
            "Revenue concentration, reference-customer fragility, churn shock risk, and whether "
            "a small number of pilots or logos are doing too much analytical work."
        ),
        "affects_dimensions": ["social_proof_demand", "business_model_viability"],
        "research_keys": [
            "company_profile", "traction_breakdown", "customer_evidence",
            "pricing_analysis", "facts", "sources",
        ],
        "condition": "commercial",
    },
    {
        "domain": "legal_corporate_risk",
        "label": "Legal/Corporate Risk",
        "focus": (
            "Corporate/legal hygiene, data privacy exposure, litigation risk, fundraising structure, "
            "and legal blockers beyond product regulation."
        ),
        "affects_dimensions": ["regulatory_news_environment", "capital_efficiency"],
        "research_keys": [
            "company_profile", "deal_history", "board_members", "regulatory",
            "sources", "facts",
        ],
        "condition": "legal",
    },
]


@dataclass
class RiskFinding:
    domain: str
    label: str
    status: str
    severity: str
    confidence: float
    summary: str
    evidence: List[str] = field(default_factory=list)
    mitigation: str = ""
    affects_dimensions: List[str] = field(default_factory=list)
    model_used: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain,
            "label": self.label,
            "status": self.status,
            "severity": self.severity,
            "confidence": round(max(0.0, min(1.0, float(self.confidence))), 2),
            "summary": self.summary,
            "evidence": self.evidence,
            "mitigation": self.mitigation,
            "affects_dimensions": self.affects_dimensions,
            "model_used": self.model_used,
        }


@dataclass
class RiskPanelResult:
    findings: List[RiskFinding]
    execution_time_seconds: float
    domains_run: int
    risk_found_count: int
    insufficient_evidence_count: int
    high_severity_count: int
    medium_severity_count: int
    low_severity_count: int
    overall_penalty: float
    dimension_penalties: Dict[str, float]
    summary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "findings": [finding.to_dict() for finding in self.findings],
            "execution_time_seconds": round(self.execution_time_seconds, 2),
            "domains_run": self.domains_run,
            "risk_found_count": self.risk_found_count,
            "insufficient_evidence_count": self.insufficient_evidence_count,
            "high_severity_count": self.high_severity_count,
            "medium_severity_count": self.medium_severity_count,
            "low_severity_count": self.low_severity_count,
            "overall_penalty": round(self.overall_penalty, 2),
            "dimension_penalties": self.dimension_penalties,
            "summary": self.summary,
        }


def _coerce_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return {}


def _coerce_int(value: Any) -> int:
    try:
        if value in (None, ""):
            return 0
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _truthy_string(value: Any) -> bool:
    return str(value or "").strip().lower() in {"yes", "true", "1", "y"}


def _nonempty_subset(payload: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
    subset: Dict[str, Any] = {}
    for key in keys:
        value = payload.get(key)
        if value not in (None, "", [], {}):
            subset[key] = value
    return subset


def _has_commercial_signal(extraction: Dict[str, Any], research: Dict[str, Any]) -> bool:
    if _truthy_string(extraction.get("has_customers")) or _truthy_string(extraction.get("generating_revenue")):
        return True
    if _coerce_int(extraction.get("paid_customer_count")) > 0 or _coerce_int(extraction.get("active_customer_count")) > 0:
        return True
    if _coerce_int(extraction.get("pilot_count")) > 0 or _coerce_int(extraction.get("loi_count")) > 0:
        return True
    customer_evidence = research.get("customer_evidence")
    return isinstance(customer_evidence, list) and len(customer_evidence) > 0


def _needs_legal_review(extraction: Dict[str, Any], research: Dict[str, Any]) -> bool:
    regulatory = research.get("regulatory") or []
    deal_history = research.get("deal_history") or []
    extra_context = " ".join([
        str(extraction.get("primary_risk_category", "")),
        str(extraction.get("risk", "")),
        str(extraction.get("industry", "")),
        str(extraction.get("business_model", "")),
        str(extraction.get("target_market", "")),
    ]).lower()
    legal_markers = ("privacy", "gdpr", "ccpa", "hipaa", "financial", "insurance", "government", "regulated")
    return bool(regulatory) or bool(deal_history) or any(marker in extra_context for marker in legal_markers)


def _should_run(spec: Dict[str, Any], extraction: Dict[str, Any], research: Dict[str, Any]) -> bool:
    condition = spec.get("condition", "always")
    if condition == "always":
        return True
    if condition == "commercial":
        return _has_commercial_signal(extraction, research)
    if condition == "legal":
        return _needs_legal_review(extraction, research)
    return True


def _prediction_snapshot(prediction: Dict[str, Any]) -> Dict[str, Any]:
    dims = prediction.get("dimensions", [])
    contested = prediction.get("contested_dimensions", [])
    return {
        "verdict": prediction.get("verdict"),
        "confidence": prediction.get("confidence"),
        "overall_score": prediction.get("overall_score", prediction.get("composite_score")),
        "contested_dimensions": contested if isinstance(contested, list) else [],
        "dimensions": dims if isinstance(dims, list) else [],
        "reasoning": prediction.get("reasoning", ""),
    }


def _swarm_snapshot(swarm: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "verdict": swarm.get("verdict"),
        "positive_pct": swarm.get("positive_pct"),
        "negative_pct": swarm.get("negative_pct"),
        "avg_confidence": swarm.get("avg_confidence"),
        "avg_scores": swarm.get("avg_scores", {}),
        "contested_themes": swarm.get("contested_themes", []),
        "key_themes_negative": swarm.get("key_themes_negative", []),
        "top_fixes": swarm.get("top_fixes", []),
        "divergence": swarm.get("divergence", {}),
    }


def _status_rank(status: str) -> int:
    order = {
        "risk_found": 0,
        "insufficient_evidence": 1,
        "no_material_risk_found": 2,
    }
    return order.get(status, 9)


def _severity_rank(severity: str) -> int:
    order = {"high": 0, "medium": 1, "low": 2}
    return order.get(severity, 9)


def _normalize_status(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"risk_found", "risk", "found"}:
        return "risk_found"
    if normalized in {"no_material_risk_found", "no_risk", "no risk", "clear"}:
        return "no_material_risk_found"
    if normalized in {"insufficient_evidence", "unknown", "unclear", "needs_more_evidence"}:
        return "insufficient_evidence"
    return "insufficient_evidence"


def _normalize_severity(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"high", "medium", "low"}:
        return normalized
    return "medium"


def _clean_evidence(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    cleaned: List[str] = []
    for entry in value:
        text = str(entry or "").strip()
        if text and text not in cleaned:
            cleaned.append(text)
    return cleaned[:5]


class RiskPanel:
    """Run a fixed set of domain-specific risk checks after swarm."""

    def __init__(self):
        models = Config.get_swarm_models() or Config.get_council_models()
        if not models:
            models = [{"model": Config.LLM_MODEL_NAME, "label": "Default"}]
        self._models = models

    def run(
        self,
        *,
        exec_summary: str,
        extraction: Dict[str, Any],
        research: Dict[str, Any],
        prediction: Dict[str, Any],
        swarm: Optional[Dict[str, Any]] = None,
    ) -> RiskPanelResult:
        started_at = time.time()
        extraction_dict = _coerce_dict(extraction)
        research_dict = _coerce_dict(research)
        prediction_dict = _coerce_dict(prediction)
        swarm_dict = _coerce_dict(swarm)

        scheduled_specs = [
            spec for spec in _RISK_PANEL_SPECS
            if _should_run(spec, extraction_dict, research_dict)
        ]
        findings: List[RiskFinding] = []

        with ThreadPoolExecutor(max_workers=min(_MAX_WORKERS, len(scheduled_specs) or 1)) as pool:
            futures = {
                pool.submit(
                    self._run_domain,
                    index,
                    spec,
                    exec_summary,
                    extraction_dict,
                    research_dict,
                    prediction_dict,
                    swarm_dict,
                ): spec
                for index, spec in enumerate(scheduled_specs)
            }
            for future in as_completed(futures):
                findings.append(future.result())

        findings.sort(
            key=lambda finding: (
                _status_rank(finding.status),
                _severity_rank(finding.severity),
                -(finding.confidence or 0.0),
                finding.label,
            )
        )

        dimension_penalties: Dict[str, float] = {}
        overall_penalty = 0.0
        risk_found_count = 0
        insufficient_evidence_count = 0
        high_severity_count = 0
        medium_severity_count = 0
        low_severity_count = 0

        for finding in findings:
            if finding.status == "insufficient_evidence":
                insufficient_evidence_count += 1
                continue
            if finding.status != "risk_found":
                continue

            risk_found_count += 1
            if finding.severity == "high":
                high_severity_count += 1
            elif finding.severity == "medium":
                medium_severity_count += 1
            else:
                low_severity_count += 1

            base_penalty = _SEVERITY_WEIGHTS.get(finding.severity, 0.12)
            weighted_penalty = base_penalty * max(0.35, min(1.0, finding.confidence or 0.0))
            overall_penalty += weighted_penalty
            affected = finding.affects_dimensions or []
            if not affected:
                continue
            per_dimension = weighted_penalty / len(affected)
            for dimension in affected:
                dimension_penalties[dimension] = dimension_penalties.get(dimension, 0.0) + per_dimension

        overall_penalty = min(_MAX_OVERALL_PENALTY, overall_penalty)
        dimension_penalties = {
            key: round(min(0.6, value), 2)
            for key, value in sorted(dimension_penalties.items())
            if value > 0
        }

        summary_bits: List[str] = []
        if high_severity_count:
            summary_bits.append(f"{high_severity_count} high-severity")
        if medium_severity_count:
            summary_bits.append(f"{medium_severity_count} medium-severity")
        if low_severity_count:
            summary_bits.append(f"{low_severity_count} low-severity")
        if insufficient_evidence_count:
            summary_bits.append(f"{insufficient_evidence_count} evidence gaps")
        summary = ", ".join(summary_bits) if summary_bits else "No material risks flagged."

        return RiskPanelResult(
            findings=findings,
            execution_time_seconds=time.time() - started_at,
            domains_run=len(findings),
            risk_found_count=risk_found_count,
            insufficient_evidence_count=insufficient_evidence_count,
            high_severity_count=high_severity_count,
            medium_severity_count=medium_severity_count,
            low_severity_count=low_severity_count,
            overall_penalty=overall_penalty,
            dimension_penalties=dimension_penalties,
            summary=summary,
        )

    def _run_domain(
        self,
        index: int,
        spec: Dict[str, Any],
        exec_summary: str,
        extraction: Dict[str, Any],
        research: Dict[str, Any],
        prediction: Dict[str, Any],
        swarm: Dict[str, Any],
    ) -> RiskFinding:
        model_cfg = self._models[index % len(self._models)]
        model_name = model_cfg.get("model", Config.LLM_MODEL_NAME)
        client = LLMClient(model=model_name)

        packet = {
            "startup": {
                "company": extraction.get("company"),
                "industry": extraction.get("industry"),
                "product": extraction.get("product"),
                "target_market": extraction.get("target_market"),
                "business_model": extraction.get("business_model"),
                "stage": extraction.get("stage"),
                "economic_buyer": extraction.get("economic_buyer"),
                "end_user": extraction.get("end_user"),
                "switching_trigger": extraction.get("switching_trigger"),
                "current_substitute": extraction.get("current_substitute"),
                "traction": extraction.get("traction"),
                "primary_risk_category": extraction.get("primary_risk_category"),
                "founder_problem_fit": extraction.get("founder_problem_fit"),
                "technical_founder": extraction.get("technical_founder"),
                "funding": extraction.get("funding"),
                "known_competitors": extraction.get("known_competitors"),
            },
            "research": _nonempty_subset(research, spec.get("research_keys", [])),
            "research_quality": _nonempty_subset(
                research.get("research_quality", {}) if isinstance(research.get("research_quality"), dict) else {},
                ["overall_score", "low_coverage_dimensions", "missing_evidence_flags", "freshness_score", "source_quality_score"],
            ),
            "council": _prediction_snapshot(prediction),
            "swarm": _swarm_snapshot(swarm),
            "executive_summary": exec_summary,
        }

        prompt = (
            f"You are the {spec['label']} on a venture risk panel.\n"
            f"Your only job is to evaluate the domain '{spec['domain']}'.\n"
            f"Domain focus: {spec['focus']}\n\n"
            "Use ONLY the provided packet. Do not invent missing facts. If the packet does not support a clear call, "
            "set status='insufficient_evidence'.\n\n"
            "Return JSON only with this schema:\n"
            "{\n"
            '  "status": "risk_found | no_material_risk_found | insufficient_evidence",\n'
            '  "severity": "high | medium | low",\n'
            '  "confidence": 0.0,\n'
            '  "summary": "1-2 sentence decision",\n'
            '  "evidence": ["specific evidence from the packet"],\n'
            '  "mitigation": "single most important mitigation or next diligence step",\n'
            '  "affects_dimensions": ["dimension_name"]\n'
            "}\n\n"
            "Guidance:\n"
            "- Use 'risk_found' only when the evidence points to a concrete issue.\n"
            "- Use 'no_material_risk_found' when the packet supports a reasonably clean read for this domain.\n"
            "- Use 'insufficient_evidence' when the packet is thin, stale, or inconclusive.\n"
            "- If status='risk_found', severity must reflect business impact, not drama.\n"
            "- Keep evidence factual and specific.\n\n"
            f"Packet:\n{json.dumps(packet, indent=2, default=str)}"
        )

        try:
            response = client.chat_json(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a disciplined due-diligence reviewer. "
                            "Be specific, evidence-driven, and conservative."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=1200,
            )
            finding = RiskFinding(
                domain=spec["domain"],
                label=spec["label"],
                status=_normalize_status(response.get("status")),
                severity=_normalize_severity(response.get("severity")),
                confidence=float(response.get("confidence", 0.0) or 0.0),
                summary=str(response.get("summary", "") or "").strip(),
                evidence=_clean_evidence(response.get("evidence")),
                mitigation=str(response.get("mitigation", "") or "").strip(),
                affects_dimensions=[
                    dim for dim in response.get("affects_dimensions", spec.get("affects_dimensions", []))
                    if isinstance(dim, str) and dim
                ] or list(spec.get("affects_dimensions", [])),
                model_used=model_name,
            )
            if not finding.summary:
                finding.summary = "No summary returned."
            if not finding.mitigation:
                finding.mitigation = "Collect stronger domain-specific evidence and re-run diligence."
            return finding
        except Exception as exc:
            logger.warning(f"[RiskPanel] {spec['label']} failed (non-fatal): {exc}")
            return RiskFinding(
                domain=spec["domain"],
                label=spec["label"],
                status="insufficient_evidence",
                severity="medium",
                confidence=0.0,
                summary=f"{spec['label']} could not complete a reliable assessment.",
                evidence=["Risk panel execution failed before a clean domain call was possible."],
                mitigation="Re-run this domain check after stabilizing the model or supplying clearer evidence.",
                affects_dimensions=list(spec.get("affects_dimensions", [])),
                model_used=model_name,
            )
