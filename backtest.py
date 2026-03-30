#!/usr/bin/env python3
"""
Mirai Backtest — Run predictions against companies with known outcomes.

Usage:
    python3 backtest.py                  # Run Tier 1 (30 companies)
    python3 backtest.py --tier 2         # Run Tier 2 (30 more)
    python3 backtest.py --tier all       # Run all 100
    python3 backtest.py --resume         # Resume from last checkpoint
    python3 backtest.py --report         # Just print results from saved data
    python3 backtest.py --compare        # Compare last two runs

Results saved to:
  - backtest_results.json              (auto-checkpointed after each company)
  - ~/.mirai/backtest/run_{timestamp}.json  (archived per-run with full metadata)
"""

import json
import time
import sys
import os
import subprocess
import glob as glob_mod
from datetime import datetime
from typing import Dict, List, Any, Optional

import requests

# ── Prompt registry integration ──────────────────────────────────
try:
    from subconscious.swarm.utils.prompt_registry import get_all_hashes, get_snapshot
except ImportError:
    def get_all_hashes(): return {}
    def get_snapshot(): return {}

API_BASE = "http://localhost:5000"
DB_PATH = os.path.join(os.path.dirname(__file__), "subconscious/swarm/data/companies.db")
RESULTS_FILE = os.path.join(os.path.dirname(__file__), "backtest_results.json")
BACKTEST_ARCHIVE_DIR = os.path.join(os.path.expanduser("~"), ".mirai", "backtest")

# ── Scoring thresholds ───────────────────────────────────────────
SUCCESS_THRESHOLD = 6.0   # Scores >= this count as "predicted success"
FAILURE_THRESHOLD = 5.5   # Scores < this count as "predicted failure"

# ── Persona zones (must match persona_engine.py ZONE_ROLES keys) ─
ALL_ZONES = ["investor", "customer", "operator", "analyst", "contrarian", "wildcard"]

# ── Scoring dimensions from the BI pipeline ──────────────────────
SCORING_DIMENSIONS = [
    "market_timing", "competition_landscape", "business_model_viability",
    "team_execution_signals", "regulatory_news_environment",
    "product_differentiation", "financial_sustainability",
]

# ── Tier 1: Must-Test (30) — Famous outcomes, maximum signal ──

TIER1_SUCCESSES = [
    {"name": "Airbnb", "one_liner": "Online marketplace for short-term home rentals", "industry": "Consumer/Travel", "stage": "MVP", "business_model": "Commission on bookings (3% host, up to 14.2% guest)", "target_market": "Travelers seeking alternatives to hotels, homeowners with spare space", "expected": "success", "actual_outcome": "IPO — $75B+ market cap"},
    {"name": "Dropbox", "one_liner": "Backup and share files in the cloud", "industry": "B2B/Cloud Storage", "stage": "MVP", "business_model": "Freemium SaaS — free tier + $10/mo pro", "target_market": "Individual users and businesses needing file sync across devices", "expected": "success", "actual_outcome": "IPO — $10B+ market cap"},
    {"name": "Coinbase", "one_liner": "Buy, sell, and manage cryptocurrencies", "industry": "Fintech/Crypto", "stage": "MVP", "business_model": "Transaction fees on crypto trades", "target_market": "Retail and institutional crypto investors", "expected": "success", "actual_outcome": "IPO — $50B+ peak market cap"},
    {"name": "DoorDash", "one_liner": "Restaurant delivery platform", "industry": "Consumer/Food Delivery", "stage": "MVP", "business_model": "Commission on restaurant orders + delivery fees + DashPass subscription", "target_market": "Consumers ordering food delivery, restaurants wanting delivery reach", "expected": "success", "actual_outcome": "IPO — $50B+ peak market cap"},
    {"name": "Instacart", "one_liner": "Marketplace for grocery delivery and pickup", "industry": "Consumer/Grocery", "stage": "MVP", "business_model": "Delivery fees + service fees + Instacart+ subscription + advertising", "target_market": "Consumers who want groceries delivered from local stores", "expected": "success", "actual_outcome": "IPO — $10B+ market cap"},
    {"name": "GitLab", "one_liner": "A complete DevOps platform delivered as a single application", "industry": "B2B/Developer Tools", "stage": "Revenue", "business_model": "Open core SaaS — free tier + Premium $29/user/mo + Ultimate $99/user/mo", "target_market": "Software development teams needing integrated CI/CD, source control, and security", "expected": "success", "actual_outcome": "IPO — $15B+ peak market cap"},
    {"name": "Brex", "one_liner": "Business accounts, corporate cards, and spend management", "industry": "Fintech", "stage": "Revenue", "business_model": "Interchange fees on card transactions + SaaS subscription for spend management", "target_market": "Startups and growth-stage companies needing corporate cards without personal guarantees", "expected": "success", "actual_outcome": "$12B+ valuation"},
    {"name": "Deel", "one_liner": "All-in-one HR and payroll platform for global teams", "industry": "B2B/HR Tech", "stage": "Revenue", "business_model": "SaaS — per-contractor and per-employee fees for global payroll and compliance", "target_market": "Companies hiring remote workers internationally", "expected": "success", "actual_outcome": "$12B+ valuation"},
    {"name": "Rippling", "one_liner": "One place to run all your HR, IT, and Finance globally", "industry": "B2B/HR Tech", "stage": "Revenue", "business_model": "SaaS — per-employee pricing for unified HR, IT, and finance platform", "target_market": "Mid-market and enterprise companies wanting unified employee management", "expected": "success", "actual_outcome": "$13B+ valuation"},
    {"name": "Faire", "one_liner": "Online wholesale marketplace empowering independent retail", "industry": "B2B/Marketplace", "stage": "Revenue", "business_model": "Commission on wholesale orders between brands and retailers", "target_market": "Independent retailers sourcing products and brands seeking distribution", "expected": "success", "actual_outcome": "$12B+ valuation"},
    {"name": "PagerDuty", "one_liner": "Real-time visibility into critical apps and services", "industry": "B2B/DevOps", "stage": "Revenue", "business_model": "SaaS — tiered pricing for incident management and on-call scheduling", "target_market": "Engineering and IT operations teams managing service reliability", "expected": "success", "actual_outcome": "IPO"},
    {"name": "Razorpay", "one_liner": "Full-stack financial solutions for businesses in India", "industry": "Fintech", "stage": "Revenue", "business_model": "Transaction fees on payment processing (2% per transaction)", "target_market": "Indian businesses needing online payment acceptance", "expected": "success", "actual_outcome": "$7.5B valuation"},
    {"name": "Groww", "one_liner": "Making financial services simple, transparent and delightful", "industry": "Fintech", "stage": "Revenue", "business_model": "Brokerage fees on stock/mutual fund trades", "target_market": "Indian retail investors seeking simple investment platform", "expected": "success", "actual_outcome": "IPO"},
    {"name": "Vercel", "one_liner": "Frontend cloud platform — deploy web apps instantly", "industry": "B2B/Developer Tools", "stage": "Revenue", "business_model": "Freemium — free tier + Pro $20/user/mo + Enterprise custom", "target_market": "Frontend developers and teams deploying Next.js and web applications", "expected": "success", "actual_outcome": "$2.5B+ valuation"},
    {"name": "Amplitude", "one_liner": "Digital analytics platform for product teams", "industry": "B2B/Analytics", "stage": "Revenue", "business_model": "SaaS — usage-based pricing for product analytics", "target_market": "Product and growth teams at digital companies", "expected": "success", "actual_outcome": "IPO"},
]

