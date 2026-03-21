"""
Persona Engine — loads and selects personas from the FinePersonas dataset.

Provides two modes:
  1. Dataset mode: Selects from 21M real personas (when downloaded)
  2. Generator mode: Generates personas on-the-fly from trait combinations (fallback)

The engine matches personas to the startup being evaluated by label relevance.
"""

import json
import os
import random
import linecache
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from ..utils.logger import get_logger

logger = get_logger('mirofish.personas')

_DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
_PERSONAS_FILE = os.path.join(_DATA_DIR, 'personas.jsonl')
_INDEX_FILE = os.path.join(_DATA_DIR, 'label_index.json')

# ── Trait-based generator (fallback when dataset not available) ────

ROLES = [
    "Angel Investor", "Seed VC", "Series-A VC", "Series-B VC", "Growth VC",
    "PE Partner", "Family Office Manager", "Corporate VC", "Impact Investor",
    "Hedge Fund Analyst", "Investment Banker", "Sovereign Wealth Fund Manager",
    "Target Customer (Enterprise)", "Target Customer (SMB)", "Target Customer (Consumer)",
    "Non-Target Consumer", "Enterprise IT Director", "Procurement Manager",
    "Startup Founder (Failed)", "Startup Founder (Successful)", "Serial Entrepreneur",
    "CTO", "CMO", "CFO", "COO", "VP Engineering", "VP Sales",
    "Competitor CEO", "Competitor Product Manager", "Big Tech PM",
    "Industry Analyst (Gartner)", "Industry Analyst (Forrester)",
    "Tech Journalist", "Investigative Reporter",
    "Regulatory Expert", "Patent Attorney", "Data Privacy Officer",
    "Domain Expert", "Academic Researcher", "Professor of Entrepreneurship",
    "Supply Chain Manager", "Operations Expert",
    "Behavioral Economist", "UX Researcher", "Brand Strategist",
    "Market Strategist (BCG)", "Market Strategist (McKinsey)",
    "Macro Economist", "Emerging Markets Specialist",
    "Insurance Underwriter", "Risk Analyst",
    "Open Source Advocate", "Cybersecurity Expert", "Platform Risk Analyst",
    "Government Policy Advisor", "Lobbyist",
    "Retail Investor", "Crypto Native", "Real Estate Investor",
]

MBTI_TYPES = [
    "INTJ", "INTP", "ENTJ", "ENTP",
    "INFJ", "INFP", "ENFJ", "ENFP",
    "ISTJ", "ISFJ", "ESTJ", "ESFJ",
    "ISTP", "ISFP", "ESTP", "ESFP",
]

RISK_PROFILES = ["very conservative", "conservative", "moderate", "aggressive", "very aggressive"]

EXPERIENCE_LEVELS = [
    "junior (2-3 years)", "mid-career (5-8 years)", "senior (10-15 years)",
    "veteran (20+ years)", "legendary (30+ years)",
]

BIASES = [
    "optimistic about new technology", "skeptical of hype",
    "data-driven and quantitative", "intuition-driven",
    "focused on unit economics", "focused on vision and TAM",
    "concerned about regulatory risk", "concerned about execution risk",
    "pattern-matches to past successes", "pattern-matches to past failures",
    "values team above all", "values market timing above all",
    "contrarian thinker", "consensus follower",
]

GEOGRAPHIC_LENS = [
    "Silicon Valley", "New York", "London", "Berlin", "Singapore",
    "Bangalore", "Tel Aviv", "Beijing", "Sao Paulo", "Lagos",
    "Tokyo", "Seoul", "Dubai", "Toronto", "Sydney",
]

INDUSTRY_FOCUS = [
    "SaaS", "FinTech", "HealthTech", "EdTech", "CleanTech", "DeepTech",
    "Consumer", "Enterprise", "Marketplace", "Hardware", "BioTech",
    "AI/ML", "Cybersecurity", "Gaming", "Media", "LegalTech",
    "PropTech", "InsurTech", "AgriTech", "SpaceTech", "Web3",
    "Robotics", "Logistics", "HRTech", "FoodTech", "RetailTech",
]


@dataclass
class Persona:
    name: str
    prompt: str
    source: str  # "dataset" or "generated"
    labels: List[str]


