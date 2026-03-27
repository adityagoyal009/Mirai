"""
Fact Checker — validates factual claims from swarm agent reasoning
against the research data that was provided to them.
"""

import json
from typing import Dict, List, Any

from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from ..config import Config

logger = get_logger('mirofish.factcheck')


def check_facts(agent_reasonings: List[str], research_context: str) -> Dict[str, Any]:
    """
    Extract top factual claims from agent reasoning and cross-check
    against research data. Returns fact check report.
    """
    if not agent_reasonings:
        return {"verified": 0, "unverified": 0, "contradicted": 0, "claims": []}

    # Combine top reasoning samples
    sample = "\n".join(f"- {r[:200]}" for r in agent_reasonings[:30])

    try:
        llm = LLMClient()
        messages = [
            {"role": "system", "content": (
                "You are a fact checker. Given agent reasoning about a startup and "
                "the research data they were given, identify the top 15 factual claims "
                "and classify each as:\n"
                "- VERIFIED: claim is supported by the research data\n"
                "- UNVERIFIED: claim is plausible but not in the research data\n"
                "- CONTRADICTED: claim conflicts with the research data\n\n"
                "Return JSON: {\"claims\": [{\"claim\": \"...\", \"status\": \"VERIFIED|UNVERIFIED|CONTRADICTED\", "
                "\"evidence\": \"brief note\"}]}"
            )},
            {"role": "user", "content": (
                f"Agent Reasoning Samples:\n{sample}\n\n"
                f"Research Data:\n{research_context[:4000]}"
            )},
        ]
        result = llm.chat_json(messages=messages, temperature=0.2, max_tokens=2000)
        claims = result.get("claims", [])

        verified = sum(1 for c in claims if c.get("status") == "VERIFIED")
        unverified = sum(1 for c in claims if c.get("status") == "UNVERIFIED")
        contradicted = sum(1 for c in claims if c.get("status") == "CONTRADICTED")

        logger.info(f"[FactCheck] {verified} verified, {unverified} unverified, {contradicted} contradicted")

        trust_score = round(verified / max(len(claims), 1), 2)
        critical_contradictions = [
            c.get("claim", "") for c in claims
            if c.get("status") == "CONTRADICTED"
        ]

        return {
            "verified": verified,
            "unverified": unverified,
            "contradicted": contradicted,
            "claims": claims[:15],
            "trust_score": trust_score,
            "confidence_impact": trust_score,
            "critical_contradictions": critical_contradictions[:5],
        }

    except Exception as e:
        logger.warning(f"[FactCheck] Failed: {e}")
        return {"verified": 0, "unverified": 0, "contradicted": 0, "claims": [], "error": str(e)}
