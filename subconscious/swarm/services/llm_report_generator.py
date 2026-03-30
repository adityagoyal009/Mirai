"""
LLM Report Generator — Sonnet generates the complete HTML report.

Replaces the 1700-line report_generator.py with a single LLM call.
Sonnet receives the full analysis data + CSS template and produces
publication-ready HTML with inline SVG charts. Playwright (Chromium) renders to PDF.

Uses Claude CLI headless calls — no proxy server needed.
"""

import json
import os
import re
import threading
import atexit
from typing import Dict, Any, Optional
from datetime import datetime

from ..utils.cli_llm import call_claude
from ..utils.logger import get_logger

logger = get_logger('mirofish.llm_report')

# In-memory cache for pre-generated reports {analysis_id: pdf_bytes}
_pdf_cache: Dict[str, bytes] = {}

# In-memory cache for HTML reports {report_id: html_string}
_html_cache: Dict[str, str] = {}

# ── Persistent Browser Pool ──────────────────────────────────────────────────
# Keeps a Chromium instance alive in the background. Tabs are created per-render
# and closed after, so memory stays bounded. The browser itself persists.

_browser_lock = threading.Lock()
_playwright_instance = None
_browser_instance = None
_POOL_SIZE = 1  # Single browser, multiple tabs — sufficient for sequential renders


def _get_browser():
    """Get or launch the persistent Chromium browser. Thread-safe."""
    global _playwright_instance, _browser_instance
    with _browser_lock:
        if _browser_instance and _browser_instance.is_connected():
            return _browser_instance
        # Launch fresh
        try:
            from playwright.sync_api import sync_playwright
            if _playwright_instance is None:
                _playwright_instance = sync_playwright().start()
            _browser_instance = _playwright_instance.chromium.launch(headless=True)
            logger.info("[Browser Pool] Chromium launched and ready")
            return _browser_instance
        except Exception as e:
            logger.error(f"[Browser Pool] Failed to launch Chromium: {e}")
            raise


def _shutdown_browser():
    """Clean shutdown on process exit."""
    global _browser_instance, _playwright_instance
    try:
        if _browser_instance:
            _browser_instance.close()
            logger.info("[Browser Pool] Chromium closed")
        if _playwright_instance:
            _playwright_instance.stop()
            logger.info("[Browser Pool] Playwright stopped")
    except Exception:
        pass
    _browser_instance = None
    _playwright_instance = None


atexit.register(_shutdown_browser)