class PersonaEngine:
    """Loads and selects personas for swarm prediction."""

    def __init__(self):
        self._index: Optional[Dict] = None
        self._dataset_available = os.path.exists(_PERSONAS_FILE)
        self._persona_count = 0
        if self._dataset_available:
            self._persona_count = self._count_lines()
            logger.info(f"[Personas] Dataset loaded: {self._persona_count:,} personas")
        else:
            logger.info("[Personas] Dataset not found, using trait-based generator")

    _cached_line_count = None

    def _count_lines(self) -> int:
        if PersonaEngine._cached_line_count is not None:
            return PersonaEngine._cached_line_count
        try:
            # Use wc -l equivalent — much faster than Python iteration for large files
            import subprocess
            result = subprocess.run(['wc', '-l', _PERSONAS_FILE],
                                    capture_output=True, text=True, timeout=30)
            count = int(result.stdout.strip().split()[0])
            PersonaEngine._cached_line_count = count
            return count
        except Exception:
            try:
                with open(_PERSONAS_FILE, 'r') as f:
                    count = sum(1 for _ in f)
                PersonaEngine._cached_line_count = count
                return count
            except IOError:
                return 0

    def _load_index(self) -> Dict:
        if self._index is not None:
            return self._index
        try:
            with open(_INDEX_FILE, 'r') as f:
                self._index = json.load(f)
        except (IOError, json.JSONDecodeError):
            self._index = {}
        return self._index

    def _read_persona_at_line(self, line_num: int) -> Optional[Dict]:
        """Read a specific persona from the JSONL file by line number."""
        try:
            # linecache is 1-indexed
            line = linecache.getline(_PERSONAS_FILE, line_num + 1)
            if line:
                return json.loads(line)
        except (json.JSONDecodeError, IOError):
            pass
        return None

    def _find_relevant_indices(self, keywords: List[str], limit: int) -> List[int]:
        """Find persona indices matching any of the given keywords."""
        index = self._load_index()
        matched = set()
        for kw in keywords:
            kw_lower = kw.lower().strip()
            for label, data in index.items():
                if kw_lower in label:
                    if isinstance(data, list):
                        matched.update(data[:limit])
                    elif isinstance(data, dict):
                        matched.update(data.get('sample', [])[:limit])
                    if len(matched) >= limit * 3:
                        break
        return list(matched)

    def select_personas(self, count: int, industry: str = "",
                        product: str = "", keywords: List[str] = None) -> List[Persona]:
        """
        Select personas for swarm prediction.
        Mixes dataset personas (if available) with generated ones.
        """
        if keywords is None:
            keywords = []

        # Build search keywords from industry/product
        search_terms = list(keywords)
        if industry:
            search_terms.extend(industry.lower().split())
        if product:
            search_terms.extend([w for w in product.lower().split() if len(w) > 3])
        # Add generic business terms
        search_terms.extend([
            "business", "finance", "investment", "startup", "entrepreneur",
            "marketing", "technology", "management", "strategy", "economics",
            "customer", "consumer", "product", "market", "sales",
        ])

        personas: List[Persona] = []

        if self._dataset_available and self._persona_count > 0:
            # Get relevant personas from dataset
            relevant_indices = self._find_relevant_indices(search_terms, count * 2)

            # Mix: 60% relevant dataset personas, 20% random dataset, 20% generated
            relevant_count = int(count * 0.6)
            random_count = int(count * 0.2)
            generated_count = count - relevant_count - random_count

            # Pull relevant
            if relevant_indices:
                sampled = random.sample(
                    relevant_indices,
                    min(relevant_count, len(relevant_indices))
                )
                for idx in sampled:
                    data = self._read_persona_at_line(idx)
                    if data:
                        personas.append(Persona(
                            name=data['persona'][:80],
                            prompt=self._dataset_persona_to_prompt(data['persona']),
                            source="dataset",
                            labels=data.get('labels', []),
                        ))

            # Pull random from dataset for diversity
            if self._persona_count > 0:
                random_indices = random.sample(
                    range(self._persona_count),
                    min(random_count, self._persona_count)
                )
                for idx in random_indices:
                    data = self._read_persona_at_line(idx)
                    if data:
                        personas.append(Persona(
                            name=data['persona'][:80],
                            prompt=self._dataset_persona_to_prompt(data['persona']),
                            source="dataset",
                            labels=data.get('labels', []),
                        ))

            # Fill remaining with generated
            personas.extend(self._generate_personas(generated_count))
        else:
            # No dataset — all generated
            personas = self._generate_personas(count)

        # Ensure we have exactly the right count
        while len(personas) < count:
            personas.extend(self._generate_personas(count - len(personas)))
        personas = personas[:count]

        random.shuffle(personas)
        return personas

    @staticmethod
    def _dataset_persona_to_prompt(persona_text: str) -> str:
        """Convert a FinePersonas description into a startup evaluation prompt."""
        return (
            f"You are: {persona_text}\n\n"
            "You are evaluating a startup from your unique perspective and expertise. "
            "Consider how this startup's product, market, and business model relates to "
            "your domain knowledge and experience. Give your honest, informed assessment."
        )

    @staticmethod
    def _generate_personas(count: int) -> List[Persona]:
        """Generate personas from trait combinations."""
        personas = []
        for i in range(count):
            role = random.choice(ROLES)
            mbti = random.choice(MBTI_TYPES)
            risk = random.choice(RISK_PROFILES)
            exp = random.choice(EXPERIENCE_LEVELS)
            bias = random.choice(BIASES)
            geo = random.choice(GEOGRAPHIC_LENS)
            industry = random.choice(INDUSTRY_FOCUS)

            name = f"{role} ({mbti}, {geo})"
            prompt = (
                f"You are a {role} based in {geo} with {exp} of experience. "
                f"Your MBTI type is {mbti}. Your risk profile is {risk}. "
                f"You are {bias}. Your primary industry focus is {industry}.\n\n"
                f"Evaluate this startup from your unique perspective. "
                f"Your assessment should reflect your personality, experience level, "
                f"risk tolerance, and domain expertise."
            )
            personas.append(Persona(
                name=name,
                prompt=prompt,
                source="generated",
                labels=[role, industry, geo],
            ))
        return personas
