"""
Business Intelligence Engine — research, predict, plan.

Given an executive summary, the engine:
  1. Researches the market (SearXNG + ChromaDB + Mem0 + OpenBB + LLM synthesis)
  2. Predicts hit or miss across 7 dimensions (LLM Council in deep mode)
  3. Plans strategic next moves

Capability stack:
  - SearXNG: Fast structured URL discovery (replaces DuckDuckGo navigation)
  - Crawl4AI / browser-use: Content extraction (fast path / full path)
  - Mem0: Relationship-aware memory (past analyses inform future ones)
  - OpenBB: Live financial data (stock prices, fundamentals, market news)
  - CrewAI: Multi-agent parallel analysis (deep mode)
  - ChromaDB: Episode storage + semantic search (unchanged for MiroFish)
"""

import uuid
import json
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple

from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from ..config import Config

logger = get_logger('mirofish.bi')

# ── Research depth presets ────────────────────────────────────────

_DEPTH_CONFIG = {
    "quick": {"search_limit": 5, "query_count": 4, "max_tokens": 1500, "council": False},
    "standard": {"search_limit": 15, "query_count": 8, "max_tokens": 3000, "council": False},
    "deep": {"search_limit": 30, "query_count": 12, "max_tokens": 4096, "council": True},
}

# ── LLM Council — models to consult in parallel (all via OpenClaw) ──

_COUNCIL_MODELS = [
    {"model": "anthropic/claude-opus-4-6", "label": "Claude Opus 4.6"},
    {"model": "openai/gpt-5.4", "label": "GPT-5.4"},
]

# Dimensions where models disagree by more than this are flagged as "contested"
_DISAGREEMENT_THRESHOLD = 3

# ── Exec summary template ────────────────────────────────────────

EXEC_SUMMARY_TEMPLATE = {
    "template": (
        "Company name: [Your company name]\n"
        "Industry: [e.g. fintech, healthtech, edtech, SaaS, e-commerce]\n"
        "Product/Service: [What you are building — one or two sentences]\n"
        "Target market: [Who buys this — be specific about segment and geography]\n"
        "Business model: [How you make money — subscription, transaction fee, freemium, etc.]\n"
        "Stage: [idea / MVP / revenue / scaling]\n"
        "Traction: [Any numbers — users, revenue, growth rate, partnerships]\n"
        "Ask: [What you want to know — go/no-go, funding viability, market entry strategy]"
    ),
    "example": (
        "Company name: LegalLens AI\n"
        "Industry: legaltech\n"
        "Product/Service: AI-powered contract analysis platform that reviews legal "
        "documents in seconds, flagging risky clauses and suggesting edits.\n"
        "Target market: Mid-size US law firms (50-200 attorneys) and in-house legal "
        "teams at Fortune 1000 companies.\n"
        "Business model: SaaS — $500/seat/month for firms, enterprise tier at $25k/year.\n"
        "Stage: MVP — working prototype, 3 pilot customers.\n"
        "Traction: 3 paid pilots ($1,500 MRR), 12 firms on waitlist, processing "
        "~200 contracts/week across pilots.\n"
        "Ask: Is this a viable market to pursue aggressively? Should we raise a seed round?"
    ),
    "fields": {
        "company_name": {"required": True, "description": "Name of the company"},
        "industry": {"required": True, "description": "Industry or vertical"},
        "product_service": {"required": True, "description": "What you are building"},
        "target_market": {"required": True, "description": "Who buys this"},
        "business_model": {"required": True, "description": "How you make money"},
        "stage": {"required": False, "description": "idea / MVP / revenue / scaling"},
        "traction": {"required": False, "description": "Users, revenue, growth metrics"},
        "ask": {"required": False, "description": "What you want to know"},
    },
}

# ── Critical fields — analysis won't proceed without these ────────

_CRITICAL_FIELDS = ["company", "industry", "product"]
_IMPORTANT_FIELDS = ["target_market", "business_model"]
_OPTIONAL_FIELDS = ["stage", "traction", "ask", "claims", "key_differentiators"]

# ── Data classes ──────────────────────────────────────────────────


@dataclass
class ExtractionResult:
    """Result of extracting structured data from freeform exec summary."""
    company: str = ""
    industry: str = ""
    product: str = ""
    target_market: str = ""
    business_model: str = ""
    stage: str = ""
    traction: str = ""
    ask: str = ""
    claims: List[str] = field(default_factory=list)
    key_differentiators: List[str] = field(default_factory=list)
    # Quality tracking
    fields_present: List[str] = field(default_factory=list)
    fields_missing: List[str] = field(default_factory=list)
    fields_vague: List[str] = field(default_factory=list)
    data_quality: float = 0.0  # 0-1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ResearchReport:
    """Structured research findings."""
    company: str
    industry: str
    product: str
    market_data: List[str] = field(default_factory=list)
    competitors: List[str] = field(default_factory=list)
    news: List[str] = field(default_factory=list)
    trends: List[str] = field(default_factory=list)
    sentiment: str = "neutral"
    context_facts: List[str] = field(default_factory=list)
    browser_queries: List[str] = field(default_factory=list)
    # New: data source tracking
    financial_data: Dict[str, Any] = field(default_factory=dict)
    mem0_context: List[str] = field(default_factory=list)
    data_sources_used: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DimensionScore:
    """A single scoring dimension."""
    name: str
    score: float  # 1-10
    reasoning: str


