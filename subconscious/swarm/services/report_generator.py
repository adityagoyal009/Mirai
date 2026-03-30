"""
Report Generator — PitchBook-quality PDF reports with SVG charts, professional tables,
and LLM-generated narrative sections.

Sections:
  1. Highlights (score gauge, council verdict, swarm donut) + General Info
  2. Market Analysis (key figures) + Competitors table
  3. Competitive Position + Council Deliberation
  4-5. Swarm Analysis (zone bars, agent table with full reasoning)
  6. OASIS Market Simulation
  7. Risk Assessment + Strategic Recommendations
  8. Actionable Improvements + Investment Verdict
  Appendix: Full Market Analysis + Competitive Landscape narratives
"""

import math
import os
import re
from datetime import datetime
from typing import Dict, Any, List, Optional

from ..utils.logger import get_logger

logger = get_logger('mirofish.report')


def _strip_markdown(text: str) -> str:
    """Strip markdown formatting from LLM output for HTML rendering."""
    # Convert **bold** to <strong>
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Convert *italic* to <em>
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    # Remove any remaining markdown headers
    text = re.sub(r'^#{1,4}\s+', '', text, flags=re.MULTILINE)
    return text


def _replace_em_dashes(text: str) -> str:
    """Replace em dashes with regular dashes for cleaner PDF output."""
    return text.replace('\u2014', '-').replace('\u2013', '-').replace('—', '-')


def _to_paragraphs(text: str) -> str:
    """Convert plain text to HTML paragraphs, splitting on double newlines or long single blocks."""
    if not text:
        return ''
    # Split on double newlines
    parts = re.split(r'\n\s*\n', text.strip())
    if len(parts) <= 1 and len(text) > 600:
        # Try splitting on single newlines
        parts = text.strip().split('\n')
    if len(parts) <= 1 and len(text) > 800:
        # Split long single block into ~300 char paragraphs at sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        parts = []
        current = ''
        for s in sentences:
            if len(current) + len(s) > 400 and current:
                parts.append(current.strip())
                current = s
            else:
                current = current + ' ' + s if current else s
        if current:
            parts.append(current.strip())
    return '\n'.join(f'<p style="margin-bottom: 10px;">{p.strip()}</p>' for p in parts if p.strip())


def _extract_key_figures(text: str) -> List[Dict[str, str]]:
    """Extract key numerical figures from market/competitive analysis text for summary cards."""
    figures = []
    # TAM / market size
    tam_match = re.search(r'(?:TAM|market|addressable).*?[\$]?([\d,.]+)\s*(billion|million|B|M|trillion|T)', text, re.IGNORECASE)
    if tam_match:
        market_size = f'${tam_match.group(1)}{tam_match.group(2)[0].upper()}'
        market_size = str(market_size).strip()
        # Fix common LLM formatting issues
        if market_size in ('$.T', '$T', '$', '.T', 'T', ''):
            market_size = 'Not available'
        # Remove trailing periods, dots before letters
        market_size = re.sub(r'\.\s*([A-Z])', r' \1', market_size)
        figures.append({'label': 'Market Size', 'value': market_size})
    # Growth rate / CAGR
    growth_match = re.search(r'(\d+(?:\.\d+)?)\s*%\s*(?:CAGR|growth|annually|year.over.year)', text, re.IGNORECASE)
    if growth_match:
        figures.append({'label': 'Growth Rate', 'value': f'{growth_match.group(1)}% CAGR'})
    # Customer segments / count
    seg_match = re.search(r'([\d,]+)\s+(?:conservation districts|utilities|companies|customers|organizations)', text, re.IGNORECASE)
    if seg_match:
        figures.append({'label': 'Target Segment', 'value': f'{seg_match.group(1)} orgs'})
    # Competitors count
    comp_match = re.findall(r'(?:Xylem|Hach|Ketos|BlueGreen|Wexus|Danaher|Aquatic Informatics|Upstream Tech|120Water|LG Sonic)', text, re.IGNORECASE)
    if comp_match:
        figures.append({'label': 'Key Competitors', 'value': f'{len(set(comp_match))} identified'})
    # Price point
    price_match = re.search(r'\$([\d,]+)[\s\-–]+\$([\d,]+)(?:K)?(?:\s*per|\s*annual)', text, re.IGNORECASE)
    if price_match:
        figures.append({'label': 'Price Range', 'value': f'${price_match.group(1)}-${price_match.group(2)}K'})
    return figures[:5]


# ── Secret Sanitization (hide LLM names and methodology details) ──

_SECRET_TERMS = ['Claude', 'Opus', 'Sonnet', 'GPT-5', 'GPT-4', 'GPT-3', 'Gemini',
                 'Anthropic', 'OpenAI', 'Google DeepMind', 'Mistral']

def _sanitize_reasoning(text: str) -> str:
    """Remove LLM model names and provider names from reasoning text."""
    for secret in _SECRET_TERMS:
        text = re.sub(re.escape(secret), 'AI Model', text, flags=re.IGNORECASE)
    return text


def _truncate(text: str, max_len: int) -> str:
    """Truncate text at word boundary, never mid-word."""
    if not text or len(text) <= max_len:
        return text
    truncated = text[:max_len]
    last_space = truncated.rfind(' ')
    if last_space > max_len * 0.6:
        truncated = truncated[:last_space]
    return truncated.rstrip('.,;:- ') + '...'


def _sanitize_persona_name(name: str) -> str:
    """Clean persona name for display:
    - Remove MBTI: 'Series-B VC (INTJ, Berlin)' → 'Series-B VC (Berlin)'
    - Truncate dataset descriptions: 'A textile engineer who helps develop innovative...' → 'Textile Engineer'
    """
    # Remove MBTI
    name = re.sub(r'\([A-Z]{4},\s*', '(', name)
    # If name starts with "A " or "An " (dataset persona), extract the role
    if re.match(r'^An?\s+', name) and len(name) > 60:
        # Try to get first meaningful noun phrase
        short = re.sub(r'^An?\s+', '', name)
        # Cut at first "who", "with", "that", "specializing", "focused"
        short = re.split(r'\s+(?:who|with|that|specializing|focused|familiar|interested|looking)', short)[0]
        name = short.strip().title()[:60]
    return name


# ── SVG Chart Generators (inline, no dependencies) ──────────────

def _color_for_score(score: float) -> str:
    if score >= 7: return '#2e7d32'
    if score >= 5: return '#f57c00'
    return '#d32f2f'


def svg_score_gauge(score: float, max_score: float = 10) -> str:
    """Semicircle gauge showing overall score."""
    pct = min(score / max_score, 1.0)
    angle = pct * 180
    rad = math.radians(180 - angle)
    r = 60
    cx, cy = 80, 75
    ex = cx + r * math.cos(rad)
    ey = cy - r * math.sin(rad)
    large = 1 if angle > 180 else 0
    color = _color_for_score(score)

    return f'''<svg width="160" height="100" viewBox="0 0 160 100">
  <path d="M {cx-r} {cy} A {r} {r} 0 0 1 {cx+r} {cy}" fill="none" stroke="#e0e0e0" stroke-width="12" stroke-linecap="round"/>
  <path d="M {cx-r} {cy} A {r} {r} 0 {large} 1 {ex:.1f} {ey:.1f}" fill="none" stroke="{color}" stroke-width="12" stroke-linecap="round"/>
  <text x="{cx}" y="{cy-10}" text-anchor="middle" font-size="28" font-weight="bold" fill="{color}">{score:.1f}</text>
  <text x="{cx}" y="{cy+8}" text-anchor="middle" font-size="11" fill="#888">/ {max_score:.0f}</text>
</svg>'''


def svg_horizontal_bars(items: List[Dict], width: int = 500) -> str:
    """Horizontal bar chart for dimension scores."""
    bar_h = 22
    gap = 8
    label_w = 180
    bar_w = width - label_w - 50
    h = len(items) * (bar_h + gap) + 10

    lines = [f'<svg width="{width}" height="{h}" viewBox="0 0 {width} {h}">']
    for i, item in enumerate(items):
        y = i * (bar_h + gap) + 5
        name = item.get('name', '').replace('_', ' ').title()
        score = item.get('score', 0)
        contested = item.get('contested', False)
        color = _color_for_score(score)
        fill_w = (score / 10) * bar_w

        lines.append(f'  <text x="0" y="{y+15}" font-size="12" fill="#333">{name}</text>')
        if contested:
            lines.append(f'  <text x="{label_w-20}" y="{y+15}" font-size="10" fill="#f57c00">⚠</text>')
        lines.append(f'  <rect x="{label_w}" y="{y}" width="{bar_w}" height="{bar_h}" rx="3" fill="#f0f0f0"/>')
        lines.append(f'  <rect x="{label_w}" y="{y}" width="{fill_w:.0f}" height="{bar_h}" rx="3" fill="{color}"/>')
        lines.append(f'  <text x="{label_w + bar_w + 8}" y="{y+16}" font-size="13" font-weight="bold" fill="{color}">{score:.1f}</text>')

    lines.append('</svg>')
    return '\n'.join(lines)


def svg_donut_chart(positive_pct: float, negative_pct: float, size: int = 140) -> str:
    """Donut chart for HIT vs MISS vote distribution."""
    r = size // 2 - 10
    cx = cy = size // 2
    circumference = 2 * math.pi * r
    pos_len = (positive_pct / 100) * circumference
    neg_len = circumference - pos_len

    return f'''<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#e8e8e8" stroke-width="16"/>
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#d32f2f" stroke-width="16"
    stroke-dasharray="{neg_len:.1f} {pos_len:.1f}" stroke-dashoffset="{circumference*0.25:.1f}" transform="rotate(-90 {cx} {cy})"/>
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#2e7d32" stroke-width="16"
    stroke-dasharray="{pos_len:.1f} {neg_len:.1f}" stroke-dashoffset="{circumference*0.25:.1f}" transform="rotate(-90 {cx} {cy})"/>
  <text x="{cx}" y="{cy-6}" text-anchor="middle" font-size="20" font-weight="bold" fill="#333">{positive_pct:.0f}%</text>
  <text x="{cx}" y="{cy+12}" text-anchor="middle" font-size="10" fill="#888">HIT</text>
</svg>'''


def svg_zone_bars(zones: List[Dict], width: int = 450) -> str:
    """Stacked horizontal bars showing per-zone vote breakdown."""
    bar_h = 20
    gap = 6
    label_w = 120
    bar_w = width - label_w - 60
    h = len(zones) * (bar_h + gap) + 10

    lines = [f'<svg width="{width}" height="{h}" viewBox="0 0 {width} {h}">']
    for i, z in enumerate(zones):
        y = i * (bar_h + gap) + 5
        name = z.get('name', '')
        pos = z.get('positive_pct', 0)
        neg = 100 - pos
        pos_w = (pos / 100) * bar_w
        neg_w = bar_w - pos_w

        lines.append(f'  <text x="0" y="{y+15}" font-size="11" fill="#333">{name}</text>')
        lines.append(f'  <rect x="{label_w}" y="{y}" width="{pos_w:.0f}" height="{bar_h}" fill="#2e7d32"/>')
        lines.append(f'  <rect x="{label_w+pos_w:.0f}" y="{y}" width="{neg_w:.0f}" height="{bar_h}" fill="#d32f2f"/>')
        lines.append(f'  <text x="{label_w+bar_w+8}" y="{y+15}" font-size="11" fill="#666">{pos:.0f}%</text>')

    lines.append('</svg>')
    return '\n'.join(lines)


# ── New SVG Charts (v0.7.0) ──────────────────────────────────

