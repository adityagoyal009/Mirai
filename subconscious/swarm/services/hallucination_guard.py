"""
Hallucination Guard — verifies LLM-synthesized research is faithful to raw sources.

Extracts specific claims (numbers, dollar amounts, percentages, dates, growth rates)
from a synthesis and checks whether each claim is traceable to the raw source findings.
Claims that cannot be traced are flagged as LLM-inferred / potentially hallucinated.

Self-contained: no external dependencies beyond the standard library.
OpenAI is imported lazily only when an llm_client is passed for re-synthesis.
"""

import re
from typing import Dict, List, Tuple, Optional


# ──────────────────────────────────────────────────────────────────────
# Number extraction
# ──────────────────────────────────────────────────────────────────────

# Multiplier suffixes — order matters (longest first for alternation)
_MULTIPLIER_WORDS = {
    "trillion": 1_000_000_000_000,
    "billion": 1_000_000_000,
    "million": 1_000_000,
    "thousand": 1_000,
}

_MULTIPLIER_SYMBOLS = {
    "T": 1_000_000_000_000,
    "B": 1_000_000_000,
    "M": 1_000_000,
    "K": 1_000,
}

# Regex: captures things like "$2.5B", "2.5 billion", "$50M", "50 million",
#         "40%", "1,200", "3.14", "$120,000", "€9.5M", etc.
# Group layout:
#   1 — optional currency symbol ($, €, £)
#   2 — the numeric part (digits, commas, decimal point)
#   3 — optional suffix letter (B, M, K, T) immediately after number
#   4 — optional word suffix ("billion", "million", …) after optional space
#   5 — optional percent sign
_NUMBER_PATTERN = re.compile(
    r'(?<![A-Za-z])'                               # no leading letter
    r'([$€£])?'                                     # (1) optional currency
    r'(\d[\d,]*\.?\d*)'                             # (2) numeric part
    r'([TBMK](?![a-z]))?'                           # (3) suffix letter
    r'(?:\s*(trillion|billion|million|thousand))?'   # (4) word suffix
    r'(\s*%)?'                                       # (5) percent
    r'(?![A-Za-z])',                                 # no trailing letter
    re.IGNORECASE,
)


def extract_numbers(text: str) -> List[float]:
    """Parse all numeric values from *text* into canonical float values.

    Handles formats such as:
      "$2.5B"       -> 2_500_000_000.0
      "2.5 billion" -> 2_500_000_000.0
      "$50M"        -> 50_000_000.0
      "50 million"  -> 50_000_000.0
      "40%"         -> 40.0   (kept as-is; percentage semantics preserved)
      "1,200"       -> 1200.0
      "$120,000"    -> 120_000.0
    """
    values: List[float] = []
    for m in _NUMBER_PATTERN.finditer(text):
        raw_num = m.group(2).replace(",", "")
        try:
            value = float(raw_num)
        except ValueError:
            continue

        # Apply suffix multiplier (letter form: B, M, K, T)
        suffix_letter = (m.group(3) or "").upper()
        if suffix_letter in _MULTIPLIER_SYMBOLS:
            value *= _MULTIPLIER_SYMBOLS[suffix_letter]

        # Apply suffix multiplier (word form: billion, million, …)
        suffix_word = (m.group(4) or "").lower().strip()
        if suffix_word in _MULTIPLIER_WORDS:
            value *= _MULTIPLIER_WORDS[suffix_word]

        values.append(value)

    return values


# ──────────────────────────────────────────────────────────────────────
# Claim extraction
# ──────────────────────────────────────────────────────────────────────

# Claims are sentences / fragments that contain quantitative data or
# other specific assertions worth verifying.
_CLAIM_INDICATORS = re.compile(
    r'\$|€|£|%|\d+\.\d+'        # currency/percent/decimal numbers
    r'|\d{4}'                     # years
    r'|\d[\d,]+\s*(?:billion|million|thousand|[BMKT](?![a-z]))'
    r'|(?:grew|growth|increase|decline|drop|raise|raised|valued|worth)'
    r'|(?:market\s+size|TAM|revenue|funding|valuation)',
    re.IGNORECASE,
)


