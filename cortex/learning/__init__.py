"""
Mirai Self-Learning System.

Three learning loops:
  1. Experience (every cycle) — store action→outcome pairs, recall before acting
  2. Reflection (every N cycles) — analyze patterns, update strategy journal
  3. Evolution (scheduled) — detect skill gaps, monitor market signals
"""

from .experience_store import ExperienceStore, Experience
from .reflection import ReflectionEngine, ReflectionResult
from .skill_forge import SkillForge
from .market_radar import MarketRadar, MarketWatch, MarketSignal

__all__ = [
    "ExperienceStore",
    "Experience",
    "ReflectionEngine",
    "ReflectionResult",
    "SkillForge",
    "MarketRadar",
    "MarketWatch",
    "MarketSignal",
]
