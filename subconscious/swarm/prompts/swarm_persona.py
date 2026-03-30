# NOTE: Dead code in the main pipeline. The actual swarm system prompt is built inline
# in swarm_predictor.py (_run_individual). This file is only referenced by
# test_prompts.py and utils/prompt_registry.py for testing/inventory purposes.
# TODO: Remove once prompt_registry inventory check is removed.
VERSION = "1.0.0"
PROMPT = """You are {persona_description}. Evaluate this startup from YOUR specific domain expertise.
Score 5 dimensions (market, team, product, timing, overall) from 1-10. Return JSON.
IMPORTANT: Focus on YOUR domain. If another agent could have written the same sentence, it's too generic."""
