"""
Swarm Predictor — spawns 50-1000 agents with variable personalities
to independently predict startup outcomes.

Hybrid execution:
  Wave 1: Up to 100 individual LLM calls with unique detailed personas
  Wave 2: Batch remaining agents (each call simulates 25 personas)

Calls distributed round-robin across all logged-in models.
"""

import json
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any

from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from ..config import Config
from .persona_engine import PersonaEngine, ZONE_EVAL_ANGLES

logger = get_logger('mirofish.swarm')

# ── Data classes ──────────────────────────────────────────────────


SCORE_DIMENSIONS = ["market", "team", "product", "timing", "overall"]


@dataclass
class SwarmAgent:
    agent_id: int
    persona: str
    scores: Dict[str, float]  # {market, team, product, timing, overall} each 1-10
    overall: float  # shortcut for scores["overall"]
    reasoning: str
    model_used: str
    zone: str = "wildcard"

    @property
    def vote(self) -> str:
        """Backward compat — positive if overall >= 5.5"""
        return "positive" if self.overall >= 5.5 else "negative"

    @property
    def confidence(self) -> float:
        """Backward compat — map distance from 5.0 to confidence"""
        return min(1.0, abs(self.overall - 5.0) / 5.0)


@dataclass
class SwarmResult:
    total_agents: int
    wave1_individual: int
    wave2_batched: int
    # Score-based metrics
    avg_scores: Dict[str, float]  # {market, team, product, timing, overall}
    median_overall: float
    std_overall: float
    score_distribution: Dict[str, int]  # {strong_hit, likely_hit, uncertain, likely_miss, strong_miss}
    # Backward-compat vote metrics
    positive_pct: float
    negative_pct: float
    avg_confidence: float
    # Themes
    key_themes_positive: List[str]
    key_themes_negative: List[str]
    contested_themes: List[str]
    # Meta
    agent_results: List[SwarmAgent]
    models_used: List[str]
    execution_time_seconds: float
    verdict: str  # "Strong Hit" / "Likely Hit" / "Uncertain" / "Likely Miss" / "Strong Miss"
    fact_check: Optional[Dict[str, Any]] = None
    divergence: Optional[Dict[str, Any]] = None
    deliberation: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_agents": self.total_agents,
            "wave1_individual": self.wave1_individual,
            "wave2_batched": self.wave2_batched,
            "verdict": self.verdict,
            "avg_scores": self.avg_scores,
            "median_overall": self.median_overall,
            "std_overall": self.std_overall,
            "score_distribution": self.score_distribution,
            "positive_pct": self.positive_pct,
            "negative_pct": self.negative_pct,
            "avg_confidence": self.avg_confidence,
            "key_themes_positive": self.key_themes_positive,
            "key_themes_negative": self.key_themes_negative,
            "contested_themes": self.contested_themes,
            "models_used": self.models_used,
            "execution_time_seconds": self.execution_time_seconds,
            "sample_agents": [
                {"persona": a.persona, "overall": a.overall,
                 "scores": a.scores, "reasoning": a.reasoning,
                 "zone": a.zone}
                for a in self.agent_results
            ],
            "fact_check": self.fact_check,
            "divergence": self.divergence,
            "deliberation": self.deliberation,
        }


# ── Persona pool (50+ archetypes) ────────────────────────────────

