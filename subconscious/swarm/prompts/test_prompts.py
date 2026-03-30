"""
Mirai Prompt Regression Tester — validates all critical prompts produce correct output.
Replaces promptfoo YAML with pure Python. Zero external deps beyond openai + requests.
Run: python -m subconscious.swarm.prompts.test_prompts
"""
import json
import sys
import time
from typing import List, Callable, Dict, Any, Optional

from openai import OpenAI

from ..config import Config
from . import council_scoring, swarm_persona, deliberation, research_synthesis, fact_check, oasis_event


# ═══════════════════════════════════════════════════════════════════════
# Gateway LLM client
# ═══════════════════════════════════════════════════════════════════════

def _get_client() -> OpenAI:
    return OpenAI(api_key=Config.LLM_API_KEY, base_url=Config.LLM_BASE_URL)


def _call_llm(prompt: str) -> str:
    """Send a prompt to the gateway LLM and return the raw text response."""
    client = _get_client()
    resp = client.chat.completions.create(
        model="anthropic/claude-sonnet-4-6",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
        temperature=0.4,
    )
    return (resp.choices[0].message.content or "").strip()


# ═══════════════════════════════════════════════════════════════════════
# Assertion helpers
# ═══════════════════════════════════════════════════════════════════════

def is_json(output: str) -> bool:
    """Assert the output is valid JSON."""
    try:
        json.loads(output)
        return True
    except (json.JSONDecodeError, TypeError):
        return False


def has_fields(fields: List[str]) -> Callable[[str], bool]:
    """Assert the JSON output contains all specified top-level fields."""
    def check(output: str) -> bool:
        try:
            parsed = json.loads(output)
            return all(f in parsed for f in fields)
        except (json.JSONDecodeError, TypeError):
            return False
    check.__name__ = f"has_fields({fields})"
    return check


def scores_in_range(low: int, high: int, fields: List[str]) -> Callable[[str], bool]:
    """Assert that numeric fields in the JSON output fall within [low, high]."""
    def check(output: str) -> bool:
        try:
            parsed = json.loads(output)
            return all(
                isinstance(parsed.get(f), (int, float)) and low <= parsed[f] <= high
                for f in fields
            )
        except (json.JSONDecodeError, TypeError):
            return False
    check.__name__ = f"scores_in_range({low}-{high}, {fields})"
    return check


def not_contains(substring: str) -> Callable[[str], bool]:
    """Assert the output does NOT contain the given substring."""
    def check(output: str) -> bool:
        return substring.lower() not in output.lower()
    check.__name__ = f"not_contains('{substring}')"
    return check


def contains(substring: str) -> Callable[[str], bool]:
    """Assert the output DOES contain the given substring."""
    def check(output: str) -> bool:
        return substring.lower() in output.lower()
    check.__name__ = f"contains('{substring}')"
    return check


def is_json_array(output: str) -> bool:
    """Assert the output is a valid JSON array."""
    try:
        parsed = json.loads(output)
        return isinstance(parsed, list)
    except (json.JSONDecodeError, TypeError):
        return False


def array_min_length(min_len: int) -> Callable[[str], bool]:
    """Assert the JSON array has at least min_len elements."""
    def check(output: str) -> bool:
        try:
            parsed = json.loads(output)
            return isinstance(parsed, list) and len(parsed) >= min_len
        except (json.JSONDecodeError, TypeError):
            return False
    check.__name__ = f"array_min_length({min_len})"
    return check


def array_items_have_fields(fields: List[str]) -> Callable[[str], bool]:
    """Assert every item in the JSON array has the specified fields."""
    def check(output: str) -> bool:
        try:
            parsed = json.loads(output)
            if not isinstance(parsed, list):
                return False
            return all(
                all(f in item for f in fields)
                for item in parsed
            )
        except (json.JSONDecodeError, TypeError):
            return False
    check.__name__ = f"array_items_have_fields({fields})"
    return check


def array_items_category_valid(valid_categories: List[str]) -> Callable[[str], bool]:
    """Assert every item's 'category' field is one of the valid categories."""
    def check(output: str) -> bool:
        try:
            parsed = json.loads(output)
            if not isinstance(parsed, list):
                return False
            return all(item.get("category") in valid_categories for item in parsed)
        except (json.JSONDecodeError, TypeError):
            return False
    check.__name__ = f"array_items_category_valid({valid_categories})"
    return check