def _extract_claims(synthesis: str) -> List[str]:
    """Split synthesis into individual claim-bearing sentences.

    A "claim" is any sentence (or semicolon-delimited fragment) that
    contains a quantitative indicator — a number, dollar amount,
    percentage, year, growth verb, or market-data keyword.
    """
    # Split on sentence boundaries and semicolons
    fragments = re.split(r'(?<=[.!?;])\s+', synthesis)
    claims: List[str] = []
    for frag in fragments:
        frag = frag.strip()
        if not frag:
            continue
        if _CLAIM_INDICATORS.search(frag):
            claims.append(frag)
    return claims


# ──────────────────────────────────────────────────────────────────────
# Traceability checks
# ──────────────────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    """Lowercase and collapse whitespace for comparison."""
    return re.sub(r'\s+', ' ', text.lower().strip())


def _exact_substring_match(claim: str, raw_texts: List[str]) -> bool:
    """Case-insensitive substring match of the full claim in any raw text."""
    claim_n = _normalize(claim)
    for raw in raw_texts:
        if claim_n in _normalize(raw):
            return True
    return False


def _number_match(claim: str, raw_texts: List[str], tolerance: float = 0.01) -> bool:
    """Extract numbers from the claim and check if each appears in *any* raw text.

    Uses a relative tolerance (default 1%) to accommodate rounding differences
    (e.g. "$2.5B" in synthesis vs "$2,500,000,000" in source).
    """
    claim_numbers = extract_numbers(claim)
    if not claim_numbers:
        return False  # no numbers to verify — cannot confirm via this method

    # Collect all numbers from raw sources once
    raw_numbers: List[float] = []
    for raw in raw_texts:
        raw_numbers.extend(extract_numbers(raw))

    if not raw_numbers:
        return False

    # Every number in the claim must match at least one raw number
    for cn in claim_numbers:
        found = False
        for rn in raw_numbers:
            if cn == 0 and rn == 0:
                found = True
                break
            if cn != 0 and abs(cn - rn) / max(abs(cn), 1e-9) <= tolerance:
                found = True
                break
        if not found:
            return False

    return True


def _key_phrase_overlap(claim: str, raw_texts: List[str], min_overlap: int = 3) -> bool:
    """Check for a contiguous key-phrase overlap of *min_overlap*+ words.

    A sliding window over the claim's words is checked against each raw text.
    """
    claim_words = _normalize(claim).split()
    if len(claim_words) < min_overlap:
        return False

    for raw in raw_texts:
        raw_n = _normalize(raw)
        # Slide a window of size min_overlap over claim words
        for i in range(len(claim_words) - min_overlap + 1):
            phrase = " ".join(claim_words[i : i + min_overlap])
            if phrase in raw_n:
                return True

    return False


# ──────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────

def check_faithfulness(synthesis: str, raw_findings: List[str]) -> Dict:
    """Check how faithful a synthesis is to the raw source findings.

    Parameters
    ----------
    synthesis : str
        The LLM-generated synthesis text to verify.
    raw_findings : list[str]
        The raw source texts (crawled page content, search snippets, etc.)
        that the synthesis was supposed to be based on.

    Returns
    -------
    dict with keys:
        claims          — list of extracted claim strings
        results         — list of {"claim": str, "status": "TRACEABLE"|"LLM-INFERRED",
                                    "method": str|None}
        traceable_count — int
        total_claims    — int
        faithfulness    — float in [0, 1] (traceable / total, or 1.0 if no claims)
    """
    claims = _extract_claims(synthesis)
    results: List[Dict] = []
    traceable = 0

    for claim in claims:
        status = "LLM-INFERRED"
        method: Optional[str] = None

        # Check 1: exact substring
        if _exact_substring_match(claim, raw_findings):
            status = "TRACEABLE"
            method = "exact_substring"
        # Check 2: number matching
        elif _number_match(claim, raw_findings):
            status = "TRACEABLE"
            method = "number_match"
        # Check 3: key-phrase overlap (3+ consecutive words)
        elif _key_phrase_overlap(claim, raw_findings):
            status = "TRACEABLE"
            method = "key_phrase_overlap"

        if status == "TRACEABLE":
            traceable += 1

        results.append({"claim": claim, "status": status, "method": method})

    total = len(claims)
    return {
        "claims": claims,
        "results": results,
        "traceable_count": traceable,
        "total_claims": total,
        "faithfulness": traceable / total if total > 0 else 1.0,
    }


