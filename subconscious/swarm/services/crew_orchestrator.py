"""
CrewAI Multi-Agent Orchestrator — parallel role-based analysis.

Spawns specialized sub-agents (Market Researcher, Competitor Analyst,
Strategy Consultant) that work in parallel on different aspects of
business analysis, then synthesizes their findings.

Used in deep BI analysis mode to get more thorough, multi-perspective
analysis instead of running everything sequentially through one LLM call.

Usage:
    crew = CrewOrchestrator()
    result = crew.analyze_business(company="LegalLens AI", industry="legaltech", ...)
"""

import os
from typing import Dict, Any, Optional

from ..utils.logger import get_logger

logger = get_logger('mirofish.crew')


class CrewOrchestrator:
    """
    CrewAI-based multi-agent orchestration for BI analysis.
    Falls back to single-agent mode if CrewAI is not available.
    """

    def __init__(self):
        self._available = None
        self._crewai = None

    def _ensure_crewai(self) -> bool:
        """Lazy-initialize CrewAI."""
        if self._available is not None:
            return self._available

        try:
            import crewai
            self._crewai = crewai
            self._available = True
            logger.info("[CrewAI] Available for multi-agent orchestration")
        except ImportError:
            self._available = False
            logger.warning("[CrewAI] Not installed. Run: pip install crewai")

        return self._available

    def is_available(self) -> bool:
        """Check if CrewAI is available."""
        return self._ensure_crewai()

    def _create_llm(self):
        """Create LLM instance for CrewAI agents."""
        from crewai import LLM
        return LLM(
            model=os.environ.get("LLM_MODEL_NAME", "claude-opus-4-6"),
            base_url=os.environ.get("LLM_BASE_URL", "http://localhost:4000/v1"),
            api_key=os.environ.get("LLM_API_KEY", ""),
        )

    def analyze_business(
        self,
        company: str,
        industry: str,
        product: str,
        target_market: str = "",
        business_model: str = "",
        exec_summary: str = "",
        context: str = "",
    ) -> Dict[str, Any]:
        """
        Run a multi-agent business analysis crew.

        Creates three agents:
        1. Market Researcher — market size, trends, demand signals
        2. Competitor Analyst — competitive landscape, moats, threats
        3. Strategy Consultant — risks, opportunities, action plan

        Returns combined findings from all agents.
        """
        if not self._ensure_crewai():
            return {
                "success": False,
                "error": "CrewAI not available",
                "fallback": "Use single-agent analysis",
            }

        try:
            from crewai import Agent, Task, Crew, Process

            llm = self._create_llm()

            # ── Define Agents ──────────────────────────────────────
            researcher = Agent(
                role="Market Researcher",
                goal=(
                    f"Research the {industry} market thoroughly. Find market size, "
                    f"growth trends, key players, and demand signals for {product}."
                ),
                backstory=(
                    "You are a seasoned market research analyst with 15 years of "
                    "experience across tech verticals. You specialize in identifying "
                    "emerging trends and sizing markets accurately."
                ),
                llm=llm,
                verbose=False,
                allow_delegation=False,
            )

            competitor_analyst = Agent(
                role="Competitor Analyst",
                goal=(
                    f"Analyze the competitive landscape for {company} in {industry}. "
                    f"Identify direct competitors, indirect alternatives, and assess moats."
                ),
                backstory=(
                    "You are a competitive intelligence specialist who has evaluated "
                    "thousands of startups. You can quickly identify competitive "
                    "threats, moats, and market positioning gaps."
                ),
                llm=llm,
                verbose=False,
                allow_delegation=False,
            )

            strategist = Agent(
                role="Strategy Consultant",
                goal=(
                    f"Create a strategic assessment for {company}. "
                    f"Identify top risks, highest-impact next moves, and a go-to-market plan."
                ),
                backstory=(
                    "You are a former McKinsey partner who now advises AI startups. "
                    "You combine analytical rigor with practical startup experience "
                    "to create actionable strategies."
                ),
                llm=llm,
                verbose=False,
                allow_delegation=False,
            )

            # ── Define Tasks ───────────────────────────────────────
            business_context = (
                f"Company: {company}\n"
                f"Industry: {industry}\n"
                f"Product: {product}\n"
                f"Target Market: {target_market}\n"
                f"Business Model: {business_model}\n"
                f"Executive Summary: {exec_summary}\n"
            )
            if context:
                business_context += f"\nAdditional Context:\n{context}\n"

            research_task = Task(
                description=(
                    f"Research the market for this business:\n\n{business_context}\n\n"
                    "Provide:\n"
                    "1. Estimated total addressable market (TAM) and growth rate\n"
                    "2. Key market trends (at least 3)\n"
                    "3. Demand signals — is the market pulling for this?\n"
                    "4. Regulatory environment — tailwinds or headwinds?\n"
                    "5. Recent relevant news or developments"
                ),
                expected_output=(
                    "A structured market research report with TAM estimate, "
                    "growth trends, demand signals, regulatory assessment, "
                    "and recent developments."
                ),
                agent=researcher,
            )

            competitor_task = Task(
                description=(
                    f"Analyze competitors for this business:\n\n{business_context}\n\n"
                    "Provide:\n"
                    "1. Top 5 direct competitors (name, what they do, how they differ)\n"
                    "2. Indirect alternatives or substitutes\n"
                    "3. Competitive moats or advantages this company might have\n"
                    "4. Key competitive threats\n"
                    "5. Market positioning assessment"
                ),
                expected_output=(
                    "A structured competitive analysis with named competitors, "
                    "their strengths/weaknesses, moat assessment, and positioning."
                ),
                agent=competitor_analyst,
            )

            strategy_task = Task(
                description=(
                    f"Create a strategic assessment for this business:\n\n{business_context}\n\n"
                    "Using the market research and competitive analysis, provide:\n"
                    "1. Top 3 risks (with severity and mitigation)\n"
                    "2. Top 5 next moves (prioritized by impact)\n"
                    "3. Go-to-market recommendations\n"
                    "4. Cheapest validation experiments\n"
                    "5. Overall verdict: Strong Hit, Likely Hit, Uncertain, Likely Miss, or Strong Miss"
                ),
                expected_output=(
                    "A strategic assessment with prioritized risks, action items, "
                    "GTM plan, validation experiments, and an overall verdict."
                ),
                agent=strategist,
                context=[research_task, competitor_task],
            )

            # ── Run Crew ───────────────────────────────────────────
            crew = Crew(
                agents=[researcher, competitor_analyst, strategist],
                tasks=[research_task, competitor_task, strategy_task],
                process=Process.sequential,  # Strategy needs research + competitor context
                verbose=False,
            )

            logger.info(
                f"[CrewAI] Starting multi-agent analysis for {company} ({industry})"
            )
            result = crew.kickoff()

            logger.info(f"[CrewAI] Analysis complete for {company}")

            return {
                "success": True,
                "crew_output": str(result),
                "task_outputs": {
                    "market_research": str(research_task.output) if research_task.output else "",
                    "competitor_analysis": str(competitor_task.output) if competitor_task.output else "",
                    "strategy": str(strategy_task.output) if strategy_task.output else "",
                },
            }

        except Exception as e:
            logger.error(f"[CrewAI] Analysis failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }
