# Shinsa (審査) — AI Patent Application Review

**AI-powered patent application analysis for university researchers**

Part of the VCLabs.org platform alongside Mirai (未来) and Sensei (先生).

---

## What Shinsa Does

Researcher uploads their invention description + claims → Shinsa searches global patent databases for prior art, scores patentability across 8 dimensions using a multi-model council, stress-tests claims with a swarm of patent examiner / IP attorney / domain expert personas, and generates a review report in NDSU's patent application format — ready to submit to the university patent office.

## Why This Exists

University researchers spend weeks preparing patent applications without knowing if their invention is actually patentable. The NDSU patent office reviews submissions manually, often bouncing back applications that have obvious prior art conflicts or weak claims. Shinsa catches these issues before submission — saving the researcher time, saving the patent office effort, and improving the quality of applications that reach formal review.

## Pipeline (reuses Mirai infrastructure)

```
Researcher input (invention description + claims)
  │
  ├── Phase 1: Prior Art Search
  │   Dual-model web research (Opus-web + GPT-5.4-web)
  │   → Google Patents, USPTO PatentsView API, Lens.org
  │   → Find similar patents, competing claims, CPC classification
  │
  ├── Phase 2: Patentability Council (4 models × 8 dimensions)
  │   → Novelty, Non-Obviousness, Utility, Enablement,
  │     Written Description, Claim Breadth, Prior Art Risk, Commercial Potential
  │   → Chairman reconciliation on contested dimensions
  │
  ├── Phase 3: Examiner Swarm (25-100 personas)
  │   Patent Examiners (USPTO-style), IP Attorneys, Domain Scientists,
  │   Prior Art Researchers, Technology Transfer Officers, Industry Experts
  │   → Each reviews claims from their unique perspective
  │   → Deliberation committee synthesizes tensions
  │
  ├── Phase 4: Report Generation (NDSU format)
  │   → Opus generates report matching NDSU patent office template
  │   → Prior art table, patentability assessment, claim-by-claim analysis
  │   → Risk flags, suggested claim amendments, examiner objection predictions
  │
  └── Output: PDF in NDSU patent application format
```

## 8-Dimension Patentability Scoring

| Dimension | Weight | What it measures |
|---|---|---|
| novelty | 20% | Is this genuinely new? No identical prior art? |
| non_obviousness | 20% | Would it be obvious to someone skilled in the art? |
| utility | 10% | Does it have a specific, credible, substantial use? |
| enablement | 10% | Could someone reproduce it from the description? |
| written_description | 10% | Does the spec adequately describe the invention? |
| claim_breadth | 10% | Are claims appropriately scoped? (too broad = rejected, too narrow = useless) |
| prior_art_risk | 10% | How close is the nearest prior art? |
| commercial_potential | 10% | Is this worth patenting? Market value, licensing opportunity |

## Examiner Personas (6 zones)

| Zone | Role | What they check |
|---|---|---|
| **USPTO Examiners** | Patent examiners by CPC class | §102 novelty, §103 obviousness, §112 enablement |
| **IP Attorneys** | Patent prosecution specialists | Claim drafting quality, freedom-to-operate, prosecution strategy |
| **Domain Scientists** | Researchers in the same field | Technical accuracy, real-world feasibility, state of the art |
| **Prior Art Researchers** | Search specialists | Missed references, foreign patents, non-patent literature |
| **Tech Transfer Officers** | University TTO staff | Commercial viability, licensing potential, university policy fit |
| **Industry Experts** | Engineers/product managers | Practical value, market need, implementation challenges |

## Data Sources

| Source | Use | API |
|---|---|---|
| Google Patents | Primary prior art search | Web search (Opus-web) |
| USPTO PatentsView | Structured patent data, CPC codes, citations | Free REST API |
| Lens.org | Global patent + scholarly search | Free tier (50/day) |
| EPO Open Patent Services | European patent data | Free (registration) |
| Google Scholar | Non-patent literature (NPL) prior art | Web search |
| NDSU patent database | Past NDSU applications for calibration | Local (if accessible) |

## NDSU Integration

- **Input format**: Matches NDSU's Invention Disclosure Form fields
- **Output format**: PDF matching NDSU patent office review template
- **Fields**: Title, Inventors, Department, Sponsor/Funding, Description of Invention, Novel Aspects, Prior Art Known, Potential Applications, Development Stage, Publications/Disclosures
- **TODO**: Get actual NDSU template from patent office to match exactly

## Technical Implementation

- **WebSocket route**: `/ws/shinsa` on the same FastAPI backend (port 5000)
- **Frontend**: New tab/panel in the dashboard, or separate route at `/shinsa/`
- **Backend**: Reuses `AgenticResearcher` (with patent-specific prompt), `BusinessIntelEngine.predict()` (with patent dimensions), `SwarmPredictor` (with examiner personas)
- **New code**: ~3 files:
  - `subconscious/swarm/services/patent_researcher.py` — prior art search prompt + USPTO API
  - `subconscious/swarm/prompts/patent_scoring.py` — 8 patentability dimensions
  - `subconscious/swarm/services/patent_report.py` — NDSU format report generator
- **Shared code**: council scoring, swarm predictor, persona engine, LLM report generator, research cache

## Roadmap

| Phase | What | Effort |
|---|---|---|
| **v0.1** | Prior art search + basic patentability score (reuse Mirai council) | 1-2 days |
| **v0.2** | Examiner swarm with patent-specific personas | 1 day |
| **v0.3** | NDSU-format PDF report (need template from patent office) | 1 day |
| **v0.4** | USPTO PatentsView API integration for structured patent data | 1 day |
| **v0.5** | Claim-by-claim analysis, suggested amendments, objection predictions | 2 days |
| **v1.0** | Full pipeline, tested with real NDSU applications | 1 week total |

## Example Use Case

**Input:**
```
Title: Camera-Based Algal Bloom Detection Using Convolutional Neural Networks
Inventors: Aditya Goyal (NDSU Computer Science)
Description: A system that uses low-cost cameras mounted on lake buoys to
capture water surface images, processes them through a CNN trained on 50,000+
labeled algal bloom images, and classifies bloom severity in real-time...
```

**Output (Shinsa Review):**
```
Patentability Score: 6.2 / 10 — Potentially Patentable (with amendments)

Novelty: 7/10 — Camera-based detection is known (see US10234567), but the
specific CNN architecture + buoy-mounted deployment is novel.

Non-Obviousness: 5/10 — Risk: Combining existing CNN techniques with existing
buoy-mounted sensors may be considered obvious. Suggest emphasizing the novel
training data pipeline and real-time edge processing.

Prior Art Found:
1. US10234567 — "Automated algal bloom detection" (Xylem, 2020) — uses satellite imagery, not cameras
2. US9876543 — "Water quality monitoring with neural networks" (IBM, 2019) — lab-based, not field-deployed
3. WO2021123456 — "IoT water monitoring system" (LG Sonic) — sensors, not vision

Recommended Claim Amendments:
- Narrow claim 1 to specify "edge-deployed CNN on buoy-mounted camera system"
- Add dependent claim for the training data augmentation method
- Remove claim 4 (too broad — overlaps with US9876543)
```

## Contact

**Aditya Goyal** — NDSU Computer Science
VCLabs.org
