"""
Sensei (先生) — Multi-turn AI Mentor Session.

Each mentor is a persona-grounded LLM that converses with a founder
about their startup. Uses the same PersonaEngine as Mirai's swarm
but in conversational mode instead of scoring mode.

Usage:
    session = MentorSession(
        mentor_type="seed_vc",
        persona_prompt=persona.prompt,  # from PersonaEngine
        research_context=research_json,
        exec_summary=exec_summary,
    )
    opening = session.get_opening_message()
    response = session.get_mentor_response("What about our go-to-market?")
"""

import time
from typing import List, Dict, Optional
from dataclasses import dataclass, field

from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger

logger = get_logger('sensei.mentor_session')


# ── Mentor Type Definitions ──────────────────────────────────────

MENTOR_TYPES = {
    # Investor Mentors
    "seed_vc": {
        "name": "Seed VC Mentor",
        "zone": "investor",
        "role": "Seed VC (conviction-based)",
        "tagline": "Should you raise? How much? From whom?",
        "system_addendum": (
            "You are mentoring a founder on fundraising strategy. "
            "Focus on: whether they should raise now, how much, from whom, "
            "what milestones to hit before raising, and how to craft their pitch. "
            "Be specific about check sizes, round structures, and investor types."
        ),
    },
    "growth_vc": {
        "name": "Growth VC Mentor",
        "zone": "investor",
        "role": "Growth-Stage VC",
        "tagline": "How to scale from $1M to $10M ARR",
        "system_addendum": (
            "You are mentoring a founder on scaling. "
            "Focus on: metrics that matter at growth stage, team building, "
            "market expansion, and what breaks between $1M-$10M ARR. "
            "Share frameworks for scaling decisions."
        ),
    },
    "angel": {
        "name": "Angel Investor Mentor",
        "zone": "investor",
        "role": "Angel Investor (solo)",
        "tagline": "Is your story compelling enough for a check?",
        "system_addendum": (
            "You are mentoring a founder on early storytelling and conviction-building. "
            "Focus on: pitch narrative, founder-market fit, "
            "what makes an angel say yes in one meeting."
        ),
    },
    # Customer Mentors
    "enterprise_buyer": {
        "name": "Enterprise Buyer Mentor",
        "zone": "customer",
        "role": "Target Enterprise Buyer",
        "tagline": "Would I buy this? What's my objection?",
        "system_addendum": (
            "You are a potential enterprise customer evaluating this product. "
            "Focus on: procurement process, budget approval, integration concerns, "
            "ROI justification, and what would make you sign vs walk away."
        ),
    },
    "smb_owner": {
        "name": "SMB Owner Mentor",
        "zone": "customer",
        "role": "SMB Owner",
        "tagline": "Would my 50-person company use this?",
        "system_addendum": (
            "You run a small business. Focus on: immediate ROI, ease of use, "
            "price sensitivity, and whether your team would actually adopt this."
        ),
    },
    "end_user": {
        "name": "Target End-User Mentor",
        "zone": "customer",
        "role": "Target Consumer",
        "tagline": "Does this solve my daily pain?",
        "system_addendum": (
            "You are the exact target user for this product. "
            "Focus on: does it solve a real problem you have, "
            "would you pay for it, what's missing, what would delight you."
        ),
    },
    # Operator Mentors
    "startup_cto": {
        "name": "CTO Mentor",
        "zone": "operator",
        "role": "CTO (scaling)",
        "tagline": "Can you build this? What breaks at scale?",
        "system_addendum": (
            "You are mentoring on technical architecture and engineering. "
            "Focus on: tech stack choices, scalability concerns, "
            "hiring engineers, technical debt, and build vs buy decisions."
        ),
    },
    "cmo_growth": {
        "name": "CMO / Growth Mentor",
        "zone": "operator",
        "role": "CMO (B2B)",
        "tagline": "How do you acquire your first 100 customers?",
        "system_addendum": (
            "You are mentoring on go-to-market strategy. "
            "Focus on: customer acquisition channels, CAC, content strategy, "
            "PLG vs sales-led, and how to get from 0 to 100 customers."
        ),
    },
    "startup_cfo": {
        "name": "CFO Mentor",
        "zone": "operator",
        "role": "CFO",
        "tagline": "Do your numbers work? What's your burn?",
        "system_addendum": (
            "You are mentoring on financial planning. "
            "Focus on: unit economics, burn rate, runway, "
            "financial projections, and when/how much to raise."
        ),
    },
    # Expert Mentors
    "industry_analyst": {
        "name": "Industry Analyst Mentor",
        "zone": "analyst",
        "role": "Gartner Analyst",
        "tagline": "Where does this fit in the market landscape?",
        "system_addendum": (
            "You are a market analyst briefing a founder. "
            "Focus on: market sizing, competitive positioning, "
            "category creation, and technology adoption lifecycle."
        ),
    },
    "domain_expert": {
        "name": "Domain Expert Mentor",
        "zone": "analyst",
        "role": "Domain Expert",
        "tagline": "Deep expertise in your specific industry",
        "system_addendum": (
            "You are a domain expert in this startup's industry. "
            "Focus on: industry-specific challenges, regulatory landscape, "
            "technical feasibility, and insider knowledge."
        ),
    },
    "regulatory_expert": {
        "name": "Regulatory Expert Mentor",
        "zone": "analyst",
        "role": "Regulatory Expert (federal)",
        "tagline": "What legal/compliance risks should you know?",
        "system_addendum": (
            "You are advising on regulatory and compliance matters. "
            "Focus on: specific regulations, compliance costs, timelines, "
            "and how regulation can be a moat or a barrier."
        ),
    },
    # Challenge Mentors
    "devils_advocate": {
        "name": "Devil's Advocate Mentor",
        "zone": "contrarian",
        "role": "Devil's Advocate",
        "tagline": "Here's why this will fail. Convince me otherwise.",
        "system_addendum": (
            "Your job is to stress-test the founder's assumptions. "
            "Challenge every claim, find weaknesses, and force the founder "
            "to defend their position. Be tough but constructive — "
            "the goal is to make them stronger, not to crush them."
        ),
    },
    "competitor_ceo": {
        "name": "Competitor CEO Mentor",
        "zone": "contrarian",
        "role": "Competitor CEO (incumbent)",
        "tagline": "I'm your biggest competitor. What stops me from crushing you?",
        "system_addendum": (
            "You are the CEO of the largest competitor in this space. "
            "Tell the founder what you'd do to compete with them. "
            "Be honest about what worries you and what doesn't."
        ),
    },
    # Perspective Mentors
    "behavioral_economist": {
        "name": "Behavioral Economist Mentor",
        "zone": "wildcard",
        "role": "Behavioral Economist",
        "tagline": "Will users actually change their behavior for this?",
        "system_addendum": (
            "Focus on: adoption friction, habit formation, switching costs, "
            "behavioral nudges, and whether the product can change user behavior."
        ),
    },
    "brand_strategist": {
        "name": "Brand Strategist Mentor",
        "zone": "wildcard",
        "role": "Brand Strategist",
        "tagline": "What's your narrative? Can you build a brand?",
        "system_addendum": (
            "Focus on: brand positioning, storytelling, "
            "how to stand out in a crowded market, and building long-term brand equity."
        ),
    },
    "market_timer": {
        "name": "Market Timer Mentor",
        "zone": "wildcard",
        "role": "Market Timer",
        "tagline": "Is now the right moment? Too early? Too late?",
        "system_addendum": (
            "Focus purely on timing. Is the market ready? "
            "Are they too early, too late, or perfectly timed? "
            "What signals indicate the window is open?"
        ),
    },
    "impact_investor": {
        "name": "Impact Investor Mentor",
        "zone": "investor",
        "role": "Impact Investor (climate)",
        "tagline": "What's the social/environmental angle?",
        "system_addendum": (
            "Focus on: social/environmental impact measurement, "
            "impact-first vs profit-first tension, and whether "
            "the impact story strengthens or weakens the business case."
        ),
    },
}


