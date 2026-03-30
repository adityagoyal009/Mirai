# Mirai — Calibration & Backtest Methodology

> How to validate whether the swarm actually predicts startup outcomes better than chance.
> Created: 2026-03-30

---

## The Bias Problem

### Why naive backtesting is useless

If you feed "Figma" into Mirai in 2026:
1. **Web research finds the outcome** — "Adobe acquired Figma for $20B"
2. **LLMs already know** — Claude/GPT have Figma's outcome in training data
3. **The swarm isn't predicting** — it's just reading the answer

This makes any backtest against known companies meaningless unless we control for information leakage.

### Two layers of contamination

| Layer | Source | Problem |
|-------|--------|---------|
| Research bias | Web search, news, Wikipedia | Finds acquisition/IPO/failure directly |
| Training bias | LLM weights (pre-training data) | Models "know" outcomes of famous companies |

---

## Unbiased Calibration Method

### 1. Anonymized Blind Mode

Strip all identifying information. Feed the swarm ONLY structured features:

```json
{
  "name": "Company_4821",
  "industry": "SaaS",
  "market": "B2B Enterprise",
  "founded_year": 2013,
  "location": "San Francisco, CA",
  "funding_total_usd": 2100000,
  "funding_rounds": 2,
  "last_round_type": "Seed",
  "team_size": 8,
  "time_first_to_last_funding_days": 180,
  "has_international_presence": false,
  "category": "Software"
}
```

**No company name. No web research. No product description.**

The swarm evaluates purely on structural signals — which is exactly what early-stage investors often do.

### 2. Use Obscure Companies

The 50K+ Crunchbase dataset contains thousands of companies LLMs likely DON'T know:
- Small startups that raised <$1M and quietly died
- Companies in niche verticals outside tech media coverage
- Companies from 2005-2012 that never made headlines

If Claude doesn't know "Acme Widget Corp, Des Moines, 2011" then training bias doesn't apply.

### 3. Time-Locked Evaluation

For any company, only provide information that existed BEFORE the outcome:
- Founding date, early funding rounds, team size at founding
- Industry and location (static facts)
- NO subsequent events, pivots, acquisitions, or failure news

### 4. Novel Companies (Production)

In production, Mirai evaluates companies that haven't had outcomes yet. Bias only matters for calibration/backtesting, not for actual predictions on new startups.

---

