"""
Report Enhancement Features — Top 5 Fixes extensions.

Score Forecast: estimates score improvement per fix.
Rewritten Exec Summary: generates improved version addressing top fixes.
Similar Funded Startups: finds comparable companies from the 231K database.
"""

import json
import os
import sqlite3
from typing import List, Dict, Any, Optional

from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger

logger = get_logger('mirai.report_enhancements')

_DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'companies.db')


def generate_score_forecast(
    top_fixes: List[Dict[str, Any]],
    current_scores: Dict[str, float],
    median_overall: float,
    stage: str = "",
) -> Optional[List[Dict[str, Any]]]:
    """Estimate score improvement per fix.

    Uses one LLM call to project how each fix would affect dimension scores.
    Returns list of fixes with added 'projected_scores' and 'projected_overall'.
    Returns None on failure (non-blocking)."""
    if not top_fixes:
        return None

    fixes_text = "\n".join(
        f"FIX {i+1}: {f.get('title', 'Unknown')} (severity: {f.get('severity', '?')})\n"
        f"  Action: {f.get('action', 'N/A')}"
        for i, f in enumerate(top_fixes[:5])
    )

    scores_text = "\n".join(f"  {k}: {v}" for k, v in current_scores.items())

    prompt = (
        f"You are estimating how fixing specific issues would change a {stage or 'startup'}'s scores.\n\n"
        f"CURRENT SCORES (0-10 scale):\n{scores_text}\n"
        f"Current overall: {median_overall}\n\n"
        f"PROPOSED FIXES:\n{fixes_text}\n\n"
        "For EACH fix, estimate:\n"
        "- which dimensions would improve and by how much (be conservative, +0.5 to +2.0 is typical)\n"
        "- the new projected overall score\n"
        "Label these as ESTIMATES. Do not guarantee outcomes.\n\n"
        "Return JSON: {\"forecasts\": [{\"fix_index\": 0, \"dimension_deltas\": {\"dim_name\": +X.X, ...}, "
        "\"projected_overall\": X.X, \"explanation\": \"one sentence\"}]}"
    )

    try:
        llm = LLMClient()
        result = llm.chat_json(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        forecasts = result.get("forecasts", [])
        logger.info(f"[Enhancements] Score forecast generated for {len(forecasts)} fixes")
        return forecasts
    except Exception as e:
        logger.warning(f"[Enhancements] Score forecast failed (non-fatal): {e}")
        return None


def rewrite_exec_summary(
    original_summary: str,
    top_fixes: List[Dict[str, Any]],
    stage: str = "",
) -> Optional[str]:
    """Generate an improved executive summary addressing the top fixes.

    Returns the rewritten text, or None on failure."""
    if not top_fixes:
        return None

    fixes_text = "\n".join(
        f"- {f.get('title', 'Unknown')}: {f.get('action', 'N/A')}"
        for f in top_fixes[:3]  # Focus on top 3 most impactful
    )

    prompt = (
        f"You are rewriting a {stage or 'startup'} executive summary to address its top weaknesses.\n\n"
        f"ORIGINAL EXECUTIVE SUMMARY:\n{original_summary}\n\n"
        f"TOP ISSUES TO ADDRESS:\n{fixes_text}\n\n"
        "Rewrite the executive summary to:\n"
        "1. Keep all factual information from the original\n"
        "2. Strengthen the narrative around the identified weak areas\n"
        "3. Add specificity where the original was vague\n"
        "4. Maintain the same approximate length\n\n"
        "Return ONLY the rewritten executive summary text, nothing else.\n"
        "Do NOT add notes, disclaimers, or meta-commentary."
    )

    try:
        llm = LLMClient()
        result = llm.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
        )
        if result and len(result) > 50:
            logger.info(f"[Enhancements] Exec summary rewritten ({len(result)} chars)")
            return result
        return None
    except Exception as e:
        logger.warning(f"[Enhancements] Exec summary rewrite failed (non-fatal): {e}")
        return None


def find_similar_funded(
    industry: str,
    stage: str = "",
    limit: int = 5,
) -> Optional[List[Dict[str, Any]]]:
    """Find similar funded startups from the 231K company database.

    Queries by industry match, funded/active/acquired status.
    Returns list of company dicts, or None on failure."""
    if not os.path.exists(_DB_PATH):
        # RE-3 FIX: This is a deployment configuration error, not a runtime warning.
        # The 231K companies database must be present for find_similar_funded to work.
        logger.error(f"[Enhancements] Companies database not found at {_DB_PATH} — 'Similar Funded Startups' feature unavailable. Deploy the companies DB to enable this feature.")
        return None

    try:
        conn = sqlite3.connect(_DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        # Normalize industry for matching
        industry_lower = (industry or "").lower().strip()

        # Map stage to database stage vocabulary for filtering
        stage_lower = (stage or "").lower().strip()
        stage_filter = ""
        stage_params: list = []
        if stage_lower in ("idea", "pre-seed", "preseed", "seed", "mvp"):
            stage_filter = "AND LOWER(stage) IN ('early', 'seed', 'pre-seed')"
        elif stage_lower in ("series a", "series-a", "revenue"):
            stage_filter = "AND LOWER(stage) IN ('early', 'growth')"
        elif stage_lower in ("series b", "series-b"):
            stage_filter = "AND LOWER(stage) IN ('growth', 'late')"
        elif stage_lower in ("series c", "series-c", "growth", "scaling", "late stage"):
            stage_filter = "AND LOWER(stage) IN ('growth', 'late')"

        # Try exact industry match first, then fuzzy via LIKE
        c.execute(f"""
            SELECT name, one_liner, industry, stage, status, outcome, outcome_score,
                   location, batch, team_size
            FROM companies
            WHERE LOWER(industry) = ?
              AND outcome IN ('active', 'acquired', 'ipo')
              AND outcome_score >= 0.6
              {stage_filter}
            ORDER BY outcome_score DESC
            LIMIT ?
        """, (industry_lower, limit))

        rows = c.fetchall()

        # Fallback: fuzzy match if exact didn't find enough
        if len(rows) < limit:
            remaining = limit - len(rows)
            existing_names = {r['name'] for r in rows}
            c.execute(f"""
                SELECT name, one_liner, industry, stage, status, outcome, outcome_score,
                       location, batch, team_size
                FROM companies
                WHERE LOWER(industry) LIKE ?
                  AND outcome IN ('active', 'acquired', 'ipo')
                  AND outcome_score >= 0.5
                  {stage_filter}
                ORDER BY outcome_score DESC
                LIMIT ?
            """, (f"%{industry_lower}%", remaining + 10))

            for r in c.fetchall():
                if r['name'] not in existing_names:
                    rows.append(r)
                    existing_names.add(r['name'])
                    if len(rows) >= limit:
                        break

        conn.close()

        if not rows:
            return None

        results = []
        for r in rows[:limit]:
            results.append({
                "name": r['name'],
                "one_liner": r['one_liner'],
                "industry": r['industry'],
                "stage": r['stage'],
                "status": r['status'],
                "outcome": r['outcome'],
                "location": r['location'],
                "batch": r['batch'],
                "team_size": r['team_size'],
            })

        logger.info(f"[Enhancements] Found {len(results)} similar funded companies for '{industry}'")
        return results

    except Exception as e:
        logger.warning(f"[Enhancements] Similar funded query failed (non-fatal): {e}")
        return None