PERSONA_POOL = [
    # ── Investors ──
    {"name": "Skeptical Series-B VC", "bias": "critical",
     "prompt": "You are a Series-B venture capitalist who has seen 1000 pitches and funded 20. You are naturally skeptical and focus on unit economics, retention metrics, and defensibility. You've been burned by hype before."},
    {"name": "Enthusiastic Angel Investor", "bias": "positive",
     "prompt": "You are an angel investor who loves backing bold ideas early. You focus on the founder's vision, market size, and potential for disruption. You're willing to bet on incomplete data."},
    {"name": "Conservative PE Partner", "bias": "critical",
     "prompt": "You are a private equity partner who only invests in proven models. You care about cash flow, margins, and a clear path to profitability. High-growth narratives without revenue make you nervous."},
    {"name": "Growth-Stage VC", "bias": "neutral",
     "prompt": "You are a growth-stage VC who evaluates companies at Series C+. You focus on market share trajectory, competitive moats, and whether the company can become a category leader."},
    {"name": "Family Office Allocator", "bias": "cautious",
     "prompt": "You manage a family office portfolio. You prioritize capital preservation and steady returns. You need to see a clear risk-adjusted return thesis before committing."},
    {"name": "Impact Investor", "bias": "positive",
     "prompt": "You are an impact investor who evaluates both financial returns and social/environmental impact. You care about mission alignment and whether the company can scale its impact."},
    {"name": "Seed-Stage VC", "bias": "positive",
     "prompt": "You are a seed-stage VC betting on early conviction. You focus on team quality, market timing, and whether the insight is non-obvious. Revenue doesn't matter yet."},
    {"name": "Corporate VC", "bias": "neutral",
     "prompt": "You represent a corporate venture arm. You evaluate strategic fit with your parent company, potential for partnerships, and whether the technology could be acquired."},

    # ── Operators ──
    {"name": "Failed Startup Founder", "bias": "critical",
     "prompt": "You are a founder whose startup failed after raising $10M. You now see every pitch through the lens of what went wrong for you — team dynamics, premature scaling, market misjudgment."},
    {"name": "Successful Exit Founder", "bias": "neutral",
     "prompt": "You sold your last company for $200M. You evaluate based on pattern-matching: does this feel like a winner? You focus on founder-market fit, timing, and execution velocity."},
    {"name": "Startup CTO", "bias": "neutral",
     "prompt": "You are a CTO evaluating the technical feasibility. You focus on technical moat, engineering complexity, scalability challenges, and whether the tech claims are realistic."},
    {"name": "Startup CMO", "bias": "positive",
     "prompt": "You are a CMO evaluating go-to-market strategy. You focus on customer acquisition costs, channel strategy, brand positioning, and viral potential."},
    {"name": "Startup CFO", "bias": "critical",
     "prompt": "You are a CFO who scrutinizes financial models. You focus on burn rate, runway, unit economics, and whether the revenue projections are grounded in reality."},
    {"name": "Serial Entrepreneur", "bias": "neutral",
     "prompt": "You've built and sold 3 companies. You evaluate based on your gut feeling calibrated by experience. You look for signs of founder obsession, market pull, and timing luck."},

    # ── Market Perspectives ──
    {"name": "Target Enterprise Buyer", "bias": "pragmatic",
     "prompt": "You are a VP at a Fortune 500 company who would be the target buyer of this product. You evaluate based on: does it solve a real pain point, does it integrate with my stack, will my board approve the spend?"},
    {"name": "SMB Owner", "bias": "pragmatic",
     "prompt": "You own a small business with 50 employees. You evaluate tools based on immediate ROI, ease of use, and whether your team will actually adopt it. You hate complexity."},
    {"name": "Target Consumer", "bias": "positive",
     "prompt": "You are exactly the target end-user for this product. You evaluate based on whether it solves your daily frustration, if the UX is intuitive, and if you'd pay for it."},
    {"name": "Non-Target Consumer", "bias": "critical",
     "prompt": "You are not the target market but represent the mainstream. You evaluate whether this product has crossover appeal or if it's too niche to achieve scale."},
    {"name": "Enterprise IT Director", "bias": "cautious",
     "prompt": "You manage IT procurement for a large enterprise. You evaluate security compliance, vendor stability, integration complexity, and total cost of ownership."},

    # ── Industry Experts ──
    {"name": "Domain Expert (AI/ML)", "bias": "neutral",
     "prompt": "You are an AI researcher at a top lab. You evaluate whether the AI claims are technically sound, whether the moat is real or just a wrapper, and if the approach will age well."},
    {"name": "Domain Expert (FinTech)", "bias": "cautious",
     "prompt": "You are a fintech veteran with 15 years in banking tech. You evaluate regulatory risk, compliance burden, partnership requirements, and whether incumbents will copy this."},
    {"name": "Domain Expert (HealthTech)", "bias": "cautious",
     "prompt": "You are a healthtech expert. You evaluate FDA/regulatory pathway, clinical validation requirements, reimbursement strategy, and time to market in a heavily regulated industry."},
    {"name": "Academic Researcher", "bias": "neutral",
     "prompt": "You are a professor studying entrepreneurship. You evaluate based on academic frameworks: market size estimation, competitive advantage theory, and historical base rates for startups in this category."},
    {"name": "Industry Analyst", "bias": "neutral",
     "prompt": "You are a Gartner analyst covering this sector. You evaluate market maturity, category creation potential, and how this fits into the broader technology adoption lifecycle."},

    # ── Contrarians ──
    {"name": "Devil's Advocate", "bias": "critical",
     "prompt": "Your job is to find every possible reason this startup will fail. Challenge every assumption, highlight every risk, and stress-test the weakest parts of the business model."},
    {"name": "Eternal Optimist", "bias": "positive",
     "prompt": "You see the best in every idea. Focus on the upside potential, the best-case scenario, and what could go incredibly right if all the pieces fall into place."},
    {"name": "Cynical Realist", "bias": "critical",
     "prompt": "You've seen too many cycles. Most startups fail. You evaluate based on base rates, survivorship bias, and whether this is genuinely different or just the same pitch with new buzzwords."},
    {"name": "Contrarian Thinker", "bias": "neutral",
     "prompt": "You specifically look for ideas that the crowd is wrong about. If everyone thinks this will fail, you look for why it might succeed, and vice versa. Your edge is non-consensus thinking."},

    # ── External Stakeholders ──
    {"name": "Tech Journalist", "bias": "neutral",
     "prompt": "You cover startups for a major tech publication. You evaluate newsworthiness, narrative strength, founder story, and whether this would make a compelling cover story."},
    {"name": "Regulatory Expert", "bias": "cautious",
     "prompt": "You are a regulatory compliance attorney. You evaluate legal exposure, regulatory uncertainty, data privacy risks, and whether the business model could be undermined by future regulation."},
    {"name": "Market Strategist", "bias": "neutral",
     "prompt": "You are a strategy consultant at BCG. You evaluate competitive positioning, market entry strategy, value chain position, and whether the timing is right for this category."},
    {"name": "Supply Chain Expert", "bias": "pragmatic",
     "prompt": "You evaluate operational feasibility. Can they actually deliver at scale? What are the supply chain risks, manufacturing constraints, or delivery challenges?"},

    # ── Macro/Timing ──
    {"name": "Macro Economist", "bias": "neutral",
     "prompt": "You evaluate this startup in the context of macroeconomic conditions: interest rates, capital availability, consumer spending trends, and sector-level headwinds or tailwinds."},
    {"name": "Market Timer", "bias": "neutral",
     "prompt": "You focus purely on timing. Is the market ready for this? Are they too early, too late, or perfectly timed? You study technology adoption curves and market readiness signals."},
    {"name": "Emerging Markets Specialist", "bias": "positive",
     "prompt": "You focus on growth potential in emerging markets. You evaluate whether this solution has global applicability, localization potential, and untapped market opportunities."},

    # ── Technology ──
    {"name": "Platform Risk Analyst", "bias": "critical",
     "prompt": "You evaluate platform dependency risk. Is this startup built on top of someone else's platform (AWS, Apple, Google)? Could a platform change destroy the business overnight?"},
    {"name": "Open Source Advocate", "bias": "neutral",
     "prompt": "You evaluate from an open-source perspective. Could an open-source alternative emerge? Is the proprietary moat real? You've seen many commercial products disrupted by free alternatives."},
    {"name": "Cybersecurity Expert", "bias": "cautious",
     "prompt": "You evaluate security posture, attack surface, data handling practices, and whether a breach could be existential for this company. You focus on trust and safety."},

    # ── Behavioral ──
    {"name": "Behavioral Economist", "bias": "neutral",
     "prompt": "You study human decision-making biases. You evaluate whether the product leverages behavioral economics principles, whether adoption friction is low, and whether switching costs will retain users."},
    {"name": "UX Researcher", "bias": "neutral",
     "prompt": "You evaluate the product-market fit signal. Is there genuine user pull? Are the engagement patterns sustainable? You focus on usability, retention curves, and whether users truly need this."},
    {"name": "Brand Strategist", "bias": "positive",
     "prompt": "You evaluate brand potential, positioning clarity, and whether this company can build a lasting brand identity that commands premium pricing."},

    # ── Adversarial ──
    {"name": "Competitor CEO", "bias": "adversarial",
     "prompt": "You are the CEO of the largest competitor in this space. You evaluate whether this startup poses a real threat to your business. If so, how would you respond — copy, acquire, or crush?"},
    {"name": "Big Tech Product Manager", "bias": "critical",
     "prompt": "You are a PM at Google/Microsoft/Amazon evaluating whether to build this internally. How hard would it be? Is there a moat you can't replicate? Would this be a good tuck-in acquisition?"},
    {"name": "Patent Attorney", "bias": "neutral",
     "prompt": "You evaluate intellectual property strength. Are there defensible patents? Prior art risks? Could patent trolls or incumbents with large patent portfolios create problems?"},

    # ── Financial ──
    {"name": "Hedge Fund Analyst", "bias": "critical",
     "prompt": "You evaluate this as a potential short or long position. You focus on valuation relative to comparables, revenue multiples, and whether the growth story justifies the implied market cap."},
    {"name": "Investment Banker", "bias": "positive",
     "prompt": "You evaluate M&A potential. Who would acquire this company? At what multiple? You focus on strategic value to acquirers and comparable transaction data."},
    {"name": "Insurance Underwriter", "bias": "cautious",
     "prompt": "You evaluate risk from an insurance perspective. What could go catastrophically wrong? Product liability, E&O exposure, D&O risks? You price risk for a living."},
]

