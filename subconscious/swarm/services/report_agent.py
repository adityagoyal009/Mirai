"""
ReACT Report Agent — generates PitchBook-quality report sections using LLM reasoning.

Each section is a separate LLM call for quality and specificity.
Anti-hallucination: only cites actual research data.
"""

import json
from typing import Dict, Any, List, Optional

from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger

logger = get_logger('mirofish.report_agent')


# Stub classes for backward compatibility with MiroFish report API
class ReportStatus:
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportManager:
    @staticmethod
    def get_report_by_simulation(sim_id):
        return None

    @staticmethod
    def save_report(report):
        pass


class ReportAgent:
    """Generates professional report sections using ReACT-style LLM calls."""

    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or LLMClient()

    def generate_report(self, analysis: Dict[str, Any]) -> Dict[str, str]:
        """Generate all report sections. Returns {section_title: content}."""
        company = analysis.get('extraction', {}).get('company', 'this startup')
        industry = analysis.get('extraction', {}).get('industry', '')
        prediction = analysis.get('prediction', {})
        research = analysis.get('research', {})
        swarm = analysis.get('swarm', {})
        plan = analysis.get('plan', {})

        data_context = self._build_data_context(analysis)
        sections = {}

        configs = [
            ("Executive Summary", 375, "Write a concise executive summary covering the company, verdict, key strengths and weaknesses. Lead with the verdict and score."),
            ("Market Analysis", 650, "Analyze the target market: TAM, growth trends, regulatory landscape, timing. Cite specific data. If no market size data, say so."),
            ("Competitive Landscape", 550, "Name each competitor, describe their position, explain where this startup fits. What's defensible?"),
            ("Risk Assessment", 525, "Detail top 3-5 risks. For each: the risk, why it matters, severity (High/Medium/Low), specific mitigation."),
            ("Strategic Recommendations", 500, "5 specific actionable recommendations with effort, impact, and timeline per move. Prioritize by urgency."),
            ("Investment Verdict", 375, "Final investment thesis or anti-thesis. Should someone invest? At what terms? What milestones would change the verdict?"),
        ]

        # Generate all 6 sections in parallel (no inter-dependencies)
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = {
                pool.submit(self._generate_section, company, title, instruction, data_context, words): title
                for title, words, instruction in configs
            }
            for f in as_completed(futures):
                title = futures[f]
                try:
                    content = f.result()
                    sections[title] = content
                    logger.info(f"[ReportAgent] Generated '{title}': {len(content)} chars")
                except Exception as e:
                    # RA-1 FIX: Use a visible placeholder instead of empty string.
                    # Empty string looks like "no content" vs a clear generation failure.
                    logger.warning(f"[ReportAgent] Failed '{title}': {e}")
                    sections[title] = f"[Section generation failed: {type(e).__name__}: {e}]"

        return sections

    def _build_data_context(self, analysis: Dict) -> str:
        prediction = analysis.get('prediction', {})
        research = analysis.get('research', {})
        swarm = analysis.get('swarm', {})
        plan = analysis.get('plan', {})
        extraction = analysis.get('extraction', {})
        oasis = analysis.get('oasis', {})
        risk_panel = analysis.get('risk_panel', {})
        founder_narrative = analysis.get('exec_summary', '')
        risk_panel = analysis.get('risk_panel', {})

        lines = [
            f"COMPANY: {extraction.get('company', '?')}",
            f"INDUSTRY: {extraction.get('industry', '?')}",
            f"PRODUCT: {extraction.get('product', '?')}",
            f"TARGET MARKET: {extraction.get('target_market', '?')}",
            f"BUSINESS MODEL: {extraction.get('business_model', '?')}",
            f"STAGE: {extraction.get('stage', '?')}",
            f"TRACTION: {extraction.get('traction', '?')}",
            f"VERDICT: {prediction.get('verdict', '?')} ({prediction.get('composite_score', prediction.get('overall_score', '?'))}/10)",
            f"CONFIDENCE: {prediction.get('confidence', '?')}",
            f"SWARM: {swarm.get('positive_pct', swarm.get('positivePct', '?'))}% positive, {swarm.get('total_agents', swarm.get('totalAgents', '?'))} agents",
            "",
            "DIMENSIONS:",
        ]
        for d in prediction.get('dimensions', []):
            if isinstance(d, dict):
                lines.append(f"  {d.get('name','?')}: {d.get('score','?')}/10")

        risk_adjusted_dimensions = prediction.get('risk_adjusted_dimensions', [])
        if risk_adjusted_dimensions:
            lines.append("\nRISK-ADJUSTED DIMENSIONS:")
            for d in risk_adjusted_dimensions:
                if isinstance(d, dict):
                    lines.append(
                        f"  {d.get('name','?')}: raw={d.get('score','?')}/10, "
                        f"penalty={d.get('risk_penalty', 0)}, adjusted={d.get('risk_adjusted_score','?')}/10"
                    )

        lines.extend([
            "",
            "VERDICT CONSTRUCTION:",
            f"  Council score: {prediction.get('council_score', prediction.get('overall_score', '?'))}",
            f"  Swarm score: {prediction.get('swarm_score', '?')}",
            f"  Risk panel penalty: {prediction.get('risk_panel_penalty', 0)}",
            f"  OASIS trajectory: {oasis.get('trajectory', 'unavailable') if isinstance(oasis, dict) else 'unavailable'}",
            f"  Final score: {prediction.get('composite_score', prediction.get('overall_score', '?'))}",
        ])

        if isinstance(risk_panel, dict) and risk_panel.get('summary'):
            lines.append(f"  Risk panel summary: {str(risk_panel.get('summary', ''))}")

        if isinstance(oasis, dict):
            timeline = oasis.get('timeline', [])
            if isinstance(timeline, list) and timeline:
                lines.append(f"  OASIS months simulated: {len(timeline)}")
                for item in timeline:
                    if isinstance(item, dict):
                        lines.append(
                            f"  OASIS: Month {item.get('month', '?')} - "
                            f"{str(item.get('event', ''))}"
                        )

        if founder_narrative:
            lines.append(f"\nFOUNDER NARRATIVE:\n{str(founder_narrative)}")

        comps = research.get('competitors', [])
        if comps:
            lines.append("\nCOMPETITORS: " + ', '.join(str(c) for c in comps))

        market_data = research.get('market_data', {})
        if isinstance(market_data, dict) and market_data:
            lines.append(
                "\nMARKET DATA: "
                + "; ".join(
                    f"{k.upper()}: {v}" for k, v in market_data.items() if v
                )
            )

        pricing_analysis = research.get('pricing_analysis', {})
        if isinstance(pricing_analysis, dict) and pricing_analysis:
            lines.append(
                "\nPRICING ANALYSIS: "
                + "; ".join(
                    f"{k.replace('_', ' ').title()}: {v}"
                    for k, v in pricing_analysis.items() if v
                )
            )

        summary = research.get('summary', '')
        if summary:
            lines.append(f"\nRESEARCH: {summary}")

        for fact in research.get('context_facts', []):
            lines.append(f"  FACT: {str(fact)}")

        risks = plan.get('risks', [])
        if risks:
            lines.append("\nRISKS:")
            for r in risks:
                lines.append(f"  - {str(r.get('risk', r) if isinstance(r, dict) else r)}")

        moves = plan.get('next_moves', plan.get('moves', []))
        if moves:
            lines.append("\nMOVES:")
            for m in moves:
                lines.append(f"  - {str(m.get('move', m.get('action', m)) if isinstance(m, dict) else m)}")

        panel_findings = risk_panel.get('findings', []) if isinstance(risk_panel, dict) else []
        if panel_findings:
            lines.append("\nDETERMINISTIC RISK PANEL:")
            for finding in panel_findings:
                if isinstance(finding, dict):
                    evidence = finding.get('evidence', []) if isinstance(finding.get('evidence', []), list) else []
                    evidence_preview = "; ".join(str(item) for item in evidence)
                    lines.append(
                        f"  - {finding.get('label', finding.get('domain', 'risk'))}: "
                        f"{finding.get('status', '')} / {finding.get('severity', '')}. "
                        f"{str(finding.get('summary', ''))}"
                    )
                    if evidence_preview:
                        lines.append(f"    evidence: {evidence_preview}")

        agents = swarm.get('sample_agents', [])
        if agents:
            miss = [a for a in agents if float(a.get('overall', 0)) < 5.5]
            hit = [a for a in agents if float(a.get('overall', 0)) >= 5.5]
            if miss:
                lines.append(f"\nTOP MISS REASONS ({len(miss)} agents):")
                for a in miss[:6]:
                    lines.append(f"  - {str(a.get('reasoning',''))}")
            if hit:
                lines.append(f"\nTOP HIT REASONS ({len(hit)} agents):")
                for a in hit[:6]:
                    lines.append(f"  - {str(a.get('reasoning',''))}")

        return "\n".join(lines)

    def _generate_section(self, company, title, instruction, data_context, word_count):
        prompt = (
            f"Write the \"{title}\" section of a professional investment analysis report for {company}.\n\n"
            f"AVAILABLE DATA (use ONLY these facts):\n{data_context}\n\n"
            f"INSTRUCTIONS: {instruction}\n\n"
            f"RULES:\n"
            f"- ~{word_count} words. Professional analyst tone.\n"
            f"- Use ONLY facts from AVAILABLE DATA. Do NOT invent statistics.\n"
            f"- If data unavailable, say so. Do NOT fabricate.\n"
            f"- Name competitors. Cite specific numbers.\n"
            f"- Be specific to {company}, not generic advice.\n"
            f"- No markdown formatting (no **, no ##, no bullet lists). Plain flowing prose only.\n\n"
            f"Write the \"{title}\" section:"
        )
        messages = [{"role": "user", "content": prompt}]
        return (self.llm.chat(messages, max_tokens=word_count * 3) or "").strip()
