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
            ("Executive Summary", 300, "Write a concise executive summary covering the company, verdict, key strengths and weaknesses. Lead with the verdict and score."),
            ("Market Analysis", 500, "Analyze the target market: TAM, growth trends, regulatory landscape, timing. Cite specific data. If no market size data, say so."),
            ("Competitive Landscape", 400, "Name each competitor, describe their position, explain where this startup fits. What's defensible?"),
            ("Risk Assessment", 400, "Detail top 3-5 risks. For each: the risk, why it matters, severity (High/Medium/Low), specific mitigation."),
            ("Strategic Recommendations", 400, "5 specific actionable recommendations with effort, impact, and timeline per move. Prioritize by urgency."),
            ("Investment Verdict", 300, "Final investment thesis or anti-thesis. Should someone invest? At what terms? What milestones would change the verdict?"),
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

        comps = research.get('competitors', [])
        if comps:
            lines.append("\nCOMPETITORS: " + ', '.join(str(c) for c in comps[:8]))

        summary = research.get('summary', '')
        if summary:
            lines.append(f"\nRESEARCH: {summary[:800]}")

        for fact in research.get('context_facts', [])[:5]:
            lines.append(f"  FACT: {str(fact)[:200]}")

        risks = plan.get('risks', [])
        if risks:
            lines.append("\nRISKS:")
            for r in risks[:5]:
                lines.append(f"  - {str(r.get('risk', r) if isinstance(r, dict) else r)[:200]}")

        moves = plan.get('next_moves', plan.get('moves', []))
        if moves:
            lines.append("\nMOVES:")
            for m in moves[:5]:
                lines.append(f"  - {str(m.get('move', m.get('action', m)) if isinstance(m, dict) else m)[:200]}")

        agents = swarm.get('sample_agents', [])
        if agents:
            miss = [a for a in agents if float(a.get('overall', 0)) < 5.5]
            hit = [a for a in agents if float(a.get('overall', 0)) >= 5.5]
            if miss:
                lines.append(f"\nTOP MISS REASONS ({len(miss)} agents):")
                for a in miss[:5]:
                    lines.append(f"  - {str(a.get('reasoning',''))[:150]}")
            if hit:
                lines.append(f"\nTOP HIT REASONS ({len(hit)} agents):")
                for a in hit[:5]:
                    lines.append(f"  - {str(a.get('reasoning',''))[:150]}")

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
