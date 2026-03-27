# Design System — Mirai PDF Reports

## Product Context
- **What this is:** AI due diligence reports for startup evaluation, generated from a 5-phase pipeline (research, council, swarm, verdict blending, OASIS simulation)
- **Who it's for:** Founders evaluating their own startups, VCs doing preliminary screening, accelerator partners reviewing batches
- **Space/industry:** VC due diligence (PitchBook, CB Insights, Crunchbase, Dealroom, Tracxn)
- **Project type:** PDF report generation (A4, rendered from HTML via Playwright/Chromium)

## Aesthetic Direction
- **Direction:** Industrial/Utilitarian meets Editorial
- **Decoration level:** Intentional (subtle tinted backgrounds for agent cards, gradient score bars)
- **Mood:** Institutional credibility for data sections, editorial warmth for AI agent perspectives. The report should feel like reading a Goldman Sachs research note that suddenly includes the actual partner meeting debate transcript.
- **Two zones:** Data zone (PitchBook-grade tables, stat cards, navy headers) and Intelligence zone (serif italic agent quotes, tinted vote cards, peer review flags). The zones are visually distinct but share the same palette.
- **Reference sites:** PitchBook company profiles, Tracxn company pages

## Typography
- **Display/Hero:** Instrument Serif — serif gravitas for company names and scores without being stuffy. Sets Mirai apart from every sans-serif VC tool.
- **Body:** DM Sans — clean, modern geometric sans. Excellent tabular-nums for financial data alignment. Not overused in this space.
- **UI/Labels:** DM Sans (same as body, weight 600 for labels, weight 500 for values)
- **Data/Tables:** DM Sans with `font-feature-settings: 'tnum'` — numbers align perfectly in columns
- **Agent Voices:** Source Serif 4 italic — editorial serif for persona reasoning. Immediately signals "this is a human voice, not a data field." The key visual differentiator from PitchBook.
- **Code:** JetBrains Mono (if needed for technical sections)
- **Loading:** Google Fonts CDN for preview/web. For PDF generation, Playwright renders with system fonts + Google Fonts loaded via `<link>` tags in the HTML.
- **Scale:** 26pt cover company, 13pt brand, 11pt section headers, 9pt body, 8pt footnotes/dates, 10px stat labels

## Color
- **Approach:** Restrained institutional palette with semantic accents for verdicts and alerts
- **Primary:** #0f2440 — deep midnight navy. Section headers, page headers, cover text. Darker than standard PitchBook (#1a365d) for more authority.
- **Accent:** #2563eb — electric blue. Links, accent labels, brand kanji, interactive elements. More vibrant than muted teal.
- **Neutrals:** warm-cool slate scale:
  - Surface: #f8fafc (barely-there blue-gray, NOT pure white)
  - Surface Alt: #f1f5f9 (alternating table rows)
  - Border: #e2e8f0
  - Muted text: #64748b (slate gray for labels, dates, secondary info)
  - Body text: #0f172a (near-black for readability)
  - Secondary text: #475569 (for table cells, descriptions)
- **Semantic:**
  - HIT green: #059669 — positive verdicts, revenue growth, score bars >=7
  - MISS red: #dc2626 — negative verdicts, losses, score bars <4
  - Amber warning: #d97706 — alerts, cache staleness, OASIS warnings, score bars 4-6.9
  - Info blue: #2563eb (same as accent)
- **Agent card tints:**
  - HIT card: #f0fdf4 background + #059669 left border
  - MISS card: #fef2f2 background + #dc2626 left border
- **Dark mode:** Redesign surfaces (swap #f8fafc to #0f172a), reduce saturation 10-20% on accents. Agent cards: HIT=#052e16, MISS=#450a0a.

## Spacing
- **Base unit:** 4px (PDF is dense, A4 pages need compact spacing)
- **Density:** Compact (data-dense PitchBook style)
- **Scale:** 2xs(2px) xs(4px) sm(6px) md(8px) lg(12px) xl(16px) 2xl(24px) 3xl(32px)
- **Page margins:** 15mm top, 20mm sides, 18mm bottom (A4)
- **Section header margin:** 14px top, 8px bottom
- **Table cell padding:** 8px 12px

## Layout
- **Approach:** Grid-disciplined (strict columns, predictable alignment, PitchBook-grade data density)
- **Grid:** Single column for A4 pages, 2-column KV grids for General Information
- **Max content width:** 210mm (A4)
- **Stat cards:** Flexbox row, equal-width cards
- **Score bars:** Label (180px fixed) + bar (flex:1) + number (32px fixed)
- **Border radius:** None on section headers. 2px on score bar fills. 4px on verdict pills. 0 on tables (sharp, institutional).

## Motion
- **Approach:** N/A for PDF (static document)
- **Web preview:** minimal-functional (hover states only)

## Component Patterns

### Agent Quote Card (THE DIFFERENTIATOR)
```
border-left: 4px solid [green/red by vote]
background: [green-tint/red-tint by vote]
padding: 16px 20px
---
Agent name: DM Sans 13px bold
Meta: DM Sans 11px, vote in bold green/red
Quote: Source Serif 4 italic 13px, line-height 1.55
```

### PitchBook Navy Section Header
```
background: #0f2440
color: #fff
padding: 7px 14px
font: DM Sans 13px weight 600
border-left: 4px solid #2563eb
```

### Warning Banner
```
padding: 10px 16px
background: #fffbeb (amber), #fef2f2 (red), #eff6ff (blue)
border-left: 3px solid [amber/red/blue]
font: DM Sans 12px
```

### Peer Review Flag
```
padding: 8px 12px
background: #fef3c7
border-left: 3px solid #d97706
"Evaluator X flags Evaluator Y:" in bold amber
```

## Decisions Log
| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-27 | Initial design system created | Created by /design-consultation. Industrial + Editorial dual-zone approach. PitchBook credibility for data, editorial serif warmth for AI agent voices. |
| 2026-03-27 | Instrument Serif for display | Gravitas without being stuffy. Every competitor uses sans-serif. Serif on the company name immediately signals premium. |
| 2026-03-27 | Source Serif 4 italic for agents | The key differentiator. Agent reasoning in italic serif on tinted cards feels like reading partner meeting notes, not database output. No competitor has this. |
| 2026-03-27 | DM Sans over Inter/Roboto | Clean geometric sans that isn't overused. Excellent tabular-nums for financial data alignment. |
| 2026-03-27 | Deeper navy #0f2440 | More authoritative than PitchBook's #1a365d. Small change, noticeable difference in perceived quality. |
| 2026-03-27 | Gradient score bars | Red-through-amber-to-green gradient instead of solid fills. A 6.2 looks visually different from 6.8. Precision matters in scoring. |