TIER1_FAILURES = [
    {"name": "Moxion Power", "one_liner": "Mobile energy storage technology — battery-electric alternatives to diesel generators", "industry": "CleanTech/Energy Storage", "stage": "MVP", "business_model": "Hardware sales + rental of mobile battery units to construction and events", "target_market": "Construction sites, outdoor events, film sets needing temporary power", "expected": "failure", "actual_outcome": "Failed — YC top company, shut down"},
    {"name": "Lantern", "one_liner": "Postgres vector database extension to build AI applications", "industry": "B2B/Database", "stage": "MVP", "business_model": "Open source with managed cloud service", "target_market": "Developers building AI apps who already use Postgres", "expected": "failure", "actual_outcome": "Failed — YC W24"},
    {"name": "RadMate AI", "one_liner": "Copilot for radiologists — AI-assisted medical image reading", "industry": "Healthcare/AI", "stage": "MVP", "business_model": "SaaS per-radiologist seat license", "target_market": "Radiology practices and hospital imaging departments", "expected": "failure", "actual_outcome": "Failed — YC W24"},
    {"name": "BiteSight", "one_liner": "Video-first food delivery app — TikTok meets DoorDash", "industry": "Consumer/Food Delivery", "stage": "Idea", "business_model": "Commission on food orders placed through video content", "target_market": "Gen Z consumers who discover restaurants through short-form video", "expected": "failure", "actual_outcome": "Failed — YC W24"},
    {"name": "Lumona", "one_liner": "AI-enabled search engine featuring insights from social media", "industry": "Consumer/Search", "stage": "MVP", "business_model": "Freemium search with premium insights subscription", "target_market": "Consumers wanting search results enriched with social media perspectives", "expected": "failure", "actual_outcome": "Failed — YC W24"},
    {"name": "Parabolic", "one_liner": "AI assistant for customer support teams", "industry": "B2B/Customer Support", "stage": "MVP", "business_model": "SaaS per-agent pricing", "target_market": "Customer support teams looking to automate ticket responses", "expected": "failure", "actual_outcome": "Failed — YC W23"},
    {"name": "crmCopilot", "one_liner": "Give Salesforce the AI upgrade it deserves", "industry": "B2B/CRM", "stage": "MVP", "business_model": "SaaS add-on to Salesforce — per-user pricing", "target_market": "Salesforce users wanting AI-powered CRM automation", "expected": "failure", "actual_outcome": "Failed — YC W24"},
    {"name": "Toolify", "one_liner": "Build internal tools with AI — describe what you need, get a working app", "industry": "B2B/No-Code", "stage": "MVP", "business_model": "SaaS — freemium with paid tiers for team usage", "target_market": "Non-technical teams needing internal tools without developer resources", "expected": "failure", "actual_outcome": "Failed — YC W24"},
    {"name": "Celest", "one_liner": "The Vercel of Flutter — deploy Flutter apps to the cloud instantly", "industry": "B2B/Developer Tools", "stage": "MVP", "business_model": "Freemium cloud hosting — free tier + usage-based pricing", "target_market": "Flutter developers wanting serverless backend deployment", "expected": "failure", "actual_outcome": "Failed — YC W24"},
    {"name": "Fileforge", "one_liner": "API for PDF document workflows — generate, merge, sign PDFs programmatically", "industry": "B2B/Developer Tools", "stage": "MVP", "business_model": "Usage-based API pricing — per-document processed", "target_market": "Developers needing programmatic PDF generation and manipulation", "expected": "failure", "actual_outcome": "Failed — YC W24"},
    {"name": "Sublingual", "one_liner": "Daily productivity tracker for individuals and teams", "industry": "B2B/Productivity", "stage": "MVP", "business_model": "SaaS subscription — $10/mo individual, $25/user/mo team", "target_market": "Knowledge workers and remote teams tracking daily output", "expected": "failure", "actual_outcome": "Failed — YC W25"},
    {"name": "Lavo Life Sciences", "one_liner": "AI for drug formulation — predict optimal drug delivery mechanisms", "industry": "Healthcare/Pharma", "stage": "MVP", "business_model": "Enterprise SaaS for pharmaceutical companies", "target_market": "Pharmaceutical R&D teams working on drug formulation", "expected": "failure", "actual_outcome": "Failed — YC W23"},
    {"name": "Rubber Ducky Labs", "one_liner": "AI-powered product discovery for e-commerce", "industry": "B2B/E-commerce", "stage": "MVP", "business_model": "SaaS for e-commerce retailers — usage-based pricing", "target_market": "E-commerce merchants wanting AI-powered product recommendations", "expected": "failure", "actual_outcome": "Failed — YC W23"},
    {"name": "Struct", "one_liner": "Multi-lingual AI voice agents for customer service", "industry": "B2B/AI", "stage": "MVP", "business_model": "Per-minute pricing for AI voice agent calls", "target_market": "Companies needing multilingual phone-based customer support", "expected": "failure", "actual_outcome": "Failed — YC W23"},
    {"name": "Blyss", "one_liner": "End-to-end encrypted AI — run AI models on encrypted data", "industry": "B2B/Security", "stage": "MVP", "business_model": "Enterprise SaaS for privacy-preserving AI inference", "target_market": "Enterprises needing AI on sensitive data without exposure", "expected": "failure", "actual_outcome": "Failed — YC W23"},
]