# CSS template — LLM fills the HTML body, we provide the styling
REPORT_CSS = """
/* ── Reset & Base (DESIGN.md: DM Sans body, Instrument Serif display, Source Serif 4 agents) ── */
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=Instrument+Serif:ital@0;1&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400;1,8..60,600&display=swap');
@page { size: A4; margin: 0; }
*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: 'DM Sans', 'Helvetica Neue', Helvetica, Arial, sans-serif;
  color: #0f172a;
  font-size: 9pt;
  line-height: 1.45;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}

/* ── Page Layout ──────────────────────────────────────────────────────────── */
.page {
  width: 100%;
  max-width: 1100px;
  margin: 0 auto;
  min-height: 297mm;
  padding: 15mm 20mm 18mm 20mm;
  page-break-after: always;
  position: relative;
  overflow: hidden;
}
.page:last-child { page-break-after: avoid; }

/* ── Page Header (pages 2+) ───────────────────────────────────────────────── */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 6px;
  border-bottom: 2px solid #0f2440;
  margin-bottom: 12px;
}
.page-header .brand {
  font-size: 9pt;
  font-weight: 700;
  color: #0f2440;
  letter-spacing: 0.5px;
}
.page-header .company-name {
  font-size: 8pt;
  color: #666;
}

/* ── Cover Page ───────────────────────────────────────────────────────────── */
.cover-top-bar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 28mm;
}
.cover-brand {
  font-size: 13pt;
  font-weight: 800;
  color: #0f2440;
  letter-spacing: 1px;
}
.cover-brand .kanji { color: #2563eb; margin-right: 6px; }
.cover-date { font-size: 8pt; color: #888; text-align: right; line-height: 1.6; }
.cover-title-block { margin-bottom: 10mm; }
.cover-company {
  font-family: 'Instrument Serif', Georgia, serif;
  font-size: 26pt;
  font-weight: 400;
  color: #0f2440;
  line-height: 1.1;
  margin-bottom: 4px;
}
.cover-subtitle {
  font-size: 12pt;
  font-weight: 400;
  color: #2563eb;
  letter-spacing: 0.5px;
}
.cover-divider {
  border: none;
  border-top: 3px solid #0f2440;
  margin: 6mm 0;
}

/* ── Section Headers (PitchBook navy banners) ─────────────────────────────── */
.section-header {
  background: #0f2440;
  color: #fff;
  padding: 7px 14px;
  font-size: 11pt;
  font-weight: 600;
  margin: 14px 0 8px 0;
  border-left: 4px solid #2563eb;
  letter-spacing: 0.2px;
}
.section-header.appendix-header {
  background: #0f2440;
  border-left-color: #dc2626;
}
.subsection-label {
  font-size: 9pt;
  font-weight: 700;
  color: #0f2440;
  margin: 10px 0 4px 0;
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

/* ── Stat Cards ───────────────────────────────────────────────────────────── */
.stats-row {
  display: flex;
  gap: 8px;
  margin: 10px 0;
}
.stat-card {
  flex: 1;
  background: #f8f9fa;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  padding: 10px 8px;
  text-align: center;
}
.stat-card .stat-value {
  font-size: 20pt;
  font-weight: 800;
  color: #0f2440;
  line-height: 1.1;
}
.stat-card .stat-value.accent { color: #2563eb; }

/* ── Agent Quote Cards (DESIGN.md: Source Serif 4 italic on tinted backgrounds) ── */
.agent-card {
  border-left: 4px solid #64748b;
  padding: 12px 16px;
  margin-bottom: 8px;
  background: #fff;
}
.agent-card.hit { border-left-color: #059669; background: #f0fdf4; }
.agent-card.miss { border-left-color: #dc2626; background: #fef2f2; }
.agent-card .agent-name { font-size: 9pt; font-weight: 700; color: #0f172a; }
.agent-card .agent-meta { font-size: 7.5pt; color: #64748b; }
.agent-card .agent-meta .vote-hit { color: #059669; font-weight: 700; }
.agent-card .agent-meta .vote-miss { color: #dc2626; font-weight: 700; }
.agent-card .agent-quote {
  font-family: 'Source Serif 4', Georgia, serif;
  font-style: italic;
  font-size: 8.5pt;
  line-height: 1.55;
  color: #475569;
  margin-top: 6px;
}

/* ── Warning Banners ── */
.warning-banner {
  padding: 8px 12px;
  background: #fffbeb;
  border-left: 3px solid #d97706;
  font-size: 7.5pt;
  color: #92400e;
  margin: 8px 0;
}
.warning-banner.red { border-left-color: #dc2626; background: #fef2f2; color: #991b1b; }
.warning-banner.blue { border-left-color: #2563eb; background: #eff6ff; color: #1e40af; }

/* ── Peer Review Flags ── */
.peer-flag {
  padding: 6px 10px;
  background: #fef3c7;
  border-left: 3px solid #d97706;
  margin-bottom: 6px;
  font-size: 7.5pt;
}
.peer-flag .flagged-by { font-weight: 700; color: #d97706; }
.stat-card .stat-value.green { color: #059669; }
.stat-card .stat-label {
  font-size: 7pt;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-top: 3px;
}

/* ── Verdict Badge ────────────────────────────────────────────────────────── */
.verdict-pill {
  display: inline-block;
  padding: 4px 14px;
  border-radius: 20px;
  font-size: 10pt;
  font-weight: 700;
  letter-spacing: 0.3px;
  text-transform: uppercase;
}
.verdict-strong-hit  { background: #1a7a3c; color: #fff; }
.verdict-likely-hit  { background: #059669; color: #fff; }
.verdict-mixed       { background: #f39c12; color: #fff; }
.verdict-likely-miss { background: #e67e22; color: #fff; }
.verdict-strong-miss { background: #dc2626; color: #fff; }

/* ── Score Bars (10-Dimension) ────────────────────────────────────────────── */
.score-bars { margin: 8px 0; }
.score-row {
  display: flex;
  align-items: center;
  margin: 3px 0;
  gap: 8px;
}
.score-dim-name {
  width: 190px;
  font-size: 8.5pt;
  color: #333;
  flex-shrink: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.score-bar-bg {
  flex: 1;
  height: 14px;
  background: #e8ecf1;
  border-radius: 2px;
  overflow: hidden;
}
.score-bar-fill {
  height: 100%;
  border-radius: 2px;
}
.score-bar-fill.green  { background: #059669; }
.score-bar-fill.orange { background: #f39c12; }
.score-bar-fill.red    { background: #dc2626; }
.score-num {
  width: 28px;
  text-align: right;
  font-weight: 700;
  font-size: 8.5pt;
  color: #0f2440;
  flex-shrink: 0;
}

/* ── Key-Value Grid (PitchBook style) ─────────────────────────────────────── */
.kv-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 16px;
  margin: 6px 0;
}
.kv-col { /* each column */ }
.kv-row {
  display: flex;
  padding: 4px 0;
  border-bottom: 1px solid #f0f0f0;
  font-size: 8.5pt;
}
.kv-label {
  font-weight: 700;
  color: #0f2440;
  width: 42%;
  flex-shrink: 0;
}
.kv-value {
  color: #333;
  flex: 1;
  word-break: break-word;
}

/* ── Tables (PitchBook style) ─────────────────────────────────────────────── */
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 8.5pt;
  margin: 6px 0 10px 0;
}
th {
  background: #0f2440;
  color: #fff;
  padding: 6px 8px;
  text-align: left;
  font-size: 7.5pt;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  font-weight: 600;
  white-space: nowrap;
}
th.right, td.right { text-align: right; }
td {
  padding: 5px 8px;
  border-bottom: 1px solid #eaeaea;
  vertical-align: top;
  color: #222;
}
tr:nth-child(even) td { background: #f8f9fa; }
td.num { text-align: right; font-variant-numeric: tabular-nums; }
td.green-text { color: #059669; font-weight: 600; }
td.red-text   { color: #dc2626; font-weight: 600; }
.table-no-data {
  font-size: 8.5pt;
  color: #888;
  font-style: italic;
  padding: 8px 0;
}

/* ── Tags / Pills ─────────────────────────────────────────────────────────── */
.tag {
  display: inline-block;
  background: #e8f4f8;
  color: #0f2440;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 7.5pt;
  margin: 2px 2px 2px 0;
  font-weight: 500;
}
.zone-badge {
  display: inline-block;
  background: #e8f4f8;
  color: #0f2440;
  padding: 1px 7px;
  border-radius: 10px;
  font-size: 7pt;
  font-weight: 600;
}
.badge-hit  { background: #059669; color: #fff; padding: 2px 8px; border-radius: 3px; font-size: 7pt; font-weight: 700; display: inline-block; }
.badge-miss { background: #dc2626; color: #fff; padding: 2px 8px; border-radius: 3px; font-size: 7pt; font-weight: 700; display: inline-block; }
.badge-high   { background: #dc2626; color: #fff; padding: 2px 7px; border-radius: 3px; font-size: 7pt; font-weight: 700; display: inline-block; }
.badge-medium { background: #f39c12; color: #fff; padding: 2px 7px; border-radius: 3px; font-size: 7pt; font-weight: 700; display: inline-block; }
.badge-low    { background: #059669; color: #fff; padding: 2px 7px; border-radius: 3px; font-size: 7pt; font-weight: 700; display: inline-block; }

/* ── Verdict Box ──────────────────────────────────────────────────────────── */
.verdict-box {
  background: #f8f9fa;
  border: 2px solid #0f2440;
  border-radius: 6px;
  padding: 16px 20px;
  margin: 10px 0;
  display: flex;
  gap: 20px;
  align-items: flex-start;
}
.verdict-score-block { text-align: center; flex-shrink: 0; }
.verdict-big-score {
  font-size: 48pt;
  font-weight: 900;
  color: #0f2440;
  line-height: 1;
}
.verdict-out-of { font-size: 10pt; color: #888; }
.verdict-details { flex: 1; }
.verdict-details p { font-size: 9pt; color: #333; line-height: 1.5; margin-top: 8px; }

/* ── Narrative Text ───────────────────────────────────────────────────────── */
.narrative { font-size: 8.5pt; color: #333; line-height: 1.55; margin: 6px 0 10px 0; }
.narrative p { margin-bottom: 6px; }

/* ── Bullet Lists ─────────────────────────────────────────────────────────── */
ul.strength-list, ul.weakness-list { list-style: none; padding: 0; margin: 4px 0; }
ul.strength-list li, ul.weakness-list li {
  padding: 2px 0 2px 16px;
  position: relative;
  font-size: 8.5pt;
  line-height: 1.45;
}
ul.strength-list li::before { content: "\\2022"; color: #059669; position: absolute; left: 2px; font-size: 10pt; line-height: 1.1; }
ul.weakness-list li::before { content: "\\2022"; color: #dc2626; position: absolute; left: 2px; font-size: 10pt; line-height: 1.1; }
ul.plain-list { list-style: none; padding: 0; margin: 4px 0; }
ul.plain-list li { padding: 2px 0 2px 14px; position: relative; font-size: 8.5pt; }
ul.plain-list li::before { content: "\\25B6"; color: #2563eb; position: absolute; left: 0; font-size: 6pt; top: 5px; }
ol.numbered-list { padding-left: 18px; margin: 4px 0; }
ol.numbered-list li { font-size: 8.5pt; padding: 2px 0; line-height: 1.45; }

/* ── Agent Response Cards (Appendix D) ───────────────────────────────────── */
.agent-card {
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  padding: 8px 10px;
  margin: 5px 0;
  page-break-inside: avoid;
}
.agent-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 5px;
  flex-wrap: wrap;
}
.agent-persona { font-weight: 700; font-size: 8.5pt; color: #0f2440; }
.agent-score   { font-size: 8pt; font-weight: 700; color: #333; margin-left: auto; }
.agent-reasoning { font-size: 8pt; color: #444; line-height: 1.5; }
.zone-group-header {
  background: #f0f4f8;
  padding: 4px 10px;
  font-size: 8pt;
  font-weight: 700;
  color: #0f2440;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 10px 0 4px 0;
  border-left: 3px solid #2563eb;
}

/* ── Two-column flex layout ───────────────────────────────────────────────── */
.cols-2 { display: flex; gap: 14px; }
.cols-2 > .col { flex: 1; min-width: 0; }
.cols-3 { display: flex; gap: 10px; }
.cols-3 > .col { flex: 1; min-width: 0; }

/* ── Misc helpers ─────────────────────────────────────────────────────────── */
.mt4 { margin-top: 4px; }
.mt8 { margin-top: 8px; }
.mt12 { margin-top: 12px; }
.text-right { text-align: right; }
.text-muted { color: #888; font-size: 7.5pt; }
.bold { font-weight: 700; }
.divider { border: none; border-top: 1px solid #e0e0e0; margin: 8px 0; }

/* ── Footer (page number via CSS counters) ────────────────────────────────── */
body { counter-reset: page-counter; }
.page { counter-increment: page-counter; }
.footer {
  position: absolute;
  bottom: 10mm;
  left: 20mm;
  right: 20mm;
  font-size: 6.5pt;
  color: #aaa;
  border-top: 1px solid #e0e0e0;
  padding-top: 4px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.footer .footer-right::after { content: "Page " counter(page-counter); }

/* ── SVG charts ───────────────────────────────────────────────────────────── */
svg { display: block; }
svg text { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }
"""