def any_item_has_search_query() -> Callable[[str], bool]:
    """Assert at least one item in the JSON array has a non-empty search_query."""
    def check(output: str) -> bool:
        try:
            parsed = json.loads(output)
            if not isinstance(parsed, list):
                return False
            return any(
                isinstance(item.get("search_query"), str) and len(item["search_query"]) > 5
                for item in parsed
            )
        except (json.JSONDecodeError, TypeError):
            return False
    check.__name__ = "any_item_has_search_query()"
    return check


def contains_any(substrings: List[str]) -> Callable[[str], bool]:
    """Assert the output contains at least one of the given substrings (case-insensitive)."""
    def check(output: str) -> bool:
        lower = output.lower()
        return any(s.lower() in lower for s in substrings)
    check.__name__ = f"contains_any({substrings})"
    return check


def all_7_dimensions_present() -> Callable[[str], bool]:
    """Assert all 7 council scoring dimensions are present as numeric values."""
    dims = [
        "market_timing", "business_model_viability", "competition_landscape",
        "pattern_match", "team_execution_signals", "regulatory_news_environment",
        "social_proof_demand",
    ]
    def check(output: str) -> bool:
        try:
            parsed = json.loads(output)
            return all(isinstance(parsed.get(d), (int, float)) for d in dims)
        except (json.JSONDecodeError, TypeError):
            return False
    check.__name__ = "all_7_dimensions_present()"
    return check


# ═══════════════════════════════════════════════════════════════════════
# Prompt builders — render each prompt template with test vars
# ═══════════════════════════════════════════════════════════════════════

def _build_council_prompt(vars: Dict[str, str]) -> str:
    return (
        f"{council_scoring.PROMPT}\n\n"
        f"Company: {vars['company']}\n"
        f"Industry: {vars['industry']}\n"
        f"Research:\n{vars['research']}"
    )


def _build_persona_prompt(vars: Dict[str, str]) -> str:
    rendered = swarm_persona.PROMPT.format(persona_description=vars["persona_description"])
    return (
        f"{rendered}\n\n"
        f"Company: {vars['company']}\n"
        f"Executive Summary:\n{vars['exec_summary']}"
    )


def _build_deliberation_prompt(vars: Dict[str, str]) -> str:
    return deliberation.PROMPT.format(
        score=vars["score"],
        consensus=vars["consensus"],
        num_outliers=vars["num_outliers"],
    )


def _build_synthesis_prompt(vars: Dict[str, str]) -> str:
    rendered = research_synthesis.PROMPT.format(
        model_count=vars["model_count"],
        company=vars["company"],
    )
    return f"{rendered}\n\nAgent findings:\n{vars['findings']}"


def _build_fact_check_prompt(vars: Dict[str, str]) -> str:
    return f"{fact_check.PROMPT}\n\nText:\n{vars['text']}"


def _build_oasis_prompt(vars: Dict[str, str]) -> str:
    rendered = oasis_event.PROMPT.format(
        company=vars["company"],
        industry=vars["industry"],
    )
    return f"{rendered}\n\nHeadlines:\n{vars['headlines']}"


# ═══════════════════════════════════════════════════════════════════════
# Test case definitions — ported from promptfoo.yaml (17 total)
# ═══════════════════════════════════════════════════════════════════════

COUNCIL_DIMS = [
    "market_timing", "business_model_viability", "competition_landscape",
    "pattern_match", "team_execution_signals", "regulatory_news_environment",
    "social_proof_demand",
]

PERSONA_DIMS = ["market", "team", "product", "timing", "overall"]