def svg_zone_sentiment_donut(zone_agreement: Dict, total_hit_pct: float, size: int = 160) -> str:
    """Multi-segment donut showing per-zone HIT percentages."""
    zone_colors = {
        'investor': '#1565c0', 'customer': '#2e7d32', 'operator': '#f57c00',
        'analyst': '#7b1fa2', 'contrarian': '#d32f2f', 'wildcard': '#00838f',
    }
    cx = cy = size // 2
    r = size // 2 - 15
    circumference = 2 * math.pi * r

    zones = [(k, v) for k, v in zone_agreement.items() if isinstance(v, dict) and v.get('total', 0) > 0]
    total_agents = sum(z['total'] for _, z in zones) or 1

    lines = [f'<svg width="{size + 120}" height="{size}" viewBox="0 0 {size + 120} {size}">']
    offset = 0
    legend_y = 15
    for zone_name, data in zones:
        pct = data['total'] / total_agents
        seg_len = pct * circumference
        hit_pct = data.get('hits', 0) / max(data.get('total', 1), 1) * 100
        color = zone_colors.get(zone_name, '#888')
        opacity = max(0.3, hit_pct / 100)
        lines.append(
            f'  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" '
            f'stroke-width="14" stroke-opacity="{opacity:.2f}" '
            f'stroke-dasharray="{seg_len:.1f} {circumference - seg_len:.1f}" '
            f'stroke-dashoffset="{-offset + circumference * 0.25:.1f}" '
            f'transform="rotate(-90 {cx} {cy})"/>'
        )
        offset += seg_len
        # Legend
        lx = size + 5
        lines.append(f'  <rect x="{lx}" y="{legend_y - 8}" width="10" height="10" rx="2" fill="{color}" fill-opacity="{opacity:.2f}"/>')
        lines.append(f'  <text x="{lx + 14}" y="{legend_y}" font-size="9" fill="#333">{zone_name.title()} {hit_pct:.0f}%</text>')
        legend_y += 16

    lines.append(f'  <text x="{cx}" y="{cy - 6}" text-anchor="middle" font-size="20" font-weight="bold" fill="#333">{total_hit_pct:.0f}%</text>')
    lines.append(f'  <text x="{cx}" y="{cy + 12}" text-anchor="middle" font-size="10" fill="#888">HIT</text>')
    lines.append('</svg>')
    return '\n'.join(lines)