REPORT_PROMPT = """You are a professional investment analyst and report designer. Generate a COMPLETE HTML report body for a startup due diligence analysis.

ANALYSIS DATA (JSON):
{analysis_json}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL RULES — FOLLOW EXACTLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. USE ONLY CSS CLASSES defined in the stylesheet. Do NOT use inline styles.
2. Every number, name, and fact MUST come from the analysis JSON. NO invented data.
3. If a field is missing or empty, skip that section gracefully (no empty tables, no "N/A", no "Unknown").
4. Produce ALL pages including appendices A through E in a single output.
5. Every .page div MUST end with a footer div:
   <div class="footer"><span>Mirai (未来) + Sensei (先生) — VCLabs.org</span><span class="footer-right"></span></div>
6. ALL agent responses from sample_agents MUST appear in Appendix D, grouped by zone.
7. Financial numbers (amounts, revenue) must use class="num" on <td> for right-alignment.
8. Positive growth uses class="green-text", losses use class="red-text" on <td>.
9. SVG charts must be self-contained, sized to fit, with the color scheme: navy=#0f2440, teal=#2563eb, green=#059669, orange=#f39c12, red=#dc2626.
10. Keep total report to 12–15 pages. Compress prose; prefer tables.
11. ANONYMIZATION: Council evaluators are labeled "Elder 1", "Elder 2", etc. NEVER reveal actual model names, providers, or AI company names (no "Claude", "GPT", "Llama", "Qwen", etc.). Use only the Elder labels provided. Swarm agents use their persona names only.
12. In the Methodology appendix, describe the council as "10 frontier language models across 8 model families" — do NOT list model names.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DATA FIELD REFERENCE:
- Company name: extraction.company
- Industry: extraction.industry
- Product: extraction.product
- Stage: extraction.stage
- Business model: extraction.business_model or extraction.model
- Website: extraction.website
- LinkedIn: extraction.linkedin
- HQ: research.company_profile.hq OR extraction.hq
- Founded: research.company_profile.founded OR extraction.founded
- Employees: research.company_profile.employees OR extraction.employees
- Target market: extraction.target_market
- Entity type: extraction.entity_type
- Business status: extraction.business_status
- Score: prediction.composite_score
- Verdict: prediction.verdict
- Confidence: prediction.confidence
- Dimensions array: prediction.dimensions (each has .name and .score)
- Council models: prediction.council_models (array of "Elder N" labels)
- Council scores: prediction.council_scores (object mapping "Elder N" -> overall score float)
- Research sources: research.sources (array of {url, title} — use count for "Sources Cited" stat, cite in narrative where relevant)
- Deal history: research.company_profile.deal_history (array of objects)
- Financials: research.company_profile.financials
- Team: research.company_profile.team (array)
- Board: research.company_profile.board (array)
- Market data: research.market_data (has .tam, .sam, .growth_rate, .source)
- Pricing: research.pricing_analysis
- Competitors list: research.competitors (array of names)
- Competitor details: research.competitor_details (array of objects with name, hq, industry, founded, total_raised, financing_status, last_financing, employees, description)
- Patent data: research.patent_landscape (has .total_families, .active, .pending, .expiring, .freedom_to_operate, .key_patents)
- Swarm stats: swarm.total_agents, swarm.positive_pct, swarm.negative_pct, swarm.avg_confidence
- Swarm themes: swarm.key_themes_positive (array), swarm.key_themes_negative (array)
- Sample agents: swarm.sample_agents (array, each has .persona, .zone, .overall, .reasoning)
- Outliers: swarm.divergence.critical_outliers (array)
- Zone agreement: swarm.divergence.zone_agreement (object, zone->avg_score)
- Deliberation recommendation: swarm.deliberation.recommendation
- Consensus points: swarm.deliberation.consensus_points (array)
- Risks: plan.risks (array, each has .risk, .severity)
- Next moves: plan.next_moves (array, each has .action, .priority, .effort, .impact)
- Validation experiments: plan.validation_experiments (array)
- Report sections (narrative text): report_sections.* (keys like market_analysis, competitive_analysis, etc.)
- Strengths: report_sections.strengths OR extract from report_sections
- Weaknesses: report_sections.weaknesses OR extract from report_sections
- Evaluator count: length of prediction.council_models array (or prediction.dimensions length)
- Cache age: cache_age_days (float, days since research was cached — show "Research from X days ago" if > 1)
- Peer review flags: peer_review.flags (array of {flagged_by, target, claim, objection})
- Peer review rankings: peer_review.aggregate_rankings (object, evaluator_label -> avg_rank)
- Board members: research.company_profile.board_members (array of {name, title, representing, since})
- Revenue: research.company_profile.revenue or research.company_profile.financials.revenue
- Revenue growth: research.company_profile.financials.revenue_growth
- EBITDA: research.company_profile.financials.ebitda
- Total raised: research.company_profile.total_raised
- Last valuation: research.company_profile.last_valuation
- Contested severity: prediction.contested_dimensions[].severity ("disputed" or "heavily_contested")
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EXACT REPORT STRUCTURE — Generate each page as <div class="page">
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

═══ PAGE 1: COVER + HIGHLIGHTS ═══

Structure:
<div class="page">
  <!-- TOP BAR -->
  <div class="cover-top-bar">
    <div class="cover-brand"><span class="kanji">未来</span> MIRAI ANALYSIS</div>
    <div class="cover-date">Generated [DATE from today]<br>Analysis Depth: Deep</div>
  </div>

  <!-- COMPANY TITLE -->
  <div class="cover-title-block">
    <div class="cover-company">[extraction.company]</div>
    <div class="cover-subtitle">Private Company Profile</div>
  </div>
  <hr class="cover-divider">

  <!-- HIGHLIGHTS SECTION HEADER -->
  <div class="section-header">Highlights</div>

  <!-- STAT CARDS ROW: Score gauge + Verdict + Confidence + Evaluators + Agents -->
  <div class="stats-row">
    <!-- Card 1: Mirai Score with SVG gauge arc (semi-circle, 0-10 scale) -->
    <div class="stat-card" style="flex:1.2">
      [SVG gauge: semi-circle arc, navy background arc, colored fill arc proportional to score/10, score number in center]
      <div class="stat-label">Mirai Score</div>
    </div>
    <!-- Card 2: Verdict badge (color-coded pill, pick class based on verdict string) -->
    <div class="stat-card" style="flex:1.2">
      <div style="padding:6px 0">[verdict pill using appropriate .verdict-* class]</div>
      <div class="stat-label">Mirai Verdict</div>
    </div>
    <!-- Card 3: Council Confidence -->
    <div class="stat-card">
      <div class="stat-value">[prediction.confidence]%</div>
      <div class="stat-label">Council Confidence</div>
    </div>
    <!-- Card 4: Evaluators -->
    <div class="stat-card">
      <div class="stat-value">[count of prediction.council_models]</div>
      <div class="stat-label">Evaluators</div>
    </div>
    <!-- Card 5: Swarm Agents -->
    <div class="stat-card">
      <div class="stat-value">[swarm.total_agents]</div>
      <div class="stat-label">Swarm Agents</div>
    </div>
  </div>

  <!-- 10-DIMENSION SCORING: horizontal bar chart -->
  <div class="section-header" style="margin-top:12px">10-Dimension Scoring</div>
  <div class="score-bars">
    [For EACH dimension in prediction.dimensions, render:]
    <div class="score-row">
      <div class="score-dim-name">[dimension.name]</div>
      <div class="score-bar-bg">
        <div class="score-bar-fill [green if >=7, orange if 5-6.9, red if <5]"
             style="width:[score*10]%"></div>
      </div>
      <div class="score-num">[score]</div>
    </div>
    [If prediction.dimensions is empty or missing, skip this block entirely]
  </div>

  <!-- SWARM VOTE DONUT + DATA QUALITY + SOURCES (PitchBook density) -->
  [If swarm data exists:]
  <div class="stats-row" style="margin-top:12px">
    <div class="stat-card" style="flex:1.2">
      [SVG donut chart: 100x100, green arc = positive_pct%, red arc = negative_pct%,
       center text showing "{positive_pct}% HIT" or "{negative_pct}% MISS" (whichever is larger).
       Use: green=#059669, red=#dc2626, background=#e2e8f0]
      <div class="stat-label">Swarm by Vote</div>
    </div>
    <div class="stat-card" style="flex:1.2">
      [SVG donut chart: 100x100, showing zone distribution from swarm.divergence.zone_agreement.
       One colored arc per zone: Investor=#0f2440, Customer=#059669, Operator=#2563eb,
       Analyst=#d97706, Contrarian=#dc2626, Wildcard=#64748b.
       Legend with zone names and agent counts below.]
      <div class="stat-label">Swarm by Zone</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">[data_quality × 100, rounded]%</div>
      <div class="stat-label">Data Quality</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">[count of research sources]</div>
      <div class="stat-label">Sources Cited</div>
    </div>
  </div>

  [FOOTER]
</div>

═══ PAGE 2: GENERAL INFORMATION ═══

Structure:
<div class="page">
  <div class="page-header">
    <div class="cover-brand"><span class="kanji">未来</span> MIRAI ANALYSIS</div>
    <div class="company-name">[extraction.company]</div>
  </div>

  <div class="section-header">General Information</div>

  <!-- TWO-COLUMN KEY-VALUE GRID (PitchBook style) -->
  <div class="kv-grid">
    <div class="kv-col">
      <div class="kv-row"><span class="kv-label">Company</span><span class="kv-value">[extraction.company]</span></div>
      <div class="kv-row"><span class="kv-label">Industry</span><span class="kv-value">[extraction.industry]</span></div>
      <div class="kv-row"><span class="kv-label">Product</span><span class="kv-value">[extraction.product, truncated to ~80 chars]</span></div>
      <div class="kv-row"><span class="kv-label">Entity Type</span><span class="kv-value">[extraction.entity_type or "Private Company"]</span></div>
      <div class="kv-row"><span class="kv-label">Business Status</span><span class="kv-value">[extraction.business_status]</span></div>
      [if website exists:] <div class="kv-row"><span class="kv-label">Website</span><span class="kv-value">[extraction.website]</span></div>
      [if linkedin exists:] <div class="kv-row"><span class="kv-label">LinkedIn</span><span class="kv-value">[extraction.linkedin]</span></div>
    </div>
    <div class="kv-col">
      [if founded exists:] <div class="kv-row"><span class="kv-label">Year Founded</span><span class="kv-value">[founded]</span></div>
      [if hq exists:] <div class="kv-row"><span class="kv-label">HQ Location</span><span class="kv-value">[hq]</span></div>
      [if employees exists:] <div class="kv-row"><span class="kv-label">Employees</span><span class="kv-value">[employees]</span></div>
      <div class="kv-row"><span class="kv-label">Target Market</span><span class="kv-value">[extraction.target_market, truncated]</span></div>
      <div class="kv-row"><span class="kv-label">Business Model</span><span class="kv-value">[business_model]</span></div>
      <div class="kv-row"><span class="kv-label">Stage</span><span class="kv-value">[extraction.stage]</span></div>
    </div>
  </div>

  <!-- DESCRIPTION: 2-3 sentences from report_sections -->
  <div class="section-header">Description</div>
  <div class="narrative"><p>[2-3 sentence description from report_sections.company_overview or extraction data]</p></div>

  <!-- MOST RECENT FINANCING STATUS (like PitchBook) -->
  [If deal_history exists and has entries:]
  <div class="section-header">Most Recent Financing Status</div>
  <div class="narrative"><p>[1 paragraph describing most recent deal from research.company_profile.deal_history]</p></div>

  <!-- INDUSTRIES / VERTICALS / KEYWORDS -->
  <div class="section-header">Industries, Verticals &amp; Keywords</div>
  <div class="cols-3">
    <div class="col">
      <div class="subsection-label">Primary Industry</div>
      <span class="tag">[extraction.industry]</span>
    </div>
    <div class="col">
      <div class="subsection-label">Verticals</div>
      [tags for each vertical/keyword from extraction or research]
    </div>
    <div class="col">
      <div class="subsection-label">Keywords</div>
      [3-6 keyword tags relevant to the company]
    </div>
  </div>

  [FOOTER]
</div>

═══ PAGE 3: DEAL HISTORY + FINANCIALS ═══

Structure:
<div class="page">
  [page-header]
  <div class="section-header">Deal History</div>

  [If research.company_profile.deal_history exists and is non-empty:]
  <!-- DEAL HISTORY TABLE (PitchBook style) -->
  <table>
    <thead><tr>
      <th>#</th><th>Deal Type</th><th>Date</th>
      <th class="right">Amount</th><th class="right">Raised to Date</th>
      <th class="right">Pre-Val</th><th class="right">Post-Val</th><th>Status</th>
    </tr></thead>
    <tbody>
      [For each deal in deal_history, most recent first:]
      <tr>
        <td>[#]</td><td>[deal_type]</td><td>[date]</td>
        <td class="num">[amount or "Undisclosed"]</td>
        <td class="num">[raised_to_date or "—"]</td>
        <td class="num">[pre_val or "—"]</td>
        <td class="num">[post_val or "—"]</td>
        <td>[status]</td>
      </tr>
    </tbody>
  </table>

  <!-- TOTAL RAISED + VALUATION STAT CARDS -->
  <div class="stats-row">
    <div class="stat-card">
      <div class="stat-value">[total raised, e.g. "$45.84M"]</div>
      <div class="stat-label">Total Raised to Date</div>
    </div>
    [If last_valuation exists:]
    <div class="stat-card">
      <div class="stat-value accent">[last_valuation, e.g. "$59.55M"]</div>
      <div class="stat-label">Post Valuation</div>
    </div>
  </div>

  <!-- VALUATION STEP-UP CHART (SVG, PitchBook style) -->
  [If deal_history has 2+ entries with valuation data:]
  <div style="margin:8px 0">
    [SVG bar chart: 100% width × 100px height.
     One bar per funding round (most recent on right).
     Bar height proportional to post-money valuation.
     Label each bar: deal type on X-axis, "$XM" value on top.
     Connect bar tops with accent=#2563eb line to show progression.
     Bars: navy=#0f2440. Grid: #e2e8f0. Font: 7pt DM Sans.]
  </div>

  [Else if no deal history:]
  <p class="table-no-data">No disclosed funding rounds found in research data.</p>

  <!-- FINANCIALS TABLE (if research.company_profile.financials exists) -->
  [If financials data exists:]
  <div class="section-header">Financials</div>
  <table>
    <thead><tr>
      <th>Metric</th>
      [For each fiscal year column:]
      <th class="right">[FY Year]</th>
    </tr></thead>
    <tbody>
      <tr><td>Total Revenue</td>[<td class="num">values</td>]</tr>
      <tr><td>Revenue % Growth</td>[<td class="num [green-text if positive, red-text if negative]">values</td>]</tr>
      <tr><td>EBITDA (Normalized)</td>[<td class="num [red-text if negative]">values</td>]</tr>
    </tbody>
  </table>

  [FOOTER]
</div>

═══ PAGE 4: MARKET ANALYSIS ═══

Structure:
<div class="page">
  [page-header]
  <div class="section-header">Market Analysis</div>

  <!-- MARKET STAT CARDS: TAM, SAM, Growth Rate, Source -->
  <div class="stats-row">
    [If research.market_data.tam exists:]
    <div class="stat-card"><div class="stat-value">[tam]</div><div class="stat-label">Total Addressable Market</div></div>
    [If research.market_data.sam exists:]
    <div class="stat-card"><div class="stat-value">[sam]</div><div class="stat-label">Serviceable Addressable Market</div></div>
    [If research.market_data.growth_rate exists:]
    <div class="stat-card"><div class="stat-value">[growth_rate]</div><div class="stat-label">Market Growth Rate (CAGR)</div></div>
    [If research.market_data.source exists:]
    <div class="stat-card"><div class="stat-value green" style="font-size:8pt;font-weight:600">[source name only, ≤20 chars]</div><div class="stat-label">Source</div></div>
  </div>

  <!-- TAM/SAM/SOM FUNNEL (SVG visual, PitchBook style) -->
  [If market_data has tam AND sam:]
  <div style="margin:8px 0">
    [SVG nested horizontal bars: 100% width × 80px.
     Bar 1 (TAM): full width, fill=#0f2440 at 0.15 opacity, label "TAM: $X.XB" left-aligned
     Bar 2 (SAM): 65% width, fill=#0f2440 at 0.3 opacity, label "SAM: $X.XB" left-aligned
     Bar 3 (SOM): 35% width, fill=#2563eb, label "SOM: $XXM" left-aligned (if data exists)
     Source citation in 7pt below the chart.]
  </div>

  <!-- MARKET NARRATIVE: 2-3 paragraphs from report_sections.market_analysis -->
  [If report_sections.market_analysis exists:]
  <div class="narrative">[2-3 paragraphs of market_analysis text]</div>

  <!-- PRICING COMPARISON TABLE (if research.pricing_analysis exists) -->
  [If pricing data is available:]
  <div class="section-header">Pricing Comparison</div>
  <table>
    <thead><tr><th>Company</th><th>Plan / Tier</th><th class="right">Price</th><th>Notes</th></tr></thead>
    <tbody>[pricing rows from research.pricing_analysis]</tbody>
  </table>

  [FOOTER]
</div>

═══ PAGE 5: COMPETITIVE LANDSCAPE ═══

Structure:
<div class="page">
  [page-header]
  <div class="section-header">Top Similar Companies</div>

  <!-- TOP SIMILAR COMPANIES TABLE (PitchBook style) -->
  <table>
    <thead><tr>
      <th>#</th><th>Name</th><th>Financing Status</th>
      <th>HQ Location</th><th>Primary Industry</th>
      <th>Year Founded</th><th class="right">Total Raised</th>
    </tr></thead>
    <tbody>
      [For each competitor in research.competitor_details (up to 6), use REAL data:]
      <tr>
        <td>[#]</td>
        <td class="bold">[name]</td>
        <td>[financing_status — use actual value, not "Unknown"]</td>
        <td>[hq — use actual value]</td>
        <td>[industry]</td>
        <td>[founded]</td>
        <td class="num">[total_raised or "Undisclosed"]</td>
      </tr>
      [Skip any competitor row where name is missing]
    </tbody>
  </table>

  <!-- SIDE-BY-SIDE COMPARISONS TABLE (PitchBook Comparisons section) -->
  <div class="section-header">Comparisons</div>
  <table>
    <thead><tr>
      <th>Attribute</th>
      <th>[extraction.company] (Target)</th>
      [For top 3-4 competitors in competitor_details:]
      <th>[competitor.name]</th>
    </tr></thead>
    <tbody>
      <tr>
        <td class="bold kv-label">Description</td>
        <td>[2-sentence description of target company]</td>
        [<td>[competitor.description, ~1 sentence]</td> for each]
      </tr>
      <tr>
        <td class="bold kv-label">Primary Industry</td>
        <td>[extraction.industry]</td>
        [<td>[competitor.industry]</td>]
      </tr>
      <tr>
        <td class="bold kv-label">HQ Location</td>
        <td>[hq]</td>
        [<td>[competitor.hq]</td>]
      </tr>
      <tr>
        <td class="bold kv-label">Employees</td>
        <td>[employees]</td>
        [<td>[competitor.employees]</td>]
      </tr>
      <tr>
        <td class="bold kv-label">Total Raised</td>
        <td>[total raised or "Undisclosed"]</td>
        [<td>[competitor.total_raised]</td>]
      </tr>
      <tr>
        <td class="bold kv-label">Last Financing</td>
        <td>[most recent deal from deal_history]</td>
        [<td>[competitor.last_financing]</td>]
      </tr>
    </tbody>
  </table>

  <!-- COMPETITIVE POSITIONING SCATTER (SVG, price vs capability) -->
  [If competitor_details has 3+ entries:]
  <div style="margin:8px 0">
    [SVG scatter plot: 100% width × 180px.
     X-axis: "Price Point (Low → High)". Y-axis: "Capability Scope (Low → High)".
     Plot the target company as a large green circle (#059669, r=8) with bold label.
     Plot each competitor as a gray circle (#94a3b8, r=5) with label.
     Position based on your assessment of each company's pricing and capability.
     Light grid lines in #e2e8f0. Axis labels in 7pt #64748b.]
  </div>

  [FOOTER]
</div>

═══ PAGE 6: TEAM + PATENTS + VERDICT ═══

Structure:
<div class="page">
  [page-header]

  <!-- TEAM TABLE (if research.company_profile.team exists and is non-empty) -->
  [If team data exists:]
  <div class="section-header">Current Team</div>
  <table>
    <thead><tr><th>Name</th><th>Title</th><th>Background</th></tr></thead>
    <tbody>
      [For each team member:]
      <tr><td class="bold">[name]</td><td>[title]</td><td>[background/bio, ≤100 chars]</td></tr>
    </tbody>
  </table>

  <!-- BOARD MEMBERS TABLE (if board data exists) -->
  [If board data exists:]
  <div class="section-header">Board Members</div>
  <table>
    <thead><tr><th>Name</th><th>Title</th><th>Representing</th><th>Since</th></tr></thead>
    <tbody>[board member rows]</tbody>
  </table>

  <!-- PATENT SUMMARY STAT CARDS (if research.patent_landscape exists) -->
  [If patent_landscape.total_families > 0 OR patent_landscape.active > 0:]
  <div class="section-header">Patents &amp; IP</div>
  <div class="stats-row">
    <div class="stat-card"><div class="stat-value">[total_families or 0]</div><div class="stat-label">Total Patent Families</div></div>
    <div class="stat-card"><div class="stat-value green">[active or 0]</div><div class="stat-label">Active</div></div>
    <div class="stat-card"><div class="stat-value accent">[pending or 0]</div><div class="stat-label">Pending</div></div>
    [if expiring:] <div class="stat-card"><div class="stat-value">[expiring]</div><div class="stat-label">Expiring (12mo)</div></div>
  </div>
  [If freedom_to_operate text exists:]
  <div class="narrative"><p>[freedom_to_operate text, ≤200 chars]</p></div>

  <!-- SCORE RADAR (SVG spider chart, PitchBook-style visual density) -->
  [If prediction.dimensions has data:]
  <div style="margin:8px 0; text-align:center">
    [SVG radar/spider chart: 220x220, centered.
     10 axes radiating from center for 10 dimensions.
     Blue filled polygon (#2563eb at 0.15 opacity) connecting score points.
     Blue border line (#2563eb, stroke-width 1.5).
     Gray pentagon rings at score=2, 4, 6, 8 for reference (#e2e8f0, stroke-width 0.5).
     Red dashed circle at score=5.0 as "average" line (#dc2626, opacity 0.3).
     Dimension name labels around outside in 6.5pt #64748b.
     Score value at each vertex in 7pt bold.]
  </div>

  <!-- INVESTMENT VERDICT BOX (large, prominent) -->
  <div class="section-header">Investment Verdict</div>
  <div class="verdict-box">
    <div class="verdict-score-block">
      <div class="verdict-big-score">[prediction.composite_score]</div>
      <div class="verdict-out-of">/ 10</div>
      <div style="margin-top:6px">[verdict pill: <span class="verdict-pill verdict-[mapped class]">[verdict]</span>]</div>
      <div style="margin-top:4px;font-size:7.5pt;color:#666">[prediction.confidence]% confidence</div>
    </div>
    <div class="verdict-details">
      <p>[swarm.deliberation.recommendation OR report_sections.recommendation, 1 paragraph, ≤400 chars]</p>
      [If report_sections.strengths exists:]
      <div class="subsection-label mt8">Strengths</div>
      <ul class="strength-list">[3-5 strength bullet items from data]</ul>
      [If report_sections.weaknesses exists:]
      <div class="subsection-label mt8">Weaknesses</div>
      <ul class="weakness-list">[3-5 weakness bullet items from data]</ul>
    </div>
  </div>

  [FOOTER]
</div>

═══ APPENDIX A (page): SWARM INTELLIGENCE ═══

Structure:
<div class="page">
  [page-header]
  <div class="section-header appendix-header">Appendix A — Swarm Intelligence</div>

  <!-- SWARM STAT CARDS -->
  <div class="stats-row">
    <div class="stat-card"><div class="stat-value">[swarm.total_agents]</div><div class="stat-label">Total Agents</div></div>
    <div class="stat-card"><div class="stat-value green">[swarm.positive_pct]%</div><div class="stat-label">Positive</div></div>
    <div class="stat-card"><div class="stat-value accent">[swarm.negative_pct]%</div><div class="stat-label">Negative</div></div>
    <div class="stat-card"><div class="stat-value">[swarm.avg_confidence]%</div><div class="stat-label">Avg Confidence</div></div>
  </div>

  <!-- SWARM BY ZONE: SVG donut chart using swarm.divergence.zone_agreement data -->
  [Generate SVG donut chart: for each zone in zone_agreement, a colored arc segment proportional to agent count/score.
   Use: Investor=#0f2440, Customer=#059669, Operator=#2563eb, Analyst=#f39c12, Contrarian=#dc2626, Wildcard=#9b59b6.
   Size: 140x140, centered, with zone labels and percentages around the outside.]

  <!-- KEY THEMES: side-by-side positive / negative -->
  <div class="cols-2 mt8">
    <div class="col">
      <div class="subsection-label">Positive Themes</div>
      <ul class="strength-list">
        [For each theme in swarm.key_themes_positive:] <li>[theme]</li>
      </ul>
    </div>
    <div class="col">
      <div class="subsection-label">Negative Themes</div>
      <ul class="weakness-list">
        [For each theme in swarm.key_themes_negative:] <li>[theme]</li>
      </ul>
    </div>
  </div>

  <!-- TOP 6 AGENT PERSPECTIVES TABLE (condensed, NOT full reasoning) -->
  <div class="section-header" style="margin-top:12px">Top Agent Perspectives</div>
  <table>
    <thead><tr><th>Persona</th><th>Zone</th><th class="right">Score</th><th>Key Insight (1–2 sentences)</th></tr></thead>
    <tbody>
      [For each agent in swarm.sample_agents (up to 6):]
      <tr>
        <td class="bold">[agent.persona]</td>
        <td><span class="zone-badge">[agent.zone]</span></td>
        <td class="num">[agent.overall]/10</td>
        <td>[agent.reasoning — full text, show complete reasoning]</td>
      </tr>
    </tbody>
  </table>

  <!-- CRITICAL DIVERGENCE: outlier agents -->
  [If swarm.divergence.critical_outliers is non-empty:]
  <div class="subsection-label mt8">Critical Divergence</div>
  <table>
    <thead><tr><th>Persona</th><th>Zone</th><th class="right">Score</th><th>Divergence Note</th></tr></thead>
    <tbody>
      [For each outlier in critical_outliers:]
      <tr>
        <td class="bold">[outlier.persona]</td>
        <td><span class="zone-badge">[outlier.zone]</span></td>
        <td class="num">[outlier.overall]/10</td>
        <td>[outlier.reasoning_excerpt — full text]</td>
      </tr>
    </tbody>
  </table>

  [FOOTER]
</div>

═══ APPENDIX B (page): COUNCIL DELIBERATION ═══

Structure:
<div class="page">
  [page-header]
  <div class="section-header appendix-header">Appendix B — Council Deliberation</div>

  <!-- COMMITTEE TABLE: show anonymized council elders with their overall scores from prediction.council_scores -->
  [If prediction.council_models exists and non-empty:]
  <div class="subsection-label">Committee</div>
  <table>
    <thead><tr><th>Evaluator</th><th>Zone</th><th class="right">Overall Score</th></tr></thead>
    <tbody>
      [For each elder label in prediction.council_models, look up score in prediction.council_scores[elder_label]:]
      <tr>
        <td class="bold">[elder label, e.g. "Elder 1"]</td>
        <td><span class="zone-badge">Council</span></td>
        <td class="num">[prediction.council_scores[elder_label] rounded to 1 decimal, e.g. "5.3"]</td>
      </tr>
    </tbody>
  </table>

  <!-- CONSENSUS POINTS -->
  [If swarm.deliberation.consensus_points is non-empty:]
  <div class="subsection-label mt8">Consensus Points</div>
  <ol class="numbered-list">
    [For each consensus point:] <li>[point]</li>
  </ol>

  <!-- COMMITTEE RECOMMENDATION: 1 paragraph -->
  [If swarm.deliberation.recommendation exists:]
  <div class="subsection-label mt8">Committee Recommendation</div>
  <div class="narrative"><p>[recommendation, ≤500 chars]</p></div>

  <!-- PEER REVIEW (Karpathy Stage 2 — evaluators cross-validating each other) -->
  [If peer_review exists and has data:]
  <div class="subsection-label mt8">Peer Review — Cross-Validation</div>
  <p style="font-size:7.5pt;color:#666;margin-bottom:4px">Each evaluator reviewed the others' reasoning and flagged disagreements.</p>

  [If peer_review.aggregate_rankings exists:]
  <div class="subsection-label">Evaluator Trust Rankings (peer-rated)</div>
  <table>
    <thead><tr><th>Evaluator</th><th class="right">Avg Rank (lower = more trusted)</th></tr></thead>
    <tbody>
      [For each evaluator sorted by avg_rank:]
      <tr><td class="bold">[evaluator label]</td><td class="num">[avg_rank]</td></tr>
    </tbody>
  </table>

  [If peer_review.flags exists and non-empty:]
  <div class="subsection-label mt8">Flagged Claims</div>
  <table>
    <thead><tr><th>Flagged By</th><th>Target</th><th>Claim</th><th>Objection</th></tr></thead>
    <tbody>
      [For each flag (up to 5):]
      <tr>
        <td>[flagged_by]</td><td>[target]</td>
        <td>[claim, ≤80 chars]</td><td>[objection, ≤120 chars]</td>
      </tr>
    </tbody>
  </table>

  <!-- CACHE STALENESS WARNING -->
  [If cache_age_days exists and cache_age_days > 1:]
  <div class="narrative" style="margin-top:8px;padding:6px 10px;background:#fff8e1;border-left:3px solid #f39c12;font-size:7.5pt">
    Research data is [cache_age_days] days old. Recent developments may not be reflected.
  </div>

  [FOOTER]
</div>

═══ APPENDIX C (page): RISK ASSESSMENT + STRATEGY ═══

Structure:
<div class="page">
  [page-header]
  <div class="section-header appendix-header">Appendix C — Risk Assessment &amp; Strategy</div>

  <!-- RISKS TABLE -->
  [If plan.risks is non-empty:]
  <div class="subsection-label">Key Risks</div>
  <table>
    <thead><tr><th>#</th><th>Risk</th><th>Severity</th><th>Mitigation</th></tr></thead>
    <tbody>
      [For each risk in plan.risks (up to 8):]
      <tr>
        <td>[#]</td>
        <td>[risk.risk, ≤120 chars]</td>
        <td><span class="badge-[high/medium/low based on risk.severity]">[risk.severity]</span></td>
        <td>[mitigation if available, else leave blank]</td>
      </tr>
    </tbody>
  </table>

  <!-- NEXT MOVES TABLE -->
  [If plan.next_moves is non-empty:]
  <div class="subsection-label mt8">Strategic Next Moves</div>
  <table>
    <thead><tr><th>Action</th><th>Priority</th><th>Effort</th><th>Impact</th></tr></thead>
    <tbody>
      [For each move in plan.next_moves:]
      <tr>
        <td>[move.action, ≤120 chars]</td>
        <td>[move.priority]</td>
        <td>[move.effort]</td>
        <td>[move.impact]</td>
      </tr>
    </tbody>
  </table>

  <!-- VALIDATION EXPERIMENTS TABLE -->
  [If plan.validation_experiments is non-empty:]
  <div class="subsection-label mt8">Validation Experiments</div>
  <table>
    <thead><tr><th>Experiment</th><th>Cost</th><th>Timeline</th></tr></thead>
    <tbody>
      [For each experiment in plan.validation_experiments:]
      <tr>
        <td>[experiment.experiment, ≤150 chars]</td>
        <td>[experiment.cost]</td>
        <td>[experiment.timeline]</td>
      </tr>
    </tbody>
  </table>

  [FOOTER]
</div>

═══ APPENDIX D (1–3 pages): FULL AGENT RESPONSES ═══

NOTE: This section may span multiple .page divs. Start a new .page when content fills ~270mm.
Each .page must have its own footer.

Structure — first page of Appendix D:
<div class="page">
  [page-header]
  <div class="section-header appendix-header">Appendix D — Full Agent Responses ([swarm.total_agents] agents)</div>

  [Group ALL agents from swarm.sample_agents by zone. For each zone group:]
  <div class="zone-group-header">[Zone Name]</div>
  [For each agent in this zone:]
  <div class="agent-card">
    <div class="agent-card-header">
      <span class="agent-persona">[agent.persona]</span>
      <span class="zone-badge">[agent.zone]</span>
      <span class="[badge-hit if score>=6 else badge-miss]">[HIT if score>=6 else MISS]</span>
      <span class="agent-score">[agent.overall] / 10</span>
    </div>
    <div class="agent-reasoning">[agent.reasoning — FULL text, not truncated]</div>
  </div>

  [FOOTER]
</div>
[Continue in additional .page divs if needed]

═══ APPENDIX E (page): SCORING FRAMEWORK ═══

Structure:
<div class="page">
  [page-header]
  <div class="section-header appendix-header">Appendix E — Scoring Framework</div>

  <div class="subsection-label">10-Dimension Scoring Rubric</div>
  <table>
    <thead><tr><th>Dimension</th><th>What It Measures</th><th>Score Range</th></tr></thead>
    <tbody>
      <tr><td class="bold">Market Timing</td><td>Alignment of product launch with market readiness, demand signals, and macro trends</td><td>0–10</td></tr>
      <tr><td class="bold">Competition Landscape</td><td>Density and strength of existing competitors; defensibility of position</td><td>0–10</td></tr>
      <tr><td class="bold">Business Model Viability</td><td>Unit economics, pricing sustainability, revenue model coherence</td><td>0–10</td></tr>
      <tr><td class="bold">Team Execution Signals</td><td>Team completeness, domain expertise, track record, and operational capacity</td><td>0–10</td></tr>
      <tr><td class="bold">Regulatory Environment</td><td>Regulatory tailwinds/headwinds, compliance requirements, government funding signals</td><td>0–10</td></tr>
      <tr><td class="bold">Social Proof & Demand</td><td>Customer traction, LOIs, pilots, waitlists, partnerships, press coverage</td><td>0–10</td></tr>
      <tr><td class="bold">Pattern Match</td><td>Similarity to historically successful startups in structure, timing, and approach</td><td>0–10</td></tr>
      <tr><td class="bold">Capital Efficiency</td><td>Ability to achieve milestones with minimal capital; burn rate discipline</td><td>0–10</td></tr>
      <tr><td class="bold">Scalability Potential</td><td>Technical and operational ability to grow revenue without proportional cost increases</td><td>0–10</td></tr>
      <tr><td class="bold">Exit Potential</td><td>Likelihood and attractiveness of acquisition or IPO based on market, IP, and positioning</td><td>0–10</td></tr>
    </tbody>
  </table>

  <div class="subsection-label mt12">Verdict Scale</div>
  <table>
    <thead><tr><th>Score</th><th>Verdict</th><th>Meaning</th></tr></thead>
    <tbody>
      <tr><td class="num">8.0–10.0</td><td><span class="verdict-strong-hit">STRONG HIT</span></td><td>Exceptional fundamentals across all dimensions</td></tr>
      <tr><td class="num">6.5–7.9</td><td><span class="verdict-likely-hit">LIKELY HIT</span></td><td>Strong profile with manageable risks</td></tr>
      <tr><td class="num">5.0–6.4</td><td><span class="verdict-mixed">UNCERTAIN</span></td><td>Mixed signals; outcome depends on execution</td></tr>
      <tr><td class="num">3.5–4.9</td><td><span class="verdict-likely-miss">LIKELY MISS</span></td><td>Structural challenges outweigh strengths</td></tr>
      <tr><td class="num">0.0–3.4</td><td><span class="verdict-strong-miss">STRONG MISS</span></td><td>Fundamental viability concerns</td></tr>
    </tbody>
  </table>

  [FOOTER]
</div>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FOOTER TEMPLATE (use on every .page):
<div class="footer">
  <span>Mirai (未来) + Sensei (先生) — VCLabs.org</span>
  <span class="footer-right"></span>
</div>

VERDICT → CSS CLASS MAPPING:
- "Strong Hit" or "STRONG HIT" → verdict-strong-hit
- "Likely Hit" or "LIKELY HIT" → verdict-likely-hit
- "Mixed Signal" or "MIXED SIGNAL" or "Mixed" → verdict-mixed
- "Uncertain" or "UNCERTAIN" → verdict-mixed
- "Likely Miss" or "LIKELY MISS" → verdict-likely-miss
- "Strong Miss" or "STRONG MISS" → verdict-strong-miss
- Any other → verdict-mixed

SVG GAUGE INSTRUCTIONS (Page 1 Mirai Score):
- SVG size: 120x70 (semi-circle gauge)
- Background arc: stroke #e0e0e0, stroke-width 10, from 180deg to 0deg (path or arc element)
- Filled arc: stroke color based on score (>=7=#059669, 5-6.9=#f39c12, <5=#dc2626), from 180deg proportional to score/10
- Score text: centered below arc, 18pt bold, color #0f2440
- All coordinates calculated precisely for a 120-wide, 70-tall semi-circle with cx=60, cy=60, r=44

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT INSTRUCTIONS:
Return ONLY the HTML body content — all .page divs from Page 1 through Appendix E.
Do NOT include <html>, <head>, <style>, or <body> tags.
Do NOT wrap in markdown code fences.
Do NOT include explanations or commentary.
Start directly with the first <div class="page"> element."""