TEST_CASES: List[Dict[str, Any]] = [
    # ── Council Scoring (3 tests) ──────────────────────────────────
    {
        "id": "council_stripe",
        "description": "Council scoring — Stripe (FinTech)",
        "prompt_builder": _build_council_prompt,
        "vars": {
            "company": "Stripe",
            "industry": "FinTech / Payments",
            "research": (
                "Stripe processes over $1 trillion in payment volume annually. "
                "Founded 2010, reached $95B valuation in 2023 fundraise. "
                "Competes with Adyen, Square, PayPal. Strong developer ecosystem. "
                "Regulatory scrutiny on payment processors increasing globally. "
                "Expanded into lending, treasury, and identity products."
            ),
        },
        "assertions": [
            is_json,
            scores_in_range(1, 10, COUNCIL_DIMS),
            not_contains("I don't have information"),
        ],
    },
    {
        "id": "council_climate_tech",
        "description": "Council scoring — early-stage climate tech",
        "prompt_builder": _build_council_prompt,
        "vars": {
            "company": "CarbonCapture Inc.",
            "industry": "Climate Tech / Carbon Removal",
            "research": (
                "Direct air capture startup, Series A ($30M). Technology unproven at scale. "
                "TAM for carbon removal estimated at $100B+ by 2040. "
                "Competing with Climeworks (Switzerland), backed by $650M. "
                "Team has 2 PhDs in chemical engineering, no prior startup experience. "
                "No revenue yet, pilot plant producing 500 tonnes CO2/year."
            ),
        },
        "assertions": [
            is_json,
            scores_in_range(1, 10, ["market_timing", "team_execution_signals"]),
        ],
    },
    {
        "id": "council_all_7_dims",
        "description": "Council scoring — all 7 dimensions present",
        "prompt_builder": _build_council_prompt,
        "vars": {
            "company": "Notion",
            "industry": "Productivity SaaS",
            "research": (
                "Notion valued at $10B. 30M+ users. Competing with Confluence, Coda. "
                "Revenue estimated $250M ARR. Strong product-led growth. "
                "Founded 2013, slow start but exponential growth post-2020."
            ),
        },
        "assertions": [
            is_json,
            all_7_dimensions_present(),
        ],
    },
    # ── Swarm Persona (3 tests) ────────────────────────────────────
    {
        "id": "persona_vc_stripe",
        "description": "Swarm persona — VC investor lens on Stripe",
        "prompt_builder": _build_persona_prompt,
        "vars": {
            "persona_description": "a seasoned Series B venture capital investor specializing in FinTech infrastructure",
            "company": "Stripe",
            "exec_summary": (
                "Stripe is a payments infrastructure company processing $1T+ annually. "
                "$95B valuation, expanding into lending and treasury."
            ),
        },
        "assertions": [
            is_json,
            scores_in_range(1, 10, PERSONA_DIMS),
        ],
    },
    {
        "id": "persona_regulatory_revolut",
        "description": "Swarm persona — regulatory expert lens",
        "prompt_builder": _build_persona_prompt,
        "vars": {
            "persona_description": "a regulatory compliance expert with 15 years experience in financial services regulation across EU and US",
            "company": "Revolut",
            "exec_summary": (
                "Revolut is a digital banking app with 35M+ customers. "
                "Pursuing full banking licenses in multiple jurisdictions. "
                "Has faced regulatory delays in UK banking license application."
            ),
        },
        "assertions": [
            is_json,
            scores_in_range(1, 10, ["overall"]),
            not_contains("as an AI"),
        ],
    },
    {
        "id": "persona_cto_supabase",
        "description": "Swarm persona — technical CTO lens",
        "prompt_builder": _build_persona_prompt,
        "vars": {
            "persona_description": "a CTO who has built and scaled distributed systems at 3 unicorn startups, expert in API platform architecture",
            "company": "Supabase",
            "exec_summary": (
                "Supabase is an open-source Firebase alternative built on PostgreSQL. "
                "$116M raised, 500K+ databases created. Developer-first GTM."
            ),
        },
        "assertions": [
            is_json,
            scores_in_range(1, 10, PERSONA_DIMS),
        ],
    },
    # ── Deliberation (3 tests) ─────────────────────────────────────
    {
        "id": "deliberation_outlier",
        "description": "Deliberation — outlier adjusts score",
        "prompt_builder": _build_deliberation_prompt,
        "vars": {
            "score": "9",
            "consensus": "6.2/10 — mixed signals on market timing",
            "num_outliers": "2",
        },
        "assertions": [
            is_json,
            has_fields(["position", "adjusted_score", "adjustment_reason"]),
            scores_in_range(1, 10, ["adjusted_score"]),
        ],
    },
    {
        "id": "deliberation_aligned",
        "description": "Deliberation — aligned agent confirms",
        "prompt_builder": _build_deliberation_prompt,
        "vars": {
            "score": "6",
            "consensus": "6.5/10 — moderate confidence, solid fundamentals",
            "num_outliers": "0",
        },
        "assertions": [
            is_json,
            has_fields(["position", "adjusted_score", "adjustment_reason"]),
            scores_in_range(1, 10, ["adjusted_score"]),
        ],
    },
    {
        "id": "deliberation_extreme",
        "description": "Deliberation — extreme disagreement",
        "prompt_builder": _build_deliberation_prompt,
        "vars": {
            "score": "2",
            "consensus": "8.1/10 — strong positive signal across most agents",
            "num_outliers": "1",
        },
        "assertions": [
            is_json,
            scores_in_range(1, 10, ["adjusted_score"]),
        ],
    },
    # ── Research Synthesis (2 tests) ───────────────────────────────
    {
        "id": "synthesis_figma",
        "description": "Research synthesis — cross-referencing 3 agents",
        "prompt_builder": _build_synthesis_prompt,
        "vars": {
            "model_count": "3",
            "company": "Figma",
            "findings": (
                "Agent 1 (GPT-4o): Figma has 4M+ users, $400M ARR. Adobe acquisition blocked by regulators. "
                "Strong product-market fit in design collaboration. Competes with Sketch, Canva.\n\n"
                "Agent 2 (Claude): Figma ARR estimated $500M+. Dominant in UI/UX design. "
                "Adobe deal collapsed due to CMA and EU antitrust concerns. Growing into AI features.\n\n"
                "Agent 3 (Gemini): Figma is widely used in tech companies. "
                "Revenue is growing. Adobe tried to acquire but failed. Market size for design tools is $15B."
            ),
        },
        "assertions": [
            is_json,
            has_fields(["confirmed_facts", "contradictions", "unique_insights", "coverage_gaps"]),
        ],
    },
    {
        "id": "synthesis_spacex_contradiction",
        "description": "Research synthesis — detects contradiction in revenue",
        "prompt_builder": _build_synthesis_prompt,
        "vars": {
            "model_count": "2",
            "company": "SpaceX",
            "findings": (
                "Agent 1: SpaceX revenue estimated at $8B in 2023. Starlink has 2M subscribers. "
                "Valued at $180B.\n\n"
                "Agent 2: SpaceX revenue reportedly $5.5B in 2023. Starlink at 2.3M subscribers. "
                "Valuation around $150B."
            ),
        },
        "assertions": [
            is_json,
            has_fields(["confirmed_facts"]),
            # Should detect the revenue/valuation contradictions
            contains_any(["contradiction", "revenue", "discrepan"]),
        ],
    },
    # ── Fact Check (3 tests) ───────────────────────────────────────
    {
        "id": "fact_check_stripe_quant",
        "description": "Fact check — extracts quantitative claims",
        "prompt_builder": _build_fact_check_prompt,
        "vars": {
            "text": (
                "Stripe processes over $1 trillion in total payment volume annually. "
                "The company was valued at $95 billion after its 2023 funding round. "
                "Founded in 2010 by Patrick and John Collison, Stripe now serves "
                "millions of businesses. The global payments market is projected "
                "to reach $3.3 trillion by 2028."
            ),
        },
        "assertions": [
            is_json_array,
            array_min_length(2),
            array_items_have_fields(["text", "category"]),
            array_items_category_valid(["market_size", "revenue", "funding", "growth", "company_fact", "other"]),
        ],
    },
    {
        "id": "fact_check_no_quant",
        "description": "Fact check — handles text with no quantitative claims",
        "prompt_builder": _build_fact_check_prompt,
        "vars": {
            "text": (
                "The team seems passionate about their product. They have a nice office "
                "in San Francisco and the CEO gave an inspiring talk at a conference."
            ),
        },
        "assertions": [
            is_json_array,
        ],
    },
    {
        "id": "fact_check_search_query",
        "description": "Fact check — includes search_query for verification",
        "prompt_builder": _build_fact_check_prompt,
        "vars": {
            "text": (
                "OpenAI raised $6.6 billion at a $157 billion valuation in October 2024. "
                "The company has over 200 million weekly active users of ChatGPT. "
                "Microsoft has invested approximately $13 billion in OpenAI."
            ),
        },
        "assertions": [
            is_json_array,
            any_item_has_search_query(),
        ],
    },
    # ── OASIS Event (3 tests) ──────────────────────────────────────
    {
        "id": "oasis_stripe_relevant",
        "description": "OASIS event — relevant headline found",
        "prompt_builder": _build_oasis_prompt,
        "vars": {
            "company": "Stripe",
            "industry": "FinTech",
            "headlines": (
                '- "Stripe launches new AI-powered fraud detection tool for merchants" (Reuters, March 2026)\n'
                '- "Global semiconductor shortage easing, TSMC reports" (Bloomberg)\n'
                '- "EU proposes new digital payments regulation affecting cross-border transactions" (FT)\n'
                '- "Tesla recalls 500K vehicles over software issue" (AP)'
            ),
        },
        "assertions": [
            not_contains("No significant market event this month"),
            contains_any(["stripe", "payment", "fraud"]),
            not_contains("Tesla"),
        ],
    },
    {
        "id": "oasis_notion_irrelevant",
        "description": "OASIS event — no relevant headlines",
        "prompt_builder": _build_oasis_prompt,
        "vars": {
            "company": "Notion",
            "industry": "Productivity SaaS",
            "headlines": (
                '- "Oil prices surge as OPEC cuts production" (Reuters)\n'
                '- "New species of deep-sea fish discovered near Mariana Trench" (Nature)\n'
                '- "FIFA announces 2030 World Cup host cities" (ESPN)'
            ),
        },
        "assertions": [
            contains("No significant market event this month"),
        ],
    },
    {
        "id": "oasis_no_fabrication",
        "description": "OASIS event — does not fabricate events",
        "prompt_builder": _build_oasis_prompt,
        "vars": {
            "company": "Anthropic",
            "industry": "AI / LLMs",
            "headlines": (
                '- "Google DeepMind publishes new protein folding research" (Nature)\n'
                '- "NVIDIA reports record quarterly revenue of $22B" (CNBC)\n'
                '- "EU AI Act enforcement begins with first compliance audits" (Reuters)'
            ),
        },
        "assertions": [
            not_contains("Anthropic raised"),
            not_contains("Anthropic announced"),
            not_contains("Anthropic launched"),
        ],
    },
]