# ── Tier 2: Nuanced Cases (30) ──

TIER2_ACQUISITIONS = [
    {"name": "Cruise Automation", "one_liner": "Self-driving car technology for autonomous ride-hailing", "industry": "Auto/Autonomous Vehicles", "stage": "MVP", "business_model": "Autonomous ride-hailing fleet operations", "target_market": "Urban commuters in dense cities", "expected": "acquired", "actual_outcome": "Acquired by GM for $1B+"},
    {"name": "Bear Flag Robotics", "one_liner": "Autonomous driving technology for farm tractors", "industry": "AgTech/Robotics", "stage": "MVP", "business_model": "Retrofit kit for existing tractors + autonomous operation service", "target_market": "Large-scale farms needing autonomous tractor operation", "expected": "acquired", "actual_outcome": "Acquired by John Deere for $250M"},
    {"name": "Paystack", "one_liner": "Modern payments infrastructure for Africa", "industry": "Fintech", "stage": "Revenue", "business_model": "Transaction fees on payment processing (1.5% + flat fee)", "target_market": "African businesses needing online and offline payment acceptance", "expected": "acquired", "actual_outcome": "Acquired by Stripe for $200M+"},
    {"name": "Truebill", "one_liner": "App to manage subscriptions, lower bills, and track spending", "industry": "Fintech/Consumer", "stage": "Revenue", "business_model": "Freemium — free tracking + premium $12/mo for bill negotiation", "target_market": "Consumers wanting to cancel unwanted subscriptions and lower bills", "expected": "acquired", "actual_outcome": "Acquired by Rocket Companies for $1.3B"},
    {"name": "Sqreen", "one_liner": "Application security platform for the modern enterprise", "industry": "B2B/Security", "stage": "Revenue", "business_model": "SaaS — per-app pricing for runtime application security", "target_market": "Engineering teams needing in-app security monitoring", "expected": "acquired", "actual_outcome": "Acquired by Datadog"},
]

TIER2_UNCERTAIN = [
    {"name": "Whatnot", "one_liner": "Largest livestream shopping platform in the US", "industry": "Consumer/E-commerce", "stage": "Revenue", "business_model": "Commission on livestream sales (typically 8%)", "target_market": "Collectors, hobbyists, and sellers of cards, collectibles, fashion", "expected": "uncertain", "actual_outcome": "Active — $3.7B valuation but US livestream commerce adoption unclear"},
    {"name": "Zepto", "one_liner": "10-minute grocery delivery in India", "industry": "Consumer/Grocery", "stage": "Revenue", "business_model": "Delivery fees + product margins on quick-commerce grocery", "target_market": "Urban Indian consumers wanting near-instant grocery delivery", "expected": "uncertain", "actual_outcome": "Active — $5B valuation but massive burn rate, unit economics questioned"},
    {"name": "Ginkgo Bioworks", "one_liner": "Making biology easier to engineer — cell programming platform", "industry": "Healthcare/Biotech", "stage": "Revenue", "business_model": "Platform fees for cell engineering + royalties on downstream products", "target_market": "Companies in pharma, agriculture, and industrial bio needing organism engineering", "expected": "uncertain", "actual_outcome": "Public via SPAC — stock down 95% from peak, revenue struggles"},
    {"name": "Rigetti Computing", "one_liner": "Quantum coherent supercomputing — full-stack quantum computing", "industry": "DeepTech/Quantum", "stage": "MVP", "business_model": "Quantum computing as a service via cloud API", "target_market": "Researchers and enterprises needing quantum computation", "expected": "uncertain", "actual_outcome": "Public via SPAC — pre-revenue for years, speculative"},
    {"name": "Momentus", "one_liner": "Space infrastructure services — in-space transportation", "industry": "Space/Industrials", "stage": "MVP", "business_model": "Fees for satellite deployment and repositioning services", "target_market": "Satellite operators needing last-mile orbital delivery", "expected": "uncertain", "actual_outcome": "Public via SPAC — stock cratered, regulatory issues"},
]