def guard_synthesis(
    synthesis: str,
    raw_findings: List[str],
    llm_client=None,
    threshold: float = 0.6,
) -> Tuple[str, float]:
    """Guard an LLM synthesis against hallucination.

    Parameters
    ----------
    synthesis : str
        The LLM-generated synthesis text.
    raw_findings : list[str]
        Raw source texts the synthesis should be grounded in.
    llm_client : optional
        An OpenAI-compatible client.  If provided and faithfulness is below
        *threshold*, a stricter re-synthesis is attempted.
    threshold : float
        Minimum acceptable faithfulness score (0-1).  Default 0.6.

    Returns
    -------
    (cleaned_synthesis, faithfulness_score)
        If faithfulness >= threshold, the original synthesis is returned.
        Otherwise, either a re-synthesized version (if llm_client) or an
        inline-annotated version is returned.
    """
    report = check_faithfulness(synthesis, raw_findings)
    score = report["faithfulness"]

    if score >= threshold:
        return synthesis, score

    # ── Below threshold — attempt remediation ──

    if llm_client is not None:
        # Re-synthesize with a strict grounding prompt
        sources_block = "\n\n---\n\n".join(
            f"[Source {i+1}]\n{txt[:1500]}" for i, txt in enumerate(raw_findings[:10])
        )
        strict_prompt = (
            "STRICT MODE: Only include facts that appear verbatim in the source "
            "material. Do not add any numbers, statistics, or claims not explicitly "
            "stated in the sources. Prefix any inference with [INFERRED].\n\n"
            "SOURCE MATERIAL:\n"
            f"{sources_block}\n\n"
            "Rewrite the following synthesis so that every claim is directly "
            "supported by the sources above. Remove or clearly mark anything "
            "that cannot be verified from the sources.\n\n"
            f"ORIGINAL SYNTHESIS:\n{synthesis}"
        )
        try:
            resp = llm_client.chat.completions.create(
                model="claude-sonnet-4-6",
                messages=[{"role": "user", "content": strict_prompt}],
                max_tokens=1500,
            )
            new_synthesis = (resp.choices[0].message.content or "").strip()
            if new_synthesis:
                # Re-check the rewritten version
                new_report = check_faithfulness(new_synthesis, raw_findings)
                return new_synthesis, new_report["faithfulness"]
        except Exception as e:
            # HG-2 FIX: add debug log so re-synthesis failures are visible
            import logging as _logging
            _logging.getLogger('mirofish.hallucination_guard').debug(
                f"[HallucinationGuard] Re-synthesis LLM call failed, falling through to annotation path: {e}"
            )  # Fall through to annotation path

    # ── No client (or re-synthesis failed) — annotate inline ──
    annotated = synthesis
    for item in report["results"]:
        if item["status"] == "LLM-INFERRED":
            claim = item["claim"]
            # Insert [LLM-INFERRED] tag before the untraceable claim.
            # Use a single replacement to avoid duplicating if the claim
            # text appears more than once (replace only the first occurrence).
            annotated = annotated.replace(claim, f"[LLM-INFERRED] {claim}", 1)

    return annotated, score
