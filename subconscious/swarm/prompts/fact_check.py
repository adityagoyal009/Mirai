# NOTE: Dead code in the main pipeline. The actual claim extraction prompt is
# _CLAIM_EXTRACTION_PROMPT defined inline in fact_checker.py. This file is only
# referenced by test_prompts.py and utils/prompt_registry.py.
# TODO: Remove once prompt_registry inventory check is removed.
VERSION = "1.0.0"
PROMPT = """Extract specific factual claims from this text, especially quantitative claims (market sizes, revenue, funding amounts, growth rates, dates).
Return JSON array of claims with fields: text, category (market_size|revenue|funding|growth|company_fact|other), search_query, ticker (if public company)."""
