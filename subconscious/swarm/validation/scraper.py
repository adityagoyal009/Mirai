"""
Startup Data Scraper — collects historical startup data from public sources
for backtesting Mirai's prediction accuracy.

Sources: Y Combinator directory, public startup databases.
"""

import json
import os
import time
from typing import List, Dict, Optional

import requests
from ..utils.logger import get_logger

logger = get_logger('mirofish.validation.scraper')

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
OUTPUT_FILE = os.path.join(DATA_DIR, 'historical_startups.json')

# Known YC companies with outcomes (manually curated seed data)
# This bootstraps the dataset — scraper can expand it later
SEED_DATA = [
    # ── Strong Successes (IPO/Major Acquisition/Unicorn) ──
    {"company": "Stripe", "industry": "FinTech", "product": "Online payments API for developers", "batch": "S09", "stage": "Seed", "outcome": "success", "outcome_detail": "Private, $95B valuation", "target_market": "Developers and internet businesses", "business_model": "Transaction fees (2.9% + $0.30)"},
    {"company": "Airbnb", "industry": "Marketplace", "product": "Peer-to-peer home/apartment rental marketplace", "batch": "W09", "stage": "Seed", "outcome": "success", "outcome_detail": "IPO, $75B market cap", "target_market": "Travelers and property owners", "business_model": "Service fee on bookings (3-15%)"},
    {"company": "Dropbox", "industry": "SaaS", "product": "Cloud file storage and sync for consumers and teams", "batch": "S07", "stage": "Seed", "outcome": "success", "outcome_detail": "IPO, $10B market cap", "target_market": "Consumers and small businesses", "business_model": "Freemium SaaS ($12-20/user/month)"},
    {"company": "Coinbase", "industry": "FinTech", "product": "Cryptocurrency exchange and wallet", "batch": "S12", "stage": "Seed", "outcome": "success", "outcome_detail": "IPO, $50B+ peak valuation", "target_market": "Crypto traders and institutions", "business_model": "Trading fees (0.5-4.5%)"},
    {"company": "DoorDash", "industry": "Marketplace", "product": "Food delivery marketplace connecting restaurants and customers", "batch": "S13", "stage": "Seed", "outcome": "success", "outcome_detail": "IPO, $40B+ market cap", "target_market": "Urban consumers and restaurants", "business_model": "Delivery fees + restaurant commissions"},
    {"company": "Instacart", "industry": "Marketplace", "product": "Grocery delivery and pickup marketplace", "batch": "S12", "stage": "Seed", "outcome": "success", "outcome_detail": "IPO at $10B", "target_market": "Grocery shoppers", "business_model": "Delivery fees + retailer partnerships"},
    {"company": "Brex", "industry": "FinTech", "product": "Corporate credit cards for startups with no personal guarantee", "batch": "W17", "stage": "Seed", "outcome": "success", "outcome_detail": "Unicorn, $12B valuation", "target_market": "Startups and SMBs", "business_model": "Interchange fees + SaaS"},
    {"company": "Faire", "industry": "Marketplace", "product": "Wholesale marketplace connecting brands with independent retailers", "batch": "W17", "stage": "Seed", "outcome": "success", "outcome_detail": "Unicorn, $12.4B valuation", "target_market": "Independent retailers and wholesale brands", "business_model": "Commission on wholesale orders"},
    {"company": "Rappi", "industry": "Marketplace", "product": "On-demand delivery super-app (food, groceries, pharmacy)", "batch": "W16", "stage": "Seed", "outcome": "success", "outcome_detail": "Unicorn, $5.25B valuation", "target_market": "Latin American consumers", "business_model": "Delivery fees + merchant commissions"},
    {"company": "Gusto", "industry": "SaaS", "product": "Payroll, benefits, and HR platform for small businesses", "batch": "W12", "stage": "Seed", "outcome": "success", "outcome_detail": "Unicorn, $10B valuation", "target_market": "Small businesses (1-100 employees)", "business_model": "Per-employee monthly SaaS fee"},

    # ── Moderate Successes (Acquired/Profitable/Growing) ──
    {"company": "Heroku", "industry": "DeepTech", "product": "Cloud application platform (PaaS) for developers", "batch": "W08", "stage": "Seed", "outcome": "acquired", "outcome_detail": "Acquired by Salesforce for $212M", "target_market": "Web developers", "business_model": "Usage-based cloud hosting fees"},
    {"company": "Optimizely", "industry": "SaaS", "product": "A/B testing and experimentation platform", "batch": "W10", "stage": "Seed", "outcome": "acquired", "outcome_detail": "Acquired by Episerver/Optimizely for $600M+", "target_market": "Product and marketing teams", "business_model": "Enterprise SaaS"},
    {"company": "Zapier", "industry": "SaaS", "product": "No-code automation platform connecting 5000+ apps", "batch": "S12", "stage": "Seed", "outcome": "success", "outcome_detail": "Profitable, $5B+ valuation, fully remote", "target_market": "Non-technical business users", "business_model": "Freemium SaaS ($20-600/month)"},
    {"company": "Weebly", "industry": "SaaS", "product": "Drag-and-drop website builder for small businesses", "batch": "W07", "stage": "Seed", "outcome": "acquired", "outcome_detail": "Acquired by Square for $365M", "target_market": "Small businesses and individuals", "business_model": "Freemium website hosting"},
    {"company": "Pebble", "industry": "Hardware", "product": "Smartwatch with e-paper display and app ecosystem", "batch": "Standalone", "stage": "Seed", "outcome": "acquired", "outcome_detail": "Acquired by Fitbit (acqui-hire, assets only)", "target_market": "Tech enthusiasts and fitness users", "business_model": "Hardware sales ($99-249/unit)"},

    # ── Failures / Shutdowns ──
    {"company": "Homejoy", "industry": "Marketplace", "product": "On-demand home cleaning service marketplace", "batch": "W13", "stage": "Series A", "outcome": "failed", "outcome_detail": "Shut down 2015, worker classification issues", "target_market": "Urban homeowners", "business_model": "Service fee on cleaning bookings"},
    {"company": "Kiko", "industry": "SaaS", "product": "Web-based calendar application", "batch": "S05", "stage": "Seed", "outcome": "failed", "outcome_detail": "Sold on eBay for $258K, couldn't compete with Google Calendar", "target_market": "Consumers", "business_model": "Freemium web app"},
    {"company": "Tutorspree", "industry": "EdTech", "product": "Online marketplace matching students with tutors", "batch": "S11", "stage": "Seed", "outcome": "failed", "outcome_detail": "Shut down 2013, couldn't achieve marketplace liquidity", "target_market": "Students and parents", "business_model": "Commission on tutoring sessions"},
    {"company": "Exec", "industry": "Marketplace", "product": "On-demand personal assistant and errand running service", "batch": "W12", "stage": "Seed", "outcome": "failed", "outcome_detail": "Shut down, pivoted, eventually acqui-hired", "target_market": "Busy professionals", "business_model": "Hourly rate for assistant services"},
    {"company": "Mattermark", "industry": "SaaS", "product": "Startup data and analytics platform for investors", "batch": "S12", "stage": "Series A", "outcome": "failed", "outcome_detail": "Acquired for ~$3M (down round) by FullContact", "target_market": "VCs and investors", "business_model": "Enterprise SaaS subscription"},
    {"company": "Teforia", "industry": "Hardware", "product": "Smart tea infuser with IoT connectivity and premium tea pods", "batch": "Standalone", "stage": "Series A", "outcome": "failed", "outcome_detail": "Shut down 2017, burned $15M on $1000 tea machine", "target_market": "Premium tea enthusiasts", "business_model": "Hardware + consumable pods"},
    {"company": "ScoreBig", "industry": "Marketplace", "product": "Name-your-own-price ticket marketplace for events", "batch": "Standalone", "stage": "Series C", "outcome": "failed", "outcome_detail": "Shut down 2016 after raising $100M+", "target_market": "Event attendees seeking deals", "business_model": "Commission on ticket sales"},
    {"company": "Rdio", "industry": "Consumer", "product": "Music streaming service", "batch": "Standalone", "stage": "Series C", "outcome": "failed", "outcome_detail": "Bankrupt 2015, couldn't compete with Spotify", "target_market": "Music listeners", "business_model": "Subscription ($5-10/month)"},
    {"company": "Secret", "industry": "Consumer", "product": "Anonymous social sharing app", "batch": "Standalone", "stage": "Series B", "outcome": "failed", "outcome_detail": "Shut down 2015, returned $2M to investors, cyberbullying concerns", "target_market": "Young adults", "business_model": "Ad-supported social network"},
    {"company": "Juicero", "industry": "Hardware", "product": "$400 WiFi-connected juice press with proprietary juice packs", "batch": "Standalone", "stage": "Series C", "outcome": "failed", "outcome_detail": "Shut down 2017, packs could be squeezed by hand", "target_market": "Health-conscious consumers", "business_model": "Hardware + consumable juice packs"},
]


