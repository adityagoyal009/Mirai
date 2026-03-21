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
from .persona_engine import PersonaEngine

logger = get_logger('mirofish.swarm')

# ── Data classes ──────────────────────────────────────────────────


@dataclass
class SwarmAgent:
    agent_id: int
    persona: str
    vote: str  # "positive" or "negative"
    confidence: float  # 0.0 - 1.0
    reasoning: str
    model_used: str


@dataclass
class SwarmResult:
    total_agents: int
    wave1_individual: int
    wave2_batched: int
    positive_pct: float
    negative_pct: float
    avg_confidence: float
    confidence_distribution: Dict[str, int]
    key_themes_positive: List[str]
    key_themes_negative: List[str]
    contested_themes: List[str]
    agent_results: List[SwarmAgent]
    models_used: List[str]
    execution_time_seconds: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_agents": self.total_agents,
            "wave1_individual": self.wave1_individual,
            "wave2_batched": self.wave2_batched,
            "positive_pct": self.positive_pct,
            "negative_pct": self.negative_pct,
            "avg_confidence": self.avg_confidence,
            "confidence_distribution": self.confidence_distribution,
            "key_themes_positive": self.key_themes_positive,
            "key_themes_negative": self.key_themes_negative,
            "contested_themes": self.contested_themes,
            "models_used": self.models_used,
            "execution_time_seconds": self.execution_time_seconds,
            "sample_agents": [
                {"persona": a.persona, "vote": a.vote,
                 "confidence": a.confidence, "reasoning": a.reasoning[:200]}
                for a in self.agent_results[:20]
            ],
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

VALID_COUNTS = [50, 100, 250, 500, 1000]
WAVE1_MAX = 100
BATCH_SIZE = 25
# Max concurrent LLM calls — keep low to avoid CPU hang + rate limits
WAVE1_WORKERS = 3
WAVE2_WORKERS = 2