## Calibration Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    Calibration Pipeline                       │
│                                                               │
│  1. Load Dataset     2. Anonymize        3. Run Swarm        │
│  ┌──────────┐       ┌──────────┐       ┌──────────┐         │
│  │ 50K+     │──────>│ Strip    │──────>│ Blind    │         │
│  │ companies│       │ names    │       │ eval     │         │
│  │ w/known  │       │ No web   │       │ Score    │         │
│  │ outcomes │       │ search   │       │ 1-10     │         │
│  └──────────┘       └──────────┘       └──────────┘         │
│       │                                      │               │
│       │         4. Compare                   │               │
│       │         ┌──────────┐                 │               │
│       └────────>│ Swarm    │<────────────────┘               │
│                 │ score vs │                                  │
│                 │ actual   │                                  │
│                 │ outcome  │                                  │
│                 └──────────┘                                  │
│                      │                                        │
│              5. Metrics                                       │
│              ┌──────────┐                                     │
│              │ AUC-ROC  │                                     │
│              │ Recall   │                                     │
│              │ Precision│                                     │
│              │ F1       │                                     │
│              │ Calibr.  │                                     │
│              └──────────┘                                     │
│                                                               │
│  Baseline to beat: 73% AUC-ROC (ML-only, no LLM)            │
│  If swarm < baseline, LLM approach isn't adding value        │
└─────────────────────────────────────────────────────────────┘
```

## Outcome Definitions

From the academic literature (Żbikowski & Antosiuk 2021):

| Outcome | Label | Definition |
|---------|-------|------------|
| Acquired | SUCCESS | Company was acquired |
| IPO | SUCCESS | Company went public |
| Operating | EXCLUDE | Still running, outcome unknown |
| Closed | FAILURE | Company shut down |

**Important:** "Operating" companies must be excluded — they haven't had an outcome yet. Including them biases toward failure (most operating companies haven't been acquired YET).

---

## Datasets

### Primary: Crunchbase 50K+ (RyanFabrick)
- **Repo:** github.com/RyanFabrick/ML-Startup-Success-Prediction
- **Size:** 50,000+ companies, 1990-2015
- **Features:** 22 engineered features (geographic, industry, temporal)
- **Labels:** Success/failure based on Crunchbase status
- **Method:** Bias-free (founding-time info only)
- **Baseline:** 79% AUC-ROC with XGBoost
- **Paper:** Żbikowski & Antosiuk (2021)

### Secondary: Startup Classification (ntdoris)
- **Repo:** github.com/ntdoris/startup-classification
- **Size:** Crunchbase data, companies 1902-2014
- **Source:** Kaggle Crunchbase dataset (included in repo `data/` folder)
- **Baseline:** 80% recall, 73% AUC-ROC
- **Key features:** funding_total_usd, founded_year, time_first_to_last_funding, international

### Tertiary: Startup Success Prediction (sumitjhaleriya)
- **Repo:** github.com/sumitjhaleriya/Startup-Success-Prediction-using-Machine-Learning
- **Size:** Several thousand companies
- **Source:** Crunchbase via Kaggle
- **Features:** Funding, location, industry, team size

### Also: Mirai's Existing Database
- **Location:** Mirai's SQLite DB
- **Size:** 231K companies, 22.8K with known outcomes
- **Can cross-reference** with above datasets to expand labeled set

---

## Implementation Plan

### Phase 1: Build Calibration Mode
1. Clone datasets, extract CSV/data files
2. Build anonymizer: strips names, URLs, descriptions — keeps only structural features
3. Add `--calibration` flag to Mirai pipeline that:
   - Disables web research (Phase 1)
   - Disables fact checking
   - Uses anonymized company profiles
   - Runs council + swarm on structural features only
4. Collect swarm scores for N companies (start with 100, scale to 1000)

### Phase 2: Measure Performance
1. Compare swarm scores vs actual outcomes (success/failure)
2. Calculate AUC-ROC, precision, recall, F1
3. Compare against ML baselines (79% AUC from RyanFabrick, 73% from ntdoris)
4. Identify which persona types/models are most predictive

### Phase 3: Calibration Flywheel
1. Feed results back: "personas of type X overpredict success in SaaS"
2. Adjust persona weights in production
3. Track accuracy over time as more outcomes become known
4. Re-run calibration quarterly

---

## Key Question to Answer

**Does the LLM swarm add predictive value over basic ML features?**

- If swarm AUC > 79% (RyanFabrick baseline): YES, LLMs add value. Ship it.
- If swarm AUC ≈ 79%: Maybe. LLMs add qualitative insights but not predictive accuracy.
- If swarm AUC < 73% (ntdoris baseline): NO. The swarm is worse than logistic regression on 5 features. Rethink the approach.

The honest answer matters more than a flattering one.

---

## References

1. Żbikowski, K., & Antosiuk, P. (2021). "A machine learning, bias-free approach for predicting business success using Crunchbase data." Information Processing & Management.
2. RyanFabrick/ML-Startup-Success-Prediction — github.com/RyanFabrick/ML-Startup-Success-Prediction
3. ntdoris/startup-classification — github.com/ntdoris/startup-classification
4. sumitjhaleriya/Startup-Success-Prediction — github.com/sumitjhaleriya/Startup-Success-Prediction-using-Machine-Learning
5. yogeshwaran-shanmuganathan/Success-Prediction-Analysis-for-Startups — github.com/yogeshwaran-shanmuganathan/Success-Prediction-Analysis-for-Startups
6. RamkishanPanthena/Startup-Success-Prediction — github.com/RamkishanPanthena/Startup-Success-Prediction

---

*The calibration question is existential: if we can't beat a basic XGBoost model, the swarm is theater, not intelligence.*
