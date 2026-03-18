"""
Reflection Engine — periodic self-analysis of recent experiences.

Every N cycles, Mirai pauses to reflect: What patterns am I seeing?
What's working? What's failing? Updates a persistent Strategy Journal
that gets injected into every future system prompt.
"""

import os
import sys
import time
from dataclasses import dataclass, field
from typing import List, Optional

from .experience_store import Experience

# Ensure project root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

_llm_client = None


def _get_llm():
    global _llm_client
    if _llm_client is None:
        from subconscious.swarm.utils.llm_client import LLMClient
        _llm_client = LLMClient()
    return _llm_client


@dataclass
class ReflectionResult:
    """Output of a reflection cycle."""
    new_rules: List[str] = field(default_factory=list)
    failure_patterns: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    improvement_priorities: List[str] = field(default_factory=list)
    timestamp: str = ""


class ReflectionEngine:
    """Analyzes recent experiences and maintains a Strategy Journal."""

    def __init__(self):
        self.reflection_interval = int(os.environ.get("REFLECTION_INTERVAL", "100"))
        self.journal_path = os.environ.get(
            "MIRAI_JOURNAL_PATH",
            os.path.expanduser("~/.mirai/strategy_journal.md"),
        )

    def should_reflect(self, cycle_number: int) -> bool:
        return cycle_number > 0 and cycle_number % self.reflection_interval == 0

    def reflect(self, recent_experiences: List[Experience]) -> ReflectionResult:
        """Analyze recent experiences and extract patterns."""
        if not recent_experiences:
            return ReflectionResult()

        # Build experience summary for LLM
        exp_lines = []
        successes = 0
        failures = 0
        for exp in recent_experiences[:50]:
            status = "OK" if exp.success else "FAIL"
            if exp.success:
                successes += 1
            else:
                failures += 1
            exp_lines.append(
                f"- [{status}] cycle={exp.cycle_number} action={exp.action_type} "
                f"score={exp.score} | {exp.situation[:80]} → {exp.outcome[:80]}"
            )

        summary = "\n".join(exp_lines)

        prompt_messages = [
            {
                "role": "system",
                "content": (
                    "You are Mirai's self-reflection module. Analyze the recent experience log "
                    "and extract actionable patterns. Be concise — each rule should be one sentence. "
                    "Return JSON with keys: new_rules (list of behavioral rules to follow), "
                    "failure_patterns (list of recurring failure patterns to avoid), "
                    "strengths (list of things working well), "
                    "improvement_priorities (list of top 3 areas to improve)."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Recent experience log ({len(recent_experiences)} entries, "
                    f"{successes} successes, {failures} failures):\n\n{summary}\n\n"
                    "Analyze these experiences. What rules should I follow? "
                    "What failure patterns should I avoid? What am I good at? "
                    "What should I prioritize improving?"
                ),
            },
        ]

        try:
            llm = _get_llm()
            result = llm.chat_json(messages=prompt_messages, temperature=0.3)
            return ReflectionResult(
                new_rules=result.get("new_rules", []),
                failure_patterns=result.get("failure_patterns", []),
                strengths=result.get("strengths", []),
                improvement_priorities=result.get("improvement_priorities", []),
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )
        except Exception as e:
            print(f"[LEARNING] Reflection LLM call failed: {e}")
            return ReflectionResult(
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )

    def update_strategy_journal(self, reflection: ReflectionResult):
        """Merge new reflection into the persistent Strategy Journal."""
        os.makedirs(os.path.dirname(self.journal_path), exist_ok=True)

        existing = self._load_journal_sections()

        # Merge with dedup
        existing["rules"] = self._merge_dedup(existing.get("rules", []), reflection.new_rules)
        existing["failure_patterns"] = self._merge_dedup(existing.get("failure_patterns", []), reflection.failure_patterns)
        existing["strengths"] = self._merge_dedup(existing.get("strengths", []), reflection.strengths)
        existing["priorities"] = reflection.improvement_priorities or existing.get("priorities", [])

        # Write back
        lines = [
            f"# Mirai Strategy Journal",
            f"Last updated: {reflection.timestamp}",
            "",
            "## Rules",
        ]
        for r in existing["rules"][-20:]:  # cap at 20 rules
            lines.append(f"- {r}")

        lines.append("")
        lines.append("## Failure Patterns")
        for f in existing["failure_patterns"][-15:]:
            lines.append(f"- {f}")

        lines.append("")
        lines.append("## Strengths")
        for s in existing["strengths"][-10:]:
            lines.append(f"- {s}")

        lines.append("")
        lines.append("## Priorities")
        for p in existing["priorities"][:5]:
            lines.append(f"- {p}")

        with open(self.journal_path, "w") as f:
            f.write("\n".join(lines) + "\n")

        print(f"[LEARNING] Strategy journal updated: {len(existing['rules'])} rules, "
              f"{len(existing['failure_patterns'])} failure patterns")

    def load_strategy_journal(self) -> str:
        """Load the strategy journal content for system prompt injection."""
        try:
            with open(self.journal_path, "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            return ""

    def _load_journal_sections(self) -> dict:
        """Parse existing journal into sections."""
        sections = {"rules": [], "failure_patterns": [], "strengths": [], "priorities": []}
        try:
            with open(self.journal_path, "r") as f:
                content = f.read()
        except FileNotFoundError:
            return sections

        current_section = None
        section_map = {
            "## Rules": "rules",
            "## Failure Patterns": "failure_patterns",
            "## Strengths": "strengths",
            "## Priorities": "priorities",
        }

        for line in content.split("\n"):
            stripped = line.strip()
            if stripped in section_map:
                current_section = section_map[stripped]
            elif current_section and stripped.startswith("- "):
                sections[current_section].append(stripped[2:])

        return sections

    @staticmethod
    def _merge_dedup(existing: List[str], new: List[str]) -> List[str]:
        """Merge lists, dedup by normalized comparison."""
        normalized = {item.lower().strip() for item in existing}
        merged = list(existing)
        for item in new:
            if item.lower().strip() not in normalized:
                merged.append(item)
                normalized.add(item.lower().strip())
        return merged