def generate_llm_report(analysis: Dict[str, Any]) -> str:
    """Generate complete HTML report using Opus via CLI, then GPT-5.4 reviews it."""
    try:
        # Prepare analysis data — trim to fit context
        trimmed = _trim_analysis(analysis)
        analysis_json = json.dumps(trimmed, indent=2, default=str)

        logger.info(f"[LLM Report] Sending {len(analysis_json)} chars to Opus via CLI...")

        # Use string replace instead of .format() to avoid KeyError on braces in template
        today_str = datetime.now().strftime("%d %B %Y")
        prompt = REPORT_PROMPT.replace("{analysis_json}", analysis_json)
        prompt = prompt.replace("[DATE from today]", today_str)
        prompt = prompt.replace("[today's date and time]", today_str)

        body_html = call_claude(
            prompt,
            model="claude-opus-4-6",
            max_tokens=16000,
            timeout=600,
        )

        logger.info(f"[LLM Report] Opus returned {len(body_html)} chars")

        # Strip markdown fences if present
        body_html = re.sub(r'^```(?:html)?\s*\n?', '', body_html.strip(), flags=re.IGNORECASE)
        body_html = re.sub(r'\n?```\s*$', '', body_html)

        # Review step removed — it either returns HTML unchanged (wasting time)
        # or returns QA notes instead of HTML (corrupting the report)

        # Wrap in full HTML document
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Mirai Analysis — {analysis.get('extraction', {}).get('company', 'Report')}</title>
<style>{REPORT_CSS}</style>
</head>
<body>
{body_html}
</body>
</html>"""

        return html

    except Exception as e:
        logger.error(f"[LLM Report] Failed: {e}")
        raise


def _review_report_html(body_html: str, analysis: Dict) -> str:
    """GPT-5.4 reviews the generated HTML for missing sections/tables and patches them."""
    try:
        # Build a checklist from the analysis data
        has_competitors = bool(analysis.get('research', {}).get('competitor_details'))
        has_team = bool(analysis.get('research', {}).get('company_profile', {}).get('team') or
                       analysis.get('extraction', {}).get('team'))
        has_deals = bool(analysis.get('research', {}).get('company_profile', {}).get('deal_history'))
        has_patents = bool(analysis.get('research', {}).get('patent_landscape'))
        has_swarm = bool(analysis.get('swarm', {}).get('total_agents'))
        has_plan = bool(analysis.get('plan', {}).get('risks') or analysis.get('plan', {}).get('next_moves'))
        has_peer_review = bool(analysis.get('peer_review', {}).get('flags') or analysis.get('peer_review', {}).get('aggregate_rankings'))
        has_board = bool(analysis.get('research', {}).get('company_profile', {}).get('board_members') or
                        analysis.get('research', {}).get('company_profile', {}).get('board'))

        review_prompt = (
            "You are a QA reviewer for a PDF report rendered from HTML. "
            "Check this HTML report body for completeness and fix any issues.\n\n"
            "EXPECTED SECTIONS (based on available data):\n"
            "1. Cover page with company name, Mirai score gauge, verdict badge, dimension bars\n"
            "2. General Information grid (2-col layout)\n"
            f"3. Deal History table {'(DATA EXISTS - must show table)' if has_deals else '(no data - skip gracefully)'}\n"
            "4. Market Analysis with TAM/SAM stats\n"
            f"5. Competitive Landscape table {'(DATA EXISTS - must show competitor table)' if has_competitors else '(no data - skip gracefully)'}\n"
            f"6. Team section {'(DATA EXISTS)' if has_team else '(no data - skip gracefully)'}\n"
            f"7. Patents/IP section {'(DATA EXISTS)' if has_patents else '(no data - skip gracefully)'}\n"
            f"8. Swarm Intelligence section {'(DATA EXISTS - must show zone breakdown, themes)' if has_swarm else '(skip)'}\n"
            f"9. Risk Assessment + Strategy {'(DATA EXISTS)' if has_plan else '(skip)'}\n"
            f"9b. Peer Review cross-validation {'(DATA EXISTS — show trust rankings + flags)' if has_peer_review else '(skip)'}\n"
            f"9c. Board Members table {'(DATA EXISTS — include Representing column)' if has_board else '(skip)'}\n"
            "10. Investment Verdict page with final score, verdict, strengths/weaknesses\n"
            "11. Every page must have a footer with 'Mirai (未来) + Sensei (先生) — VCLabs.org'\n\n"
            "CHECK FOR:\n"
            "- Missing tables that should exist (competitor comparison, deal history)\n"
            "- Empty sections that should have content\n"
            "- Broken HTML structure (unclosed tags, missing page breaks)\n"
            "- Score bars without actual scores\n"
            "- SVG charts that are empty or have no data\n"
            "- Pages without footers\n\n"
            "If everything looks complete, return the HTML unchanged.\n"
            "If there are issues, fix them and return the COMPLETE corrected HTML.\n\n"
            "Return ONLY the HTML body content. No markdown fences. No explanation.\n\n"
            f"HTML TO REVIEW ({len(body_html)} chars):\n{body_html}"
        )

        logger.info("[LLM Report] Reviewing report completeness...")
        reviewed = call_claude(review_prompt, model="claude-opus-4-6", max_tokens=16000, timeout=180)

        # Strip markdown fences from review output
        reviewed = re.sub(r'^```(?:html)?\s*\n?', '', reviewed.strip(), flags=re.IGNORECASE)
        reviewed = re.sub(r'\n?```\s*$', '', reviewed)

        if reviewed and len(reviewed) > len(body_html) * 0.5:
            logger.info(f"[LLM Report] Review done: {len(body_html)} -> {len(reviewed)} chars")
            return reviewed
        else:
            logger.warning("[LLM Report] Review returned short output, keeping original")
            return body_html

    except Exception as e:
        logger.warning(f"[LLM Report] GPT-5.4 review failed (non-fatal, keeping original): {e}")
        return body_html


def _trim_analysis(analysis: Dict) -> Dict:
    """Aggressively trim analysis data for the HTML report generator.

    The HTML generator needs numbers, scores, and pre-written narrative sections.
    It does NOT need full agent reasoning, raw research text, or deliberation transcripts.
    Target: <20K chars JSON to keep the prompt under 25K total.
    """
    trimmed = {}

    # Extraction — full (small, structured)
    trimmed['extraction'] = analysis.get('extraction', {})

    # Prediction — scores and verdict only
    pred = analysis.get('prediction', {})
    trimmed['prediction'] = {
        'verdict': pred.get('verdict', ''),
        'composite_score': pred.get('composite_score', 0),
        'confidence': pred.get('confidence', 0),
        'dimensions': pred.get('dimensions', []),
        'contested_dimensions': [
            {'dimension': c.get('dimension', ''), 'spread': c.get('spread', 0),
             'scores': {f"Elder {j+1}": v for j, (k, v) in enumerate(c.get('scores', {}).items())}}
            for c in pred.get('contested_dimensions', [])[:5]
        ],
        'council_models': [f"Elder {i+1}" for i in range(len(pred.get('council_models', [])))],
        'council_scores': {
            f"Elder {i+1}": scores.get('overall', 0)
            for i, (label, scores) in enumerate(pred.get('model_scores', {}).items())
        },
    }

    # Research — competitors list + market stats only (narrative is in report_sections)
    research = analysis.get('research', {})
    trimmed['research'] = {
        'competitors': research.get('competitors', [])[:8],
        'competitor_details': [
            {k: v for k, v in c.items() if k != 'description'}
            for c in research.get('competitor_details', [])[:6]
        ],
        'market_data': research.get('market_data', {}),
        'trends': research.get('trends', [])[:5],
        'pricing_analysis': research.get('pricing_analysis', {}),
        'patent_landscape': {
            k: v for k, v in research.get('patent_landscape', {}).items()
            if k in ('total_families', 'active', 'pending', 'expiring', 'freedom_to_operate', 'key_patents')
        },
        'company_profile': {
            k: v for k, v in research.get('company_profile', {}).items()
            if k in ('team', 'board', 'board_members', 'deal_history', 'financials',
                      'founded', 'employees', 'hq', 'total_raised', 'last_valuation',
                      'revenue', 'revenue_growth', 'ebitda')
        },
        'sources': research.get('sources', [])[:30],
    }

    # Swarm — stats + trimmed agents (persona + scores only, NO full reasoning)
    swarm = analysis.get('swarm', {})
    trimmed['swarm'] = {
        'total_agents': swarm.get('total_agents', 0),
        'positive_pct': swarm.get('positive_pct', 0),
        'negative_pct': swarm.get('negative_pct', 0),
        'avg_confidence': swarm.get('avg_confidence', 0),
        'verdict': swarm.get('verdict', ''),
        'key_themes_positive': swarm.get('key_themes_positive', [])[:5],
        'key_themes_negative': swarm.get('key_themes_negative', [])[:5],
        'sample_agents': [
            {'persona': a.get('persona', ''), 'overall': a.get('overall', 0),
             'scores': a.get('scores', {}), 'zone': a.get('zone', ''),
             'reasoning': a.get('reasoning', '') or ''}
            for a in swarm.get('sample_agents', [])[:50]
        ],
        'divergence': {
            'zone_agreement': swarm.get('divergence', {}).get('zone_agreement', {}),
            'most_divided_dimension': swarm.get('divergence', {}).get('most_divided_dimension', ''),
            'critical_outliers': [
                {'persona': o.get('persona', ''), 'zone': o.get('zone', ''),
                 'overall': o.get('overall', 0), 'z_score': o.get('z_score', 0),
                 'reasoning_excerpt': o.get('reasoning_excerpt', '') or ''}
                for o in swarm.get('divergence', {}).get('critical_outliers', [])[:5]
            ],
        },
        'deliberation': {
            'recommendation': swarm.get('deliberation', {}).get('synthesis', {}).get('recommendation', ''),
            'consensus_points': swarm.get('deliberation', {}).get('synthesis', {}).get('consensus_points', [])[:3],
            'critical_risk': swarm.get('deliberation', {}).get('synthesis', {}).get('critical_risk', ''),
            'verdict_shifted': swarm.get('deliberation', {}).get('synthesis', {}).get('verdict_shifted', False),
        },
    }

    # Plan — keep structured data (defensive: items may be strings or dicts)
    plan = analysis.get('plan', {})
    if not isinstance(plan, dict):
        plan = {}
    def _safe_risk(r):
        if isinstance(r, str): return {'risk': r[:200], 'severity': ''}
        if isinstance(r, dict): return {'risk': r.get('risk', '')[:200], 'severity': r.get('severity', '')}
        return {'risk': str(r)[:200], 'severity': ''}
    def _safe_move(m):
        if isinstance(m, str): return {'action': m[:150], 'priority': '', 'effort': '', 'impact': ''}
        if isinstance(m, dict): return {'action': m.get('action', '')[:150], 'priority': m.get('priority', ''), 'effort': m.get('effort', ''), 'impact': m.get('impact', '')}
        return {'action': str(m)[:150], 'priority': '', 'effort': '', 'impact': ''}
    def _safe_exp(e):
        if isinstance(e, str): return {'experiment': e, 'cost': '', 'timeline': ''}
        if isinstance(e, dict): return {'experiment': e.get('experiment', ''), 'cost': e.get('cost', ''), 'timeline': e.get('timeline', '')}
        return {'experiment': str(e), 'cost': '', 'timeline': ''}
    _risks = plan.get('risks', [])
    _moves = plan.get('next_moves', plan.get('moves', []))
    _exps = plan.get('validation_experiments', [])
    if not isinstance(_risks, list): _risks = [_risks] if _risks else []
    if not isinstance(_moves, list): _moves = [_moves] if _moves else []
    if not isinstance(_exps, list): _exps = [_exps] if _exps else []
    trimmed['plan'] = {
        'risks': [_safe_risk(r) for r in _risks[:5]],
        'next_moves': [_safe_move(m) for m in _moves[:5]],
        'validation_experiments': [_safe_exp(e) for e in _exps[:3]],
    }

    # Report sections — the pre-written narratives ARE the content for the PDF
    # Keep them but cap each at 1500 chars (they're already summarized)
    trimmed['report_sections'] = {}
    for key, val in analysis.get('report_sections', {}).items():
        trimmed['report_sections'][key] = (val or '')[:1500]

    # Meta
    trimmed['data_quality'] = analysis.get('data_quality', 0)
    # Cache staleness indicator (from ResearchCache)
    _cache_age = analysis.get('research', {}).get('_cache_age_days')
    if _cache_age is not None:
        trimmed['cache_age_days'] = _cache_age
    # Peer review data (from Karpathy Stage 2) — anonymize evaluator labels
    peer_review = analysis.get('prediction', {}).get('peer_review', {})
    if peer_review:
        # Build label→Elder mapping from council_models
        _real_labels = pred.get('council_models', [])
        _elder_map = {label: f"Elder {i+1}" for i, label in enumerate(_real_labels)}
        trimmed['peer_review'] = {
            'flags': [
                {k: (_elder_map.get(v, v) if k in ('flagged_by', 'target') else v)
                 for k, v in f.items()}
                for f in peer_review.get('flags', [])[:5]
            ],
            'aggregate_rankings': {
                _elder_map.get(k, k): v
                for k, v in peer_review.get('aggregate_rankings', {}).items()
            },
        }
    oasis = analysis.get('oasis', {})
    if not isinstance(oasis, dict):
        oasis = {}
    trimmed['oasis'] = {
        k: v for k, v in oasis.items()
        if k in ('trajectory', 'final_sentiment', 'rounds', 'agent_count')
    }

    # Enhancements (Top 5 Fixes, Investor Match, Score Forecast, etc.)
    enhancements = analysis.get('enhancements', {})
    if isinstance(enhancements, dict) and enhancements:
        trimmed['enhancements'] = {
            'top_fixes': enhancements.get('top_fixes', [])[:5],
            'investor_matches': enhancements.get('investor_matches', [])[:5],
            'score_forecast': enhancements.get('score_forecast', [])[:5],
            'rewritten_exec_summary': (enhancements.get('rewritten_exec_summary', '') or '')[:2000],
            'similar_funded': enhancements.get('similar_funded', [])[:5],
        }

    return trimmed


def _render_pdf_playwright(html: str) -> bytes:
    """Render HTML to PDF using persistent Chromium browser pool. Full CSS support."""
    browser = _get_browser()
    page = browser.new_page()
    try:
        page.set_content(html, wait_until='networkidle')
        pdf_bytes = page.pdf(
            format='A4',
            print_background=True,
            margin={'top': '0', 'right': '0', 'bottom': '0', 'left': '0'},
        )
        return pdf_bytes
    finally:
        page.close()  # Close the tab, keep the browser alive


def _render_pdf_weasyprint(html: str) -> bytes:
    """Render HTML to PDF using WeasyPrint. Fallback — limited CSS support."""
    from weasyprint import HTML
    return HTML(string=html).write_pdf()


def generate_pdf_report(analysis: Dict[str, Any], narrative: str = '', output_path: Optional[str] = None) -> bytes:
    """Generate PDF using LLM-generated HTML. Renders with Playwright (Chromium), falls back to WeasyPrint."""
    # Check cache first
    analysis_id = _get_analysis_id(analysis)
    if analysis_id and analysis_id in _pdf_cache:
        logger.info(f"[LLM Report] Serving cached PDF for {analysis_id}")
        pdf_bytes = _pdf_cache[analysis_id]
        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)
        return pdf_bytes

    try:
        html = generate_llm_report(analysis)
    except Exception as e:
        # LR-3 FIX: this is a significant quality degradation — the LLM-written
        # narrative is lost and the user gets a template-only report with no indication.
        logger.error(
            f"[LLM Report] LLM report generation FAILED — falling back to legacy template generator. "
            f"Report will lack LLM-written narrative sections and dynamic layouts. Error: {e}"
        )
        from .report_generator import generate_html_report
        html = generate_html_report(analysis, narrative)

    # Render: Playwright (Chromium) → WeasyPrint fallback
    pdf_bytes = None
    try:
        logger.info("[LLM Report] Rendering PDF with Playwright (Chromium)...")
        pdf_bytes = _render_pdf_playwright(html)
        logger.info(f"[LLM Report] Playwright PDF: {len(pdf_bytes)} bytes")
    except Exception as pw_err:
        logger.warning(f"[LLM Report] Playwright failed, falling back to WeasyPrint: {pw_err}")
        try:
            pdf_bytes = _render_pdf_weasyprint(html)
            logger.info(f"[LLM Report] WeasyPrint fallback PDF: {len(pdf_bytes)} bytes")
        except Exception as wp_err:
            logger.error(f"[LLM Report] Both renderers failed: Playwright={pw_err}, WeasyPrint={wp_err}")
            raise wp_err

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)
    # Cache the result
    if analysis_id:
        _pdf_cache[analysis_id] = pdf_bytes
    logger.info(f"[LLM Report] PDF generated: {len(pdf_bytes)} bytes")
    return pdf_bytes


def pre_generate_pdf(analysis: Dict[str, Any]) -> Optional[bytes]:
    """Pre-generate PDF in background during analysis pipeline.
    Returns PDF bytes on success, None on failure (non-fatal)."""
    try:
        logger.info("[LLM Report] Pre-generating PDF...")
        pdf_bytes = generate_pdf_report(analysis)
        analysis_id = _get_analysis_id(analysis)
        if analysis_id:
            _pdf_cache[analysis_id] = pdf_bytes
        logger.info(f"[LLM Report] Pre-generated PDF cached: {len(pdf_bytes)} bytes")
        return pdf_bytes
    except Exception as e:
        logger.warning(f"[LLM Report] Pre-generation failed (non-fatal): {e}")
        return None


def get_cached_pdf(analysis_id: str) -> Optional[bytes]:
    """Retrieve a pre-generated PDF from cache."""
    return _pdf_cache.get(analysis_id)


def _get_analysis_id(analysis: Dict) -> str:
    """Extract a stable ID from analysis data for caching."""
    extraction = analysis.get('extraction', {})
    company = extraction.get('company', '')
    if isinstance(extraction, dict):
        company = extraction.get('company', '')
    elif hasattr(extraction, 'company'):
        company = extraction.company
    if company:
        return f"{company.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}"
    return ""