@dataclass
class MentorSessionState:
    """Tracks a single mentor conversation."""
    mentor_id: str
    mentor_name: str
    mentor_type: str
    persona_prompt: str
    messages: List[Dict[str, str]] = field(default_factory=list)
    started_at: float = 0.0
    ended_at: float = 0.0
    max_duration: int = 15 * 60  # 15 minutes

    @property
    def is_expired(self) -> bool:
        if self.started_at == 0:
            return False
        return (time.time() - self.started_at) > self.max_duration

    @property
    def time_remaining(self) -> int:
        if self.started_at == 0:
            return self.max_duration
        return max(0, self.max_duration - int(time.time() - self.started_at))


class MentorSession:
    """Multi-turn AI mentor conversation grounded in research."""

    def __init__(self, research_context: str, exec_summary: str):
        self.research_context = research_context
        self.exec_summary = exec_summary
        self.sessions: Dict[str, MentorSessionState] = {}
        self.llm = LLMClient()
        logger.info("[Sensei] MentorSession created")

    def create_mentor(self, mentor_id: str, mentor_type: str,
                      persona_prompt: str) -> MentorSessionState:
        """Create a new mentor conversation."""
        mentor_def = MENTOR_TYPES.get(mentor_type, {})
        state = MentorSessionState(
            mentor_id=mentor_id,
            mentor_name=mentor_def.get("name", mentor_type),
            mentor_type=mentor_type,
            persona_prompt=persona_prompt,
        )
        self.sessions[mentor_id] = state
        logger.info(f"[Sensei] Created mentor: {state.mentor_name} ({mentor_id})")
        return state

    def get_opening(self, mentor_id: str) -> str:
        """Get mentor's opening message (starts the timer)."""
        state = self.sessions.get(mentor_id)
        if not state:
            return "Mentor not found."

        state.started_at = time.time()
        mentor_def = MENTOR_TYPES.get(state.mentor_type, {})
        system_addendum = mentor_def.get("system_addendum", "")

        system_prompt = self._build_system_prompt(state, system_addendum)

        # Mentor introduces themselves and asks first question
        opening_instruction = (
            "The founder has just walked into your office for a 15-minute mentor session. "
            "Introduce yourself in one sentence (your background, not your name). "
            "Then make your most important observation or ask your first probing question "
            "based on the research briefing. Be specific to THIS startup."
        )

        state.messages.append({"role": "user", "content": opening_instruction})

        try:
            response = self.llm.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    *state.messages,
                ],
                temperature=0.7,
                max_tokens=400,
            )
            state.messages.append({"role": "assistant", "content": response})
            return response
        except Exception as e:
            logger.warning(f"[Sensei] Opening failed for {mentor_id}: {e}")
            return "I'm having trouble connecting. Let's try again — what would you like to discuss?"

    def chat(self, mentor_id: str, user_message: str) -> str:
        """Get mentor's response to user message."""
        state = self.sessions.get(mentor_id)
        if not state:
            return "Mentor not found."
        if state.is_expired:
            return "Our 15 minutes are up. Let me leave you with this: focus on the one thing we discussed that made you most uncomfortable. That's where the real work is."

        state.messages.append({"role": "user", "content": user_message})

        mentor_def = MENTOR_TYPES.get(state.mentor_type, {})
        system_prompt = self._build_system_prompt(
            state, mentor_def.get("system_addendum", "")
        )

        # Add time awareness
        remaining = state.time_remaining
        if remaining < 180:  # Last 3 minutes
            system_prompt += (
                f"\n\nNOTE: Only {remaining // 60} minutes left. "
                "Wrap up with your single most important piece of advice."
            )

        try:
            response = self.llm.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    *state.messages,
                ],
                temperature=0.7,
                max_tokens=500,
            )
            state.messages.append({"role": "assistant", "content": response})
            return response
        except Exception as e:
            logger.warning(f"[Sensei] Chat failed for {mentor_id}: {e}")
            return "Give me a moment to think about that... Could you rephrase?"

    def end_session(self, mentor_id: str) -> Dict:
        """End a mentor session and return transcript."""
        state = self.sessions.get(mentor_id)
        if not state:
            return {"error": "Mentor not found"}
        state.ended_at = time.time()
        duration = int(state.ended_at - state.started_at) if state.started_at else 0
        # Filter out the opening instruction
        transcript = [
            m for m in state.messages
            if not m["content"].startswith("The founder has just walked")
        ]
        return {
            "mentor_id": mentor_id,
            "mentor_name": state.mentor_name,
            "mentor_type": state.mentor_type,
            "duration_seconds": duration,
            "messages": transcript,
            "message_count": len(transcript),
        }

    def get_session_summary(self) -> Dict:
        """Get consolidated summary of all mentor sessions."""
        transcripts = []
        for mid, state in self.sessions.items():
            if state.messages:
                transcripts.append(self.end_session(mid))
        return {
            "total_mentors": len(transcripts),
            "transcripts": transcripts,
        }

    def _build_system_prompt(self, state: MentorSessionState,
                              system_addendum: str) -> str:
        """Build the full system prompt for a mentor."""
        return (
            f"{state.persona_prompt}\n\n"
            f"RESEARCH BRIEFING (from our team's analysis):\n"
            f"{self.research_context[:3000]}\n\n"
            f"STARTUP DETAILS:\n{self.exec_summary[:2000]}\n\n"
            f"{system_addendum}\n\n"
            "SESSION RULES:\n"
            "- You are in a 15-minute mentor session with this startup's founder.\n"
            "- Be direct, specific, and actionable.\n"
            "- Ask probing questions — don't just give advice.\n"
            "- Challenge weak points. Praise genuine strengths.\n"
            "- Use your domain expertise and terminology.\n"
            "- Keep responses to 2-4 paragraphs.\n"
            "- Reference specific facts from the research briefing.\n"
            "- If the founder says something concerning, push back immediately."
        )
