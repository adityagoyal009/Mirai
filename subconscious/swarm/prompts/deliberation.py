# NOTE: Dead code in the main pipeline. The actual deliberation prompt is built inline
# in swarm_predictor.py (_deliberate). This prompt has a different structure from the
# inline version and is only referenced by test_prompts.py and prompt_registry.py.
# TODO: Remove once prompt_registry inventory check is removed.
VERSION = "2.0.0"
PROMPT = """You are a committee member reviewing a startup evaluation. You previously scored {score}/10.

STEP 1: State your position in 2-3 sentences. What is your strongest conviction about this startup? What evidence supports your score?
STEP 2: Now consider — the panel consensus is {consensus} and {num_outliers} agents significantly disagree. Does this change your view? What specifically would need to be true for you to move your score?
STEP 3: Decide your final score.

Return JSON: {{position, adjusted_score, adjustment_reason}}."""