@dataclass
class Prediction:
    """Structured prediction with 7-dimension scoring."""
    dimensions: List[DimensionScore] = field(default_factory=list)
    overall_score: float = 0.0
    verdict: str = "Uncertain"
    confidence: float = 0.0
    reasoning: str = ""
    # Council metadata (populated when depth=deep)
    council_used: bool = False
    council_models: List[str] = field(default_factory=list)
    contested_dimensions: List[Dict[str, Any]] = field(default_factory=list)
    model_scores: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "dimensions": [asdict(d) for d in self.dimensions],
            "overall_score": self.overall_score,
            "verdict": self.verdict,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
        }
        if self.council_used:
            result["council"] = {
                "used": True,
                "models": self.council_models,
                "contested_dimensions": self.contested_dimensions,
                "model_scores": self.model_scores,
            }
        return result


@dataclass
class StrategyPlan:
    """Strategic recommendations."""
    risks: List[Dict[str, str]] = field(default_factory=list)
    next_moves: List[Dict[str, str]] = field(default_factory=list)
    go_to_market: List[str] = field(default_factory=list)
    validation_experiments: List[str] = field(default_factory=list)
    timeline_90_day: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FullAnalysis:
    """Complete BI analysis result."""
    id: str
    exec_summary: str
    research: ResearchReport
    prediction: Prediction
    plan: StrategyPlan
    created_at: str
    depth: str
    data_quality: float = 1.0  # 0-1, how complete the input data was

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "exec_summary": self.exec_summary,
            "research": self.research.to_dict(),
            "prediction": self.prediction.to_dict(),
            "plan": self.plan.to_dict(),
            "created_at": self.created_at,
            "depth": self.depth,
            "data_quality": self.data_quality,
        }


# ── Dimension weights for overall score ──────────────────────────

_DIMENSION_WEIGHTS = {
    "market_timing": 0.20,
    "competition_landscape": 0.15,
    "business_model_viability": 0.20,
    "team_execution_signals": 0.10,
    "regulatory_news_environment": 0.10,
    "social_proof_demand": 0.10,
    "pattern_match": 0.15,
}