def get_seed_dataset() -> List[Dict]:
    """Return the seed dataset of historical startups."""
    return SEED_DATA


def save_dataset(startups: List[Dict], path: str = OUTPUT_FILE):
    """Save startup dataset to JSON."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(startups, f, indent=2)
    logger.info(f"[Scraper] Saved {len(startups)} startups to {path}")


def load_dataset(path: str = OUTPUT_FILE) -> List[Dict]:
    """Load startup dataset from JSON."""
    if not os.path.exists(path):
        return get_seed_dataset()
    with open(path, 'r') as f:
        return json.load(f)


DB_PATH = os.path.join(DATA_DIR, 'companies.db')


def load_from_db(outcome_filter: str = None, industry: str = None,
                 limit: int = 100, exclude_active: bool = True) -> List[Dict]:
    """
    Load companies from SQLite database for backtesting.

    Args:
        outcome_filter: 'success', 'acquired', 'failed', or None for all
        industry: Filter by industry name
        limit: Max companies to return
        exclude_active: Skip 'active' companies (unknown outcome)
    """
    import sqlite3
    if not os.path.exists(DB_PATH):
        logger.warning(f"[Scraper] Database not found at {DB_PATH}")
        return get_seed_dataset()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    conditions = []
    params = []

    if exclude_active:
        conditions.append("outcome != 'active'")
    if outcome_filter:
        conditions.append("outcome = ?")
        params.append(outcome_filter)
    if industry:
        conditions.append("industry LIKE ?")
        params.append(f"%{industry}%")

    # Prefer companies with descriptions
    conditions.append("long_description IS NOT NULL AND long_description != ''")

    where = " AND ".join(conditions) if conditions else "1=1"
    query = f"""
        SELECT * FROM companies
        WHERE {where}
        ORDER BY RANDOM()
        LIMIT ?
    """
    params.append(limit)

    c.execute(query, params)
    rows = c.fetchall()
    conn.close()

    results = []
    for row in rows:
        results.append({
            "company": row["name"],
            "industry": row["industry"] or "Unknown",
            "product": row["one_liner"] or row["long_description"][:200] if row["long_description"] else "Unknown",
            "target_market": "",
            "business_model": "",
            "stage": row["stage"] or "Seed",
            "outcome": row["outcome"],
            "outcome_detail": f"Status: {row['status']}, Team: {row['team_size'] or '?'}",
            "batch": row["batch"] or "",
            "db_id": row["id"],
        })

    logger.info(f"[Scraper] Loaded {len(results)} companies from DB (filter: {outcome_filter}, industry: {industry})")
    return results


def startup_to_exec_summary(startup: Dict) -> str:
    """Convert a startup record to an exec summary string."""
    parts = [
        f"Company: {startup.get('company', 'Unknown')}",
        f"Industry: {startup.get('industry', 'Unknown')}",
        f"Product: {startup.get('product', 'Unknown product')}",
    ]
    if startup.get('target_market'):
        parts.append(f"Target Market: {startup['target_market']}")
    if startup.get('business_model'):
        parts.append(f"Business Model: {startup['business_model']}")
    if startup.get('stage'):
        parts.append(f"Stage: {startup['stage']}")
    return ". ".join(parts)


if __name__ == "__main__":
    dataset = get_seed_dataset()
    save_dataset(dataset)
    print(f"Seed dataset: {len(dataset)} startups")
    outcomes = {}
    for s in dataset:
        o = s.get('outcome', 'unknown')
        outcomes[o] = outcomes.get(o, 0) + 1
    print(f"Outcomes: {outcomes}")