# ═══════════════════════════════════════════════════════════════════════
# Test runner
# ═══════════════════════════════════════════════════════════════════════

def run_single_test(test_case: Dict[str, Any]) -> Dict[str, Any]:
    """Run a single test case and return results."""
    test_id = test_case["id"]
    description = test_case["description"]
    prompt_builder = test_case["prompt_builder"]
    vars_ = test_case["vars"]
    assertions = test_case["assertions"]

    print(f"  [{test_id}] {description} ... ", end="", flush=True)

    try:
        prompt = prompt_builder(vars_)
        output = _call_llm(prompt)
    except Exception as e:
        print(f"ERROR (LLM call failed: {e})")
        return {
            "id": test_id,
            "description": description,
            "passed": False,
            "error": str(e),
            "assertion_results": [],
        }

    assertion_results = []
    all_passed = True

    for assertion_fn in assertions:
        name = getattr(assertion_fn, "__name__", str(assertion_fn))
        try:
            result = assertion_fn(output)
            assertion_results.append({"assertion": name, "passed": result})
            if not result:
                all_passed = False
        except Exception as e:
            assertion_results.append({"assertion": name, "passed": False, "error": str(e)})
            all_passed = False

    status = "PASS" if all_passed else "FAIL"
    print(status)

    if not all_passed:
        failed = [a for a in assertion_results if not a["passed"]]
        for f in failed:
            print(f"    FAILED: {f['assertion']}")
        # Show truncated output for debugging
        print(f"    Output (first 200 chars): {output[:200]}")

    return {
        "id": test_id,
        "description": description,
        "passed": all_passed,
        "assertion_results": assertion_results,
        "output_preview": output[:300],
    }