ALL_COMPANIES = {
    "tier1": TIER1_SUCCESSES + TIER1_FAILURES,
    "tier2": TIER2_ACQUISITIONS + TIER2_UNCERTAIN,
}


# ══════════════════════════════════════════════════════════════════
# Per-run metadata
# ══════════════════════════════════════════════════════════════════

def _get_git_commit() -> str:
    """Get short git commit hash, or 'unknown' if not in a repo."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=os.path.dirname(__file__),
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except Exception:
        return "unknown"


def _build_run_metadata() -> Dict[str, Any]:
    """Build metadata dict for this backtest run."""
    return {
        "timestamp": datetime.now().isoformat(),
        "git_commit": _get_git_commit(),
        "prompt_hashes": get_all_hashes(),
        "prompt_snapshot": get_snapshot(),
    }


# ══════════════════════════════════════════════════════════════════
# Enhanced per-company result builder
# ══════════════════════════════════════════════════════════════════

def _is_correct(expected: str, score: Optional[float]) -> bool:
    """Determine if prediction matches expected outcome."""
    if score is None:
        return False
    if expected == "success":
        return score >= SUCCESS_THRESHOLD
    elif expected == "failure":
        return score < FAILURE_THRESHOLD
    elif expected == "acquired":
        # Acquisitions are a success signal — score should be moderate-to-high
        return score >= 5.0
    else:
        # "uncertain" — we skip these for accuracy calculations
        return True


def run_analysis(company: dict, depth: str = "quick", swarm_count: int = 25) -> dict:
    """Run Mirai analysis on a single company."""
    exec_summary = (
        f"Company name: {company['name']}\n"
        f"Industry: {company['industry']}\n"
        f"Product/Service: {company['one_liner']}\n"
        f"Target market: {company.get('target_market', 'Not specified')}\n"
        f"Business model: {company.get('business_model', 'Not specified')}\n"
        f"Stage: {company.get('stage', 'MVP')}\n"
    )

    try:
        resp = requests.post(
            f"{API_BASE}/api/bi/analyze",
            json={
                "exec_summary": exec_summary,
                "depth": depth,
                "swarm_count": swarm_count,
            },
            timeout=600,
        )
        data = resp.json()

        # Response nests under "analysis" key
        analysis = data.get("analysis", data)
        prediction = analysis.get("prediction", {})
        research = analysis.get("research", {})
        swarm = analysis.get("swarm", analysis.get("swarm_result", {}))

        score = prediction.get("overall_score", prediction.get("composite_score", 0))
        verdict = prediction.get("verdict", "unknown")

        # Extract per-dimension scores
        dimension_scores = {}
        for dim in prediction.get("dimensions", []):
            if isinstance(dim, dict):
                dim_name = dim.get("name", "")
                dim_score = dim.get("score", 0)
                dimension_scores[dim_name] = dim_score

        # Extract swarm zone data from divergence
        divergence = swarm.get("divergence", {})
        zone_agreement = divergence.get("zone_agreement", {}) if isinstance(divergence, dict) else {}

        # Build per-zone accuracy tracking from swarm agent data
        zone_accuracy = {}
        sample_agents = swarm.get("sample_agents", [])
        if sample_agents:
            from collections import defaultdict
            zone_votes = defaultdict(lambda: {"hit": 0, "miss": 0})
            for agent in sample_agents:
                z = agent.get("zone", "wildcard")
                if agent.get("overall", 5) >= 5.5:
                    zone_votes[z]["hit"] += 1
                else:
                    zone_votes[z]["miss"] += 1
            for z, votes in zone_votes.items():
                total = votes["hit"] + votes["miss"]
                zone_majority_hit = votes["hit"] >= votes["miss"]
                actual_is_positive = company["expected"] in ("success", "acquired")
                zone_accuracy[z] = (zone_majority_hit == actual_is_positive)
        elif zone_agreement:
            # Fall back to divergence zone_agreement data
            for z, zdata in zone_agreement.items():
                if isinstance(zdata, dict) and zdata.get("total", 0) > 0:
                    zone_majority_hit = zdata.get("majority_direction") == "HIT"
                    actual_is_positive = company["expected"] in ("success", "acquired")
                    zone_accuracy[z] = (zone_majority_hit == actual_is_positive)

        # Extract models used
        models_used = swarm.get("models_used", [])

        correct = _is_correct(company["expected"], score)

        return {
            "company": company["name"],
            "expected": company["expected"],
            "actual_outcome": company["actual_outcome"],
            "score": score,
            "verdict": verdict,
            "correct": correct,
            "confidence": prediction.get("confidence", 0),
            "dimension_scores": dimension_scores,
            "contested": prediction.get("council", {}).get("contested_dimensions", []),
            "swarm_stats": {
                "positive_pct": swarm.get("positive_pct", None),
                "total_agents": swarm.get("total_agents", 0),
                "zone_accuracy": zone_accuracy,
                "models_used": models_used,
            },
            "research_sources": research.get("sources_count", len(research.get("cited_facts", []))),
            "data_quality": analysis.get("data_quality", 0),
            "timestamp": datetime.now().isoformat(),
            "error": None,
        }
    except Exception as e:
        return {
            "company": company["name"],
            "expected": company["expected"],
            "actual_outcome": company["actual_outcome"],
            "score": None,
            "verdict": "error",
            "correct": False,
            "dimension_scores": {},
            "swarm_stats": {},
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# ══════════════════════════════════════════════════════════════════
# Summary statistics
# ══════════════════════════════════════════════════════════════════

def compute_summary_statistics(results: List[Dict]) -> Dict[str, Any]:
    """
    Compute comprehensive summary statistics from backtest results.

    Returns overall accuracy, false positive/negative rates,
    per-dimension accuracy, per-zone accuracy, and deliberation impact.
    """
    valid = [r for r in results if r.get("score") is not None and r.get("expected") in ("success", "failure")]
    if not valid:
        return {"error": "No valid success/failure results to compute statistics"}

    total = len(valid)
    correct = sum(1 for r in valid if r.get("correct", False))
    overall_accuracy = round(correct / total, 3) if total > 0 else 0

    # False positive rate: predicted success but actually failed
    actual_failures = [r for r in valid if r["expected"] == "failure"]
    false_positives = sum(1 for r in actual_failures if r.get("score", 0) >= SUCCESS_THRESHOLD)
    fp_rate = round(false_positives / len(actual_failures), 3) if actual_failures else 0

    # False negative rate: predicted failure but actually succeeded
    actual_successes = [r for r in valid if r["expected"] == "success"]
    false_negatives = sum(1 for r in actual_successes if r.get("score", 0) < FAILURE_THRESHOLD)
    fn_rate = round(false_negatives / len(actual_successes), 3) if actual_successes else 0

    # Per-dimension accuracy: for each dimension, check if that dimension's
    # score alone would have correctly predicted the outcome
    per_dimension_accuracy = {}
    for dim in SCORING_DIMENSIONS:
        dim_valid = [r for r in valid if dim in r.get("dimension_scores", {})]
        if not dim_valid:
            continue
        dim_correct = 0
        for r in dim_valid:
            dim_score = r["dimension_scores"][dim]
            predicted_positive = dim_score >= 5.5
            actual_positive = r["expected"] == "success"
            if predicted_positive == actual_positive:
                dim_correct += 1
        per_dimension_accuracy[dim] = round(dim_correct / len(dim_valid), 3)

    # Also check swarm avg_scores dimensions (market, team, product, timing)
    for swarm_dim in ["market", "team", "product", "timing"]:
        dim_key = f"swarm_{swarm_dim}"
        # These come from swarm_stats if available
        # Skip if already computed from BI dimensions
        if dim_key in per_dimension_accuracy:
            continue

    # Per-zone accuracy: for each persona zone, how often did that zone's
    # majority vote match the actual outcome?
    zone_correct = {}
    zone_total = {}
    for r in valid:
        zone_acc = r.get("swarm_stats", {}).get("zone_accuracy", {})
        for zone, was_correct in zone_acc.items():
            zone_total[zone] = zone_total.get(zone, 0) + 1
            if was_correct:
                zone_correct[zone] = zone_correct.get(zone, 0) + 1

    per_zone_accuracy = {}
    for zone in zone_total:
        per_zone_accuracy[zone] = round(
            zone_correct.get(zone, 0) / zone_total[zone], 3
        )

    # Per-model accuracy: track which LLM models are most accurate
    model_correct = {}
    model_total = {}
    for r in valid:
        models = r.get("swarm_stats", {}).get("models_used", [])
        for model in models:
            model_total[model] = model_total.get(model, 0) + 1
            if r.get("correct", False):
                model_correct[model] = model_correct.get(model, 0) + 1
    per_model_accuracy = {}
    for model in model_total:
        per_model_accuracy[model] = round(
            model_correct.get(model, 0) / model_total[model], 3
        )

    # Deliberation impact placeholder: compare weighted vs unweighted
    # (weighted accuracy uses swarm positive_pct which includes deliberation weights)
    weighted_correct = 0
    unweighted_correct = 0
    delib_count = 0
    for r in valid:
        swarm_pct = r.get("swarm_stats", {}).get("positive_pct")
        if swarm_pct is not None:
            delib_count += 1
            swarm_positive = swarm_pct >= 55
            actual_positive = r["expected"] == "success"
            if swarm_positive == actual_positive:
                weighted_correct += 1
            # Unweighted: just use the raw score threshold
            raw_positive = r.get("score", 0) >= SUCCESS_THRESHOLD
            if raw_positive == actual_positive:
                unweighted_correct += 1

    deliberation_impact = {}
    if delib_count > 0:
        deliberation_impact = {
            "weighted_accuracy": round(weighted_correct / delib_count, 3),
            "unweighted_accuracy": round(unweighted_correct / delib_count, 3),
            "sample_size": delib_count,
        }

    return {
        "overall_accuracy": overall_accuracy,
        "total_evaluated": total,
        "correct": correct,
        "wrong": total - correct,
        "false_positive_rate": fp_rate,
        "false_negative_rate": fn_rate,
        "per_dimension_accuracy": per_dimension_accuracy,
        "per_zone_accuracy": per_zone_accuracy,
        "per_model_accuracy": per_model_accuracy,
        "deliberation_impact": deliberation_impact,
    }


# ══════════════════════════════════════════════════════════════════
# Persistence: save results to ~/.mirai/backtest/
# ══════════════════════════════════════════════════════════════════

def load_results() -> list:
    """Load existing results from checkpoint file."""
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE) as f:
            return json.load(f)
    return []


def save_results(results: list):
    """Save results to checkpoint file."""
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)


def save_run_archive(results: List[Dict], summary: Dict[str, Any]) -> str:
    """
    Save a complete run to ~/.mirai/backtest/run_{timestamp}.json.
    Returns the path to the saved file.
    """
    os.makedirs(BACKTEST_ARCHIVE_DIR, exist_ok=True)

    run_data = {
        **_build_run_metadata(),
        "results": results,
        "summary": summary,
    }

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(BACKTEST_ARCHIVE_DIR, f"run_{ts}.json")
    with open(filepath, "w") as f:
        json.dump(run_data, f, indent=2, default=str)

    return filepath


def load_previous_runs(max_runs: int = 10) -> List[Dict]:
    """Load previous run archives, sorted newest first."""
    pattern = os.path.join(BACKTEST_ARCHIVE_DIR, "run_*.json")
    files = sorted(glob_mod.glob(pattern), reverse=True)
    runs = []
    for fpath in files[:max_runs]:
        try:
            with open(fpath) as f:
                run = json.load(f)
                run["_filepath"] = fpath
                runs.append(run)
        except (json.JSONDecodeError, IOError):
            continue
    return runs


# ══════════════════════════════════════════════════════════════════
# Comparison mode
# ══════════════════════════════════════════════════════════════════

def print_comparison(current_summary: Optional[Dict] = None):
    """
    Compare the last two runs and print a diff.
    If current_summary is provided, compare it against the most recent archived run.
    """
    runs = load_previous_runs(max_runs=5)

    if current_summary and runs:
        new_summary = current_summary
        old_summary = runs[0].get("summary", {})
        old_label = os.path.basename(runs[0].get("_filepath", "previous"))
        new_label = "current run"

        # Check for prompt version changes
        old_hashes = runs[0].get("prompt_hashes", {})
        new_hashes = get_all_hashes()
        _print_prompt_diff(old_hashes, new_hashes)
    elif len(runs) >= 2:
        new_summary = runs[0].get("summary", {})
        old_summary = runs[1].get("summary", {})
        new_label = os.path.basename(runs[0].get("_filepath", "newer"))
        old_label = os.path.basename(runs[1].get("_filepath", "older"))

        old_hashes = runs[1].get("prompt_hashes", {})
        new_hashes = runs[0].get("prompt_hashes", {})
        _print_prompt_diff(old_hashes, new_hashes)
    else:
        print("\n  No previous runs to compare. Run at least two backtests first.")
        return

    print(f"\n  COMPARISON: {old_label} -> {new_label}")
    print("  " + "-" * 60)

    # Overall accuracy
    old_acc = old_summary.get("overall_accuracy", 0)
    new_acc = new_summary.get("overall_accuracy", 0)
    delta = new_acc - old_acc
    sign = "+" if delta >= 0 else ""
    print(f"  Accuracy: {old_acc*100:.0f}% -> {new_acc*100:.0f}% ({sign}{delta*100:.0f}%)")

    # False positive / negative rates
    old_fp = old_summary.get("false_positive_rate", 0)
    new_fp = new_summary.get("false_positive_rate", 0)
    delta_fp = new_fp - old_fp
    sign_fp = "+" if delta_fp >= 0 else ""
    print(f"  False positive rate: {old_fp*100:.0f}% -> {new_fp*100:.0f}% ({sign_fp}{delta_fp*100:.0f}%)")

    old_fn = old_summary.get("false_negative_rate", 0)
    new_fn = new_summary.get("false_negative_rate", 0)
    delta_fn = new_fn - old_fn
    sign_fn = "+" if delta_fn >= 0 else ""
    print(f"  False negative rate: {old_fn*100:.0f}% -> {new_fn*100:.0f}% ({sign_fn}{delta_fn*100:.0f}%)")

    # Best/worst dimensions
    dim_acc = new_summary.get("per_dimension_accuracy", {})
    if dim_acc:
        best_dim = max(dim_acc, key=dim_acc.get)
        worst_dim = min(dim_acc, key=dim_acc.get)
        print(f"  Best dimension: {best_dim} ({dim_acc[best_dim]*100:.0f}%)")
        print(f"  Worst dimension: {worst_dim} ({dim_acc[worst_dim]*100:.0f}%)")

    # Per-zone accuracy
    zone_acc = new_summary.get("per_zone_accuracy", {})
    if zone_acc:
        best_zone = max(zone_acc, key=zone_acc.get)
        worst_zone = min(zone_acc, key=zone_acc.get)
        print(f"  Most accurate zone: {best_zone} ({zone_acc[best_zone]*100:.0f}%)")
        if best_zone != worst_zone:
            print(f"  Least accurate zone: {worst_zone} ({zone_acc[worst_zone]*100:.0f}%)")

    # Deliberation impact
    delib = new_summary.get("deliberation_impact", {})
    if delib:
        print(f"  Deliberation impact: weighted={delib.get('weighted_accuracy', 0)*100:.0f}% "
              f"vs unweighted={delib.get('unweighted_accuracy', 0)*100:.0f}%")

    print()


def _print_prompt_diff(old_hashes: Dict[str, str], new_hashes: Dict[str, str]):
    """Print which prompts changed between runs."""
    if not old_hashes and not new_hashes:
        return

    changed = []
    for name in set(list(old_hashes.keys()) + list(new_hashes.keys())):
        old_h = old_hashes.get(name, "<missing>")
        new_h = new_hashes.get(name, "<missing>")
        if old_h != new_h:
            changed.append(name)

    if changed:
        print(f"\n  PROMPT CHANGES DETECTED: {', '.join(changed)}")
        for name in changed:
            print(f"    {name}: {old_hashes.get(name, '<new>')[:8]} -> {new_hashes.get(name, '<removed>')[:8]}")
    else:
        print("\n  Prompts unchanged between runs.")


# ══════════════════════════════════════════════════════════════════
# Enhanced report
# ══════════════════════════════════════════════════════════════════

def print_report(results: list):
    """Print analysis of backtest results."""
    if not results:
        print("No results to report.")
        return

    successes = [r for r in results if r["expected"] == "success" and r.get("score") is not None]
    failures = [r for r in results if r["expected"] == "failure" and r.get("score") is not None]
    acquired = [r for r in results if r["expected"] == "acquired" and r.get("score") is not None]
    uncertain = [r for r in results if r["expected"] == "uncertain" and r.get("score") is not None]
    errors = [r for r in results if r.get("error")]

    print("\n" + "=" * 70)
    print("  MIRAI BACKTEST RESULTS")
    print("=" * 70)
    print(f"  Total companies tested: {len(results)}")
    print(f"  Errors: {len(errors)}")
    print()

    if successes:
        avg = sum(r["score"] for r in successes) / len(successes)
        scores = sorted(successes, key=lambda x: x["score"])
        print(f"  SUCCESSES ({len(successes)} companies)")
        print(f"  Average score: {avg:.1f}/10")
        print(f"  Range: {scores[0]['score']:.1f} ({scores[0]['company']}) — {scores[-1]['score']:.1f} ({scores[-1]['company']})")
        for r in sorted(successes, key=lambda x: -x["score"]):
            verdict = r["verdict"][:12].ljust(12)
            swarm_pct = r.get("swarm_stats", {}).get("positive_pct")
            swarm = f"{swarm_pct:.0f}% HIT" if swarm_pct is not None else "no swarm"
            correct_mark = "OK" if r.get("correct") else "XX"
            print(f"    {r['score']:4.1f}  {verdict}  {swarm:>8}  [{correct_mark}]  {r['company']}")
        print()

    if failures:
        avg = sum(r["score"] for r in failures) / len(failures)
        scores = sorted(failures, key=lambda x: x["score"])
        print(f"  FAILURES ({len(failures)} companies)")
        print(f"  Average score: {avg:.1f}/10")
        print(f"  Range: {scores[0]['score']:.1f} ({scores[0]['company']}) — {scores[-1]['score']:.1f} ({scores[-1]['company']})")
        for r in sorted(failures, key=lambda x: -x["score"]):
            verdict = r["verdict"][:12].ljust(12)
            swarm_pct = r.get("swarm_stats", {}).get("positive_pct")
            swarm = f"{swarm_pct:.0f}% HIT" if swarm_pct is not None else "no swarm"
            correct_mark = "OK" if r.get("correct") else "XX"
            print(f"    {r['score']:4.1f}  {verdict}  {swarm:>8}  [{correct_mark}]  {r['company']}")
        print()

    if acquired:
        avg = sum(r["score"] for r in acquired) / len(acquired)
        print(f"  ACQUIRED ({len(acquired)} companies)")
        print(f"  Average score: {avg:.1f}/10")
        for r in sorted(acquired, key=lambda x: -x["score"]):
            verdict = r["verdict"][:12].ljust(12)
            correct_mark = "OK" if r.get("correct") else "XX"
            print(f"    {r['score']:4.1f}  {verdict}  [{correct_mark}]  {r['company']} -> {r['actual_outcome']}")
        print()

    if uncertain:
        avg = sum(r["score"] for r in uncertain) / len(uncertain)
        print(f"  UNCERTAIN ({len(uncertain)} companies)")
        print(f"  Average score: {avg:.1f}/10")
        for r in sorted(uncertain, key=lambda x: -x["score"]):
            verdict = r["verdict"][:12].ljust(12)
            print(f"    {r['score']:4.1f}  {verdict}  {r['company']}")
        print()

    # Key metrics
    if successes and failures:
        avg_s = sum(r["score"] for r in successes) / len(successes)
        avg_f = sum(r["score"] for r in failures) / len(failures)
        gap = avg_s - avg_f
        print("  " + "-" * 50)
        print(f"  DISCRIMINATION GAP: {gap:.1f} points")
        print(f"    Success avg: {avg_s:.1f}  |  Failure avg: {avg_f:.1f}")
        if gap >= 2.0:
            print("    PASS — system discriminates between winners and losers")
        elif gap >= 1.5:
            print("    MARGINAL — some signal, but scoring rubric needs tuning")
        else:
            print("    FAIL — scores cluster too tightly, rubric needs rework")

        # Accuracy check
        correct_s = sum(1 for r in successes if r["score"] >= SUCCESS_THRESHOLD)
        correct_f = sum(1 for r in failures if r["score"] < FAILURE_THRESHOLD)
        total = len(successes) + len(failures)
        accuracy = (correct_s + correct_f) / total * 100
        print(f"\n  ACCURACY (success >= {SUCCESS_THRESHOLD}, failure < {FAILURE_THRESHOLD}): {accuracy:.0f}%")
        print(f"    Successes correctly scored >= {SUCCESS_THRESHOLD}: {correct_s}/{len(successes)}")
        print(f"    Failures correctly scored < {FAILURE_THRESHOLD}:   {correct_f}/{len(failures)}")

    # Summary statistics
    summary = compute_summary_statistics(results)
    if "error" not in summary:
        print(f"\n  " + "-" * 50)
        print(f"  EXTENDED STATISTICS")
        print(f"    Overall accuracy:      {summary['overall_accuracy']*100:.1f}%")
        print(f"    False positive rate:   {summary['false_positive_rate']*100:.1f}%")
        print(f"    False negative rate:   {summary['false_negative_rate']*100:.1f}%")

        dim_acc = summary.get("per_dimension_accuracy", {})
        if dim_acc:
            print(f"\n    Per-dimension accuracy:")
            for dim, acc in sorted(dim_acc.items(), key=lambda x: -x[1]):
                bar = "#" * int(acc * 20)
                print(f"      {dim:35s} {acc*100:5.1f}%  {bar}")

        zone_acc = summary.get("per_zone_accuracy", {})
        if zone_acc:
            print(f"\n    Per-zone accuracy:")
            for zone, acc in sorted(zone_acc.items(), key=lambda x: -x[1]):
                bar = "#" * int(acc * 20)
                print(f"      {zone:20s} {acc*100:5.1f}%  {bar}")

        model_acc = summary.get("per_model_accuracy", {})
        if model_acc:
            print(f"\n    Per-model accuracy:")
            for model, acc in sorted(model_acc.items(), key=lambda x: -x[1]):
                print(f"      {model:30s} {acc*100:5.1f}%")

        delib = summary.get("deliberation_impact", {})
        if delib:
            print(f"\n    Deliberation impact (n={delib.get('sample_size', 0)}):")
            print(f"      Weighted accuracy:   {delib.get('weighted_accuracy', 0)*100:.1f}%")
            print(f"      Unweighted accuracy: {delib.get('unweighted_accuracy', 0)*100:.1f}%")

    print("\n" + "=" * 70)
    return summary


# ══════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════

def main():
    args = sys.argv[1:]

    # Just print report
    if "--report" in args:
        results = load_results()
        print_report(results)
        return

    # Just compare previous runs
    if "--compare" in args:
        print_comparison()
        return

    # Select tiers
    tier = "1"
    if "--tier" in args:
        idx = args.index("--tier")
        tier = args[idx + 1] if idx + 1 < len(args) else "1"

    if tier == "all":
        companies = ALL_COMPANIES["tier1"] + ALL_COMPANIES["tier2"]
    elif tier == "2":
        companies = ALL_COMPANIES["tier2"]
    else:
        companies = ALL_COMPANIES["tier1"]

    # Resume support
    results = load_results() if "--resume" in args else []
    done_names = {r["company"] for r in results}
    remaining = [c for c in companies if c["name"] not in done_names]

    print(f"\nMirai Backtest — {len(remaining)} companies to test ({len(done_names)} already done)")
    print(f"Depth: quick | Swarm: 25 agents | Results: {RESULTS_FILE}")
    print(f"Git commit: {_get_git_commit()} | Prompt hashes: {len(get_all_hashes())} registered\n")

    for i, company in enumerate(remaining):
        expected = company["expected"].upper()
        print(f"[{i+1}/{len(remaining)}] {company['name']} (expected: {expected})...", end=" ", flush=True)

        start = time.time()
        result = run_analysis(company, depth="quick", swarm_count=25)
        elapsed = time.time() - start

        if result.get("error"):
            print(f"ERROR ({elapsed:.0f}s): {result['error'][:60]}")
        else:
            score = result["score"]
            verdict = result["verdict"]
            correct_mark = "OK" if result.get("correct") else "XX"
            print(f"{score:.1f}/10 — {verdict} [{correct_mark}] ({elapsed:.0f}s)")

        results.append(result)
        save_results(results)

        # Rate limit — be gentle with the LLM providers
        if i < len(remaining) - 1:
            time.sleep(3)

    # Print report and compute summary
    summary = print_report(results)

    # Save archived run with full metadata
    if summary and "error" not in summary:
        archive_path = save_run_archive(results, summary)
        print(f"  Run archived to: {archive_path}")

        # Print comparison with previous run if available
        print_comparison(current_summary=summary)


if __name__ == "__main__":
    main()