# ── Constants ─────────────────────────────────────────────────────

VALID_COUNTS = [10, 25, 50, 100, 250, 500, 1000]
WAVE1_MAX = 100
BATCH_SIZE = 25
# Max concurrent LLM calls — 25 parallel across 4 models = ~6 per model
WAVE1_WORKERS = 25
WAVE2_WORKERS = 10


class SwarmPredictor:
    """Spawns agents with variable personalities to predict startup outcomes."""

    def __init__(self):
        self._models = None
        self._tiered_models = None
        self._persona_engine = PersonaEngine()

    def _get_models(self) -> list:
        if self._models is None:
            self._models = Config.get_swarm_models()
            if not self._models:
                self._models = [{
                    'model': Config.LLM_MODEL_NAME,
                    'label': 'Default',
                    'base_url': Config.LLM_BASE_URL,
                    'api_key': Config.LLM_API_KEY,
                }]
        return self._models

    def _get_tiered_models(self) -> dict:
        if self._tiered_models is None:
            self._tiered_models = Config.get_tiered_models()
        return self._tiered_models

    def predict(self, exec_summary: str, research_context: str,
                agent_count: int = 100,
                on_agent_complete=None,
                on_agent_start=None,
                on_deliberation_start=None,
                industry: str = "",
                product: str = "") -> SwarmResult:
        """Run swarm prediction with hybrid wave execution.
        on_agent_complete: optional callback(SwarmAgent) fired for each completed agent.
        on_agent_start: optional callback(agent_id, persona_name) fired before each agent's LLM call.
        on_deliberation_start: optional callback() fired before deliberation round.
        industry: clean industry string from extraction (avoids regex parsing).
        product: clean product string from extraction."""
        start_time = time.time()

        if agent_count not in VALID_COUNTS:
            agent_count = min(VALID_COUNTS, key=lambda x: abs(x - agent_count))

        tiered = self._get_tiered_models()
        tier1_models = tiered.get('tier1', self._get_models())
        tier2_models = tiered.get('tier2', tiered.get('tier3', self._get_models()))
        wave1_count = min(agent_count, WAVE1_MAX)
        wave2_remaining = agent_count - wave1_count

        # Fall back to regex extraction if industry/product not provided
        if not industry:
            for line in exec_summary.split('\n'):
                if 'industry' in line.lower():
                    industry = line.split(':', 1)[-1].strip() if ':' in line else ""
                    break
        if not product:
            for line in exec_summary.split('\n'):
                if 'product' in line.lower():
                    product = line.split(':', 1)[-1].strip() if ':' in line else ""
                    break

        all_model_labels = [m['label'] for m in tier1_models] + [m['label'] for m in tier2_models]
        logger.info(f"[Swarm] Starting {agent_count} agents "
                    f"(wave1={wave1_count} via {len(tier1_models)} tier1, "
                    f"wave2={wave2_remaining} via {len(tier2_models)} tier2/3)")

        # Select zone-appropriate personas
        all_personas = self._persona_engine.select_personas_by_zone(
            count=wave1_count, industry=industry, product=product
        )
        wave1_personas = []
        for i, p in enumerate(all_personas):
            wave1_personas.append({
                "agent_id": i,
                "name": p.name,
                "prompt": p.prompt,
                "zone": p.zone,
            })

        all_agents: List[SwarmAgent] = []

        # ── Wave 1: Individual detailed calls ─────────────────────
        logger.info(f"[Swarm] Wave 1: {wave1_count} individual agent calls")
        with ThreadPoolExecutor(max_workers=min(WAVE1_WORKERS, wave1_count)) as pool:
            futures = []
            for i, persona in enumerate(wave1_personas):
                model_cfg = tier1_models[i % len(tier1_models)]
                if on_agent_start:
                    on_agent_start(persona['agent_id'], persona['name'], model_cfg['label'], persona.get('zone', 'wildcard'))
                futures.append(pool.submit(
                    self._run_individual, persona, exec_summary,
                    research_context, model_cfg
                ))
            for future in as_completed(futures):
                result = future.result()
                if result:
                    all_agents.append(result)
                    if on_agent_complete:
                        on_agent_complete(result)

        logger.info(f"[Swarm] Wave 1 complete: {len(all_agents)} agents responded")

        # Log all agent actions to JSONL
        try:
            import os, json
            from datetime import datetime
            log_dir = os.path.join(os.path.expanduser('~'), '.mirai', 'logs')
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, f"swarm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl")
            with open(log_file, 'w') as f:
                for a in all_agents:
                    f.write(json.dumps({
                        "agent_id": a.agent_id,
                        "persona": a.persona,
                        "zone": getattr(a, 'zone', 'unknown'),
                        "vote": a.vote,
                        "overall": a.overall,
                        "scores": a.scores,
                        "reasoning": a.reasoning,
                        "confidence": a.confidence,
                    }) + "\n")
            logger.info(f"[Swarm] Logged {len(all_agents)} agent actions to {log_file}")
        except Exception as e:
            logger.warning(f"[Swarm] Action logging failed: {e}")

        # ── Divergence + Deliberation (Wave 1 agents only) ─────────
        divergence = {}
        deliberation = {}
        if len(all_agents) >= 5:
            try:
                divergence = self._compute_divergence(all_agents)
            except Exception as e:
                logger.warning(f"[Swarm] Divergence computation failed (non-fatal): {e}")

            if divergence and not divergence.get('consensus', True) and len(divergence.get('critical_outliers', [])) >= 2:
                try:
                    if on_deliberation_start:
                        on_deliberation_start()
                    deliberation, all_agents = self._deliberate(
                        all_agents, divergence, exec_summary, tier1_models
                    )
                    logger.info(f"[Swarm] Deliberation complete: {len(deliberation.get('positions', []))} positions, "
                                f"{len(deliberation.get('adjusted_scores', {}))} adjustments")
                except Exception as e:
                    logger.warning(f"[Swarm] Deliberation failed (non-fatal): {e}")

        # ── Wave 2: Batched calls ─────────────────────────────────
        if wave2_remaining > 0:
            batch_count = (wave2_remaining + BATCH_SIZE - 1) // BATCH_SIZE
            logger.info(f"[Swarm] Wave 2: {wave2_remaining} agents in {batch_count} batches")
            with ThreadPoolExecutor(max_workers=min(WAVE2_WORKERS, batch_count)) as pool:
                futures = []
                remaining = wave2_remaining
                for i in range(batch_count):
                    batch_sz = min(BATCH_SIZE, remaining)
                    remaining -= batch_sz
                    model_cfg = tier2_models[i % len(tier2_models)]
                    futures.append(pool.submit(
                        self._run_batch, batch_sz, exec_summary,
                        research_context, model_cfg,
                        start_id=wave1_count + i * BATCH_SIZE
                    ))
                for future in as_completed(futures):
                    batch_results = future.result()
                    all_agents.extend(batch_results)
                    if on_agent_complete:
                        for agent in batch_results:
                            on_agent_complete(agent)

            logger.info(f"[Swarm] Wave 2 complete: {len(all_agents)} total agents")

        # ── Fact check ─────────────────────────────────────────────
        fact_check = None
        if all_agents:
            try:
                from .fact_checker import check_facts
                reasonings = [a.reasoning for a in all_agents if a.reasoning]
                fact_check = check_facts(reasonings, research_context)
            except Exception as e:
                logger.warning(f"[Swarm] Fact check failed (non-fatal): {e}")

        elapsed = time.time() - start_time
        result = self._aggregate(all_agents, wave1_count, wave2_remaining, elapsed, tier1_models + tier2_models)
        if fact_check:
            result.fact_check = fact_check
        if divergence:
            result.divergence = divergence
        if deliberation:
            result.deliberation = deliberation
        return result

    def _run_individual(self, persona: dict, exec_summary: str,
                        research_context: str, model_cfg: dict) -> Optional[SwarmAgent]:
        try:
            llm = LLMClient(
                model=model_cfg['model'],
                base_url=model_cfg.get('base_url'),
                api_key=model_cfg.get('api_key'),
            )
            zone = persona.get('zone', 'wildcard')
            zone_angle = ZONE_EVAL_ANGLES.get(zone, ZONE_EVAL_ANGLES.get('wildcard', ''))
            messages = [
                {"role": "system", "content": (
                    f"{persona['prompt']}\n\n"
                    "Express your analysis using terminology and concerns specific to YOUR professional domain. "
                    "Do NOT use generic investor phrases or startup cliches. "
                    "Your reasoning must sound distinctly like someone in YOUR role - "
                    "if another agent could have written the same sentence, it's too generic.\n\n"
                    f"{zone_angle}\n\n"
                    "Score this startup on each dimension from 1-10, "
                    "relative to similar companies at this stage in this industry. "
                    "5 = average, 7+ = strong, 3- = weak.\n"
                    "Base your assessment ONLY on the research data provided. "
                    "If you reference a fact not in the data, prefix with [UNVERIFIED].\n\n"
                    "Return ONLY JSON:\n"
                    "{\"market\": 1-10, \"team\": 1-10, \"product\": 1-10, "
                    "\"timing\": 1-10, \"overall\": 1-10, \"reasoning\": \"2-3 sentences\"}"
                )},
                {"role": "user", "content": (
                    f"Executive Summary:\n{exec_summary}\n\n"
                    f"Research Context:\n{research_context[:3000]}"
                )},
            ]
            result = llm.chat_json(messages=messages, temperature=0.8)
            scores = {d: max(1, min(10, float(result.get(d, 5)))) for d in SCORE_DIMENSIONS}
            return SwarmAgent(
                agent_id=persona['agent_id'],
                persona=persona['name'],
                scores=scores,
                overall=scores['overall'],
                reasoning=result.get('reasoning', ''),
                model_used=model_cfg['label'],
                zone=persona.get('zone', 'wildcard'),
            )
        except Exception as e:
            logger.warning(f"[Swarm] Agent {persona['name']} failed: {e}")
            return None

    def _run_batch(self, batch_size: int, exec_summary: str,
                   research_context: str, model_cfg: dict,
                   start_id: int) -> List[SwarmAgent]:
        try:
            llm = LLMClient(
                model=model_cfg['model'],
                base_url=model_cfg.get('base_url'),
                api_key=model_cfg.get('api_key'),
            )
            messages = [
                {"role": "system", "content": (
                    f"Simulate {batch_size} diverse startup evaluators. "
                    "Each has a different perspective (investor, customer, competitor, "
                    "analyst, operator, regulator, journalist, etc.).\n"
                    "For each, score the startup 1-10 on each dimension "
                    "(5=average, 7+=strong, 3-=weak).\n"
                    "For each, generate:\n"
                    "- persona: brief role\n"
                    "- market: 1-10\n- team: 1-10\n- product: 1-10\n"
                    "- timing: 1-10\n- overall: 1-10\n"
                    "- reasoning: 1-2 sentences\n\n"
                    f"Return JSON: {{\"agents\": [...]}} with exactly {batch_size} entries."
                )},
                {"role": "user", "content": (
                    f"Executive Summary:\n{exec_summary}\n\n"
                    f"Research Context:\n{research_context[:3000]}"
                )},
            ]
            result = llm.chat_json(messages=messages, temperature=0.9, max_tokens=4096)
            agents = []
            for i, ad in enumerate(result.get('agents', [])):
                scores = {d: max(1, min(10, float(ad.get(d, 5)))) for d in SCORE_DIMENSIONS}
                agents.append(SwarmAgent(
                    agent_id=start_id + i,
                    persona=ad.get('persona', f'Batch agent {start_id + i}'),
                    scores=scores,
                    overall=scores['overall'],
                    reasoning=ad.get('reasoning', ''),
                    model_used=model_cfg['label'],
                ))
            return agents
        except Exception as e:
            logger.warning(f"[Swarm] Batch call failed: {e}")
            return []

    def _aggregate(self, agents: List[SwarmAgent], wave1_count: int,
                   wave2_count: int, elapsed: float,
                   models: list) -> SwarmResult:
        empty = SwarmResult(
            total_agents=0, wave1_individual=wave1_count, wave2_batched=wave2_count,
            avg_scores={d: 0 for d in SCORE_DIMENSIONS}, median_overall=0, std_overall=0,
            score_distribution={"strong_hit": 0, "likely_hit": 0, "uncertain": 0, "likely_miss": 0, "strong_miss": 0},
            positive_pct=0, negative_pct=0, avg_confidence=0,
            key_themes_positive=[], key_themes_negative=[], contested_themes=[],
            agent_results=[], models_used=[], execution_time_seconds=elapsed, verdict="Uncertain",
        )
        if not agents:
            return empty

        total = len(agents)
        overall_scores = sorted([a.overall for a in agents])

        # Dimensional averages
        avg_scores = {}
        for d in SCORE_DIMENSIONS:
            vals = [a.scores.get(d, 5) for a in agents]
            avg_scores[d] = round(sum(vals) / len(vals), 2)

        median_overall = overall_scores[total // 2]
        mean_overall = sum(overall_scores) / total
        std_overall = round((sum((s - mean_overall) ** 2 for s in overall_scores) / total) ** 0.5, 2)

        # Score distribution buckets
        strong_hit = sum(1 for s in overall_scores if s >= 7.5)
        likely_hit = sum(1 for s in overall_scores if 6.0 <= s < 7.5)
        uncertain = sum(1 for s in overall_scores if 4.5 <= s < 6.0)
        likely_miss = sum(1 for s in overall_scores if 3.0 <= s < 4.5)
        strong_miss = sum(1 for s in overall_scores if s < 3.0)

        # Vote metrics (computed before verdict so consensus informs verdict)
        positive = [a for a in agents if a.vote == 'positive']
        negative = [a for a in agents if a.vote != 'positive']
        positive_pct = round(len(positive) / total * 100, 1)
        negative_pct = round(len(negative) / total * 100, 1)

        # Confidence based on agreement, not score extremeness
        agreement_confidence = max(0.1, min(1.0, 1.0 - (std_overall / 3.0)))
        avg_confidence = round(agreement_confidence, 2)

        # Verdict blends median score + swarm consensus (neither alone is sufficient)
        if median_overall >= 7.5 and positive_pct >= 70: verdict = "Strong Hit"
        elif median_overall >= 7.5 and positive_pct >= 50: verdict = "Likely Hit"
        elif median_overall >= 6.0 and positive_pct >= 60: verdict = "Likely Hit"
        elif median_overall >= 6.0 and positive_pct >= 40: verdict = "Mixed Signal"
        elif median_overall >= 4.5 and positive_pct >= 40: verdict = "Mixed Signal"
        elif median_overall >= 4.5: verdict = "Likely Miss"
        elif median_overall >= 3.0: verdict = "Likely Miss"
        else: verdict = "Strong Miss"

        # Themes from high vs low scorers
        high_scorers = [a for a in agents if a.overall >= 6.0]
        low_scorers = [a for a in agents if a.overall < 5.0]
        pos_themes = self._extract_themes([a.reasoning for a in high_scorers[:50]])
        neg_themes = self._extract_themes([a.reasoning for a in low_scorers[:50]])
        pos_set = set(t.lower() for t in pos_themes)
        neg_set = set(t.lower() for t in neg_themes)
        contested = list(pos_set & neg_set)

        models_used = list(set(a.model_used for a in agents))

        return SwarmResult(
            total_agents=total,
            wave1_individual=wave1_count,
            wave2_batched=wave2_count,
            avg_scores=avg_scores,
            median_overall=median_overall,
            std_overall=std_overall,
            score_distribution={
                "strong_hit": strong_hit, "likely_hit": likely_hit,
                "uncertain": uncertain, "likely_miss": likely_miss, "strong_miss": strong_miss,
            },
            positive_pct=positive_pct,
            negative_pct=negative_pct,
            avg_confidence=avg_confidence,
            key_themes_positive=pos_themes[:10],
            key_themes_negative=neg_themes[:10],
            contested_themes=contested[:5],
            agent_results=agents,
            models_used=models_used,
            execution_time_seconds=round(elapsed, 2),
            verdict=verdict,
        )

    @staticmethod
    def _compute_divergence(agents: List[SwarmAgent]) -> Dict[str, Any]:
        """Compute consensus vs divergence metrics across the panel."""
        if len(agents) < 5:
            return {}

        from collections import defaultdict
        overall_scores = [a.overall for a in agents]
        mean_overall = sum(overall_scores) / len(overall_scores)
        std_overall = (sum((s - mean_overall) ** 2 for s in overall_scores) / len(overall_scores)) ** 0.5

        if std_overall < 0.01:
            return {"consensus": True, "critical_outliers": [], "zone_agreement": {},
                    "most_divided_dimension": None, "divergence_narrative": []}

        # Per-agent z-score
        agent_z = []
        for a in agents:
            z = (a.overall - mean_overall) / std_overall
            agent_z.append({
                "agent_id": a.agent_id, "persona": a.persona, "zone": a.zone,
                "overall": a.overall, "z_score": round(z, 2),
                "reasoning_excerpt": a.reasoning[:200] if a.reasoning else "",
            })

        # Critical outliers: |z| > 1.0 (lowered from 1.5 — 1.5 was too strict for 25-agent panels)
        critical_outliers = sorted(
            [a for a in agent_z if abs(a["z_score"]) > 1.0],
            key=lambda x: abs(x["z_score"]), reverse=True
        )

        # Fallback: if no z-score outliers but score spread >= 3 points, use top/bottom agents
        if not critical_outliers:
            spread = max(a.overall for a in agents) - min(a.overall for a in agents)
            if spread >= 3.0:
                sorted_by_score = sorted(agent_z, key=lambda x: x['overall'])
                critical_outliers = [sorted_by_score[0], sorted_by_score[-1]]

        # Zone agreement
        zone_map = defaultdict(list)
        for a in agents:
            zone_map[a.zone].append(a)
        zone_agreement = {}
        for zone, z_agents in zone_map.items():
            hits = sum(1 for a in z_agents if a.overall >= 5.5)
            total = len(z_agents)
            majority_pct = max(hits, total - hits) / total * 100
            zone_agreement[zone] = {
                "total": total, "hits": hits, "misses": total - hits,
                "agreement_pct": round(majority_pct, 1),
                "majority_direction": "HIT" if hits >= total / 2 else "MISS",
            }

        # Most divided dimension
        dim_stds = {}
        for d in ["market", "team", "product", "timing"]:
            vals = [a.scores.get(d, 5) for a in agents]
            d_mean = sum(vals) / len(vals)
            dim_stds[d] = round((sum((v - d_mean) ** 2 for v in vals) / len(vals)) ** 0.5, 2)
        most_divided = max(dim_stds, key=dim_stds.get) if dim_stds else None

        # Divergence narrative
        narrative = []
        for o in critical_outliers[:6]:
            narrative.append({
                "persona": o["persona"], "zone": o["zone"], "overall": o["overall"],
                "z_score": o["z_score"], "direction": "bullish" if o["z_score"] > 0 else "bearish",
                "excerpt": o["reasoning_excerpt"],
            })

        return {
            "consensus": len(critical_outliers) == 0,
            "critical_outliers": critical_outliers[:10],
            "zone_agreement": zone_agreement,
            "most_divided_dimension": most_divided,
            "dimension_stds": dim_stds,
            "divergence_narrative": narrative,
        }

    @staticmethod
    def _select_committee(agents: List[SwarmAgent], divergence: Dict[str, Any]) -> List[SwarmAgent]:
        """Select 5-6 diverse agents for investment committee roundtable."""
        selected = []
        used_ids = set()

        def pick(agent):
            if agent and agent.agent_id not in used_ids:
                selected.append(agent)
                used_ids.add(agent.agent_id)

        # 1. Strongest bull
        pick(max(agents, key=lambda a: a.overall))
        # 2. Strongest bear
        pick(min(agents, key=lambda a: a.overall))
        # 3. Most internally conflicted (highest per-dimension variance)
        remaining = [a for a in agents if a.agent_id not in used_ids]
        if remaining:
            def dim_var(a):
                vals = [a.scores.get(d, 5) for d in ["market", "team", "product", "timing"]]
                m = sum(vals) / len(vals)
                return sum((v - m) ** 2 for v in vals) / len(vals)
            pick(max(remaining, key=dim_var))
        # 4. Agent from zone that disagrees with overall consensus
        zone_agreement = divergence.get('zone_agreement', {})
        overall_dir = "HIT" if sum(a.overall for a in agents) / len(agents) >= 5.5 else "MISS"
        for z, data in zone_agreement.items():
            if data.get('majority_direction') != overall_dir:
                zone_agents = [a for a in agents if a.zone == z and a.agent_id not in used_ids]
                if zone_agents:
                    pick(max(zone_agents, key=lambda a: abs(a.overall - 5.5)))
                    break
        # 5. Most unique wild card
        wildcards = [a for a in agents if a.zone == 'wildcard' and a.agent_id not in used_ids]
        if wildcards:
            mean_o = sum(a.overall for a in agents) / len(agents)
            pick(max(wildcards, key=lambda a: abs(a.overall - mean_o)))
        # 6. Operator if all operators missed
        operators = [a for a in agents if a.zone == 'operator']
        if operators and all(a.overall < 5.5 for a in operators):
            ops_avail = [a for a in operators if a.agent_id not in used_ids]
            if ops_avail:
                pick(ops_avail[0])
        # Backfill from outliers if under 5
        for o in divergence.get('critical_outliers', []):
            if len(selected) >= 6:
                break
            cand = next((a for a in agents if a.agent_id == o['agent_id'] and a.agent_id not in used_ids), None)
            if cand:
                pick(cand)
        return selected[:6]

    def _deliberate(self, agents: List[SwarmAgent], divergence: Dict[str, Any],
                    exec_summary: str, tier1_models: list) -> Tuple[Dict[str, Any], List[SwarmAgent]]:
        """Run 5-6 agent investment committee roundtable.
        Round 1: Each member writes position statement addressing their biggest disagreement (5-6 parallel calls).
        Round 2: Chair synthesizes the debate (1 call).
        Returns (deliberation_dict, updated_agents_list)."""
        committee = self._select_committee(agents, divergence)
        if len(committee) < 3:
            return {}, agents

        delib_model = tier1_models[0] if tier1_models else self._get_models()[0]
        logger.info(f"[Swarm] Deliberation: {len(committee)} committee members selected")

        # Build position summary for all members to see
        positions_summary = "\n".join([
            f"- {m.persona} ({m.zone}) - {m.overall:.1f}/10: {m.reasoning[:120]}"
            for m in committee
        ])

        # ── Round 1: Position statements (parallel) ──
        position_results = []
        adjusted_scores = {}

        def run_position(member):
            try:
                most_disagree = max(
                    [m for m in committee if m.agent_id != member.agent_id],
                    key=lambda m: abs(m.overall - member.overall)
                )
                llm = LLMClient(
                    model=delib_model['model'],
                    base_url=delib_model.get('base_url'),
                    api_key=delib_model.get('api_key'),
                )
                messages = [
                    {"role": "system", "content": (
                        f"You are {member.persona} ({member.zone} zone). "
                        f"You scored this startup {member.overall:.1f}/10.\n\n"
                        f"INVESTMENT COMMITTEE POSITIONS:\n{positions_summary}\n\n"
                        "Write your position statement for the committee:\n"
                        f"1. Defend your score in 2-3 sentences using YOUR domain expertise and terminology\n"
                        f"2. Directly address the argument from {most_disagree.persona} "
                        f"who scored {most_disagree.overall:.1f}/10 - explain why they are wrong or what they are missing\n"
                        "3. State whether hearing the full committee changes your conviction\n\n"
                        "Return ONLY JSON:\n"
                        '{"position": "3-4 sentences", '
                        '"addresses": "who you are responding to", '
                        '"adjusted_score": <1-10 or null if unchanged>, '
                        '"conviction_change": "stronger/weaker/unchanged"}'
                    )},
                    {"role": "user", "content": f"Startup:\n{exec_summary[:1500]}"},
                ]
                result = llm.chat_json(messages=messages, temperature=0.7, max_tokens=600)
                adj = result.get('adjusted_score')
                if adj is not None:
                    adj = max(1, min(10, float(adj)))
                return {
                    "persona": member.persona, "zone": member.zone,
                    "original_score": member.overall,
                    "position": result.get('position', ''),
                    "addresses": result.get('addresses', most_disagree.persona),
                    "adjusted_score": adj,
                    "conviction_change": result.get('conviction_change', 'unchanged'),
                }
            except Exception as e:
                logger.warning(f"[Swarm] Committee position failed for {member.persona}: {e}")
                return None

        with ThreadPoolExecutor(max_workers=min(6, len(committee))) as pool:
            futures = [pool.submit(run_position, m) for m in committee]
            for f in as_completed(futures):
                r = f.result()
                if r:
                    position_results.append(r)
                    if r['adjusted_score'] is not None:
                        adjusted_scores[r['persona']] = r['adjusted_score']

        # ── Round 2: Chair synthesis ──
        synthesis = {}
        if position_results:
            try:
                positions_text = "\n\n".join([
                    f"{p['persona']} ({p['zone']}, {p['original_score']:.1f}/10"
                    + (f" -> {p['adjusted_score']:.1f}" if p['adjusted_score'] else "")
                    + f", conviction {p['conviction_change']}):\n{p['position']}"
                    for p in position_results
                ])
                llm = LLMClient(
                    model=delib_model['model'],
                    base_url=delib_model.get('base_url'),
                    api_key=delib_model.get('api_key'),
                )
                messages = [
                    {"role": "system", "content": (
                        f"You are the senior investment committee chair synthesizing a {len(position_results)}-member roundtable.\n\n"
                        f"Committee discussion:\n{positions_text}\n\n"
                        "Return ONLY JSON:\n"
                        '{"consensus_points": ["2-3 things the committee agrees on"], '
                        '"unresolved_tensions": ["2-3 things that remain debated"], '
                        '"verdict_shifted": true/false, '
                        '"recommendation": "one paragraph final recommendation", '
                        '"critical_risk": "the single risk the founder must address first"}'
                    )},
                    {"role": "user", "content": f"Startup:\n{exec_summary[:1000]}"},
                ]
                synthesis = llm.chat_json(messages=messages, temperature=0.5, max_tokens=1000)
            except Exception as e:
                logger.warning(f"[Swarm] Committee synthesis failed: {e}")
                synthesis = {"recommendation": "Synthesis unavailable.", "verdict_shifted": False}

        # Apply adjusted scores
        updated = list(agents)
        for i, agent in enumerate(updated):
            if agent.persona in adjusted_scores:
                new_score = adjusted_scores[agent.persona]
                logger.info(f"[Swarm] Committee: {agent.persona} adjusted {agent.overall:.1f} -> {new_score:.1f}")
                updated[i] = SwarmAgent(
                    agent_id=agent.agent_id, persona=agent.persona,
                    scores={**agent.scores, 'overall': new_score},
                    overall=new_score, reasoning=agent.reasoning,
                    model_used=agent.model_used, zone=agent.zone,
                )

        return {
            "committee": [{"persona": m.persona, "zone": m.zone, "score": m.overall} for m in committee],
            "positions": position_results,
            "synthesis": synthesis,
            "adjusted_scores": adjusted_scores,
            "rounds": 2,
            "extra_llm_calls": len(position_results) + (1 if synthesis else 0),
        }, updated

    @staticmethod
    def _extract_themes(reasonings: List[str]) -> List[str]:
        """Extract key themes from a list of reasoning strings using word frequency."""
        if not reasonings:
            return []

        # Simple keyword extraction — count significant phrases
        from collections import Counter
        stop_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'can', 'shall', 'this', 'that', 'these',
            'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him',
            'her', 'us', 'them', 'my', 'your', 'his', 'its', 'our', 'their',
            'and', 'but', 'or', 'not', 'no', 'nor', 'so', 'yet', 'for', 'of',
            'in', 'on', 'at', 'to', 'with', 'by', 'from', 'as', 'into', 'about',
            'than', 'if', 'then', 'very', 'too', 'also', 'just', 'more', 'most',
            'some', 'any', 'all', 'each', 'every', 'both', 'few', 'many', 'much',
            'own', 'other', 'such', 'only', 'same', 'there', 'here', 'when',
            'where', 'why', 'how', 'what', 'which', 'who', 'whom', 'whose',
        }

        word_counts = Counter()
        for r in reasonings:
            words = r.lower().split()
            significant = [w.strip('.,!?;:"\'()[]') for w in words if len(w) > 3]
            significant = [w for w in significant if w and w not in stop_words]
            word_counts.update(significant)

        return [word for word, _ in word_counts.most_common(15)]