def svg_zone_dimension_bars(agents: List[Dict], width: int = 640) -> str:
    """Grouped bar chart: per-dimension average scores by zone. Much more readable than heatmap."""
    if not agents:
        return ''

    dimensions = ['market', 'team', 'product', 'timing', 'overall']
    dim_labels = {'market': 'Market', 'team': 'Team', 'product': 'Product', 'timing': 'Timing', 'overall': 'Overall'}
    zone_colors = {
        'investor': '#2ecc71', 'customer': '#3498db', 'operator': '#9b59b6',
        'analyst': '#f39c12', 'contrarian': '#e74c3c', 'wildcard': '#1abc9c',
    }

    # Group agents by zone, compute average per dimension
    zone_scores = {}  # zone -> {dim: [scores]}
    for a in agents:
        zone = (a.get('zone') or a.get('Zone') or 'wildcard').lower()
        if zone not in zone_scores:
            zone_scores[zone] = {d: [] for d in dimensions}
        scores = a.get('scores', {})
        for d in dimensions:
            val = scores.get(d, a.get(d, a.get('overall', 5)))
            try:
                zone_scores[zone][d].append(float(val))
            except (ValueError, TypeError):
                pass

    # Compute averages
    zone_avgs = {}
    for zone, dims in zone_scores.items():
        zone_avgs[zone] = {}
        for d, scores in dims.items():
            zone_avgs[zone][d] = sum(scores) / len(scores) if scores else 0

    zones_present = [z for z in ['investor', 'analyst', 'contrarian', 'customer', 'operator', 'wildcard'] if z in zone_avgs]
    if not zones_present:
        return ''

    row_height = 50
    bar_height = max(6, 28 // len(zones_present))
    left_margin = 120
    right_margin = 40
    bar_area = width - left_margin - right_margin
    height = len(dimensions) * row_height + 60  # +60 for legend

    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" style="font-family:sans-serif;">\n'

    # Draw bars per dimension
    for di, dim in enumerate(dimensions):
        y_base = di * row_height + 10
        # Dimension label
        svg += f'<text x="{left_margin - 8}" y="{y_base + row_height // 2 + 4}" text-anchor="end" font-size="12" fill="#333">{dim_labels.get(dim, dim)}</text>\n'
        # Background
        svg += f'<rect x="{left_margin}" y="{y_base + 2}" width="{bar_area}" height="{row_height - 4}" fill="#f8f8f8" rx="2"/>\n'

        for zi, zone in enumerate(zones_present):
            avg = zone_avgs[zone].get(dim, 0)
            bar_w = max(1, (avg / 10.0) * bar_area)
            bar_y = y_base + 4 + zi * (bar_height + 1)
            color = zone_colors.get(zone, '#999')
            svg += f'<rect x="{left_margin}" y="{bar_y}" width="{bar_w}" height="{bar_height}" fill="{color}" rx="1" opacity="0.85"/>\n'
            # Score label
            if avg > 0:
                svg += f'<text x="{left_margin + bar_w + 3}" y="{bar_y + bar_height - 1}" font-size="9" fill="#666">{avg:.1f}</text>\n'

    # Legend
    legend_y = len(dimensions) * row_height + 20
    legend_x = left_margin
    for zi, zone in enumerate(zones_present):
        color = zone_colors.get(zone, '#999')
        svg += f'<rect x="{legend_x}" y="{legend_y}" width="8" height="8" fill="{color}" rx="1"/>\n'
        svg += f'<text x="{legend_x + 12}" y="{legend_y + 8}" font-size="10" fill="#666">{zone.title()}</text>\n'
        legend_x += 80

    svg += '</svg>'
    return svg


def _legacy_svg_agent_heatmap(agents: List[Dict], width: int = 520) -> str:
    """Agent-by-dimension heatmap. Rows=agents sorted by score, cols=dimensions."""
    dims = ['market', 'team', 'product', 'timing', 'overall']
    sorted_agents = sorted(agents, key=lambda a: float(a.get('overall', 0)), reverse=True)
    display = sorted_agents[:25]

    cell_w = 48
    cell_h = 18
    label_w = 170
    header_h = 25
    h = header_h + len(display) * cell_h + 10
    w = label_w + len(dims) * cell_w + 10

    lines = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">']
    for j, dim in enumerate(dims):
        x = label_w + j * cell_w + cell_w // 2
        lines.append(f'  <text x="{x}" y="15" text-anchor="middle" font-size="9" font-weight="bold" fill="#333">{dim.title()}</text>')

    for i, agent in enumerate(display):
        y = header_h + i * cell_h
        # Format as "[Zone] Role" instead of truncated backstory
        _zone = agent.get('zone', '?').title()[:4]
        _persona = str(agent.get('persona', '?'))
        _role = _persona.split('(')[0].strip()[:20]
        name = f"[{_zone}] {_role}"
        lines.append(f'  <text x="0" y="{y + 13}" font-size="8" fill="#555">{name}</text>')
        scores = agent.get('scores', {})
        for j, dim in enumerate(dims):
            score = float(scores.get(dim, agent.get(dim, 5)))
            color = _color_for_score(score)
            x = label_w + j * cell_w
            lines.append(f'  <rect x="{x}" y="{y}" width="{cell_w - 2}" height="{cell_h - 2}" rx="2" fill="{color}" opacity="0.75"/>')
            lines.append(f'  <text x="{x + cell_w // 2 - 1}" y="{y + 12}" text-anchor="middle" font-size="8" fill="white" font-weight="bold">{score:.1f}</text>')

    lines.append('</svg>')
    return '\n'.join(lines)


def svg_divergence_radar(agents: List[Dict], size: int = 280) -> str:
    """Radar chart showing min/avg/max score bands across dimensions."""
    dims = ['market', 'team', 'product', 'timing', 'overall']
    cx = cy = size // 2
    r_max = size // 2 - 40
    n = len(dims)

    dim_ranges = {}
    for dim in dims:
        vals = [float(a.get('scores', {}).get(dim, a.get(dim, 5))) for a in agents]
        if vals:
            dim_ranges[dim] = (min(vals), max(vals), sum(vals) / len(vals))
        else:
            dim_ranges[dim] = (5, 5, 5)

    def polar(idx, value):
        angle = math.radians(90 - idx * (360 / n))
        r = (value / 10) * r_max
        return (cx + r * math.cos(angle), cy - r * math.sin(angle))

    lines = [f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">']
    # Grid
    for level in [2, 4, 6, 8, 10]:
        pts = " ".join(f"{polar(i, level)[0]:.1f},{polar(i, level)[1]:.1f}" for i in range(n))
        lines.append(f'  <polygon points="{pts}" fill="none" stroke="#e0e0e0" stroke-width="0.5"/>')
    for i in range(n):
        ex, ey = polar(i, 10)
        lines.append(f'  <line x1="{cx}" y1="{cy}" x2="{ex:.1f}" y2="{ey:.1f}" stroke="#e0e0e0" stroke-width="0.5"/>')

    # Max polygon (red band)
    max_pts = " ".join(f"{polar(i, dim_ranges[d][1])[0]:.1f},{polar(i, dim_ranges[d][1])[1]:.1f}" for i, d in enumerate(dims))
    lines.append(f'  <polygon points="{max_pts}" fill="#d32f2f" fill-opacity="0.12" stroke="#d32f2f" stroke-width="1"/>')
    # Min polygon (white cutout)
    min_pts = " ".join(f"{polar(i, dim_ranges[d][0])[0]:.1f},{polar(i, dim_ranges[d][0])[1]:.1f}" for i, d in enumerate(dims))
    lines.append(f'  <polygon points="{min_pts}" fill="white" fill-opacity="0.8" stroke="#d32f2f" stroke-width="1" stroke-dasharray="3,3"/>')
    # Avg polygon (blue line)
    avg_pts = " ".join(f"{polar(i, dim_ranges[d][2])[0]:.1f},{polar(i, dim_ranges[d][2])[1]:.1f}" for i, d in enumerate(dims))
    lines.append(f'  <polygon points="{avg_pts}" fill="none" stroke="#1565c0" stroke-width="2"/>')

    # Labels
    for i, dim in enumerate(dims):
        lx, ly = polar(i, 11.5)
        rng = dim_ranges[dim][1] - dim_ranges[dim][0]
        label_color = '#d32f2f' if rng > 3 else '#f57c00' if rng > 2 else '#333'
        lines.append(f'  <text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" font-size="9" fill="{label_color}" font-weight="bold">{dim.title()}</text>')
        lines.append(f'  <text x="{lx:.1f}" y="{ly + 11:.1f}" text-anchor="middle" font-size="8" fill="#888">{dim_ranges[dim][0]:.1f}-{dim_ranges[dim][1]:.1f}</text>')

    lines.append('</svg>')
    return '\n'.join(lines)


def html_competitive_comparison(competitors: List, startup_name: str) -> str:
    """Feature comparison table with checkmarks -- instantly readable by anyone."""
    if not competitors:
        return ''

    # Extract competitor names
    comp_names = []
    for c in competitors[:6]:
        if isinstance(c, str):
            comp_names.append(c)
        elif isinstance(c, dict):
            comp_names.append(c.get('name', c.get('company', str(c))))
        else:
            comp_names.append(str(c))

    if not comp_names:
        return ''

    # Feature columns -- generic features that apply to most startups
    features = ['AI/ML', 'SaaS', 'Hardware', 'Mobile App', 'Enterprise', 'API']

    html = '<table style="width:100%;border-collapse:collapse;font-size:9pt;margin:8px 0;">\n'
    # Header
    html += '<tr style="background:#1a365d;color:#fff;">\n'
    html += '<th style="padding:6px 8px;text-align:left;">Company</th>\n'
    html += '<th style="padding:6px 8px;text-align:left;">Details</th>\n'
    html += '</tr>\n'

    # Startup row (highlighted)
    html += f'<tr style="background:#e8f5e9;font-weight:bold;">\n'
    html += f'<td style="padding:5px 8px;color:#2e7d32;">{startup_name}</td>\n'
    html += f'<td style="padding:5px 8px;color:#2e7d32;font-style:italic;">Subject of analysis</td>\n'
    html += '</tr>\n'

    # Competitor rows
    for i, name in enumerate(comp_names):
        bg = '#f8f9fa' if i % 2 == 0 else '#fff'
        detail = ''
        if i < len(competitors) and isinstance(competitors[i], dict):
            # Prefer 'detail' field (from agentic research), fall back to status/funding
            detail = (competitors[i].get('detail', '')
                      or competitors[i].get('status', '')
                      or competitors[i].get('funding', ''))
        # Truncate long details for table readability
        if len(detail) > 120:
            detail = detail[:117] + '...'
        html += f'<tr style="background:{bg};">\n'
        html += f'<td style="padding:5px 8px;font-weight:600;white-space:nowrap;">{name}</td>\n'
        html += f'<td style="padding:5px 8px;color:#444;">{detail or "—"}</td>\n'
        html += '</tr>\n'

    html += '</table>\n'
    return html


def _legacy_svg_competitive_scatter(competitors: List, startup_name: str, width: int = 450, height: int = 280) -> str:
    """Competitive positioning scatter plot. Price vs capability scope."""
    # Filter out non-competitors (research firms, accelerators, media)
    NON_COMPETITORS = {'marketsandmarkets', 'imagine h2o', 'grand view research', 'frost & sullivan',
                       'techcrunch', 'crunchbase', 'pitchbook', 'gartner', 'forrester', 'cb insights',
                       'mckinsey', 'deloitte', 'accenture', 'kpmg', 'pwc', 'ey'}
    competitors = [c for c in competitors
                   if (c.lower().strip() if isinstance(c, str) else str(c).lower().strip()) not in NON_COMPETITORS]
    KNOWN = {
        'xylem': (0.8, 0.5), 'hach': (0.75, 0.5), 'ketos': (0.5, 0.6),
        'bluegreen': (0.4, 0.45), 'wexus': (0.35, 0.4), 'danaher': (0.85, 0.55),
        'aquatic informatics': (0.6, 0.45), 'upstream tech': (0.45, 0.55),
        '120water': (0.35, 0.5), 'lg sonic': (0.55, 0.4), 'swimsol': (0.5, 0.35),
    }
    margin = 40
    pw = width - 2 * margin
    ph = height - 2 * margin

    lines = [f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">']
    # Axes
    lines.append(f'  <line x1="{margin}" y1="{height - margin}" x2="{width - margin}" y2="{height - margin}" stroke="#ccc" stroke-width="1"/>')
    lines.append(f'  <line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height - margin}" stroke="#ccc" stroke-width="1"/>')
    lines.append(f'  <text x="{width // 2}" y="{height - 8}" text-anchor="middle" font-size="9" fill="#888">Price Point (Low to High)</text>')
    lines.append(f'  <text x="12" y="{height // 2}" text-anchor="middle" font-size="9" fill="#888" transform="rotate(-90, 12, {height // 2})">Capability Scope</text>')
    # Quadrant labels
    lines.append(f'  <text x="{margin + 10}" y="{margin + 15}" font-size="8" fill="#ddd">Low price / High scope</text>')
    lines.append(f'  <text x="{width - margin - 80}" y="{height - margin - 10}" font-size="8" fill="#ddd">High price / Low scope</text>')

    plotted = 0
    for c in competitors[:10]:
        name = c if isinstance(c, str) else c.get('name', str(c)) if isinstance(c, dict) else str(c)
        name_clean = name.split('(')[0].split('/')[0].strip()
        name_lower = name_clean.lower()
        pos = None
        for k, v in KNOWN.items():
            if k in name_lower:
                pos = v
                break
        if not pos:
            h = hash(name_lower) % 1000
            pos = (0.25 + (h % 50) / 100, 0.25 + (h // 10 % 50) / 100)
        x = margin + pos[0] * pw
        y = height - margin - pos[1] * ph
        lines.append(f'  <circle cx="{x:.0f}" cy="{y:.0f}" r="5" fill="#888" fill-opacity="0.5"/>')
        lines.append(f'  <text x="{x:.0f}" y="{y - 8:.0f}" text-anchor="middle" font-size="8" fill="#666">{name_clean[:18]}</text>')
        plotted += 1

    # Startup (highlighted)
    sx = margin + 0.3 * pw
    sy = height - margin - 0.75 * ph
    lines.append(f'  <circle cx="{sx:.0f}" cy="{sy:.0f}" r="7" fill="#2e7d32" stroke="#1b5e20" stroke-width="2"/>')
    lines.append(f'  <text x="{sx:.0f}" y="{sy - 10:.0f}" text-anchor="middle" font-size="9" font-weight="bold" fill="#2e7d32">{startup_name[:22]}</text>')

    lines.append('</svg>')
    return '\n'.join(lines)


def _select_highlight_agents(agents: List[Dict], deliberation: Optional[Dict] = None) -> List[Dict]:
    """Pick 5-6 most interesting agents for highlight section."""
    if not agents:
        return []
    highlights = []
    used = set()

    sorted_by_score = sorted(agents, key=lambda a: float(a.get('overall', 5)))

    # 1. Strongest HIT
    top = sorted_by_score[-1]
    highlights.append({**top, '_highlight': 'Strongest HIT'}); used.add(id(top))
    # 2. Strongest MISS
    bottom = sorted_by_score[0]
    if id(bottom) not in used:
        highlights.append({**bottom, '_highlight': 'Strongest MISS'}); used.add(id(bottom))
    # 3. Sharpest contrarian
    contrarians = [a for a in agents if a.get('zone') == 'contrarian' and id(a) not in used]
    if contrarians:
        c = min(contrarians, key=lambda a: float(a.get('overall', 5)))
        highlights.append({**c, '_highlight': 'Sharpest Contrarian'}); used.add(id(c))
    # 4. Most surprising wild card
    wildcards = [a for a in agents if a.get('zone') == 'wildcard' and id(a) not in used]
    if wildcards:
        mean_o = sum(float(a.get('overall', 5)) for a in agents) / len(agents)
        w = max(wildcards, key=lambda a: abs(float(a.get('overall', 5)) - mean_o))
        highlights.append({**w, '_highlight': 'Most Surprising Wild Card'}); used.add(id(w))
    # 5. Most conflicted (highest dimension variance)
    remaining = [a for a in agents if id(a) not in used]
    if remaining:
        def dvar(a):
            s = a.get('scores', {})
            vals = [float(s.get(d, 5)) for d in ['market', 'team', 'product', 'timing']]
            m = sum(vals) / len(vals)
            return sum((v - m) ** 2 for v in vals) / len(vals)
        conf = max(remaining, key=dvar)
        highlights.append({**conf, '_highlight': 'Most Conflicted'}); used.add(id(conf))
    # 6. Customer perspective (often most actionable)
    customers = [a for a in agents if a.get('zone') == 'customer' and id(a) not in used]
    if customers:
        highlights.append({**customers[0], '_highlight': 'Customer Voice'}); used.add(id(customers[0]))

    return highlights[:6]


# ── Suggestion Generator ──────────────────────────────────────

def _generate_suggestions(prediction: Dict) -> List[Dict]:
    suggestions = []
    dims = prediction.get('dimensions', [])
    for d in dims:
        if not isinstance(d, dict): continue
        name = d.get('name', '').lower()
        score = d.get('score', 10)
        if score >= 7: continue

        suggestions_map = {
            'team': ('Team Execution', 'Add experienced CTO/CFO with industry exits. Build advisory board with domain credibility. Show evidence of shipping speed.'),
            'competition': ('Competitive Position', 'Identify and document 3 specific defensible advantages. Focus on a niche where incumbents are weakest. Build switching costs early.'),
            'regulatory': ('Regulatory Strategy', 'Engage specialized compliance counsel within 30 days. Map all required licenses by jurisdiction. Start in the most permissive market.'),
            'business_model': ('Business Model', 'Test pricing with 10 real customers. Calculate true unit economics including hidden costs. Consider higher-margin enterprise tier.'),
            'social_proof': ('Market Validation', 'Get 3-5 customer testimonials. Publish case studies. Build a waitlist. Apply to accelerators for credibility signal.'),
            'timing': ('Market Timing', 'Identify the specific catalyst that makes NOW the right time. If no catalyst exists, evaluate whether you are too early.'),
            'pattern': ('Pattern Match', 'Study 3 companies that succeeded and 3 that failed in adjacent spaces. Document why you are different.'),
        }

        for key, (area, action) in suggestions_map.items():
            if key in name:
                suggestions.append({'area': area, 'issue': f'{d.get("name", "").replace("_", " ").title()}: {score:.1f}/10', 'action': action})
                break

    return suggestions[:5]


# ── Main Report Generator ──────────────────────────────────────

def generate_html_report(analysis: Dict[str, Any], narrative: str = '') -> str:
    """Generate PitchBook-quality HTML report."""
    prediction = analysis.get('prediction', {})
    plan = analysis.get('plan', {})
    research = analysis.get('research', {})
    swarm = analysis.get('swarm', {})
    extraction = analysis.get('extraction', {})

    company = extraction.get('company', 'Unknown Company')
    industry = extraction.get('industry', '')
    verdict = prediction.get('verdict', 'Unknown')
    # Signal divergence note (advisory, does NOT override verdict)
    _swarm_pos_raw = swarm.get('positive_pct', swarm.get('positivePct', None))
    swarm_pos = float(_swarm_pos_raw) if _swarm_pos_raw is not None else 50.0
    signal_divergence = ""
    if swarm_pos < 30 and verdict in ('Strong Hit', 'Likely Hit'):
        signal_divergence = f"Swarm sentiment ({swarm_pos:.0f}% positive) diverges significantly from the council verdict. Consider the swarm's concerns carefully."
    elif swarm_pos < 45 and verdict in ('Strong Hit', 'Likely Hit'):
        signal_divergence = f"Swarm sentiment ({swarm_pos:.0f}% positive) is mixed despite a positive council verdict."
    score = float(prediction.get('composite_score', prediction.get('overall_score', 0)) or 0)
    confidence = float(prediction.get('confidence', 0) or 0)
    data_quality = float(analysis.get('data_quality', 0) or 0)
    timestamp = datetime.now().strftime('%d %B %Y')
    # Type-safe data extraction — protect against unexpected types
    dims = prediction.get('dimensions', [])
    dims = dims if isinstance(dims, list) else []
    contested = prediction.get('contested_dimensions', [])
    contested = contested if isinstance(contested, list) else []
    council_models = prediction.get('council_models', [])
    council_models = council_models if isinstance(council_models, list) else []
    risks = plan.get('risks', []) or []
    risks = risks if isinstance(risks, list) else []
    moves = plan.get('next_moves', plan.get('moves', [])) or []
    moves = moves if isinstance(moves, list) else []
    competitors = research.get('competitors', [])
    competitors = competitors if isinstance(competitors, list) else []
    # Enrich competitor list from the original research payload only.
    # Report rendering must never block on fresh web lookups.
    competitor_details = research.get('competitor_details', [])
    if competitor_details and isinstance(competitor_details, list):
        details_map = {}
        for cd in competitor_details:
            if isinstance(cd, dict) and cd.get('name'):
                details_map[cd['name'].strip().lower()] = cd
        enriched = []
        for c in competitors:
            name = c if isinstance(c, str) else (c.get('name', '') if isinstance(c, dict) else str(c))
            detail = details_map.get(name.strip().lower(), {})
            merged = dict(c) if isinstance(c, dict) else {'name': name}
            if detail:
                merged.setdefault('detail', detail.get('description') or detail.get('differentiator', ''))
                merged.setdefault(
                    'industry',
                    detail.get('primary_industry') or detail.get('industry') or detail.get('type', ''),
                )
                merged.setdefault(
                    'status',
                    detail.get('financing_status') or detail.get('business_status') or detail.get('status', ''),
                )
                merged.setdefault(
                    'funding',
                    detail.get('total_raised') or detail.get('funding', ''),
                )
                merged.setdefault('hq_location', detail.get('hq_location', ''))
            enriched.append(merged)
        competitors = enriched
    research_summary = str(research.get('summary', '') or '')
    context_facts = research.get('context_facts', []) or []
    context_facts = context_facts if isinstance(context_facts, list) else []
    cited_facts = research.get('cited_facts', []) or []
    cited_facts = cited_facts if isinstance(cited_facts, list) else []
    sample_agents = swarm.get('sample_agents', []) or []
    sample_agents = sample_agents if isinstance(sample_agents, list) else []
    _pos_raw = swarm.get('positive_pct', swarm.get('positivePct', None))
    pos_pct = float(_pos_raw) if _pos_raw is not None else 50.0
    neg_pct = 100 - pos_pct
    total_agents = swarm.get('total_agents', swarm.get('totalAgents', len(sample_agents)))
    suggestions = _generate_suggestions(prediction)

    # Prepare dimension items for chart
    dim_items = []
    for d in dims:
        if isinstance(d, dict):
            try:
                dim_items.append({
                    'name': str(d.get('name', '')),
                    'score': float(d.get('score', 0) or 0),
                    'contested': str(d.get('name', '')) in [str(x) for x in contested],
                })
            except (ValueError, TypeError):
                pass
    dim_items.sort(key=lambda x: x['score'], reverse=True)

    # Get report sections from ReACT agent or parse narrative
    report_sections = analysis.get('report_sections', {})
    market_analysis = _strip_markdown(report_sections.get('Market Analysis', ''))
    competitive_position = _strip_markdown(report_sections.get('Competitive Landscape', ''))
    risk_narrative = _strip_markdown(report_sections.get('Risk Assessment', ''))
    strategy_narrative = _strip_markdown(report_sections.get('Strategic Recommendations', ''))
    verdict_summary = _strip_markdown(report_sections.get('Investment Verdict', ''))
    exec_summary = _strip_markdown(report_sections.get('Executive Summary', ''))

    # Council reasoning
    council_reasoning = prediction.get('reasoning', '')
    if council_reasoning:
        council_reasoning = _strip_markdown(_replace_em_dashes(str(council_reasoning)))

    # Fallback: parse narrative string if report_sections not available
    if not market_analysis and narrative:
        sections = narrative.split('\n\n')
        for s in sections:
            sl = s.lower()
            if 'market analysis' in sl[:50] and not market_analysis:
                market_analysis = _strip_markdown(s.split('\n', 1)[-1] if '\n' in s else s)
            elif 'competitive' in sl[:50] and not competitive_position:
                competitive_position = _strip_markdown(s.split('\n', 1)[-1] if '\n' in s else s)
            elif 'risk' in sl[:30] and not risk_narrative:
                risk_narrative = _strip_markdown(s.split('\n', 1)[-1] if '\n' in s else s)
            elif ('strategic' in sl[:50] or 'recommendation' in sl[:50]) and not strategy_narrative:
                strategy_narrative = _strip_markdown(s.split('\n', 1)[-1] if '\n' in s else s)
            elif ('verdict' in sl[:30] or 'investment' in sl[:50]) and not verdict_summary:
                verdict_summary = _strip_markdown(s.split('\n', 1)[-1] if '\n' in s else s)

    # Extract key figures for summary cards
    market_figures = _extract_key_figures(market_analysis or research_summary)

    # Pre-compute zone agreement for zone donut chart
    divergence_data = swarm.get('divergence') or analysis.get('divergence') or {}
    zone_agreement = divergence_data.get('zone_agreement', {}) if isinstance(divergence_data, dict) else {}
    if not zone_agreement and sample_agents:
        from collections import defaultdict
        _za = defaultdict(lambda: {'total': 0, 'hits': 0})
        for a in sample_agents:
            z = (a.get('zone') or a.get('Zone') or 'wildcard').lower()
            _za[z]['total'] += 1
            if float(a.get('overall', 0)) >= 5.5:
                _za[z]['hits'] += 1
        zone_agreement = dict(_za)

    # Select highlight agents for featured section
    highlight_agents = _select_highlight_agents(sample_agents, analysis.get('deliberation'))

    # ── BUILD HTML ──
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Mirai Analysis: {company}</title>
<style>
  @page {{ size: letter; margin: 0.6in 0.75in; }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; color: #1a1a2e; line-height: 1.5; font-size: 12px; max-width: 850px; margin: 0 auto; padding: 0 20px; }}
  @media print {{ body {{ max-width: none; padding: 0; }} }}
  .header {{ background: #001f3f; color: white; padding: 20px 30px; margin: 0 -20px 20px; width: calc(100% + 40px); border-radius: 0 0 8px 8px; }}
  @media print {{ .header {{ margin: -0.6in -0.75in 20px; width: calc(100% + 1.5in); border-radius: 0; }} }}
  .header h1 {{ font-size: 11px; letter-spacing: 3px; opacity: 0.7; margin-bottom: 4px; }}
  .header h2 {{ font-size: 22px; font-weight: bold; }}
  .header .subtitle {{ font-size: 11px; opacity: 0.6; margin-top: 4px; }}
  .section-bar {{ background: #e8edf2; color: #001f3f; font-weight: bold; font-size: 14px; padding: 8px 16px; margin: 20px 0 12px; border-left: 4px solid #001f3f; }}
  .section-heading {{ font-size: 16px; font-weight: bold; color: #001f3f; margin: 24px 0 12px; padding-bottom: 4px; border-bottom: 2px solid #001f3f; }}
  .metrics {{ display: flex; gap: 24px; justify-content: center; margin: 16px 0; flex-wrap: wrap; }}
  .metric {{ text-align: center; min-width: 100px; }}
  .metric .value {{ font-size: 24px; font-weight: bold; color: #001f3f; }}
  .metric .label {{ font-size: 10px; color: #888; text-transform: uppercase; letter-spacing: 1px; }}
  .verdict-badge {{ display: inline-block; padding: 6px 20px; border-radius: 4px; font-size: 16px; font-weight: bold; letter-spacing: 2px; }}
  .verdict-hit {{ background: #e8f5e9; color: #2e7d32; }}
  .verdict-miss {{ background: #ffebee; color: #d32f2f; }}
  .verdict-uncertain {{ background: #fff3e0; color: #f57c00; }}
  .verdict-mixed {{ background: #fff3e0; color: #e65100; }}
  table {{ width: 100%; border-collapse: collapse; margin: 8px 0; }}
  th {{ background: #f5f5f5; color: #001f3f; text-align: left; padding: 8px 10px; border-bottom: 2px solid #001f3f; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }}
  td {{ padding: 8px 10px; border-bottom: 1px solid #e8e8e8; font-size: 11px; vertical-align: top; }}
  tr:nth-child(even) {{ background: #fafafa; }}
  .risk-card {{ padding: 12px; margin: 8px 0; border-left: 4px solid #d32f2f; background: #fff5f5; }}
  .risk-card.medium {{ border-color: #f57c00; background: #fff8e1; }}
  .move-card {{ padding: 12px; margin: 8px 0; border-left: 4px solid #2e7d32; background: #f1f8e9; }}
  .suggestion-card {{ padding: 12px; margin: 8px 0; border-left: 4px solid #1565c0; background: #e3f2fd; }}
  .severity {{ font-size: 10px; font-weight: bold; padding: 2px 8px; border-radius: 3px; }}
  .sev-high {{ background: #d32f2f; color: white; }}
  .sev-medium {{ background: #f57c00; color: white; }}
  .sev-low {{ background: #2e7d32; color: white; }}
  .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
  .grid-3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }}
  .fact-item {{ padding: 6px 0; border-bottom: 1px solid #f0f0f0; }}
  .fact-label {{ font-size: 10px; color: #888; text-transform: uppercase; }}
  .fact-value {{ font-size: 12px; color: #333; font-weight: 500; }}
  .narrative {{ color: #333; line-height: 1.7; margin: 8px 0; }}
  .narrative p {{ margin-bottom: 10px; }}
  .charts {{ display: flex; gap: 20px; align-items: center; justify-content: center; flex-wrap: wrap; margin: 16px 0; }}
  .figure-cards {{ display: flex; gap: 12px; flex-wrap: wrap; margin: 12px 0; }}
  .figure-card {{ background: #f8f9fa; border: 1px solid #e0e0e0; border-radius: 6px; padding: 12px 16px; text-align: center; min-width: 110px; flex: 1; }}
  .figure-card .fig-value {{ font-size: 18px; font-weight: bold; color: #001f3f; }}
  .figure-card .fig-label {{ font-size: 9px; color: #888; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px; }}
  .footer {{ text-align: center; color: #999; font-size: 9px; margin-top: 30px; padding-top: 12px; border-top: 1px solid #e0e0e0; }}
  .page-break {{ page-break-before: always; }}
  .keep-together {{ page-break-inside: avoid; }}

  /* Prevent orphaned section headers — always keep heading with next content */
  .section-bar {{
    page-break-after: avoid;
    break-after: avoid;
  }}

  /* Keep charts, cards, and small tables together */
  .charts, .figure-cards, .grid-2, .grid-3, table {{
    page-break-inside: avoid;
    break-inside: avoid;
  }}
  /* Large agent tables MUST be allowed to split across pages */
  table.agents-table {{
    page-break-inside: auto !important;
    break-inside: auto !important;
  }}
  table.agents-table tr {{
    page-break-inside: avoid;
    break-inside: avoid;
  }}

  /* Keep verdict badges and score gauges with their context */
  .verdict-badge, svg {{
    page-break-inside: avoid;
    break-inside: avoid;
  }}

  /* Prevent widows/orphans in narrative text */
  .narrative p {{
    orphans: 3;
    widows: 3;
  }}

  /* Each risk/move/theme item should not split */
  .fact-item {{
    page-break-inside: avoid;
    break-inside: avoid;
  }}
  .appendix-ref {{ font-size: 10px; color: #1565c0; font-style: italic; margin-top: 4px; }}
</style>
</head>
<body>

<!-- PAGE 1: HIGHLIGHTS + GENERAL INFO -->
<div class="header">
  <h1>未来 MIRAI ANALYSIS</h1>
  <h2>{company} | Private Company Profile</h2>
  <div class="subtitle">Generated {timestamp} · Analysis Depth: Deep</div>
</div>

<div class="section-bar">Highlights</div>

<div class="charts">
  <div style="text-align: center;">
    {svg_score_gauge(score)}
  </div>
  <div style="text-align: center;">
    <div class="verdict-badge {"verdict-hit" if "hit" in verdict.lower() else "verdict-miss" if "miss" in verdict.lower() else "verdict-mixed" if "mixed" in verdict.lower() else "verdict-uncertain"}">{verdict.upper()}</div>
    <div style="margin-top: 8px; font-size: 11px; color: #888;">Mirai Verdict</div>
  </div>
  <div style="text-align: center;">
    {svg_zone_sentiment_donut(zone_agreement, pos_pct) if zone_agreement else svg_donut_chart(pos_pct, neg_pct)}
    <div style="font-size: 10px; color: #888; margin-top: -4px;">Swarm by Zone</div>
  </div>
</div>

<div class="metrics">
  <div class="metric"><div class="value">{confidence:.0%}</div><div class="label">Council Confidence</div></div>
  <div class="metric"><div class="value">{data_quality:.0%}</div><div class="label">Data Quality</div></div>
  <div class="metric"><div class="value">{len(council_models) or 4}</div><div class="label">Evaluators</div></div>
  <div class="metric"><div class="value">{total_agents}</div><div class="label">Swarm Agents</div></div>
</div>
'''

    # ── Confidence band: expected score range based on agent divergence ──
    std_overall = float(swarm.get('std_overall', 0) or 0)
    swarm_median = float(swarm.get('median_overall', score) or score)
    if std_overall > 0 and total_agents > 1:
        score_low = max(1.0, round(score - std_overall * 1.2, 1))
        score_high = min(10.0, round(score + std_overall * 1.2, 1))
        band_width = score_high - score_low
        band_color = '#27ae60' if band_width < 1.5 else ('#f39c12' if band_width < 3.0 else '#e74c3c')
        band_label = 'High consensus' if band_width < 1.5 else ('Moderate agreement' if band_width < 3.0 else 'High divergence')

        # What verdict range means
        low_verdict = 'Strong Hit' if score_low > 7.5 else 'Likely Hit' if score_low > 6.0 else 'Mixed Signal' if score_low > 4.5 else 'Likely Miss' if score_low > 3.0 else 'Strong Miss'
        high_verdict = 'Strong Hit' if score_high > 7.5 else 'Likely Hit' if score_high > 6.0 else 'Mixed Signal' if score_high > 4.5 else 'Likely Miss' if score_high > 3.0 else 'Strong Miss'
        verdict_range = f'{low_verdict} to {high_verdict}' if low_verdict != high_verdict else low_verdict

        html += f'''
<div style="background:#f8f9fa; border:1px solid #e0e0e0; border-radius:6px; padding:10px 16px; margin:8px 0; display:flex; align-items:center; gap:16px;">
  <div style="flex-shrink:0;">
    <div style="font-size:9px; color:#888; text-transform:uppercase; letter-spacing:1px;">Expected Range</div>
    <div style="font-size:18px; font-weight:700; color:{band_color};">{score_low} – {score_high}</div>
    <div style="font-size:8px; color:#aaa;">out of 10</div>
  </div>
  <div style="flex:1; padding:0 8px;">
    <div style="background:#e8e8e8; height:8px; border-radius:4px; position:relative;">
      <div style="position:absolute; left:{score_low*10}%; width:{(score_high-score_low)*10}%; height:100%; background:{band_color}; border-radius:4px; opacity:0.5;"></div>
      <div style="position:absolute; left:{score*10}%; width:3px; height:100%; background:#1a1a2e; border-radius:2px; transform:translateX(-1px);"></div>
    </div>
    <div style="display:flex; justify-content:space-between; font-size:7px; color:#aaa; margin-top:2px;">
      <span>1</span><span>5</span><span>10</span>
    </div>
  </div>
  <div style="flex-shrink:0; text-align:right;">
    <div style="font-size:9px; color:{band_color}; font-weight:600;">{band_label}</div>
    <div style="font-size:8px; color:#888;">Verdict range: {verdict_range}</div>
    <div style="font-size:7px; color:#aaa;">Based on agent score std dev ({std_overall:.1f})</div>
  </div>
</div>
'''


    faith_score = analysis.get('faithfulness_score', analysis.get('research', {}).get('faithfulness_score'))
    if faith_score is not None:
        html += f'<div style="text-align:center;"><div style="font-size:20pt;font-weight:700;color:#4488ff;">{faith_score:.0%}</div><div style="font-size:8pt;color:#888;">Faithfulness</div></div>\n'

    html += f'''

<div class="keep-together">
<div class="section-bar">10-Dimension Scoring</div>
{svg_horizontal_bars(dim_items)}
</div>

<div class="section-bar" style="margin-top: 16px;">General Information</div>
<div class="grid-2 keep-together">
  <div>
    <div class="fact-item"><div class="fact-label">Company</div><div class="fact-value" style="font-weight: bold; font-size: 14px;">{company}</div></div>
    <div class="fact-item"><div class="fact-label">Industry</div><div class="fact-value">{industry}</div></div>
    <div class="fact-item"><div class="fact-label">Product</div><div class="fact-value">{extraction.get("product", "")}</div></div>
  </div>
  <div>
    <div class="fact-item"><div class="fact-label">Target Market</div><div class="fact-value">{extraction.get("target_market", "")}</div></div>
    <div class="fact-item"><div class="fact-label">Business Model</div><div class="fact-value">{extraction.get("business_model", "")}</div></div>
    <div class="fact-item"><div class="fact-label">Stage</div><div class="fact-value">{extraction.get("stage", "")}</div></div>
  </div>
</div>
<div class="grid-2 keep-together" style="margin-top: 8px;">
  <div>
    {"<div class='fact-item'><div class='fact-label'>Website</div><div class='fact-value'><a href='" + extraction.get("website_url", "") + "' style='color:#3366cc;'>" + extraction.get("website_url", "") + "</a></div></div>" if extraction.get("website_url") else ""}
    {"<div class='fact-item'><div class='fact-label'>Location</div><div class='fact-value'>" + extraction.get("location", "") + "</div></div>" if extraction.get("location") else ""}
    {"<div class='fact-item'><div class='fact-label'>Year Founded</div><div class='fact-value'>" + extraction.get("year_founded", "") + "</div></div>" if extraction.get("year_founded") else ""}
  </div>
  <div>
    {"<div class='fact-item'><div class='fact-label'>Revenue</div><div class='fact-value'>" + extraction.get("revenue", "") + "</div></div>" if extraction.get("revenue") else ""}
    {"<div class='fact-item'><div class='fact-label'>Funding</div><div class='fact-value'>" + extraction.get("funding", "") + "</div></div>" if extraction.get("funding") else ""}
    {"<div class='fact-item'><div class='fact-label'>Team</div><div class='fact-value'>" + extraction.get("team", "") + "</div></div>" if extraction.get("team") else ""}
  </div>
</div>

<!-- PAGE 2: AGENT HEATMAP + DIVERGENCE -->
<div class="page-break"></div>

<div class="section-bar">Score Breakdown by Zone</div>
'''

    # Zone dimension grouped bar chart
    if sample_agents:
        html += svg_zone_dimension_bars(sample_agents)
        html += '<div style="font-size: 9px; color: #888; margin-top: 4px;">Average scores per dimension grouped by zone. Bar length proportional to score (0-10).</div>\n'

    # Divergence radar
    if sample_agents and len(sample_agents) >= 5:
        html += '<div class="section-bar" style="margin-top: 16px;">Score Divergence Radar</div>\n'
        html += '<div class="charts">\n'
        html += svg_divergence_radar(sample_agents)
        html += '<div style="max-width: 200px; font-size: 10px; color: #666; line-height: 1.5;">'
        html += '<strong>Reading the radar:</strong><br/>'
        html += 'Blue line = average score. Red band = range (min to max across all agents). '
        html += 'Wide bands = high disagreement. Narrow bands = consensus.'
        html += '</div>\n</div>\n'

    # Competitive comparison table (if competitors available)
    if competitors and len(competitors) >= 3:
        html += '<div class="section-bar" style="margin-top: 16px;">Competitive Comparison</div>\n'
        html += html_competitive_comparison(competitors, company)
        html += '<div style="font-size: 9px; color: #888; margin-top: 4px;">Startup highlighted in green. Competitor details enriched from database where available.</div>\n'

    # ── C3: Research Overview ──
    if research_summary:
        html += '\n<div class="section-bar">Research Overview</div>\n'
        html += f'<div class="narrative"><p>{_sanitize_reasoning(_strip_markdown(research_summary[:500]))}</p></div>\n'
        cited_count = len(cited_facts) if cited_facts else 0
        source_count = len(set(c.get('source_domain', '') for c in (cited_facts or []) if c.get('source_domain')))
        if cited_count:
            html += f'<p style="font-size: 9px; color: #666;">{cited_count} facts verified across {source_count} sources</p>\n'

    html += f'''
<!-- PAGE 3: MARKET ANALYSIS + COMPETITORS -->
<div class="page-break"></div>

<div class="section-bar">Market Analysis</div>
'''

    # Market analysis key figures
    if market_figures:
        html += '<div class="figure-cards">\n'
        for fig in market_figures:
            html += f'  <div class="figure-card"><div class="fig-value">{fig["value"]}</div><div class="fig-label">{fig["label"]}</div></div>\n'
        html += '</div>\n'

    if market_analysis:
        # Show first ~300 chars as summary, reference appendix for full text
        summary_text = market_analysis
        sentences = re.split(r'(?<=[.!?])\s+', summary_text)
        short_summary = ''
        for s in sentences:
            if len(short_summary) + len(s) > 400:
                break
            short_summary = short_summary + ' ' + s if short_summary else s
        if short_summary and len(short_summary) < len(market_analysis) - 50:
            html += f'<div class="narrative"><p>{short_summary}</p></div>\n'
            html += '<div class="appendix-ref">* Full market analysis in Appendix A</div>\n'
        else:
            html += f'<div class="narrative">{_to_paragraphs(market_analysis)}</div>\n'
    elif research_summary:
        html += f'<div class="narrative">{_to_paragraphs(research_summary)}</div>\n'

    # Competitors table — use research payload only so render stays non-blocking
    if competitors:
        html += '<div class="section-bar keep-together">Top Similar Companies</div>\n<table class="keep-together">\n'
        html += '<tr><th>#</th><th>Company</th><th>Industry</th><th>Status</th><th>Funding</th></tr>\n'

        for i, c in enumerate(competitors[:8]):
            if isinstance(c, dict):
                c_name = c.get('name', str(c))
                c_industry = c.get('industry') or c.get('primary_industry') or c.get('type') or industry
                c_status = c.get('status') or c.get('financing_status') or c.get('business_status') or ''
                c_funding = c.get('funding') or c.get('total_raised') or ''
            else:
                c_name = str(c)
                c_industry = industry
                c_status = ''
                c_funding = ''

            c_industry = c_industry or '—'
            c_status = c_status or '—'
            c_funding = c_funding or '—'

            html += f'<tr><td>{i+1}</td><td style="font-weight:bold;">{c_name}</td><td>{c_industry}</td><td>{c_status}</td><td>{c_funding}</td></tr>\n'
        html += '</table>\n'

    # Competitive position summary (short version, full in appendix)
    if competitive_position:
        html += '<div class="section-bar">Competitive Position</div>\n'
        sentences = re.split(r'(?<=[.!?])\s+', competitive_position)
        short_comp = ''
        for s in sentences:
            if len(short_comp) + len(s) > 400:
                break
            short_comp = short_comp + ' ' + s if short_comp else s
        if short_comp and len(short_comp) < len(competitive_position) - 50:
            html += f'<div class="narrative"><p>{short_comp}</p></div>\n'
            html += '<div class="appendix-ref">* Full competitive analysis in Appendix B</div>\n'
        else:
            html += f'<div class="narrative">{_to_paragraphs(competitive_position)}</div>\n'

    # ═══ COUNCIL DELIBERATION ═══

    html += '<div class="section-bar">Council Deliberation</div>\n'
    html += '<p style="color: #666; margin-bottom: 12px;">Multiple AI evaluators scored independently, each blind to the others\' assessments.</p>\n'

    # B3: Show council reasoning if available
    if council_reasoning:
        html += f'<div class="narrative" style="margin-bottom: 12px;">{_to_paragraphs(_sanitize_reasoning(council_reasoning[:800]))}</div>\n'

    html += svg_horizontal_bars(dim_items)

    # Per-model score breakdown (if council used multiple models)
    council_model_scores = prediction.get('model_scores', {})
    if council_model_scores and isinstance(council_model_scores, dict) and len(council_model_scores) > 1:
        html += '<div style="margin-top: 12px;">\n'
        html += '<p style="font-size: 11px; color: #666; margin-bottom: 6px;">Per-model dimension scores:</p>\n'
        html += '<table>\n<tr><th>Model</th>'
        # Use whatever dimension names the first model has
        first_model_scores = list(council_model_scores.values())[0]
        dim_names = list(first_model_scores.keys()) if isinstance(first_model_scores, dict) else []
        for d in dim_names[:7]:
            html += f'<th style="font-size:8px;text-align:center;">{d.replace("_"," ").title()[:14]}</th>'
        html += '</tr>\n'
        for model_label, scores in council_model_scores.items():
            if not isinstance(scores, dict):
                continue
            html += f'<tr><td style="font-weight:bold;font-size:10px;">{_sanitize_reasoning(str(model_label)[:20])}</td>'
            for d in dim_names[:7]:
                s = float(scores.get(d, 0))
                color = _color_for_score(s)
                html += f'<td style="color:{color};font-weight:bold;text-align:center;font-size:11px;">{s:.1f}</td>'
            html += '</tr>\n'
        html += '</table>\n</div>\n'

    # Council reasoning (if available)
    if council_reasoning:
        html += f'<div class="narrative" style="margin-top: 12px; padding: 10px; background: #f8f9fa; border-left: 3px solid #001f3f;">{_to_paragraphs(council_reasoning)}</div>\n'

    if contested:
        html += '<div style="margin-top: 12px; padding: 10px; background: #fff3e0; border-left: 4px solid #f57c00;">\n'
        html += '<strong style="color: #f57c00;">Contested Dimensions</strong><br/>\n'
        for c in contested:
            c_name = c if isinstance(c, str) else str(c)
            html += f'<span style="color: #333;">{c_name.replace("_", " ").title()} - Models disagreed significantly on this dimension.</span><br/>\n'
        html += '</div>\n'

    # ═══ C1: KEY THEMES (positive + negative) ═══
    themes_pos = swarm.get('key_themes_positive', [])
    themes_neg = swarm.get('key_themes_negative', [])
    if themes_pos or themes_neg:
        html += '\n<div class="section-bar">Key Themes</div>\n'
        html += '<div style="display: flex; gap: 20px; margin-bottom: 16px;">\n'
        if themes_pos:
            html += '<div style="flex: 1;"><p style="color: #2e7d32; font-weight: bold; margin-bottom: 6px;">Positive Signals</p><ul style="font-size: 11px; line-height: 1.6;">\n'
            for t in themes_pos[:5]:
                html += f'<li>{_sanitize_reasoning(str(t))}</li>\n'
            html += '</ul></div>\n'
        if themes_neg:
            html += '<div style="flex: 1;"><p style="color: #d32f2f; font-weight: bold; margin-bottom: 6px;">Risk Signals</p><ul style="font-size: 11px; line-height: 1.6;">\n'
            for t in themes_neg[:5]:
                html += f'<li>{_sanitize_reasoning(str(t))}</li>\n'
            html += '</ul></div>\n'
        html += '</div>\n'

    # ═══ AGENT HIGHLIGHTS (selected 5-6 most interesting) ═══
    if highlight_agents:
        html += '<div class="page-break"></div>\n'
        html += f'<div class="section-bar">Agent Highlights ({len(highlight_agents)} selected from {total_agents})</div>\n'
        html += '<p style="color: #666; margin-bottom: 12px; font-size: 11px;">The most interesting perspectives from the swarm. Full agent responses in Appendix C.</p>\n'

        for ha in highlight_agents:
            ha_score = float(ha.get('overall', 5))
            ha_vote = 'HIT' if ha_score >= 5.5 else 'MISS'
            ha_color = '#2e7d32' if ha_vote == 'HIT' else '#d32f2f'
            ha_label = ha.get('_highlight', '')
            ha_persona = _sanitize_persona_name(str(ha.get('persona', '?')))
            ha_zone = ha.get('zone', 'wildcard').title()
            ha_reasoning = _replace_em_dashes(str(ha.get('reasoning', '')))

            html += f'<div style="margin: 10px 0; padding: 14px; border-left: 4px solid {ha_color}; background: {"#f1f8e9" if ha_vote == "HIT" else "#fff5f5"}; border-radius: 4px;">\n'
            html += f'  <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">\n'
            html += f'    <strong style="color: #001f3f;">{ha_persona}</strong>\n'
            html += f'    <span style="font-size: 11px;"><span style="color:{ha_color};font-weight:bold;">{ha_vote} {ha_score:.1f}/10</span> - {ha_zone} - <em>{ha_label}</em></span>\n'
            html += f'  </div>\n'
            html += f'  <div style="color: #333; font-size: 11px; line-height: 1.6;">{ha_reasoning}</div>\n'
            html += f'</div>\n'

    # ═══ SWARM ANALYSIS (full agent table — Appendix C) ═══
    if sample_agents:
        html += '<div class="page-break"></div>\n'
        html += f'<div class="section-heading">Appendix C: All Agent Responses ({total_agents} agents)</div>\n'

        html += '<div class="charts">\n'
        html += svg_donut_chart(pos_pct, neg_pct)
        html += f'<div style="text-align: center;"><div style="font-size: 24px; font-weight: bold; color: #d32f2f;">{neg_pct:.0f}% MISS</div><div style="font-size: 24px; font-weight: bold; color: #2e7d32;">{pos_pct:.0f}% HIT</div></div>\n'
        html += '</div>\n'

        # Agent decisions — grouped by zone
        zone_labels = {
            'investor': 'Investor Perspectives',
            'customer': 'Customer Perspectives',
            'operator': 'Operator Perspectives',
            'analyst': 'Analyst Perspectives',
            'contrarian': 'Contrarian Perspectives',
            'wildcard': 'Wild Card Perspectives',
        }

        # Group agents by zone
        from collections import defaultdict
        agents_by_zone = defaultdict(list)
        for agent in sample_agents:
            zone = agent.get('zone', 'wildcard')
            if not zone or zone == 'wildcard':
                persona_lower = str(agent.get('persona', '')).lower()
                for z, keywords in [
                    ('investor', ['vc', 'investor', 'angel', 'pe ', 'fund', 'capital']),
                    ('customer', ['customer', 'buyer', 'target', 'user', 'procurement']),
                    ('operator', ['founder', 'cto', 'cmo', 'cfo', 'coo', 'vp ', 'engineer']),
                    ('analyst', ['analyst', 'researcher', 'expert', 'economist', 'strategist', 'professor']),
                    ('contrarian', ['competitor', 'regulatory', 'patent', 'risk', 'cybersecurity', 'skeptic']),
                ]:
                    if any(kw in persona_lower for kw in keywords):
                        zone = z
                        break
            agents_by_zone[zone].append(agent)

        # Render each zone section
        for zone_key in ['investor', 'customer', 'operator', 'analyst', 'contrarian', 'wildcard']:
            zone_agents = agents_by_zone.get(zone_key, [])
            if not zone_agents:
                continue

            zone_hits = sum(1 for a in zone_agents if float(a.get('overall', 0)) >= 5.5)
            zone_total = len(zone_agents)
            zone_hit_pct = (zone_hits / zone_total * 100) if zone_total > 0 else 0
            zone_color = '#2e7d32' if zone_hit_pct >= 60 else '#d32f2f' if zone_hit_pct <= 40 else '#f57c00'

            html += f'<div class="section-bar">{zone_labels.get(zone_key, zone_key.title())} ({zone_total} agents - <span style="color:{zone_color}">{zone_hit_pct:.0f}% HIT</span>)</div>\n'
            html += '<table class="agents-table">\n<tr><th>Agent</th><th>Vote</th><th>Score</th><th>Reasoning</th></tr>\n'

            for agent in zone_agents:
                persona = _sanitize_persona_name(str(agent.get('persona', '?'))[:60])
                overall = float(agent.get('overall', 0))
                vote = 'HIT' if overall >= 5.5 else 'MISS'
                vote_color = '#2e7d32' if vote == 'HIT' else '#d32f2f'
                reasoning = _replace_em_dashes(str(agent.get('reasoning', '')))
                html += f'<tr><td>{persona}</td><td style="color:{vote_color};font-weight:bold;">{vote}</td><td>{overall:.1f}</td><td style="font-size:10px;color:#555;">{reasoning}</td></tr>\n'

            html += '</table>\n'

    # ═══ CRITICAL DIVERGENCE ═══
    divergence = swarm.get('divergence') or analysis.get('divergence')
    if divergence and isinstance(divergence, dict) and not divergence.get('consensus', True):
        outliers = divergence.get('divergence_narrative', [])
        zone_agreement = divergence.get('zone_agreement', {})
        most_divided = divergence.get('most_divided_dimension')

        if outliers:
            html += '<div class="section-bar" style="border-color: #f57c00; background: #fff3e0;">Critical Divergence</div>\n'
            if most_divided:
                html += f'<p style="color: #f57c00; font-weight: bold; margin-bottom: 10px;">Most contested dimension: {most_divided.replace("_", " ").title()}</p>\n'

            # Zone agreement table
            if zone_agreement:
                html += '<table>\n<tr><th>Zone</th><th>Agents</th><th>Agreement</th><th>Direction</th></tr>\n'
                for z_key in ['investor', 'customer', 'operator', 'analyst', 'contrarian', 'wildcard']:
                    z_data = zone_agreement.get(z_key)
                    if z_data:
                        ag_color = '#2e7d32' if z_data['agreement_pct'] >= 75 else '#f57c00' if z_data['agreement_pct'] >= 50 else '#d32f2f'
                        html += f'<tr><td>{z_key.title()}</td><td>{z_data["total"]}</td><td style="color:{ag_color};font-weight:bold;">{z_data["agreement_pct"]:.0f}%</td><td>{z_data["majority_direction"]}</td></tr>\n'
                html += '</table>\n'

            # Outlier agents
            html += '<table style="margin-top: 12px;">\n<tr><th>Agent</th><th>Zone</th><th>Score</th><th>Deviation</th><th>Position</th></tr>\n'
            for o in outliers[:6]:
                d_color = '#2e7d32' if o['direction'] == 'bullish' else '#d32f2f'
                z_display = f'{o["z_score"]:+.1f} SD'
                html += f'<tr><td>{o["persona"][:50]}</td><td>{o["zone"].title()}</td>'
                html += f'<td style="font-weight:bold;">{o["overall"]:.1f}</td>'
                html += f'<td style="color:{d_color};font-weight:bold;">{z_display}</td>'
                html += f'<td style="font-size:10px;color:#555;">{_replace_em_dashes(_truncate(o["excerpt"], 180))}</td></tr>\n'
            html += '</table>\n'

    # ═══ INVESTMENT COMMITTEE DELIBERATION ═══
    deliberation = swarm.get('deliberation') or analysis.get('deliberation')
    if deliberation and isinstance(deliberation, dict):
        has_positions = deliberation.get('positions')  # New format (5-6 member roundtable)
        has_challenges = deliberation.get('challenges')  # Old format (2-person debate)

        if has_positions or has_challenges:
            committee_size = len(deliberation.get('committee', deliberation.get('positions', deliberation.get('challenges', []))))
            html += '<div class="section-bar" style="border-color: #1565c0; background: #e3f2fd;">Investment Committee Deliberation</div>\n'
            html += f'<p style="color: #666; margin-bottom: 10px;">{committee_size}-member committee, {deliberation.get("rounds", 2)} rounds</p>\n'

        # New format: position statements from 5-6 committee members
        if has_positions:
            for pos in deliberation['positions']:
                persona = pos.get('persona', '?')[:45]
                zone = pos.get('zone', '?').title()
                orig = pos.get('original_score', 0)
                adj = pos.get('adjusted_score')
                position_text = _replace_em_dashes(str(pos.get('position', '')))
                addresses = pos.get('addresses', '')
                conviction = pos.get('conviction_change', 'unchanged')

                if adj is not None and abs(adj - orig) > 0.1:
                    ch_color = '#2e7d32' if adj > orig else '#d32f2f'
                    score_str = f'<span style="color:{ch_color};font-weight:bold;">{orig:.1f} &rarr; {adj:.1f}</span>'
                else:
                    score_str = f'<span style="color:#888;">{orig:.1f}/10</span>'

                conv_icon = '&#x2191;' if conviction == 'stronger' else '&#x2193;' if conviction == 'weaker' else '&#x2194;'

                html += f'<div style="margin: 10px 0; padding: 12px; background: #f8f9fa; border-left: 4px solid #1565c0; border-radius: 4px;">\n'
                html += f'  <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">\n'
                html += f'    <strong style="color: #1565c0;">{persona}</strong>\n'
                html += f'    <span style="font-size: 10px;">{zone} - {score_str} {conv_icon}</span>\n'
                html += f'  </div>\n'
                if addresses:
                    html += f'  <div style="font-size: 9px; color: #888; margin-bottom: 4px;">Responding to: {addresses[:40]}</div>\n'
                html += f'  <div style="color: #333; font-size: 11px; line-height: 1.6;">{position_text}</div>\n'
                html += f'</div>\n'

        # Old format: challenges (backward compat)
        elif has_challenges:
            for challenge in deliberation['challenges']:
                defender = challenge.get('defender', '?')[:45]
                challenger = challenge.get('challenger', '?')[:45]
                orig_score = challenge.get('defender_original_score', 0)
                adj_score = challenge.get('adjusted_score')
                response = _replace_em_dashes(str(challenge.get('response', '')))

                if adj_score is not None and abs(adj_score - orig_score) > 0.1:
                    change_color = '#2e7d32' if adj_score > orig_score else '#d32f2f'
                    score_change = f'<span style="color:{change_color};font-weight:bold;">{orig_score:.1f} &rarr; {adj_score:.1f}</span>'
                else:
                    score_change = f'<span style="color:#888;">Held at {orig_score:.1f}</span>'

                html += f'<div style="margin: 12px 0; padding: 12px; background: #f8f9fa; border-left: 4px solid #1565c0; border-radius: 4px;">\n'
                html += f'  <div style="display: flex; justify-content: space-between; margin-bottom: 8px;"><strong style="color: #1565c0;">{defender}</strong><span style="font-size: 11px;">vs {challenger} - {score_change}</span></div>\n'
                html += f'  <div style="color: #333; font-size: 11px;">{response}</div>\n'
                html += '</div>\n'

        # Chair synthesis (works for both formats)
        synthesis = deliberation.get('synthesis', {})
        if isinstance(synthesis, dict):
            # New format fields
            consensus_pts = synthesis.get('consensus_points', [])
            tensions = synthesis.get('unresolved_tensions', [])
            recommendation = synthesis.get('recommendation', synthesis.get('committee_recommendation', ''))
            critical_risk = synthesis.get('critical_risk', '')
            verdict_shifted = synthesis.get('verdict_shifted', False)
            # Old format fallback
            summary_text = synthesis.get('summary', '')

            if recommendation or summary_text or consensus_pts:
                html += '<div style="margin-top: 12px; padding: 14px; background: #e8edf2; border-left: 4px solid #001f3f;">\n'
                html += '<strong style="color: #001f3f;">Committee Chair Synthesis</strong>\n'

                if consensus_pts:
                    html += '<div style="margin-top: 8px;"><strong style="font-size: 11px; color: #2e7d32;">Committee agrees:</strong><ul style="margin: 4px 0 8px 16px; font-size: 11px; color: #333;">'
                    for cp in consensus_pts[:4]:
                        html += f'<li>{_replace_em_dashes(str(cp))}</li>'
                    html += '</ul></div>\n'

                if tensions:
                    html += '<div><strong style="font-size: 11px; color: #f57c00;">Unresolved:</strong><ul style="margin: 4px 0 8px 16px; font-size: 11px; color: #333;">'
                    for t in tensions[:4]:
                        html += f'<li>{_replace_em_dashes(str(t))}</li>'
                    html += '</ul></div>\n'

                if recommendation:
                    html += f'<p style="margin-top: 8px; font-size: 11px; color: #1565c0;"><strong>Recommendation:</strong> {_replace_em_dashes(str(recommendation))}</p>\n'

                if critical_risk:
                    html += f'<p style="margin-top: 4px; font-size: 11px; color: #d32f2f;"><strong>Critical risk:</strong> {_replace_em_dashes(str(critical_risk))}</p>\n'

                if verdict_shifted:
                    html += '<p style="margin-top: 4px; font-size: 10px; color: #f57c00; font-weight: bold;">The deliberation shifted the committee verdict.</p>\n'

                if summary_text and not consensus_pts:
                    html += f'<div class="narrative" style="margin-top: 8px;">{_to_paragraphs(_replace_em_dashes(summary_text))}</div>\n'

                html += '</div>\n'

    # ═══ OASIS Market Simulation ═══
    oasis = analysis.get('oasis', {})
    oasis_timeline = oasis.get('timeline', []) if isinstance(oasis, dict) else []
    if oasis_timeline:
        month_count = len(oasis_timeline)
        month_label = "month" if month_count == 1 else "months"
        html += f'<div class="section-bar">Market Trajectory Simulation ({month_count} {month_label})</div>\n'
        trajectory = oasis.get('trajectory', 'stable')
        start_s = oasis.get('start_sentiment', oasis.get('startSentiment', 50))
        end_s = oasis.get('end_sentiment', oasis.get('endSentiment', 50))
        traj_color = '#2e7d32' if trajectory == 'improving' else '#d32f2f' if trajectory == 'declining' else '#f57c00'
        html += f'<p style="color: {traj_color}; font-weight: bold; font-size: 16px;">Trajectory: {trajectory.upper()} ({start_s}% -> {end_s}%)</p>\n'
        html += '<table>\n<tr><th>Month</th><th>Event</th><th>Sentiment</th><th>Change</th><th>Confidence</th></tr>\n'
        for t in oasis_timeline:
            if isinstance(t, dict):
                change = t.get('sentiment_change', t.get('change', 0))
                change_str = f'+{change}%' if change > 0 else f'{change}%'
                change_color = '#2e7d32' if change > 0 else '#d32f2f' if change < 0 else '#888'
                event_text = _strip_markdown(_replace_em_dashes(str(t.get("event", ""))))
                conf_low = t.get("confidence_low", t.get("confidenceLow", 0))
                conf_high = t.get("confidence_high", t.get("confidenceHigh", 100))
                band_width = conf_high - conf_low
                band_color = '#27ae60' if band_width < 20 else ('#f39c12' if band_width < 40 else '#e74c3c')
                html += f'<tr><td>Month {t.get("month", "?")}</td><td>{event_text}</td><td>{t.get("sentiment_pct", t.get("sentimentPct", "?"))}%</td><td style="color:{change_color}">{change_str}</td>\n'
                html += f'<td style="color:{band_color};">{conf_low:.0f}% - {conf_high:.0f}%</td></tr>\n'
        html += '</table>\n'

        # C4: OASIS verdict adjustment note
        oasis_trajectory = oasis.get('trajectory', 'stable')
        if oasis_trajectory != 'stable':
            direction = 'upgraded' if oasis_trajectory == 'improving' else 'adjusted downward'
            html += f'<p style="font-size: 10px; color: #666; margin-top: 8px;"><em>Note: The {month_count}-month market trajectory ({oasis_trajectory}) {direction} the final verdict assessment.</em></p>\n'

    # ═══ RISKS + PLAN ═══
    html += '<div class="page-break"></div>\n'

    if risks:
        html += '<div class="section-heading">Risk Assessment</div>\n'
        for i, risk in enumerate(risks[:5]):
            r_text = risk.get('risk', risk) if isinstance(risk, dict) else str(risk)
            r_text = _replace_em_dashes(str(r_text))
            severity = 'HIGH' if i < 2 else 'MEDIUM'
            sev_class = 'sev-high' if i < 2 else 'sev-medium'
            html += f'<div class="risk-card keep-together{"" if i < 2 else " medium"}">\n'
            html += f'  <span class="severity {sev_class}">{severity}</span>\n'
            html += f'  <div style="margin-top: 6px; color: #333;">{r_text}</div>\n'
            html += '</div>\n'

    if risk_narrative:
        html += f'<div class="narrative">{_to_paragraphs(_replace_em_dashes(risk_narrative))}</div>\n'

    if moves:
        html += '<div class="section-heading">Strategic Recommendations</div>\n'
        for i, move in enumerate(moves[:5]):
            m_text = move.get('move', move.get('action', move)) if isinstance(move, dict) else str(move)
            m_text = _replace_em_dashes(str(m_text))
            html += f'<div class="move-card keep-together">\n'
            html += f'  <strong>Move {i+1}</strong>\n'
            html += f'  <div style="margin-top: 4px; color: #333;">{m_text}</div>\n'
            html += '</div>\n'

    if strategy_narrative:
        html += f'<div class="narrative">{_to_paragraphs(_replace_em_dashes(strategy_narrative))}</div>\n'

    # ═══ SUGGESTIONS + VERDICT ═══
    if suggestions:
        html += '<div class="section-bar">Actionable Improvements</div>\n'
        for sug in suggestions:
            html += f'<div class="suggestion-card keep-together">\n'
            html += f'  <strong style="color: #1565c0;">{sug["area"]}</strong> - <span style="color: #f57c00;">{sug["issue"]}</span>\n'
            html += f'  <div style="margin-top: 4px; color: #333;">{sug["action"]}</div>\n'
            html += '</div>\n'

    if verdict_summary:
        html += f'<div class="section-bar">Investment Verdict</div>\n<div class="narrative">{_to_paragraphs(_replace_em_dashes(verdict_summary))}</div>\n'

    # ═══ Fact Verification Summary ═══
    fact_check = analysis.get('fact_check', analysis.get('fact_verification', {}))
    if fact_check and isinstance(fact_check, dict):
        verified = fact_check.get('verified_count', fact_check.get('verified', 0))
        contradicted = fact_check.get('contradicted_count', fact_check.get('contradicted', 0))
        unverified = fact_check.get('unverified_count', fact_check.get('unverified', 0))
        total = verified + contradicted + unverified
        trust = fact_check.get('trust_score', 0)
        if total > 0:
            html += '<div class="section-heading">Fact Verification Summary</div>\n'
            html += f'<div style="display:flex;gap:16px;margin:8px 0;">\n'
            html += f'<div style="color:#27ae60;font-size:14pt;font-weight:700;">{verified} verified</div>\n'
            html += f'<div style="color:#e74c3c;font-size:14pt;font-weight:700;">{contradicted} contradicted</div>\n'
            html += f'<div style="color:#888;font-size:14pt;font-weight:700;">{unverified} unverified</div>\n'
            html += f'</div>\n'
            html += f'<div style="font-size:10pt;color:#aaa;">Trust score: {trust:.0%} ({verified}/{total} claims verified against external sources)</div>\n'
            # List critical contradictions
            critical = fact_check.get('critical_contradictions', [])
            if critical:
                html += '<div style="margin-top:8px;padding:8px;background:rgba(231,76,60,0.1);border-radius:4px;">\n'
                for c in critical[:5]:
                    html += f'<div style="font-size:9pt;color:#e74c3c;">- {c[:200]}</div>\n'
                html += '</div>\n'

    # ═══ APPENDIX: Full narratives ═══
    has_appendix = False
    if market_analysis and len(market_analysis) > 500:
        html += '<div class="page-break"></div>\n'
        html += '<div class="section-heading">Appendix A: Full Market Analysis</div>\n'
        html += f'<div class="narrative">{_to_paragraphs(_replace_em_dashes(market_analysis))}</div>\n'
        has_appendix = True

    if competitive_position and len(competitive_position) > 500:
        if not has_appendix:
            html += '<div class="page-break"></div>\n'
        html += '<div class="section-heading">Appendix B: Full Competitive Landscape</div>\n'
        html += f'<div class="narrative">{_to_paragraphs(_replace_em_dashes(competitive_position))}</div>\n'
        has_appendix = True

    # ═══ Appendix D: Research Sources & Citations ═══
    # Filter to only show cited facts with real sources (not "multi-model synthesis")
    real_citations = [c for c in (cited_facts or []) if isinstance(c, dict) and c.get('source_url') and c.get('source_domain', '') != 'multi-model synthesis']
    if not real_citations:
        real_citations = cited_facts or []  # fallback to all if no real sources
    if real_citations:
        html += '<div class="page-break"></div>\n'
        html += '<div class="section-heading">Appendix D: Research Sources &amp; Citations</div>\n'
        html += '<table>\n'
        html += '<tr style="background:#1a1a2e;color:#e0e0e0;"><th>Fact</th><th>Source</th><th>Confidence</th></tr>\n'
        for cf in real_citations[:20]:
            text = str(cf.get('text', ''))[:200] if isinstance(cf, dict) else str(cf)[:200]
            source = cf.get('source_domain', '') if isinstance(cf, dict) else ''
            url = cf.get('source_url', '') if isinstance(cf, dict) else ''
            conf = cf.get('confidence', 'medium') if isinstance(cf, dict) else 'medium'
            conf_color = {'high': '#2ecc71', 'medium': '#f39c12', 'low': '#e74c3c'}.get(conf, '#f39c12')
            source_cell = f'<a href="{url}" style="color:#7fdbca;">{source}</a>' if url else (source or 'multi-model synthesis')
            html += f'<tr><td>{text}</td><td>{source_cell}</td><td style="color:{conf_color};">{conf}</td></tr>\n'
        html += '</table>\n'

    # ═══ Appendix E: All Research Sources (bibliography) ═══
    # Collect all unique URLs from cited_facts + research findings
    all_urls = {}
    for cf in (cited_facts or []):
        if isinstance(cf, dict) and cf.get('source_url'):
            url = cf['source_url']
            domain = cf.get('source_domain', '')
            if url not in all_urls:
                all_urls[url] = domain
    # Also pull from research context_facts sources if available
    for src in (analysis.get('research', {}).get('sources', []) if isinstance(analysis.get('research'), dict) else []):
        url = src.get('url', '') if isinstance(src, dict) else ''
        if url and url not in all_urls:
            from urllib.parse import urlparse as _up
            all_urls[url] = _up(url).netloc

    if all_urls:
        # Group by domain
        from collections import defaultdict as _dd
        by_domain = _dd(list)
        for url, domain in all_urls.items():
            by_domain[domain or 'other'].append(url)

        html += '\n<div class="section-heading">Appendix E: Research Sources</div>\n'
        html += '<p style="font-size: 10px; color: #666; margin-bottom: 10px;">All web sources consulted during research. Links are clickable in digital PDF.</p>\n'
        for domain in sorted(by_domain.keys()):
            urls = by_domain[domain]
            html += f'<p style="margin: 6px 0 2px; font-weight: bold; font-size: 10px; color: #001f3f;">{domain} ({len(urls)} source{"s" if len(urls) > 1 else ""})</p>\n'
            html += '<ul style="font-size: 9px; margin: 0; padding-left: 16px; line-height: 1.5;">\n'
            for url in urls[:5]:  # Cap at 5 per domain
                html += f'<li><a href="{url}" style="color: #3366cc; text-decoration: none;">{url[:80]}{"..." if len(url) > 80 else ""}</a></li>\n'
            if len(urls) > 5:
                html += f'<li style="color: #888;">... and {len(urls) - 5} more</li>\n'
            html += '</ul>\n'

    # Footer
    sources = analysis.get('data_sources', [])
    html += f'''
<div class="footer">
  Generated by Mirai (未来) AI Due Diligence Platform<br/>
  Data sources: {', '.join(sources) if sources else 'Web Research, AI Council, Swarm Evaluators'}<br/>
  Council: Multi-model assessment · Swarm: {total_agents} AI evaluators with diverse professional backgrounds · {timestamp}<br/>
  &copy; 2026 Mirai Analysis. For research purposes only.
</div>

<button onclick="window.print()" style="position:fixed; bottom:24px; right:24px; background:#001f3f; color:white; border:none; padding:12px 24px; border-radius:8px; font-size:14px; font-weight:600; cursor:pointer; box-shadow:0 2px 8px rgba(0,0,0,0.2); z-index:1000; display:flex; align-items:center; gap:8px;" onmouseover="this.style.background='#003366'" onmouseout="this.style.background='#001f3f'">
  <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M6 9V2h12v7M6 18H4a2 2 0 01-2-2v-5a2 2 0 012-2h16a2 2 0 012 2v5a2 2 0 01-2 2h-2M6 14h12v8H6z"/></svg>
  Save as PDF
</button>
<style>@media print {{ button {{ display: none !important; }} }}</style>
<script>if(new URLSearchParams(window.location.search).get('print')==='1')setTimeout(()=>window.print(),500);</script>
</body>
</html>'''

    return html


def _audit_and_fix_html(html: str) -> str:
    """LLM audit of report HTML — fixes formatting issues before PDF render."""
    try:
        from openai import OpenAI
        from ..config import Config

        proxy_key = Config.LLM_API_KEY
        proxy_url = Config.LLM_BASE_URL
        if not proxy_key:
            return html

        client = OpenAI(api_key=proxy_key, base_url=proxy_url)

        # Extract just the visible text + structure (not full HTML — too long)
        # Send a condensed version for audit
        import re as _re
        # Strip CSS/style blocks for the audit prompt
        text_only = _re.sub(r'<style[^>]*>[\s\S]*?</style>', '', html)
        text_only = _re.sub(r'<[^>]+>', ' ', text_only)
        text_only = _re.sub(r'\s+', ' ', text_only).strip()

        # Check for obvious issues programmatically first
        issues = []
        if '7-Dimension' in html:
            html = html.replace('7-Dimension', '10-Dimension')
            issues.append("Fixed: '7-Dimension' → '10-Dimension'")
        if '7 dimensions' in html.lower():
            html = _re.sub(r'7 dimensions', '10 dimensions', html, flags=_re.IGNORECASE)
            issues.append("Fixed: '7 dimensions' → '10 dimensions'")

        # Check for empty sections (label followed by empty value)
        empty_fields = _re.findall(r'<div class="fact-label">([^<]+)</div>\s*<div class="fact-value">\s*</div>', html)
        if empty_fields:
            issues.append(f"Empty fields found: {', '.join(empty_fields)}")

        # Check for large empty pages (page-break followed by minimal content)
        pages = html.split('class="page-break"')
        for i, page in enumerate(pages):
            visible_text = _re.sub(r'<[^>]+>', '', page).strip()
            if len(visible_text) < 100 and i > 0 and i < len(pages) - 1:
                issues.append(f"Page {i+1} appears nearly empty ({len(visible_text)} chars)")

        # Check for "Ai" as industry in competitor tables (common bug)
        if '>Ai<' in html:
            extraction = _re.search(r'<div class="fact-label">Industry</div>\s*<div class="fact-value">([^<]+)</div>', html)
            real_industry = extraction.group(1).strip() if extraction else ''
            if real_industry and real_industry != 'Ai':
                html = html.replace('>Ai</td>', f'>{real_industry}</td>')
                issues.append(f"Fixed: competitor industry 'Ai' → '{real_industry}'")

        # LLM audit for deeper issues (only if HTML is reasonable size)
        if len(text_only) < 15000:
            audit_prompt = (
                "You are a professional report formatter. Audit this report text for issues.\n\n"
                f"REPORT TEXT (first 8000 chars):\n{text_only[:8000]}\n\n"
                "Check for:\n"
                "1. Missing data (fields that say 'Unknown' or are blank where data should exist)\n"
                "2. Inconsistencies (e.g., '7 dimensions' when there are 10)\n"
                "3. Garbled text or encoding issues\n"
                "4. Sentences that cut off mid-word\n"
                "5. Duplicate sections\n\n"
                "Return JSON: {\"issues\": [\"issue description\"], \"fixes\": [{\"find\": \"text to find\", \"replace\": \"corrected text\"}]}\n"
                "If no issues found, return: {\"issues\": [], \"fixes\": []}"
            )

            resp = client.chat.completions.create(
                model="claude-opus-4-6",
                messages=[{"role": "user", "content": audit_prompt}],
                max_tokens=1000,
                temperature=0.1,
            )

            audit_text = resp.choices[0].message.content or ""
            audit_text = _re.sub(r'^```(?:json)?\s*\n?', '', audit_text.strip(), flags=_re.IGNORECASE)
            audit_text = _re.sub(r'\n?```\s*$', '', audit_text)

            try:
                import json as _json
                first_brace = audit_text.find('{')
                if first_brace >= 0:
                    audit_result = _json.loads(audit_text[first_brace:])
                    llm_issues = audit_result.get("issues", [])
                    fixes = audit_result.get("fixes", [])

                    for fix in fixes:
                        find_text = fix.get("find", "")
                        replace_text = fix.get("replace", "")
                        if find_text and replace_text and find_text in html:
                            html = html.replace(find_text, replace_text, 1)
                            issues.append(f"LLM fix: '{find_text[:40]}' → '{replace_text[:40]}'")

                    if llm_issues:
                        issues.extend([f"LLM flagged: {i}" for i in llm_issues[:5]])
            except Exception:
                pass

        if issues:
            logger.info(f"[Report Audit] {len(issues)} issues: {'; '.join(issues[:5])}")
        else:
            logger.info("[Report Audit] No issues found")

        return html
    except Exception as e:
        logger.warning(f"[Report Audit] Audit failed (non-fatal): {e}")
        return html


def generate_pdf_report(analysis: Dict[str, Any], narrative: str = '', output_path: Optional[str] = None) -> bytes:
    """Generate PDF from analysis results. Runs LLM audit before rendering."""
    try:
        html = generate_html_report(analysis, narrative)
    except Exception as e:
        logger.error(f"[Report] HTML generation failed: {e}")
        import traceback
        traceback.print_exc()
        company = analysis.get('extraction', {}).get('company', 'Unknown')
        html = f"<html><body><h1>Mirai Report: {company}</h1><p>Report generation error: {e}</p></body></html>"

    # Audit and fix HTML before PDF render
    html = _audit_and_fix_html(html)

    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=html).write_pdf()
        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)
        return pdf_bytes
    except Exception as e:
        logger.error(f"[Report] PDF generation failed: {e}")
        raise