class SwarmPredictor:
    """Spawns agents with variable personalities to predict startup outcomes."""

    def __init__(self):
        self._models = None
        self._persona_engine = PersonaEngine()

    def _get_models(self) -> list:
        if self._models is None:
            self._models = Config.get_council_models()
            if not self._models:
                self._models = [{
                    'model': Config.LLM_MODEL_NAME,
                    'label': 'Default',
                    'base_url': Config.LLM_BASE_URL,
                    'api_key': Config.LLM_API_KEY,
                }]
        return self._models

    def predict(self, exec_summary: str, research_context: str,
                agent_count: int = 100,
                on_agent_complete=None,
                on_agent_start=None) -> SwarmResult:
        """Run swarm prediction with hybrid wave execution.
        on_agent_complete: optional callback(SwarmAgent) fired for each completed agent.
        on_agent_start: optional callback(agent_id, persona_name) fired before each agent's LLM call."""
        start_time = time.time()

        if agent_count not in VALID_COUNTS:
            agent_count = min(VALID_COUNTS, key=lambda x: abs(x - agent_count))

        models = self._get_models()
        wave1_count = min(agent_count, WAVE1_MAX)
        wave2_remaining = agent_count - wave1_count

        # Extract industry/product from exec_summary for persona matching
        industry = ""
        product = ""
        for line in exec_summary.split('\n'):
            lower = line.lower()
            if 'industry' in lower:
                industry = line.split(':', 1)[-1].strip() if ':' in line else ""
            if 'product' in lower:
                product = line.split(':', 1)[-1].strip() if ':' in line else ""

        logger.info(f"[Swarm] Starting {agent_count} agents "
                    f"(wave1={wave1_count}, wave2={wave2_remaining}) "
                    f"across {len(models)} models")

        # Select personas using PersonaEngine (dataset + generated mix)
        all_personas = self._persona_engine.select_personas(
            count=wave1_count, industry=industry, product=product
        )
        wave1_personas = []
        for i, p in enumerate(all_personas):
            wave1_personas.append({
                "agent_id": i,
                "name": p.name,
                "prompt": p.prompt,
            })

        all_agents: List[SwarmAgent] = []

        # ── Wave 1: Individual detailed calls ─────────────────────
        logger.info(f"[Swarm] Wave 1: {wave1_count} individual agent calls")
        with ThreadPoolExecutor(max_workers=min(WAVE1_WORKERS, wave1_count)) as pool:
            futures = []
            for i, persona in enumerate(wave1_personas):
                model_cfg = models[i % len(models)]
                if on_agent_start:
                    on_agent_start(persona['agent_id'], persona['name'], model_cfg['label'])
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
                    model_cfg = models[i % len(models)]
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

        elapsed = time.time() - start_time
        return self._aggregate(all_agents, wave1_count, wave2_remaining, elapsed, models)

    def _run_individual(self, persona: dict, exec_summary: str,
                        research_context: str, model_cfg: dict) -> Optional[SwarmAgent]:
        try:
            llm = LLMClient(
                model=model_cfg['model'],
                base_url=model_cfg.get('base_url'),
                api_key=model_cfg.get('api_key'),
            )
            messages = [
                {"role": "system", "content": (
                    f"{persona['prompt']}\n\n"
                    "You are evaluating a startup. Give your honest assessment.\n"
                    "Return ONLY JSON: {\"vote\": \"positive\" or \"negative\", "
                    "\"confidence\": 0.0-1.0, \"reasoning\": \"2-3 sentences\"}"
                )},
                {"role": "user", "content": (
                    f"Executive Summary:\n{exec_summary}\n\n"
                    f"Research Context:\n{research_context[:3000]}"
                )},
            ]
            result = llm.chat_json(messages=messages, temperature=0.8)
            return SwarmAgent(
                agent_id=persona['agent_id'],
                persona=persona['name'],
                vote=result.get('vote', 'negative').lower().strip(),
                confidence=max(0.0, min(1.0, float(result.get('confidence', 0.5)))),
                reasoning=result.get('reasoning', ''),
                model_used=model_cfg['label'],
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
                    "For each, generate:\n"
                    "- persona: brief role (e.g., 'Conservative PE investor')\n"
                    "- vote: 'positive' or 'negative'\n"
                    "- confidence: 0.0 to 1.0\n"
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
                agents.append(SwarmAgent(
                    agent_id=start_id + i,
                    persona=ad.get('persona', f'Batch agent {start_id + i}'),
                    vote=ad.get('vote', 'negative').lower().strip(),
                    confidence=max(0.0, min(1.0, float(ad.get('confidence', 0.5)))),
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
        if not agents:
            return SwarmResult(
                total_agents=0, wave1_individual=wave1_count,
                wave2_batched=wave2_count, positive_pct=0, negative_pct=0,
                avg_confidence=0, confidence_distribution={"high": 0, "medium": 0, "low": 0},
                key_themes_positive=[], key_themes_negative=[],
                contested_themes=[], agent_results=[], models_used=[],
                execution_time_seconds=elapsed,
            )

        positive = [a for a in agents if a.vote == 'positive']
        negative = [a for a in agents if a.vote != 'positive']
        total = len(agents)

        positive_pct = round(len(positive) / total * 100, 1)
        negative_pct = round(len(negative) / total * 100, 1)
        avg_confidence = round(sum(a.confidence for a in agents) / total, 3)

        # Confidence distribution
        high = sum(1 for a in agents if a.confidence > 0.7)
        medium = sum(1 for a in agents if 0.4 <= a.confidence <= 0.7)
        low = sum(1 for a in agents if a.confidence < 0.4)

        # Extract themes from reasoning
        pos_themes = self._extract_themes([a.reasoning for a in positive[:50]])
        neg_themes = self._extract_themes([a.reasoning for a in negative[:50]])

        # Find contested themes (appear in both)
        pos_set = set(t.lower() for t in pos_themes)
        neg_set = set(t.lower() for t in neg_themes)
        contested = list(pos_set & neg_set)

        models_used = list(set(a.model_used for a in agents))

        return SwarmResult(
            total_agents=total,
            wave1_individual=wave1_count,
            wave2_batched=wave2_count,
            positive_pct=positive_pct,
            negative_pct=negative_pct,
            avg_confidence=avg_confidence,
            confidence_distribution={"high": high, "medium": medium, "low": low},
            key_themes_positive=pos_themes[:10],
            key_themes_negative=neg_themes[:10],
            contested_themes=contested[:5],
            agent_results=agents,
            models_used=models_used,
            execution_time_seconds=round(elapsed, 2),
        )

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
