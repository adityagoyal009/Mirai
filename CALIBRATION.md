# Mirai — Calibration & Outcome Tracking

> How to validate that Mirai's scores predict real startup outcomes.
> Updated: 2026-04-04

---

## Current Approach: Live Outcome Tracking

Mirai now has production infrastructure for calibrating scores against reality. Every analysis stores structured results, and outcomes are tracked over time.

### What's Built

| Component | Status | Purpose |
|-----------|--------|---------|
| **AnalysisResult** (Prisma model) | Live | 45 flat queryable columns — council/swarm dimension scores, risk panel findings, OASIS trajectory, research quality |
| **Outcome** (Prisma model) | Live | Company progress: raised_round, revenue_milestone, shut_down, pivoted, acquired, operating, stalled |
| **FollowUp** (Prisma model) | Live | Auto-created at 3/6/12 months after each analysis |
| **Admin outcome API** | Live | `POST /api/admin/submissions/{id}/outcome` |
| **Founder self-reporting** | Live | `POST /api/portal/submissions/{id}/outcome` — dashboard prompts founders to update |
| **Calibration API** | Live | `GET /api/admin/calibration` — score distributions, verdict-outcome correlation, dimension predictive power |

### How It Works

```
Analysis completes
  ↓
AnalysisResult row persisted (council/swarm/risk scores per dimension)
  ↓
3 FollowUp records created (due at 3mo, 6mo, 12mo)
  ↓
Admin dashboard surfaces overdue follow-ups
Founder dashboard prompts "How is [Company] doing?"
  ↓
Outcomes recorded (admin verified or founder self-reported)
  ↓
Calibration API computes:
  - Score distributions by industry/stage
  - Verdict vs actual outcome correlation
  - Which dimensions best predict positive/negative outcomes
  - Percentile ranking for any submission
```

### Calibration Milestones

| Milestone | Sample size | What it enables |
|-----------|------------|-----------------|
| **Sanity check** | 10 analyses + expert review | "Do scores directionally match VC intuition?" |
| **Pattern detection** | 50 analyses + outcomes | "Are higher scores correlated with better outcomes at all?" |
| **Statistical significance** | 200 analyses + outcomes | "Which dimensions are most predictive? Should weights change?" |
| **Publishable calibration** | 500 analyses + outcomes | "Companies scoring 7+ raised 3.2x more often" |

---

## The Bias Problem (Still Real)

### Why historical backtesting is limited

If you feed "Figma" into Mirai in 2026:
1. **Web research finds the outcome** — "Adobe acquired Figma for $20B"
2. **LLMs already know** — Claude/GPT have Figma's outcome in training data
3. **The system isn't predicting** — it's reading the answer

This makes backtesting against known companies unreliable. The live outcome tracking approach avoids this entirely because Mirai evaluates companies **before** outcomes are known.

### What the historical data is good for

The `companies.db` database (231K companies, 22.8K with known outcomes from Crunchbase + YC) is useful for:

- **Score stability testing** — run the same company 3x, check if scores vary by <0.5 points
- **Internal consistency checks** — do council and swarm agree? Does the risk panel contradict council scores?
- **Prompt engineering validation** — does rewording a prompt change the score distribution?

It is NOT useful for measuring predictive accuracy because the LLMs have information leakage.

---

## Outcome Definitions

| Outcome | Type | Definition |
|---------|------|------------|
| Raised round | Positive | Raised seed, Series A, B, etc. |
| Revenue milestone | Positive | Hit meaningful ARR target |
| Acquired | Positive | Company was acquired |
| Operating | Neutral | Still running, no clear signal |
| Pivoted | Neutral | Changed direction significantly |
| Stalled | Negative | No progress, zombie state |
| Shut down | Negative | Company ceased operations |

"Operating" companies should be treated carefully in calibration — they haven't had a definitive outcome yet.

---

## What Calibration Will Answer

Once we have 200+ analyses with tracked outcomes:

1. **Do higher composite scores predict better outcomes?** — The core question. If a 7.0 and a 4.0 have the same outcome distribution, the score means nothing.

2. **Which dimensions are most predictive?** — `council_team_execution_signals` might strongly predict fundraising success while `council_market_timing` might predict nothing. The `/api/admin/calibration` endpoint computes this automatically.

3. **Should the 78/22 council/swarm blend change?** — If swarm scores predict outcomes better than council on certain dimensions, the weights should shift.

4. **Does the risk panel add real signal?** — If `risk_panel_penalty > 0` companies have worse outcomes, the panel is doing its job. If not, it's noise.

5. **Is the 5.0-7.0 mid-range meaningful?** — With enough outcome data, we can check if 5.5 and 6.5 companies have distinguishably different outcomes or if they're just noise within the mid-range.

---

## Historical Datasets (Reference)

Available in `subconscious/swarm/data/companies.db`:

| Source | Count | Outcomes | Limitations |
|--------|-------|----------|-------------|
| yc-oss | 5,690 | Active/Inactive/Acquired/Public | Best labels, but LLMs know YC companies |
| crunchbase-success-fail | 65,095 | Operating/closed/acquired/IPO | No descriptions, stale dates |
| crunchbase-large | 159,894 | Operating/acquired/IPO/closed | 35% have descriptions, data ends 2014 |
| unicorns-2021 | 534 | All unicorn (no failure signal) | Selection bias |

### Academic References

1. Żbikowski & Antosiuk (2021). "A machine learning, bias-free approach for predicting business success using Crunchbase data." Information Processing & Management.
2. RyanFabrick/ML-Startup-Success-Prediction (79% AUC-ROC with XGBoost on structural features)
3. ntdoris/startup-classification (73% AUC-ROC baseline)

---

*The real calibration comes from tracking what happens to the companies we evaluate today — not from backtesting on companies whose outcomes are already known.*