class BusinessIntelEngine:
    """
    Core BI engine. Three phases: research → predict → plan.
    Reuses LLMClient for all LLM calls, EpisodicMemoryStore for storage.
    Integrates SearXNG, Mem0, OpenBB, Crawl4AI, and CrewAI when available.
    """

    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or LLMClient()
        # Lazy-initialized services
        self._mem0 = None
        self._mem0_checked = False
        self._market_data = None
        self._market_data_checked = False
        self._crew = None
        self._crew_checked = False

    # ── Lazy service initialization ────────────────────────────────

    def _get_mem0(self):
        """Lazy-init Mem0 memory store."""
        if not self._mem0_checked:
            self._mem0_checked = True
            try:
                from subconscious.memory import Mem0MemoryStore
                store = Mem0MemoryStore(user_id=Config.MEM0_USER_ID)
                if store.is_available():
                    self._mem0 = store
                    logger.info("[BI] Mem0 memory available for relationship-aware recall")
            except Exception as e:
                logger.info(f"[BI] Mem0 not available (non-fatal): {e}")
        return self._mem0

    def _get_market_data(self):
        """Lazy-init OpenBB market data service."""
        if not self._market_data_checked:
            self._market_data_checked = True
            if Config.OPENBB_ENABLED:
                try:
                    from .market_data import MarketDataService
                    svc = MarketDataService()
                    if svc.is_available():
                        self._market_data = svc
                        logger.info("[BI] OpenBB market data available")
                except Exception as e:
                    logger.info(f"[BI] OpenBB not available (non-fatal): {e}")
        return self._market_data

    def _get_crew(self):
        """Lazy-init CrewAI orchestrator."""
        if not self._crew_checked:
            self._crew_checked = True
            try:
                from .crew_orchestrator import CrewOrchestrator
                crew = CrewOrchestrator()
                if crew.is_available():
                    self._crew = crew
                    logger.info("[BI] CrewAI available for multi-agent analysis")
            except Exception as e:
                logger.info(f"[BI] CrewAI not available (non-fatal): {e}")
        return self._crew

    # ── Extraction + Validation ───────────────────────────────────

    def extract_and_validate(self, exec_summary: str) -> ExtractionResult:
        """
        Extract structured fields from freeform exec summary via LLM,
        then validate completeness. Returns ExtractionResult with data_quality score.
        """
        extraction = self.llm.chat_json(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extract structured business information from the executive summary. "
                        "Return JSON with these keys (use empty string if not found):\n"
                        "- company: company name\n"
                        "- industry: industry or vertical\n"
                        "- product: what they are building\n"
                        "- target_market: who buys this\n"
                        "- business_model: how they make money\n"
                        "- stage: one of idea/MVP/revenue/scaling (or empty)\n"
                        "- traction: any metrics — users, revenue, growth (or empty)\n"
                        "- ask: what they want to know (or empty)\n"
                        "- claims: list of specific claims made\n"
                        "- key_differentiators: list of competitive advantages\n\n"
                        "If a field is mentioned but vague/unclear, still extract what you can "
                        "but also include the field name in a 'vague_fields' list."
                    ),
                },
                {"role": "user", "content": exec_summary},
            ],
            temperature=0.2,
        )

        result = ExtractionResult(
            company=extraction.get("company", ""),
            industry=extraction.get("industry", ""),
            product=extraction.get("product", ""),
            target_market=extraction.get("target_market", ""),
            business_model=extraction.get("business_model", ""),
            stage=extraction.get("stage", ""),
            traction=extraction.get("traction", ""),
            ask=extraction.get("ask", ""),
            claims=extraction.get("claims", []),
            key_differentiators=extraction.get("key_differentiators", []),
        )

        vague_from_llm = extraction.get("vague_fields", [])

        # Score field completeness
        all_fields = {
            "company": result.company,
            "industry": result.industry,
            "product": result.product,
            "target_market": result.target_market,
            "business_model": result.business_model,
            "stage": result.stage,
            "traction": result.traction,
            "ask": result.ask,
        }

        present = []
        missing = []
        vague = list(vague_from_llm)

        for fname, fval in all_fields.items():
            val = str(fval).strip()
            if not val or val.lower() in ("unknown", "n/a", "none", "not specified", "not mentioned", ""):
                missing.append(fname)
            elif fname in vague_from_llm:
                vague.append(fname)
                present.append(fname)
            else:
                present.append(fname)

        # Deduplicate vague
        vague = list(dict.fromkeys(vague))

        result.fields_present = present
        result.fields_missing = missing
        result.fields_vague = vague

        # Calculate data_quality: critical fields worth 60%, important 25%, optional 15%
        critical_score = sum(
            1 for f in _CRITICAL_FIELDS if f in present and f not in vague
        ) / len(_CRITICAL_FIELDS)
        important_score = sum(
            1 for f in _IMPORTANT_FIELDS if f in present and f not in vague
        ) / len(_IMPORTANT_FIELDS)
        optional_count = sum(1 for f in _OPTIONAL_FIELDS if f in present)
        optional_max = len(_OPTIONAL_FIELDS)
        optional_score = optional_count / optional_max if optional_max > 0 else 1.0

        # Vague fields count as half-present
        for f in vague:
            if f in _CRITICAL_FIELDS:
                critical_score += 0.5 / len(_CRITICAL_FIELDS)
            elif f in _IMPORTANT_FIELDS:
                important_score += 0.5 / len(_IMPORTANT_FIELDS)

        # Cap at 1.0
        critical_score = min(critical_score, 1.0)
        important_score = min(important_score, 1.0)

        result.data_quality = round(
            critical_score * 0.60 + important_score * 0.25 + optional_score * 0.15,
            2,
        )

        return result

    # ── Phase 1: Research ─────────────────────────────────────────

    def research(
        self,
        exec_summary: str,
        depth: str = "standard",
        extraction: Optional[ExtractionResult] = None,
    ) -> ResearchReport:
        """Parse exec summary, generate research queries, gather context from all sources."""
        cfg = _DEPTH_CONFIG.get(depth, _DEPTH_CONFIG["standard"])
        data_sources_used = []

        # Step 1: Extract structured info (reuse if already done)
        if extraction is None:
            extraction = self.extract_and_validate(exec_summary)

        company = extraction.company or "Unknown"
        industry = extraction.industry or "Unknown"
        product = extraction.product or "Unknown"
        target_market = extraction.target_market or ""
        business_model = extraction.business_model or ""

        # Step 2: Generate research queries
        query_prompt = self.llm.chat(
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"Generate exactly {cfg['query_count']} research queries to evaluate this business. "
                        "Cover: market size, competitors, recent news, regulatory landscape, "
                        "demand signals, and similar companies' outcomes. "
                        "Return one query per line, no numbering or bullets."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Company: {company}\nIndustry: {industry}\nProduct: {product}\n"
                        f"Target market: {target_market}\nBusiness model: {business_model}"
                    ),
                },
            ],
            temperature=0.5,
            max_tokens=500,
        )
        queries = [q.strip() for q in query_prompt.strip().split("\n") if q.strip()]

        # Step 3: Search ChromaDB for each query (if any graphs exist)
        context_facts = []
        try:
            from subconscious.memory import EpisodicMemoryStore
            store = EpisodicMemoryStore(persist_path=Config.CHROMADB_PERSIST_PATH)
            # Search across all available collections
            collections = store.client.list_collections()
            episode_collections = [
                c.name for c in collections if c.name.endswith("_episodes")
            ]
            for col_name in episode_collections[:5]:  # cap at 5 graphs
                graph_id = col_name.replace("_episodes", "")
                for query in queries[:cfg["query_count"]]:
                    results = store.search(
                        graph_id=graph_id,
                        query=query,
                        limit=cfg["search_limit"] // max(len(queries), 1),
                    )
                    for r in results:
                        if r.get("document") and r["document"] not in context_facts:
                            context_facts.append(r["document"])
            if context_facts:
                data_sources_used.append("chromadb")
        except Exception as e:
            logger.warning(f"ChromaDB search during BI research failed: {e}")

        # Step 3b: Search Mem0 for relationship-aware context
        mem0_context = []
        mem0 = self._get_mem0()
        if mem0:
            try:
                mem0_results = mem0.recall_industry_context(industry, limit=5)
                for m in mem0_results:
                    memory_text = m.get("memory", "")
                    if memory_text and memory_text not in mem0_context:
                        mem0_context.append(memory_text)
                if mem0_context:
                    data_sources_used.append("mem0")
                    logger.info(f"[BI] Mem0 recalled {len(mem0_context)} relevant memories")
            except Exception as e:
                logger.warning(f"Mem0 search during BI research failed: {e}")

        # Step 3c: Fetch live financial data via OpenBB
        financial_data = {}
        market_data_svc = self._get_market_data()
        if market_data_svc:
            try:
                financial_data = market_data_svc.get_industry_context(company, industry)
                if financial_data.get("data_sources"):
                    data_sources_used.append("openbb")
                    logger.info(
                        f"[BI] OpenBB provided: {', '.join(financial_data['data_sources'])}"
                    )
            except Exception as e:
                logger.warning(f"OpenBB data fetch during BI research failed: {e}")

        # Step 4: Live web research (SearXNG + Crawl4AI/browser)
        browser_queries = [q for q in queries if any(
            kw in q.lower() for kw in ("news", "recent", "2025", "2026", "latest", "announced")
        )]
        web_findings = []

        # Use web research for standard (news queries only) and deep (all queries)
        research_queries = browser_queries if depth != "deep" else queries
        if research_queries:
            try:
                from .web_researcher import WebResearcher
                researcher = WebResearcher()
                web_results = researcher.research_queries(
                    queries=research_queries,
                    max_results_per_query=3,
                )
                for wr in web_results:
                    if wr.get("success") and wr.get("findings"):
                        web_findings.append(wr["findings"][:500])
                if web_findings:
                    method = web_results[0].get("method", "browser") if web_results else "browser"
                    data_sources_used.append(f"web_research({method})")
                logger.info(
                    f"[BI] Web research returned {len(web_findings)} findings "
                    f"from {len(research_queries)} queries"
                )
            except Exception as e:
                logger.warning(f"Web research failed (non-fatal): {e}")

        # Step 5: Synthesize all findings via LLM
        context_block = ""
        if context_facts:
            context_block = (
                "\n\nRelevant knowledge from existing data:\n"
                + "\n".join(f"- {f[:200]}" for f in context_facts[:30])
            )
        if mem0_context:
            context_block += (
                "\n\nRelated past analyses and knowledge (Mem0):\n"
                + "\n".join(f"- {m[:300]}" for m in mem0_context[:10])
            )
        if financial_data and financial_data.get("data_sources"):
            context_block += "\n\nLive financial data (OpenBB):\n"
            if financial_data.get("overview"):
                ov = financial_data["overview"]
                context_block += (
                    f"- Company: {ov.get('name', '')} | Sector: {ov.get('sector', '')} | "
                    f"Market Cap: {ov.get('market_cap', 'N/A')} | "
                    f"Employees: {ov.get('employees', 'N/A')}\n"
                )
            if financial_data.get("stock_price"):
                sp = financial_data["stock_price"]
                context_block += (
                    f"- Stock: ${sp.get('price', 'N/A')} | "
                    f"Change: {sp.get('change_percent', 'N/A')}% | "
                    f"52w High: ${sp.get('year_high', 'N/A')} | "
                    f"52w Low: ${sp.get('year_low', 'N/A')}\n"
                )
            if financial_data.get("financial_metrics"):
                fm = financial_data["financial_metrics"]
                context_block += (
                    f"- P/E: {fm.get('pe_ratio', 'N/A')} | "
                    f"Revenue Growth: {fm.get('revenue_growth', 'N/A')} | "
                    f"ROE: {fm.get('roe', 'N/A')}\n"
                )
            if financial_data.get("company_news"):
                context_block += "- Recent news:\n"
                for n in financial_data["company_news"][:3]:
                    context_block += f"  - [{n.get('date', '')}] {n.get('title', '')}\n"
        if web_findings:
            context_block += (
                "\n\nLive web research findings:\n"
                + "\n".join(f"- {f[:300]}" for f in web_findings[:10])
            )

        synthesis = self.llm.chat_json(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a business research analyst. Synthesize research findings into "
                        "a structured report. Return JSON with keys: "
                        "market_data (list of findings), competitors (list of names/descriptions), "
                        "news (list of relevant items), trends (list), sentiment (bullish/neutral/bearish)."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Executive summary:\n{exec_summary}\n\n"
                        f"Company: {company} | Industry: {industry} | Product: {product}"
                        f"{context_block}\n\n"
                        "Synthesize all available information into research findings."
                    ),
                },
            ],
            temperature=0.3,
            max_tokens=cfg["max_tokens"],
        )

        return ResearchReport(
            company=company,
            industry=industry,
            product=product,
            market_data=synthesis.get("market_data", []),
            competitors=synthesis.get("competitors", []),
            news=synthesis.get("news", []),
            trends=synthesis.get("trends", []),
            sentiment=synthesis.get("sentiment", "neutral"),
            context_facts=context_facts[:20],
            browser_queries=browser_queries,
            financial_data=financial_data,
            mem0_context=mem0_context,
            data_sources_used=data_sources_used,
        )

    # ── Phase 2: Predict ──────────────────────────────────────────

    _SCORING_SYSTEM_PROMPT = (
        "You are a venture analyst scoring a business opportunity. "
        "Score each of these 7 dimensions from 1-10 with reasoning:\n"
        "1. market_timing — Is the market ready? Growing or saturated?\n"
        "2. competition_landscape — How crowded? Any moats?\n"
        "3. business_model_viability — Does the revenue model make sense?\n"
        "4. team_execution_signals — Any evidence of execution capability?\n"
        "5. regulatory_news_environment — Tailwinds or headwinds?\n"
        "6. social_proof_demand — Evidence of market demand?\n"
        "7. pattern_match — Do similar companies succeed or fail?\n\n"
        "Return JSON with key 'dimensions' containing a list of objects, "
        "each with: name (str), score (int 1-10), reasoning (str). "
        "Also include 'overall_reasoning' (str) and 'confidence' (float 0-1)."
    )

    def _predict_single(
        self, exec_summary: str, research_context: str, llm: LLMClient
    ) -> Tuple[List[DimensionScore], str, float]:
        """Run prediction with a single LLM. Returns (dimensions, reasoning, confidence)."""
        scoring = llm.chat_json(
            messages=[
                {"role": "system", "content": self._SCORING_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Executive summary:\n{exec_summary}\n\n"
                        f"Research findings:\n{research_context}"
                    ),
                },
            ],
            temperature=0.3,
            max_tokens=3000,
        )

        dimensions = []
        for d in scoring.get("dimensions", []):
            dimensions.append(DimensionScore(
                name=d.get("name", "unknown"),
                score=float(d.get("score", 5)),
                reasoning=d.get("reasoning", ""),
            ))

        return (
            dimensions,
            scoring.get("overall_reasoning", ""),
            float(scoring.get("confidence", 0.5)),
        )

    @staticmethod
    def _score_to_verdict(overall: float) -> str:
        if overall > 7.5:
            return "Strong Hit"
        elif overall > 6.0:
            return "Likely Hit"
        elif overall > 4.5:
            return "Uncertain"
        elif overall > 3.0:
            return "Likely Miss"
        else:
            return "Strong Miss"

    @staticmethod
    def _calc_weighted_score(dimensions: List[DimensionScore]) -> float:
        total_weight = 0.0
        weighted_sum = 0.0
        for dim in dimensions:
            weight = _DIMENSION_WEIGHTS.get(dim.name, 1.0 / 7)
            weighted_sum += dim.score * weight
            total_weight += weight
        return round(weighted_sum / total_weight, 2) if total_weight > 0 else 5.0

    def predict(
        self, exec_summary: str, research: ResearchReport, use_council: bool = False
    ) -> Prediction:
        """
        Score across 7 dimensions, classify hit/miss.
        If use_council=True, runs multiple LLMs in parallel and reconciles.
        """
        research_context = json.dumps(research.to_dict(), indent=2)

        if not use_council:
            # Single model path
            dimensions, reasoning, confidence = self._predict_single(
                exec_summary, research_context, self.llm
            )
            overall = self._calc_weighted_score(dimensions)
            return Prediction(
                dimensions=dimensions,
                overall_score=overall,
                verdict=self._score_to_verdict(overall),
                confidence=confidence,
                reasoning=reasoning,
            )

        # ── Council path: run multiple models in parallel ─────────
        logger.info("[BI] LLM Council activated — querying multiple models in parallel")

        model_results: Dict[str, Tuple[List[DimensionScore], str, float]] = {}
        model_errors: Dict[str, str] = {}

        def _query_model(model_cfg: dict):
            label = model_cfg["label"]
            try:
                llm = LLMClient(model=model_cfg["model"])
                dims, reasoning, conf = self._predict_single(
                    exec_summary, research_context, llm
                )
                return label, dims, reasoning, conf
            except Exception as e:
                logger.warning(f"[BI Council] {label} failed: {e}")
                return label, None, str(e), 0.0

        with ThreadPoolExecutor(max_workers=len(_COUNCIL_MODELS)) as pool:
            futures = [pool.submit(_query_model, m) for m in _COUNCIL_MODELS]
            for future in as_completed(futures):
                label, dims, reasoning, conf = future.result()
                if dims is not None:
                    model_results[label] = (dims, reasoning, conf)
                else:
                    model_errors[label] = reasoning

        # If no model returned results, fall back to primary
        if not model_results:
            logger.warning("[BI Council] All models failed — falling back to primary")
            dimensions, reasoning, confidence = self._predict_single(
                exec_summary, research_context, self.llm
            )
            overall = self._calc_weighted_score(dimensions)
            return Prediction(
                dimensions=dimensions,
                overall_score=overall,
                verdict=self._score_to_verdict(overall),
                confidence=confidence,
                reasoning=reasoning,
            )

        # If only one model returned, use it directly
        if len(model_results) == 1:
            label = list(model_results.keys())[0]
            dims, reasoning, conf = model_results[label]
            overall = self._calc_weighted_score(dims)
            return Prediction(
                dimensions=dims,
                overall_score=overall,
                verdict=self._score_to_verdict(overall),
                confidence=conf,
                reasoning=reasoning,
                council_used=True,
                council_models=[label],
            )

        # ── Reconcile multiple model results ──────────────────────

        # Build per-dimension scores from each model
        # Key: dimension_name → {model_label: DimensionScore}
        dim_by_name: Dict[str, Dict[str, DimensionScore]] = {}
        for label, (dims, _, _) in model_results.items():
            for d in dims:
                dim_by_name.setdefault(d.name, {})[label] = d

        # Per-model overall scores for output
        per_model_scores: Dict[str, Dict[str, float]] = {}
        for label, (dims, _, _) in model_results.items():
            overall = self._calc_weighted_score(dims)
            per_model_scores[label] = {
                "overall": overall,
                **{d.name: d.score for d in dims},
            }

        # Average dimensions + detect disagreements
        reconciled_dims: List[DimensionScore] = []
        contested: List[Dict[str, Any]] = []

        all_dim_names = list(dict.fromkeys(
            d.name for dims, _, _ in model_results.values() for d in dims
        ))

        for dim_name in all_dim_names:
            scores_for_dim = dim_by_name.get(dim_name, {})
            if not scores_for_dim:
                continue

            scores = [d.score for d in scores_for_dim.values()]
            avg_score = round(sum(scores) / len(scores), 1)

            # Combine reasoning from all models
            reasonings = [
                f"[{label}] {d.reasoning}"
                for label, d in scores_for_dim.items()
            ]
            combined_reasoning = " | ".join(reasonings)

            reconciled_dims.append(DimensionScore(
                name=dim_name,
                score=avg_score,
                reasoning=combined_reasoning,
            ))

            # Check for disagreement
            spread = max(scores) - min(scores)
            if spread >= _DISAGREEMENT_THRESHOLD:
                contested.append({
                    "dimension": dim_name,
                    "spread": spread,
                    "scores": {
                        label: d.score for label, d in scores_for_dim.items()
                    },
                })

        # Overall score from reconciled dimensions
        overall = self._calc_weighted_score(reconciled_dims)

        # Confidence: base on average model confidence, penalize disagreements
        avg_confidence = sum(
            conf for _, (_, _, conf) in model_results.items()
        ) / len(model_results)
        # Each contested dimension lowers confidence by 0.05
        confidence_penalty = len(contested) * 0.05
        final_confidence = round(max(0.1, min(1.0, avg_confidence - confidence_penalty)), 2)

        # Combine reasoning
        all_reasonings = [
            f"[{label}] {reasoning}"
            for label, (_, reasoning, _) in model_results.items()
        ]
        combined_overall_reasoning = " | ".join(all_reasonings)

        if contested:
            combined_overall_reasoning += (
                f" | COUNCIL NOTE: {len(contested)} contested dimension(s) "
                f"where models disagreed by {_DISAGREEMENT_THRESHOLD}+ points: "
                + ", ".join(c["dimension"] for c in contested)
            )

        return Prediction(
            dimensions=reconciled_dims,
            overall_score=overall,
            verdict=self._score_to_verdict(overall),
            confidence=final_confidence,
            reasoning=combined_overall_reasoning,
            council_used=True,
            council_models=list(model_results.keys()),
            contested_dimensions=contested,
            model_scores=per_model_scores,
        )

    # ── Phase 3: Plan ─────────────────────────────────────────────

    def plan(
        self,
        exec_summary: str,
        research: ResearchReport,
        prediction: Prediction,
    ) -> StrategyPlan:
        """Generate strategic recommendations based on research + prediction."""
        context = (
            f"Executive summary:\n{exec_summary}\n\n"
            f"Research sentiment: {research.sentiment}\n"
            f"Competitors: {', '.join(research.competitors[:5])}\n"
            f"Key trends: {', '.join(research.trends[:5])}\n\n"
            f"Prediction verdict: {prediction.verdict} (score: {prediction.overall_score}/10)\n"
            f"Prediction reasoning: {prediction.reasoning}\n"
        )

        # Include financial data if available
        if research.financial_data and research.financial_data.get("overview"):
            ov = research.financial_data["overview"]
            context += (
                f"\nFinancial context: {ov.get('name', '')} | "
                f"Market Cap: {ov.get('market_cap', 'N/A')} | "
                f"Sector: {ov.get('sector', '')}\n"
            )

        strategy = self.llm.chat_json(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strategy consultant. Given business research and a prediction, "
                        "create an actionable strategy plan. Return JSON with:\n"
                        "- risks: list of {risk, severity (high/medium/low), mitigation}\n"
                        "- next_moves: list of {action, priority (1-5), effort (low/medium/high), impact (low/medium/high)}\n"
                        "- go_to_market: list of GTM suggestions\n"
                        "- validation_experiments: list of cheapest ways to validate assumptions\n"
                        "- timeline_90_day: list of {week_range, milestone, deliverable}\n"
                        "Be specific and actionable. Top 3 risks, top 5 next moves."
                    ),
                },
                {"role": "user", "content": context},
            ],
            temperature=0.4,
            max_tokens=3000,
        )

        return StrategyPlan(
            risks=strategy.get("risks", [])[:3],
            next_moves=strategy.get("next_moves", [])[:5],
            go_to_market=strategy.get("go_to_market", []),
            validation_experiments=strategy.get("validation_experiments", []),
            timeline_90_day=strategy.get("timeline_90_day", []),
        )

    # ── Orchestrator ──────────────────────────────────────────────

    def analyze(
        self, exec_summary: str, depth: str = "standard"
    ) -> dict:
        """
        Full pipeline: extract → validate → research → predict → plan.
        Returns a dict. If critical data is missing, returns a needs_more_info
        response instead of a full analysis.
        """
        analysis_id = f"bi_{uuid.uuid4().hex[:12]}"
        logger.info(f"[BI:{analysis_id}] Starting {depth} analysis")

        # Phase 0: Extract and validate
        logger.info(f"[BI:{analysis_id}] Phase 0: Extract & Validate")
        extraction = self.extract_and_validate(exec_summary)

        # Check if critical fields are missing
        critical_missing = [
            f for f in _CRITICAL_FIELDS if f in extraction.fields_missing
        ]
        if critical_missing:
            logger.warning(
                f"[BI:{analysis_id}] Insufficient data — missing critical fields: "
                f"{critical_missing}"
            )
            return {
                "status": "needs_more_info",
                "analysis_id": analysis_id,
                "data_quality": extraction.data_quality,
                "fields_present": extraction.fields_present,
                "fields_missing": extraction.fields_missing,
                "fields_vague": extraction.fields_vague,
                "missing_critical": critical_missing,
                "message": (
                    f"Cannot produce a reliable analysis — missing critical information: "
                    f"{', '.join(critical_missing)}. "
                    f"Please provide at least: company name, industry, and product/service description."
                ),
                "template": EXEC_SUMMARY_TEMPLATE["template"],
                "example": EXEC_SUMMARY_TEMPLATE["example"],
            }

        # Phase 1: Research (pass extraction to avoid re-extracting)
        logger.info(f"[BI:{analysis_id}] Phase 1: Research")
        research = self.research(exec_summary, depth=depth, extraction=extraction)

        # Phase 1b: CrewAI multi-agent analysis (deep mode, if available)
        crew_output = None
        if depth == "deep":
            crew = self._get_crew()
            if crew:
                try:
                    logger.info(f"[BI:{analysis_id}] Phase 1b: CrewAI multi-agent analysis")
                    crew_result = crew.analyze_business(
                        company=extraction.company,
                        industry=extraction.industry,
                        product=extraction.product,
                        target_market=extraction.target_market,
                        business_model=extraction.business_model,
                        exec_summary=exec_summary,
                        context="\n".join(research.context_facts[:10]),
                    )
                    if crew_result.get("success"):
                        crew_output = crew_result.get("crew_output", "")
                        research.data_sources_used.append("crewai")
                        logger.info(f"[BI:{analysis_id}] CrewAI analysis complete")
                except Exception as e:
                    logger.warning(f"[BI:{analysis_id}] CrewAI failed (non-fatal): {e}")

        # Phase 2: Predict (council on deep mode)
        use_council = _DEPTH_CONFIG.get(depth, {}).get("council", False)
        logger.info(
            f"[BI:{analysis_id}] Phase 2: Predict"
            f"{' (LLM Council)' if use_council else ''}"
        )

        # If CrewAI produced output, inject it into the research for prediction
        if crew_output:
            research.context_facts.append(
                f"Multi-agent analysis: {crew_output[:2000]}"
            )

        prediction = self.predict(exec_summary, research, use_council=use_council)

        # Phase 3: Plan
        logger.info(f"[BI:{analysis_id}] Phase 3: Plan")
        strategy = self.plan(exec_summary, research, prediction)

        now = datetime.now(timezone.utc).isoformat()

        analysis = FullAnalysis(
            id=analysis_id,
            exec_summary=exec_summary,
            research=research,
            prediction=prediction,
            plan=strategy,
            created_at=now,
            depth=depth,
            data_quality=extraction.data_quality,
        )

        # Store in ChromaDB for future recall
        self._store_analysis(analysis)

        # Store in Mem0 for relationship-aware future recall
        self._store_analysis_mem0(analysis)

        logger.info(
            f"[BI:{analysis_id}] Complete — verdict: {prediction.verdict} "
            f"(score: {prediction.overall_score}) "
            f"data_quality: {extraction.data_quality} "
            f"sources: {', '.join(research.data_sources_used)}"
        )

        result = analysis.to_dict()
        result["status"] = "complete"
        # Include quality metadata so consumers know how much to trust the output
        result["fields_present"] = extraction.fields_present
        result["fields_missing"] = extraction.fields_missing
        result["fields_vague"] = extraction.fields_vague
        result["data_sources_used"] = research.data_sources_used
        if extraction.data_quality < 0.7:
            result["quality_warning"] = (
                f"Data quality is {extraction.data_quality:.0%} — "
                f"missing: {', '.join(extraction.fields_missing)}. "
                f"Results may be less reliable. Consider providing more detail."
            )
        return result

    def _store_analysis(self, analysis: FullAnalysis):
        """Store the full analysis in ChromaDB for future reference."""
        try:
            from subconscious.memory import EpisodicMemoryStore
            store = EpisodicMemoryStore(persist_path=Config.CHROMADB_PERSIST_PATH)

            # Use a dedicated BI graph
            graph_id = "bi_analyses"
            store.client.get_or_create_collection(
                name=f"{graph_id}_episodes",
                metadata={"graph_name": "Business Intelligence Analyses", "type": "episodes"},
            )

            # Store as a searchable episode
            summary_doc = (
                f"BI Analysis [{analysis.prediction.verdict}] for {analysis.research.company} "
                f"({analysis.research.industry}): {analysis.exec_summary[:300]}\n"
                f"Score: {analysis.prediction.overall_score}/10 | "
                f"Sentiment: {analysis.research.sentiment}"
            )

            store.add_episodes(
                graph_id=graph_id,
                documents=[summary_doc],
                metadatas=[{
                    "analysis_id": analysis.id,
                    "company": analysis.research.company,
                    "industry": analysis.research.industry,
                    "verdict": analysis.prediction.verdict,
                    "score": analysis.prediction.overall_score,
                    "depth": analysis.depth,
                    "created_at": analysis.created_at,
                    "full_result": json.dumps(analysis.to_dict())[:10000],
                }],
                ids=[analysis.id],
            )
            logger.info(f"[BI] Stored analysis {analysis.id} in ChromaDB")
        except Exception as e:
            logger.warning(f"[BI] Failed to store analysis: {e}\n{traceback.format_exc()}")

    def _store_analysis_mem0(self, analysis: FullAnalysis):
        """Store the analysis in Mem0 for relationship-aware future recall."""
        mem0 = self._get_mem0()
        if not mem0:
            return

        try:
            key_findings = analysis.prediction.reasoning[:200]
            mem0.store_bi_analysis(
                analysis_id=analysis.id,
                company=analysis.research.company,
                industry=analysis.research.industry,
                verdict=analysis.prediction.verdict,
                score=analysis.prediction.overall_score,
                key_findings=key_findings,
                exec_summary=analysis.exec_summary,
            )
            logger.info(f"[BI] Stored analysis {analysis.id} in Mem0")
        except Exception as e:
            logger.warning(f"[BI] Failed to store analysis in Mem0: {e}")

    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve past analyses from ChromaDB."""
        try:
            from subconscious.memory import EpisodicMemoryStore
            store = EpisodicMemoryStore(persist_path=Config.CHROMADB_PERSIST_PATH)

            try:
                collection = store.client.get_collection("bi_analyses_episodes")
            except Exception:
                return []

            count = collection.count()
            if count == 0:
                return []

            data = collection.get(limit=min(limit, count))
            results = []
            for i, doc_id in enumerate(data.get("ids", [])):
                meta = data["metadatas"][i] if data.get("metadatas") else {}
                full_json = meta.get("full_result", "{}")
                try:
                    full = json.loads(full_json)
                except (json.JSONDecodeError, TypeError):
                    full = {}
                results.append({
                    "id": doc_id,
                    "company": meta.get("company", ""),
                    "industry": meta.get("industry", ""),
                    "verdict": meta.get("verdict", ""),
                    "score": meta.get("score", 0),
                    "created_at": meta.get("created_at", ""),
                    "full_analysis": full,
                })
            return results
        except Exception as e:
            logger.warning(f"[BI] Failed to retrieve history: {e}")
            return []