def run_all_tests(test_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """Run all (or selected) test cases and return aggregate results."""
    cases = TEST_CASES
    if test_ids:
        cases = [tc for tc in TEST_CASES if tc["id"] in test_ids]

    print(f"\nMirai Prompt Regression Suite — {len(cases)} test cases")
    print("=" * 60)

    results = []
    start = time.time()

    for tc in cases:
        result = run_single_test(tc)
        results.append(result)

    elapsed = time.time() - start
    passed = sum(1 for r in results if r["passed"])
    failed = len(results) - passed

    print("=" * 60)
    print(f"Results: {passed}/{len(results)} passed, {failed} failed ({elapsed:.1f}s)")

    if failed > 0:
        print("\nFailed tests:")
        for r in results:
            if not r["passed"]:
                print(f"  - {r['id']}: {r['description']}")

    return {
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "elapsed_seconds": round(elapsed, 2),
        "results": results,
        "all_passed": failed == 0,
    }


def main():
    """CLI entry point."""
    # Allow filtering by test ID via command-line args
    test_ids = None
    if len(sys.argv) > 1:
        test_ids = sys.argv[1:]
        print(f"Running filtered tests: {test_ids}")

    summary = run_all_tests(test_ids)
    sys.exit(0 if summary["all_passed"] else 1)


if __name__ == "__main__":
    main()
