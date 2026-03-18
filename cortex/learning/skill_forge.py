"""
Skill Forge — detects capability gaps from failures and (in Phase 2)
autonomously writes new skills to fill them.

MVP: detect gaps + log them. Skill writing is a future feature.
"""

import os
import sys
from typing import List

from .experience_store import Experience

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

_llm_client = None


def _get_llm():
    global _llm_client
    if _llm_client is None:
        from subconscious.swarm.utils.llm_client import LLMClient
        _llm_client = LLMClient()
    return _llm_client


class SkillForge:
    """Detects capability gaps and (future) writes new skills."""

    def __init__(self):
        self.skill_dir = os.environ.get(
            "MIRAI_SKILLS_DIR",
            os.path.expanduser("~/.mirai/skills/"),
        )
        self.detected_gaps: List[str] = []

    def detect_capability_gaps(self, recent_failures: List[Experience]) -> List[str]:
        """Analyze failures to identify missing capabilities."""
        if not recent_failures:
            return []

        failure_summaries = []
        for exp in recent_failures[:20]:
            failure_summaries.append(
                f"- Action: {exp.action_type} | Situation: {exp.situation[:100]} | "
                f"Error: {exp.outcome[:100]}"
            )

        prompt_messages = [
            {
                "role": "system",
                "content": (
                    "You are analyzing an AI agent's failures to identify capability gaps. "
                    "A capability gap is a specific skill or tool the agent is missing. "
                    "Return JSON with key: gaps (list of concise gap descriptions, max 5)."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Recent failures ({len(recent_failures)}):\n"
                    + "\n".join(failure_summaries)
                    + "\n\nWhat specific capabilities is the agent missing?"
                ),
            },
        ]

        try:
            llm = _get_llm()
            result = llm.chat_json(messages=prompt_messages, temperature=0.3)
            gaps = result.get("gaps", [])[:5]

            for gap in gaps:
                print(f"[LEARNING] Capability gap detected: {gap}")
                if gap not in self.detected_gaps:
                    self.detected_gaps.append(gap)

            return gaps

        except Exception as e:
            print(f"[LEARNING] Skill forge LLM call failed: {e}")
            return []

    # ── Phase 2 stubs ────────────────────────────────────────────

    def research_solution(self, gap: str) -> str:
        """Research how to fill a capability gap. (Phase 2)"""
        print(f"[LEARNING] Research needed for gap: {gap}")
        return f"Research needed for: {gap}"

    def write_skill(self, gap: str, solution: str, skill_dir: str = None) -> str:
        """Write a new skill script to fill a gap. (Phase 2)"""
        print(f"[LEARNING] Skill writing not yet implemented for: {gap}")
        return ""

    def test_skill(self, skill_path: str) -> bool:
        """Test a written skill. (Phase 2)"""
        return False
