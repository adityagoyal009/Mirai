# NOTE: Dead code in the main pipeline. Research synthesis is done via
# CHAIRMAN_SYNTHESIS_PROMPT defined inline in agentic_researcher.py. This file is
# only referenced by test_prompts.py and utils/prompt_registry.py.
# TODO: Remove once prompt_registry inventory check is removed.
VERSION = "1.0.0"
PROMPT = """You are synthesizing research from {model_count} independent research agents about {company}.
Cross-reference their findings and identify:
- confirmed_facts: findings mentioned by 2+ agents (high confidence)
- contradictions: where agents disagree (flag as warnings)
- unique_insights: findings from only 1 agent (lower confidence)
- coverage_gaps: areas none of the agents covered well
Return structured JSON."""
