"""
Persona Engine — loads and selects personas from the FinePersonas dataset.

Provides two modes:
  1. Dataset mode: Selects from 1.6M+ real personas (when downloaded)
  2. Generator mode: Generates personas on-the-fly from trait combinations
     88.5B+ unique combinations across 11 dimensions with behavioral depth,
     zone-specific backstories, geographic lens, and anti-redundancy safeguards.

The engine matches personas to the startup being evaluated by label relevance.
"""

import json
import os
import random
import linecache
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from ..utils.logger import get_logger

logger = get_logger('mirofish.personas')

_DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
_PERSONAS_FILE = os.path.join(_DATA_DIR, 'personas.jsonl')
_PERSONAHUB_FILE = os.path.join(_DATA_DIR, 'personahub.jsonl')
_PERSONAHUB_ELITE_FILE = os.path.join(_DATA_DIR, 'personahub_elite.jsonl')
_INDEX_FILE = os.path.join(_DATA_DIR, 'label_index.json')

# ══════════════════════════════════════════════════════════════════
# TRAIT GENERATOR — 11 dimensions, 88.5B+ unique personas
# ══════════════════════════════════════════════════════════════════

# ── Dimension 1: Roles (zone-specific) ──

ZONE_ROLES = {
    "investor": [
        "Pre-Seed VC", "Seed VC", "Series-A VC", "Series-B VC",
        "Growth Equity VC", "Late-Stage VC", "Deep Tech VC", "Bio VC",
        "Angel Investor (solo)", "Angel Investor (syndicate lead)", "Super Angel",
        "Micro VC ($1-5M fund)", "PE Partner (buyout)", "PE Partner (growth equity)",
        "Family Office (single family)", "Family Office (multi-family)",
        "Corporate VC (strategic)", "Corporate VC (financial return)",
        "Impact Investor (climate)", "Impact Investor (social)",
        "Hedge Fund Analyst (long/short)", "Investment Banker (tech M&A)",
        "Sovereign Wealth Fund Manager", "Endowment Fund Manager",
        "Venture Debt Provider", "Revenue-Based Financing Provider",
        "Accelerator Partner (YC-style)", "Accelerator Partner (corporate)",
        "LP Evaluating Fund Allocation", "Crypto VC",
        "Retail Investor (sophisticated)", "Retail Investor (first-time)",
    ],
    "customer": [
        "Target Customer (F500 Enterprise)", "Target Customer (Mid-Market)",
        "Target Customer (SMB 10-50 employees)", "Target Customer (Micro <10)",
        "Enterprise IT Director", "Enterprise Procurement Manager",
        "Enterprise CISO", "Enterprise Chief Data Officer",
        "VP Operations (buyer)", "VP Marketing (buyer)", "VP Finance (buyer)",
        "Department Head (budget holder)", "Line Manager (end user)",
        "Supply Chain Director", "Facilities Manager",
        "Target Consumer (power user)", "Target Consumer (price-sensitive)",
        "Non-Target Consumer (mainstream)", "Gen-Z Early Adopter",
        "Channel Partner (reseller)", "Systems Integrator",
        "IT Consultant (recommender)", "Customer Who Churned From Competitor",
        "Existing Customer of Incumbent",
    ],
    "operator": [
        "Startup Founder (failed, raised $10M+)", "Startup Founder (failed, bootstrapped)",
        "Startup Founder (successful exit $50M+)", "Startup Founder (successful exit $500M+)",
        "Serial Entrepreneur (3+ companies)", "First-Time Founder (technical)",
        "CTO (scaling stage)", "CTO (early stage)",
        "CMO (B2B)", "CMO (B2C/DTC)",
        "CFO (venture-backed)", "COO (operations-heavy)",
        "Chief Product Officer", "Chief Revenue Officer",
        "VP Engineering (platform)", "VP Engineering (product)",
        "VP Sales (enterprise)", "VP Sales (PLG/self-serve)",
        "VP People/HR", "VP Customer Success",
        "Head of Growth", "Head of Partnerships",
        "Engineering Manager", "Product Manager (B2B SaaS)",
        "DevRel / Developer Advocate", "Supply Chain Operations Lead",
    ],
    "analyst": [
        "Industry Analyst (Gartner)", "Industry Analyst (Forrester)",
        "Industry Analyst (CB Insights)", "Industry Analyst (PitchBook)",
        "Equity Research Analyst (sell-side)", "Equity Research Analyst (buy-side)",
        "Credit Rating Analyst", "ESG Analyst",
        "Tech Journalist (Tier 1)", "Investigative Reporter (financial)",
        "Newsletter Writer (industry)", "Podcast Host (tech)",
        "Professor of Entrepreneurship", "Academic Researcher (CS/AI)",
        "Academic Researcher (economics)", "PhD Researcher (domain-specific)",
        "Think Tank Fellow", "Business School Case Writer",
        "Market Strategist (McKinsey)", "Market Strategist (BCG)",
        "Behavioral Economist", "Macro Economist",
        "UX Researcher", "Technology Futurist",
    ],
    "contrarian": [
        "Competitor CEO (incumbent)", "Competitor CEO (well-funded startup)",
        "Competitor Product Manager", "Big Tech PM (could build this)",
        "Big Tech Corp Dev (could acquire)", "Open Source Maintainer (competing project)",
        "Regulatory Expert (federal)", "Regulatory Expert (EU/GDPR)",
        "Patent Attorney (IP litigation)", "Patent Attorney (prosecution)",
        "Data Privacy Officer", "Antitrust Attorney",
        "Government Policy Advisor", "Lobbyist (incumbent industry)",
        "Insurance Underwriter", "Risk Analyst (operational)",
        "Cybersecurity Expert", "Platform Risk Analyst",
        "Short Seller (activist)", "Forensic Accountant",
        "Consumer Rights Advocate", "Environmental Compliance Officer",
        "Labor/Employment Attorney", "Tax Attorney (international)",
    ],
    "wildcard": [
        "High School Student (interested in the field)",
        "Retired Executive (from this industry)",
        "Small-Town Mayor (dealing with this problem)",
        "NGO Worker (in the field)",
        "Emergency Room Doctor", "Military Logistics Officer",
        "Artist/Designer (UX perspective)", "Stand-Up Comedian (BS detector)",
        "Farmer/Rancher", "Parent Evaluating For Family",
        "Philosopher of Technology", "Journalist From Developing Country",
        "Water Utility Worker (20 years field experience)",
        "Insurance Claims Adjuster (environmental damage)",
        "Real Estate Developer (lakefront properties)",
        "Fishing Guide (water quality is livelihood)",
        "Environmental Law Professor",
        "Tribal Water Rights Advocate",
        "Climate Journalist (investigative)",
        "School Superintendent (drinking water safety)",
        "Retired EPA Administrator",
        "Agricultural Extension Agent",
        "Public Health Nurse (rural community)",
        "Documentary Filmmaker (environmental)",
        "Tech-Savvy Retiree (early adopter)",
        "Urban Planner (infrastructure focus)",
        "Venture-Backed Founder (adjacent space)",
        "Local News Reporter (community impact)",
        "Science Teacher (STEM education)",
        "Community Organizer (environmental justice)",
        "Disaster Response Coordinator",
        "Data Privacy Advocate (surveillance concerns)",
        "Open Water Swimmer (personal stake)",
        "Municipal Budget Analyst",
        "Peace Corps Volunteer (water access projects)",
    ],
}

ROLES = list({role for roles in ZONE_ROLES.values() for role in roles})

# ── Dimension 2: MBTI with behavioral descriptions ──

MBTI_TYPES = [
    "INTJ", "INTP", "ENTJ", "ENTP",
    "INFJ", "INFP", "ENFJ", "ENFP",
    "ISTJ", "ISFJ", "ESTJ", "ESFJ",
    "ISTP", "ISFP", "ESTP", "ESFP",
]

MBTI_BEHAVIORAL = {
    "INTJ": "You are strategic and analytical. You demand logical consistency and distrust emotional pitches. You score harshly on vague execution plans but generously on visionary market positioning with clear moats.",
    "INTP": "You probe for first-principles reasoning and question every assumption. You score lower on team credentials (they don't impress you) but higher on product when the technical approach is genuinely elegant.",
    "ENTJ": "You are decisive and results-oriented. Bold ambition backed by execution earns your respect. You give polarized scores - strong conviction up or down, rarely a 5.",
    "ENTP": "You love novel approaches and spot logical flaws instantly. You play devil's advocate even when you agree. You score timing and market higher than average but dock points for boring, incremental improvements.",
    "INFJ": "You evaluate through mission and long-term impact. You read between the lines of founder intent. You score higher when the mission resonates, even if the financials are early-stage.",
    "INFP": "You value authenticity and distrust slick presentations. You penalize companies that feel derivative. You score product based on how it makes users feel, not just metrics.",
    "ENFJ": "You focus on team dynamics and leadership quality. Culture and narrative matter. You score team highest when leadership shows emotional intelligence and clear communication.",
    "ENFP": "You are enthusiastic and see possibilities everywhere. You get excited about big TAM numbers. Your 6 is someone else's 5 - but when something bores you, you give a 3.",
    "ISTJ": "You are methodical and trust data over narrative. You want spreadsheets, not vision decks. You score based on proven traction and historical comparables. No data means low score.",
    "ISFJ": "You are cautious and focus on downside scenarios. You value reliability and steady growth over explosive but risky bets. You score lower on early-stage companies with no revenue.",
    "ESTJ": "You are pragmatic. You evaluate operational readiness and scalability. You want clear milestones, KPIs, and accountability. You score team and product based on execution evidence, not promises.",
    "ESFJ": "You evaluate based on social proof and community validation. You want to know who else is using this and who endorses it. You score higher with visible customer love, lower for stealth-mode.",
    "ISTP": "You are hands-on and technical. You want to understand HOW it works, not just WHAT it does. You respect engineering excellence and distrust hand-wavy 'AI-powered' claims. Vaporware gets a 2.",
    "ISFP": "You are aesthetically sensitive and user-focused. You evaluate the experience, not just the function. Design quality and user delight drive your product score.",
    "ESTP": "You are action-oriented and competitive. You respect founders who ship fast and iterate. Analysis paralysis disgusts you. You score timing aggressively and penalize 'still planning' companies.",
    "ESFP": "You are trend-aware and evaluate virality and cultural relevance. You want to know if people will talk about this. You score market based on consumer excitement and cultural moment.",
}

# ── Dimension 3: Risk Profiles (7) ──

RISK_PROFILES = [
    "ultra-conservative - capital preservation above all, needs overwhelming evidence",
    "conservative - needs 3x evidence before believing, defaults to skepticism",
    "moderate-conservative - prefers proven models with upside, cautious optimist",
    "moderate - balanced risk-reward, weighs pros and cons equally",
    "moderate-aggressive - comfortable with calculated bets, leans into upside",
    "aggressive - high risk tolerance, seeks 10x+ returns, accepts high failure rate",
    "ultra-aggressive - moon-shot mentality, bets on outliers, 100x or nothing",
]

# ── Dimension 4: Experience Levels (7) ──

EXPERIENCE_LEVELS = [
    "early career (1-3 years)",
    "developing (3-5 years)",
    "mid-career (5-8 years)",
    "senior (10-15 years)",
    "veteran (15-20 years)",
    "industry elder (20-30 years)",
    "legendary (30+ years, multiple market cycles)",
]

# Role-experience compatibility: index into EXPERIENCE_LEVELS (0=earliest allowed)
ROLE_MIN_EXPERIENCE = {
    # Senior roles need veteran+ experience (index 4+)
    "PE Partner (buyout)": 4, "PE Partner (growth equity)": 4,
    "Sovereign Wealth Fund Manager": 4, "Endowment Fund Manager": 4,
    "LP Evaluating Fund Allocation": 4,
    "Retired Executive (from this industry)": 5,
    # Mid-senior roles need senior+ (index 3+)
    "Series-B VC": 3, "Growth Equity VC": 3, "Late-Stage VC": 3,
    "CFO (venture-backed)": 3, "COO (operations-heavy)": 3,
    "Chief Product Officer": 3, "Chief Revenue Officer": 3,
    "Serial Entrepreneur (3+ companies)": 3,
    "Family Office (single family)": 3, "Family Office (multi-family)": 3,
    "Industry Analyst (Gartner)": 3, "Industry Analyst (Forrester)": 3,
    "Professor of Entrepreneurship": 3,
    "Market Strategist (McKinsey)": 3, "Market Strategist (BCG)": 3,
    # Mid-career roles need mid-career+ (index 2+)
    "Series-A VC": 2, "Angel Investor (solo)": 2, "Super Angel": 2,
    "CTO (scaling stage)": 2, "CMO (B2B)": 2, "CMO (B2C/DTC)": 2,
    "VP Engineering (platform)": 2, "VP Engineering (product)": 2,
    "VP Sales (enterprise)": 2,
    "Startup Founder (successful exit $50M+)": 2,
    "Startup Founder (successful exit $500M+)": 3,
}

# ── Dimension 5: Cognitive Biases (22, categorized) ──

BIASES = [
    ("optimistic about new technology", "technology"),
    ("skeptical of hype cycles", "contrarian"),
    ("data-driven and quantitative", "financial"),
    ("intuition-driven and pattern-matching", "contrarian"),
    ("focused on unit economics above all", "financial"),
    ("focused on vision and TAM", "market"),
    ("concerned about regulatory risk", "timing"),
    ("concerned about execution risk", "execution"),
    ("pattern-matches to past successes", "market"),
    ("pattern-matches to past failures", "contrarian"),
    ("values team above all other factors", "team"),
    ("values market timing above all other factors", "timing"),
    ("contrarian thinker who bets against consensus", "contrarian"),
    ("consensus follower who trusts smart money", "market"),
    ("obsessed with competitive moats", "competition"),
    ("focused on founder-market fit", "team"),
    ("anchored on comparable exits", "financial"),
    ("biased toward capital efficiency", "financial"),
    ("biased toward growth-at-all-costs", "market"),
    ("anchored on technology differentiation", "technology"),
    ("focused on customer retention metrics", "execution"),
    ("concerned about platform dependency risk", "competition"),
]

# ── Dimension 6: Geographic Lens (28, with behavioral notes) ──

GEO_BEHAVIORAL = {
    "Silicon Valley": "You normalize massive burns and 100x outcomes. A $50M raise is table stakes. You've seen the playbook work and expect startups to follow it.",
    "San Francisco": "You live in the epicenter of tech and have high standards for product quality. You've seen a hundred pitch decks this month.",
    "New York": "You think in terms of revenue and unit economics from day one. Financial discipline matters. You compare everything to fintech and media companies.",
    "Boston": "You value deep technology and academic credibility. Biotech and enterprise software are your benchmarks. You respect technical founders.",
    "Austin": "You appreciate bootstrapped efficiency and the emerging tech scene. You're skeptical of Silicon Valley excess but respect ambition.",
    "Miami": "You see the rise of crypto, LatAm bridges, and alternative finance. You value speed and hustle over pedigree.",
    "London": "You think globally but cautiously. Regulatory compliance is non-negotiable. You benchmark against European success stories.",
    "Berlin": "You value sustainability, mission-driven companies, and efficient growth. You're skeptical of American-style blitzscaling.",
    "Paris": "You appreciate elegance in product design and deep tech. You factor in EU regulations as both constraint and opportunity.",
    "Amsterdam": "You value pragmatism and international scalability from day one. Small home market forces global thinking early.",
    "Stockholm": "You expect capital efficiency and product-led growth. Spotify and Klarna are your mental benchmarks.",
    "Singapore": "You evaluate through the lens of Southeast Asian expansion. Government support matters. You value regulatory clarity.",
    "Bangalore": "You see massive scale opportunities in price-sensitive markets. You value engineering talent depth and frugal innovation.",
    "Mumbai": "You think about India's 1.4B market and rising digital adoption. You value unit economics that work at Indian price points.",
    "Jakarta": "You evaluate for the fastest-growing digital economy in Southeast Asia. You factor in infrastructure gaps and mobile-first behavior.",
    "Tel Aviv": "You evaluate through exit velocity toward US/EU acquirers. You respect technical depth, military-grade execution, and capital efficiency.",
    "Dubai": "You see bridge opportunities between East and West. Government-backed innovation is normal. You value regional monopoly potential.",
    "Riyadh": "You evaluate through Vision 2030 lens. Government contracts and sovereign wealth fund partnerships matter enormously.",
    "Beijing": "You think at massive scale and evaluate government alignment. Technology self-sufficiency and domestic market domination are key.",
    "Shanghai": "You evaluate commercial viability in the world's largest consumer market. Speed of execution and competitive intensity are extreme.",
    "Shenzhen": "You live in hardware innovation central. You evaluate manufacturing capability, supply chain access, and iteration speed.",
    "Tokyo": "You value consensus, long-term relationships, and market stability. You are uncomfortable with 'move fast and break things.'",
    "Seoul": "You evaluate through the lens of rapid technology adoption and intense competition. You expect polished products from day one.",
    "Sao Paulo": "You see Latin America's largest economy with macro volatility. You value companies that can thrive despite currency risk and bureaucracy.",
    "Mexico City": "You evaluate nearshore opportunities and US-LatAm bridges. USMCA trade dynamics and demographics are tailwinds.",
    "Lagos": "You factor in infrastructure gaps, currency risk, and regulatory uncertainty. You look for capital efficiency and local execution strength.",
    "Nairobi": "You see mobile-first innovation and leapfrog opportunities. M-Pesa proved Africa can lead in fintech. You value frugal, scalable models.",
    "Sydney": "You evaluate for Asia-Pacific reach from a stable, well-regulated market. You value companies that can scale beyond a small domestic market.",
}

GEOGRAPHIC_LENS = list(GEO_BEHAVIORAL.keys())

# ── Dimension 7: Industry Focus (26, unchanged) ──

INDUSTRY_FOCUS = [
    "SaaS", "FinTech", "HealthTech", "EdTech", "CleanTech", "DeepTech",
    "Consumer", "Enterprise", "Marketplace", "Hardware", "BioTech",
    "AI/ML", "Cybersecurity", "Gaming", "Media", "LegalTech",
    "PropTech", "InsurTech", "AgriTech", "SpaceTech", "Web3",
    "Robotics", "Logistics", "HRTech", "FoodTech", "RetailTech",
]

# ── Dimension 8: Fund/Budget Context (zone-specific) ──

FUND_CONTEXT = {
    "investor": [
        " You manage a micro fund ($1-5M AUM) writing $25-100K checks.",
        " You manage a small fund ($5-25M AUM) leading $250K-1M rounds.",
        " You manage a mid-size fund ($25-100M AUM) leading $2-5M rounds.",
        " You manage a large fund ($100-500M AUM) leading $10-25M rounds.",
        " You manage a mega fund ($500M-1B AUM) making $25-50M bets.",
        " You invest your personal capital ($500K-2M available).",
        " You represent a corporate balance sheet with $50M+ strategic allocation.",
        " You manage an accelerator fund writing $125K standard checks.",
    ],
    "customer": [
        " Your annual software budget is under $50K.",
        " Your department budget is $50-200K for new tools.",
        " Your department budget is $200K-1M for technology.",
        " Your enterprise transformation budget is $1-5M.",
        " You are a consumer spending $20-50/month on subscriptions.",
        " You are a price-sensitive buyer who evaluates free vs. paid carefully.",
        " You manage procurement for 500+ employees.",
        " Your team already pays for 12 SaaS tools and is fatigued by new ones.",
    ],
    "operator": [
        " Your last company was bootstrapped to $3M ARR.",
        " Your last company raised a $2M seed round.",
        " Your last company raised $20M through Series B.",
        " Your last company raised $100M+ and went public.",
        " You joined a company at 10 employees and scaled to 500.",
        " You've only worked at large companies (1000+ employees).",
        " Your last company was acqui-hired for the team, not the product.",
        " You've operated in this exact market for 10+ years.",
    ],
    "analyst": [
        " You cover 200+ companies in this sector.",
        " You published the definitive industry report last year.",
        " You advise institutional investors managing $10B+ in this space.",
        " You've correctly predicted the last 3 major sector shifts.",
        " You run the most-read newsletter in this space (50K+ subscribers).",
        " You teach a graduate course on this industry.",
    ],
    "contrarian": [
        " Your company holds 40% market share in this space.",
        " You regulate this exact industry and have enforcement power.",
        " You've written patents that directly overlap with this product.",
        " You've seen the internal roadmap of a big tech company building this.",
        " You've audited companies like this and found the same problems every time.",
        " You worked at the incumbent for 15 years and know their playbook.",
    ],
    "wildcard": [],
}

# ── Dimension 9: Portfolio Composition (investor-only) ──

PORTFOLIO_CONTEXT = [
    " Your portfolio has 0 companies in this space - fresh thesis, no bias.",
    " You already have 2 investments in this sector - looking for complementary, not competing.",
    " You have 4 companies in adjacent spaces - deep domain conviction but concentration risk.",
    " Your last investment in this space failed - you're cautious but knowledgeable.",
    " You're building a concentrated thesis portfolio - this would be bet #3 of 5.",
    " Your portfolio is diversified across 30+ companies - this is one of many bets.",
    " You co-invest with 2 other funds who are already interested in this deal.",
    " Your fund is in deployment mode with 18 months of capital to put to work.",
]

# ── Dimension 10: Backstories / Scar Tissue (zone-specific, balanced bull/bear) ──

BACKSTORIES = {
    "investor": [
        "I passed on Airbnb's seed round and I'll never make that mistake again.",
        "I was early to Stripe when everyone said payment processing was boring. Trust your thesis.",
        "My best return was a company everyone hated - 150x on a contrarian bet.",
        "The best company I funded had zero revenue at seed and is now worth $5B.",
        "I backed a founder who was rejected by 50 VCs and she built a decacorn.",
        "I lost $5M on a cleantech SPAC that had beautiful metrics and no real customers.",
        "I funded a brilliant founder who couldn't hire or manage people. Total loss.",
        "My biggest loss was a company that grew 10x revenue but had -60% gross margins.",
        "I funded three AI companies in 2023 that all turned out to be GPT wrappers.",
        "I learned the hard way that a huge TAM means nothing without distribution.",
        "I watched a portfolio company get destroyed by a single regulatory change overnight.",
        "I backed a company that won every pitch competition and failed within 18 months.",
        "I've seen 5,000 pitches and funded 40. My hit rate is about 1 in 10.",
        "I've been through 3 market cycles and every crash felt different but the same.",
        "My mentor told me: bet on the jockey, not the horse. I'm still testing that theory.",
        "I invested in a pivot that turned a failing B2B into a consumer unicorn. Flexibility matters.",
        "I was in Theranos-adjacent territory once. Now I verify every technical claim personally.",
    ],
    "customer": [
        "I bought enterprise software that cost $500K and nobody on my team used it.",
        "I switched to a startup's product and it was the best decision I made all year.",
        "My last vendor was acquired and the product died. I don't trust small companies now.",
        "I implemented a tool that saved my team 20 hours a week within the first month.",
        "I got burned by a product that worked great in the demo but broke at scale.",
        "I championed a new tool internally and got promoted when it worked.",
        "I championed a new tool internally and got blamed when it failed. Never again without proof.",
        "I've had great results with smaller, hungrier vendors who actually listen to feedback.",
        "My IT team blocked the last product I wanted because of security concerns.",
        "I'm tired of vendors overpromising on integration timelines. Show me it works first.",
        "The best tool I ever bought was the cheapest one - it just worked, no training needed.",
        "I lost a quarter's worth of productivity to a botched software migration.",
        "I was an early adopter of Slack when everyone said email was fine. I trust my instincts.",
        "I don't care about features. I care about uptime, support, and whether it integrates.",
        "I've been burned by three 'AI-powered' products that were just fancy dashboards.",
    ],
    "operator": [
        "I built a product nobody wanted and burned through $5M learning that lesson.",
        "I pivoted three times before finding product-market fit. Persistence is everything.",
        "I was employee #5 at a company that IPO'd at $10B. I know what a rocketship feels like.",
        "I joined a rocketship that crashed because the founders fought. Co-founder dynamics matter.",
        "I've hired 200 people and the team is 80% of the outcome.",
        "I scaled from 100 to 100K users and everything broke between 1K and 10K.",
        "I raised $30M and returned $0 to investors. I know what failure smells like early.",
        "I bootstrapped to $10M ARR and it taught me more than any VC round.",
        "I was CTO of a company that got acqui-hired. Good tech, wrong market.",
        "I've seen companies die from premature scaling. It's the silent killer.",
        "My company was killed by a competitor who moved faster, not one who built better.",
        "I learned that customers don't care about your tech - they care about their problem.",
        "I co-founded with a friend and it destroyed the friendship. Team chemistry is fragile.",
        "I left BigTech to join a startup and it was the hardest, best year of my life.",
        "I've managed engineering teams where shipping velocity was the only metric that mattered.",
    ],
    "analyst": [
        "I predicted the crypto crash 6 months early and nobody listened until it was too late.",
        "I was wrong about cloud computing in 2010. I thought it was a fad. Humbling.",
        "I correctly identified SaaS as the dominant model before most investors caught on.",
        "I've seen 20 years of Gartner Hype Cycles and the pattern never changes.",
        "I interviewed 100 CIOs last year and the consensus surprised even me.",
        "I wrote the bear case on a company that 5x'd. I understand my blind spots now.",
        "My research showed that 90% of 'AI companies' are really services companies with a wrapper.",
        "I was the first analyst to identify the shift from on-premise to cloud. Timing is everything.",
        "I evaluate companies by comparing them to the historical base rate of success in their category.",
        "I've tracked this market for a decade and the competitive dynamics are predictable.",
        "I've seen three 'Uber for X' cycles and learned to distinguish real platforms from mimicry.",
        "My best call was downgrading a darling stock 6 months before it crashed 80%.",
    ],
    "contrarian": [
        "I built the product this startup is trying to disrupt. I know where the bodies are buried.",
        "I've filed 15 patents in this space and can spot IP infringement from the pitch deck.",
        "I've been the regulator who shut down companies like this for non-compliance.",
        "I've been short-selling overvalued tech companies for 10 years with a 70% hit rate.",
        "I audited a company with similar metrics and found the numbers were fabricated.",
        "I was part of the team that killed Google+ and I know how big companies crush startups.",
        "I've seen this exact business model fail 4 times in different geographies.",
        "I worked at the incumbent in this space for 8 years. I know their playbook for killing competitors.",
        "I've reviewed 500 patent applications in this field and there's genuinely nothing new here.",
        "My insurance underwriting model says companies like this have a 40% chance of catastrophic failure.",
        "I spent 3 years in cybersecurity incident response. I see breach risk everywhere.",
        "I managed the antitrust case against the dominant player in this market. I know the legal landscape.",
    ],
    "wildcard": [
        "I have no background in this industry, but I know what good products feel like as a user.",
        "I'm a retired teacher who evaluates everything by asking: does it help people learn?",
        "I'm a doctor who judges technology by whether it reduces human suffering.",
        "I'm a parent who evaluates everything by asking: would I want my kids to use this?",
        "I just read an article about this space and formed a strong opinion. Fresh eyes.",
        "I'm an artist who believes the best products have soul, craft, and intentional design.",
    ],
}

# ── Dimension 11: Decision Frameworks (zone-specific, categorized) ──

DECISION_FRAMEWORKS = {
    "investor": [
        ("If I can't explain the moat in one sentence, I pass.", "competition"),
        ("I need to see a path to 100x return or it's not worth my fund's time.", "financial"),
        ("I invest in markets, not companies. The rising tide must be real.", "market"),
        ("Show me three customers who would cry if the product disappeared.", "execution"),
        ("I only invest when I believe the founder knows something the market doesn't.", "team"),
        ("If the unit economics don't work at 10x current scale, they won't work at 100x.", "financial"),
        ("I look for unfair advantages: proprietary data, network effects, or regulatory capture.", "competition"),
        ("I pass on any company where the 'AI moat' is just prompt engineering.", "technology"),
        ("My litmus test: is there a burning platform forcing customers to switch NOW?", "timing"),
        ("I need to see 3 months of accelerating growth, not a single great month.", "execution"),
        ("I ask: would a smart 22-year-old build this from scratch in 6 months? If yes, no moat.", "competition"),
        ("I invest when the founder's insight is non-obvious AND correct. Obvious ideas are competed away.", "team"),
    ],
    "customer": [
        ("I won't switch unless you're 10x better than what I have today.", "competition"),
        ("My buying criteria: does it integrate with my existing stack in under a week?", "technology"),
        ("I need to see ROI within 90 days or I cancel.", "financial"),
        ("I buy from companies that will exist in 5 years. Prove your staying power.", "execution"),
        ("If my team needs training to use it, it's already failed.", "execution"),
        ("I pilot for 30 days with a small team. If adoption is organic, I buy.", "execution"),
        ("I need 3 reference customers in my industry before I sign.", "market"),
        ("My framework: does this reduce headcount, increase revenue, or reduce risk?", "financial"),
        ("I won't be the first customer. Show me social proof.", "market"),
        ("Price isn't the issue. Proving value to my CFO is the issue.", "financial"),
    ],
    "operator": [
        ("If you can't describe the customer in one sentence, you don't know your market.", "market"),
        ("I evaluate: can this team ship v2 before the competition ships v1?", "execution"),
        ("I look at burn rate first. Runway equals survival equals optionality.", "financial"),
        ("Great products get pulled by the market. If you're pushing, something is wrong.", "market"),
        ("I judge by the quality of the first 10 hires. That's the company's DNA.", "team"),
        ("Show me the customer acquisition channel that scales without linear cost.", "execution"),
        ("If the founder can't sell it themselves, no VP Sales will save them.", "team"),
        ("I ask: what's the one metric that matters right now? If they say more than one, red flag.", "execution"),
        ("Hire for slope, not intercept. Early team velocity predicts everything.", "team"),
        ("The best startups have a secret - something non-obvious that's actually true.", "market"),
    ],
    "analyst": [
        ("I benchmark against the top quartile of comparable companies at this stage.", "financial"),
        ("My framework rates: technology 25%, market 25%, business model 25%, team 25%.", "market"),
        ("I look for disconfirming evidence first. If I can't find any, that's suspicious.", "contrarian"),
        ("I compare to every company that's attempted this in the last 10 years.", "market"),
        ("I weight published research and third-party data over self-reported metrics.", "financial"),
        ("I evaluate switching costs for existing customers. High switching costs equal real moat.", "competition"),
        ("If the TAM analysis uses top-down math only, I cut the number by 80%.", "financial"),
        ("Category creation is rare. I assume they're entering an existing market until proven otherwise.", "market"),
        ("I use a Gartner-style maturity model: where is this on the hype cycle?", "timing"),
        ("My analyst rating: STRONG BUY, BUY, HOLD, SELL, or STRONG SELL.", "financial"),
    ],
    "contrarian": [
        ("My default position is NO. The startup must prove me wrong.", "contrarian"),
        ("I ask: what kills this company? Then I check if the founders have an answer.", "execution"),
        ("If the business model requires regulatory approval, I assume it won't come.", "timing"),
        ("I look for the scenario where everything goes right and the company STILL fails.", "execution"),
        ("If the incumbent hasn't built this, either they're slow or it's not valuable.", "competition"),
        ("I short-sell the narrative and evaluate what's left after removing the hype.", "contrarian"),
        ("The riskiest companies are the ones that look perfect. Where's the hidden problem?", "contrarian"),
        ("I evaluate platform risk: if AWS/Google/Apple decides to compete, what happens?", "competition"),
        ("My contrarian check: is every VC excited about this? Then the upside is priced in.", "contrarian"),
        ("I find the single point of failure and estimate its probability.", "execution"),
    ],
    "wildcard": [
        ("I go with my gut. If it excites me, it probably excites others.", "market"),
        ("I ask: would I use this product every day?", "execution"),
        ("I evaluate: does this feel like the future or the past?", "timing"),
        ("I judge by whether the founder's eyes light up when they talk about the problem.", "team"),
        ("I don't have a framework. I just know quality when I see it.", "market"),
        ("My test: would I tell my friends about this unprompted?", "market"),
    ],
}

# ── Industry-Role Priority Mapping (contextual curation) ──

INDUSTRY_ROLE_PRIORITY = {
    "healthtech": {
        "investor": ["Bio VC", "Deep Tech VC", "Impact Investor (social)"],
        "customer": ["Enterprise CISO", "Enterprise Chief Data Officer", "Target Customer (F500 Enterprise)"],
        "operator": ["CTO (scaling stage)", "Chief Product Officer"],
        "analyst": ["PhD Researcher (domain-specific)", "ESG Analyst", "Academic Researcher (CS/AI)"],
        "contrarian": ["Regulatory Expert (federal)", "Regulatory Expert (EU/GDPR)", "Data Privacy Officer", "Insurance Underwriter"],
        "wildcard": ["Emergency Room Doctor", "NGO Worker (in the field)"],
    },
    "fintech": {
        "investor": ["Growth Equity VC", "Late-Stage VC", "Hedge Fund Analyst (long/short)"],
        "customer": ["Enterprise CISO", "VP Finance (buyer)", "Enterprise Procurement Manager"],
        "operator": ["CFO (venture-backed)", "Chief Revenue Officer"],
        "analyst": ["Equity Research Analyst (sell-side)", "Credit Rating Analyst", "Behavioral Economist"],
        "contrarian": ["Regulatory Expert (federal)", "Regulatory Expert (EU/GDPR)", "Antitrust Attorney", "Forensic Accountant"],
        "wildcard": ["Retired Executive (from this industry)"],
    },
    "ai": {
        "investor": ["Deep Tech VC", "Growth Equity VC", "Corporate VC (strategic)"],
        "customer": ["Enterprise Chief Data Officer", "Enterprise IT Director", "Target Customer (F500 Enterprise)"],
        "operator": ["CTO (scaling stage)", "VP Engineering (platform)", "Chief Product Officer"],
        "analyst": ["Academic Researcher (CS/AI)", "Technology Futurist", "Industry Analyst (Gartner)"],
        "contrarian": ["Open Source Maintainer (competing project)", "Big Tech PM (could build this)", "Platform Risk Analyst", "Cybersecurity Expert"],
        "wildcard": ["Philosopher of Technology", "High School Student (interested in the field)"],
    },
    "saas": {
        "investor": ["Series-A VC", "Series-B VC", "Growth Equity VC"],
        "customer": ["Enterprise IT Director", "VP Operations (buyer)", "Target Customer (Mid-Market)"],
        "operator": ["VP Sales (PLG/self-serve)", "Head of Growth", "VP Customer Success"],
        "analyst": ["Industry Analyst (Gartner)", "Industry Analyst (Forrester)", "UX Researcher"],
        "contrarian": ["Competitor CEO (well-funded startup)", "Big Tech PM (could build this)", "Platform Risk Analyst"],
        "wildcard": ["Stand-Up Comedian (BS detector)"],
    },
    "cleantech": {
        "investor": ["Impact Investor (climate)", "Deep Tech VC", "Sovereign Wealth Fund Manager"],
        "customer": ["Supply Chain Director", "Facilities Manager", "VP Operations (buyer)"],
        "operator": ["COO (operations-heavy)", "Supply Chain Operations Lead"],
        "analyst": ["ESG Analyst", "Macro Economist", "Technology Futurist"],
        "contrarian": ["Environmental Compliance Officer", "Government Policy Advisor", "Short Seller (activist)"],
        "wildcard": ["Farmer/Rancher", "Small-Town Mayor (dealing with this problem)"],
    },
    "cybersecurity": {
        "investor": ["Deep Tech VC", "Growth Equity VC", "Corporate VC (strategic)"],
        "customer": ["Enterprise CISO", "Enterprise IT Director", "Enterprise Chief Data Officer"],
        "operator": ["CTO (scaling stage)", "VP Engineering (platform)"],
        "analyst": ["Industry Analyst (Gartner)", "Industry Analyst (Forrester)"],
        "contrarian": ["Cybersecurity Expert", "Platform Risk Analyst", "Data Privacy Officer", "Big Tech PM (could build this)"],
        "wildcard": ["Military Logistics Officer"],
    },
    "marketplace": {
        "investor": ["Series-A VC", "Growth Equity VC", "Angel Investor (syndicate lead)"],
        "customer": ["Target Consumer (power user)", "Target Consumer (price-sensitive)", "Channel Partner (reseller)"],
        "operator": ["Head of Growth", "VP Sales (PLG/self-serve)", "CMO (B2C/DTC)"],
        "analyst": ["Behavioral Economist", "UX Researcher", "Industry Analyst (CB Insights)"],
        "contrarian": ["Competitor CEO (incumbent)", "Antitrust Attorney", "Platform Risk Analyst"],
        "wildcard": ["Gen-Z Early Adopter", "Stand-Up Comedian (BS detector)"],
    },
    "biotech": {
        "investor": ["Bio VC", "Deep Tech VC", "Impact Investor (social)"],
        "customer": ["Target Customer (F500 Enterprise)", "Enterprise Procurement Manager"],
        "operator": ["CTO (scaling stage)", "Chief Product Officer"],
        "analyst": ["PhD Researcher (domain-specific)", "Academic Researcher (CS/AI)", "ESG Analyst"],
        "contrarian": ["Regulatory Expert (federal)", "Patent Attorney (IP litigation)", "Insurance Underwriter"],
        "wildcard": ["Emergency Room Doctor", "NGO Worker (in the field)"],
    },
    "edtech": {
        "investor": ["Impact Investor (social)", "Seed VC", "Angel Investor (solo)"],
        "customer": ["Department Head (budget holder)", "Line Manager (end user)", "Target Customer (Mid-Market)"],
        "operator": ["CMO (B2C/DTC)", "Head of Growth", "VP Customer Success"],
        "analyst": ["Professor of Entrepreneurship", "UX Researcher", "Academic Researcher (economics)"],
        "contrarian": ["Regulatory Expert (federal)", "Data Privacy Officer", "Consumer Rights Advocate"],
        "wildcard": ["High School Student (interested in the field)", "Parent Evaluating For Family"],
    },
    "hardware": {
        "investor": ["Deep Tech VC", "Corporate VC (strategic)", "Venture Debt Provider"],
        "customer": ["Supply Chain Director", "Facilities Manager", "Enterprise Procurement Manager"],
        "operator": ["Supply Chain Operations Lead", "COO (operations-heavy)", "CTO (scaling stage)"],
        "analyst": ["Industry Analyst (Gartner)", "Technology Futurist"],
        "contrarian": ["Patent Attorney (IP litigation)", "Competitor CEO (incumbent)", "Short Seller (activist)"],
        "wildcard": ["Farmer/Rancher", "Military Logistics Officer"],
    },
}

INDUSTRY_KEYWORDS = {
    "healthtech": ["health", "medical", "pharma", "clinical", "biomedical", "hospital", "patient"],
    "fintech": ["fintech", "financial", "banking", "payment", "insurance", "insur", "lending"],
    "ai": ["ai", "artificial intelligence", "machine learning", "ml", "deep learning", "llm", "nlp"],
    "saas": ["saas", "software as a service", "cloud software", "b2b software"],
    "edtech": ["edtech", "education", "learning", "e-learning", "training", "school"],
    "cleantech": ["cleantech", "clean tech", "climate", "energy", "solar", "sustainability", "green", "water", "environment"],
    "cybersecurity": ["cybersecurity", "security", "infosec", "cyber"],
    "marketplace": ["marketplace", "platform", "two-sided", "e-commerce", "ecommerce"],
    "biotech": ["biotech", "biotechnology", "genomics", "therapeutics", "drug"],
    "hardware": ["hardware", "iot", "devices", "robotics", "semiconductor", "sensor"],
}

# Exclude clearly irrelevant roles from random allocation
INDUSTRY_ROLE_EXCLUSIONS = {
    "cleantech": ["Crypto VC", "Gaming", "Media", "Real Estate VC"],
    "healthtech": ["Crypto VC", "Real Estate VC", "Farmer/Rancher"],
    "fintech": ["Bio VC", "Farmer/Rancher", "Emergency Room"],
    "ai": [],
    "saas": ["Crypto VC", "Bio VC", "Farmer/Rancher"],
    "biotech": ["Crypto VC", "Real Estate VC", "Stand-Up Comedian"],
    "edtech": ["Crypto VC", "Short Seller", "Forensic Accountant"],
    "cybersecurity": ["Farmer/Rancher", "NGO Worker", "Crypto VC"],
    "marketplace": ["Bio VC", "Farmer/Rancher"],
    "hardware": ["Crypto VC"],
}

# Geographic regions for target market weighting
GEO_REGIONS = {
    "us": ["Silicon Valley", "San Francisco", "New York", "Boston", "Austin", "Miami"],
    "midwest_us": ["Chicago", "Austin", "Boston", "New York"],
    "europe": ["London", "Berlin", "Paris", "Amsterdam", "Stockholm"],
    "india": ["Bangalore", "Mumbai"],
    "southeast_asia": ["Singapore", "Jakarta"],
    "east_asia": ["Tokyo", "Seoul", "Beijing", "Shanghai", "Shenzhen"],
    "middle_east": ["Dubai", "Riyadh", "Tel Aviv"],
    "latam": ["Sao Paulo", "Mexico City"],
    "africa": ["Lagos", "Nairobi"],
}

# "Stay in your lane" directive appended to all generated persona prompts
LANE_DIRECTIVE = (
    "\n\nIMPORTANT: Focus your evaluation on YOUR specific domain of expertise. "
    "A patent attorney should analyze IP defensibility, not sales cycles. "
    "A customer should evaluate purchase intent, not investment returns. "
    "An operator should assess execution feasibility, not regulatory landscape. "
    "Stay in your lane - your unique perspective is more valuable than generic startup advice."
)

# Zone-specific evaluation angles — forces domain-specific vocabulary in reasoning
ZONE_EVAL_ANGLES = {
    "investor": (
        "Focus your reasoning on: return potential, check size justification, "
        "portfolio fit, exit path, and comparable valuations. "
        "Use investor terminology - IRR, MOIC, ownership dilution, cap table dynamics, "
        "deployment pace, reserve ratio, follow-on capacity."
    ),
    "customer": (
        "Focus your reasoning on: purchase intent, switching cost from your current solution, "
        "price sensitivity, implementation effort, and whether this solves a pain you face daily. "
        "Use buyer terminology - ROI payback period, TCO, integration timeline, vendor lock-in risk, "
        "procurement approval threshold, budget cycle timing."
    ),
    "operator": (
        "Focus your reasoning on: hiring difficulty for this specific tech stack and geography, "
        "technical architecture risks at 10x scale, operational bottlenecks, team composition gaps, "
        "and shipping velocity indicators. "
        "Use builder terminology - burn multiple, runway months, sprint cadence, technical debt load, "
        "org design, single points of failure, bus factor."
    ),
    "analyst": (
        "Focus your reasoning on: market sizing methodology, competitive positioning data, "
        "comparable company benchmarks at this stage, category dynamics, and historical base rates. "
        "Use analyst terminology - TAM/SAM/SOM with bottom-up validation, Gartner quadrant position, "
        "NPS benchmarks, cohort retention curves, magic number."
    ),
    "contrarian": (
        "Focus your reasoning on: specific regulatory citations by name, IP vulnerability with prior art references, "
        "platform dependency scenarios, unit economics breakdown with actual numbers, and concrete failure mode scenarios. "
        "Use adversarial terminology - attack surface, freedom-to-operate risk, margin compression triggers, "
        "regulatory exposure by jurisdiction, customer concentration risk."
    ),
    "wildcard": (
        "Focus your reasoning on: how this affects people like you personally, "
        "unexpected use cases or failure modes that professionals would miss, "
        "and honest gut-level reactions. "
        "Use plain language - no jargon, no frameworks, just real human perspective."
    ),
}


# ══════════════════════════════════════════════════════════════════
# PERSONA DATACLASS + ZONE DISTRIBUTION
# ══════════════════════════════════════════════════════════════════

@dataclass
class Persona:
    name: str
    prompt: str
    source: str  # "dataset", "personahub", "personahub_elite", or "generated"
    labels: List[str]
    zone: str = "wildcard"


ZONE_DISTRIBUTION = {
    10:  {"investor": 2, "customer": 2, "operator": 2, "analyst": 1, "contrarian": 1, "wildcard": 2},
    25:  {"investor": 6, "customer": 4, "operator": 4, "analyst": 3, "contrarian": 3, "wildcard": 5},
    50:  {"investor": 12, "customer": 8, "operator": 8, "analyst": 7, "contrarian": 7, "wildcard": 8},
    100: {"investor": 12, "customer": 15, "operator": 12, "analyst": 18, "contrarian": 18, "wildcard": 25},
    250: {"investor": 50, "customer": 40, "operator": 35, "analyst": 35, "contrarian": 35, "wildcard": 55},
}


# ══════════════════════════════════════════════════════════════════
# PERSONA ENGINE CLASS
# ══════════════════════════════════════════════════════════════════

class PersonaEngine:
    """Loads and selects personas for swarm prediction."""

    def __init__(self):
        self._index: Optional[Dict] = None
        self._dataset_available = os.path.exists(_PERSONAS_FILE)
        self._personahub_available = os.path.exists(_PERSONAHUB_FILE)
        self._personahub_elite_available = os.path.exists(_PERSONAHUB_ELITE_FILE)
        self._persona_count = 0
        self._personahub_count = 0
        self._personahub_elite_count = 0
        if self._dataset_available:
            self._persona_count = self._count_lines(_PERSONAS_FILE)
            logger.info(f"[Personas] FinePersonas loaded: {self._persona_count:,}")
        if self._personahub_available:
            self._personahub_count = self._count_lines(_PERSONAHUB_FILE)
            logger.info(f"[Personas] Tencent PersonaHub loaded: {self._personahub_count:,}")
        if self._personahub_elite_available:
            self._personahub_elite_count = self._count_lines(_PERSONAHUB_ELITE_FILE)
            logger.info(f"[Personas] Tencent PersonaHub Elite loaded: {self._personahub_elite_count:,}")
        total = self._persona_count + self._personahub_count + self._personahub_elite_count
        if total > 0:
            logger.info(f"[Personas] Total dataset personas: {total:,}")
        else:
            logger.info("[Personas] No datasets found, using trait-based generator")

    _cached_line_counts: Dict[str, int] = {}

    def _count_lines(self, filepath: str = _PERSONAS_FILE) -> int:
        if filepath in PersonaEngine._cached_line_counts:
            return PersonaEngine._cached_line_counts[filepath]
        try:
            import subprocess
            result = subprocess.run(['wc', '-l', filepath],
                                    capture_output=True, text=True, timeout=30)
            count = int(result.stdout.strip().split()[0])
            PersonaEngine._cached_line_counts[filepath] = count
            return count
        except Exception:
            try:
                with open(filepath, 'r') as f:
                    count = sum(1 for _ in f)
                PersonaEngine._cached_line_counts[filepath] = count
                return count
            except IOError:
                return 0

    def _load_index(self) -> Dict:
        if self._index is not None:
            return self._index
        try:
            with open(_INDEX_FILE, 'r') as f:
                self._index = json.load(f)
        except (IOError, json.JSONDecodeError):
            self._index = {}
        return self._index

    def _read_persona_at_line(self, line_num: int, filepath: str = _PERSONAS_FILE) -> Optional[Dict]:
        try:
            line = linecache.getline(filepath, line_num + 1)
            if line:
                return json.loads(line)
        except (json.JSONDecodeError, IOError):
            pass
        return None

    def _find_relevant_indices(self, keywords: List[str], limit: int) -> List[int]:
        index = self._load_index()
        matched = set()
        for kw in keywords:
            kw_lower = kw.lower().strip()
            for label, data in index.items():
                if kw_lower in label:
                    if isinstance(data, list):
                        matched.update(data[:limit])
                    elif isinstance(data, dict):
                        matched.update(data.get('sample', [])[:limit])
                    if len(matched) >= limit * 3:
                        break
        return list(matched)

    def select_personas(self, count: int, industry: str = "",
                        product: str = "", keywords: List[str] = None) -> List[Persona]:
        if keywords is None:
            keywords = []
        search_terms = list(keywords)
        if industry:
            search_terms.extend(industry.lower().split())
        if product:
            search_terms.extend([w for w in product.lower().split() if len(w) > 3])
        search_terms.extend([
            "business", "finance", "investment", "startup", "entrepreneur",
            "marketing", "technology", "management", "strategy", "economics",
            "customer", "consumer", "product", "market", "sales",
        ])

        personas: List[Persona] = []
        total_dataset = self._persona_count + self._personahub_count + self._personahub_elite_count
        if total_dataset > 0:
            elite_count = int(count * 0.10) if self._personahub_elite_count > 0 else 0
            hub_count = int(count * 0.30) if self._personahub_count > 0 else 0
            fine_count = int(count * 0.30) if self._persona_count > 0 else 0
            generated_count = count - elite_count - hub_count - fine_count

            if elite_count > 0 and self._personahub_elite_count > 0:
                for idx in random.sample(range(self._personahub_elite_count), min(elite_count, self._personahub_elite_count)):
                    data = self._read_persona_at_line(idx, _PERSONAHUB_ELITE_FILE)
                    if data:
                        desc = data.get('description', data.get('persona', ''))
                        elite_domain = data.get('elite_general', '') or data.get('elite_specific', '')
                        full_desc = f"{desc} (Domain expert: {elite_domain})" if elite_domain else desc
                        personas.append(Persona(name=desc[:80], prompt=self._dataset_persona_to_prompt(full_desc), source="personahub_elite", labels=data.get('labels', [])))

            if hub_count > 0 and self._personahub_count > 0:
                for idx in random.sample(range(self._personahub_count), min(hub_count, self._personahub_count)):
                    data = self._read_persona_at_line(idx, _PERSONAHUB_FILE)
                    if data:
                        desc = data.get('description', data.get('persona', ''))
                        personas.append(Persona(name=desc[:80], prompt=self._dataset_persona_to_prompt(desc), source="personahub", labels=data.get('labels', [])))

            if fine_count > 0 and self._persona_count > 0:
                relevant_indices = self._find_relevant_indices(search_terms, fine_count * 2)
                relevant_take = int(fine_count * 0.6)
                random_take = fine_count - relevant_take
                if relevant_indices:
                    for idx in random.sample(relevant_indices, min(relevant_take, len(relevant_indices))):
                        data = self._read_persona_at_line(idx)
                        if data:
                            personas.append(Persona(name=data.get('persona', data.get('description', ''))[:80], prompt=self._dataset_persona_to_prompt(data.get('persona', data.get('description', ''))), source="dataset", labels=data.get('labels', [])))
                for idx in random.sample(range(self._persona_count), min(random_take, self._persona_count)):
                    data = self._read_persona_at_line(idx)
                    if data:
                        personas.append(Persona(name=data.get('persona', data.get('description', ''))[:80], prompt=self._dataset_persona_to_prompt(data.get('persona', data.get('description', ''))), source="dataset", labels=data.get('labels', [])))

            personas.extend(self._generate_personas(generated_count))
        else:
            personas = self._generate_personas(count)

        while len(personas) < count:
            personas.extend(self._generate_personas(count - len(personas)))
        personas = personas[:count]
        random.shuffle(personas)
        return personas

    @staticmethod
    def _dataset_persona_to_prompt(persona_text: str, zone: str = "wildcard") -> str:
        zone_pressure = PersonaEngine.ZONE_PROMPTS.get(zone, PersonaEngine.ZONE_PROMPTS.get("wildcard", ""))
        return f"You are: {persona_text}\n\n{zone_pressure}"

    # Zone-specific evaluation pressure
    ZONE_PROMPTS = {
        "investor": (
            "You are deciding whether to invest YOUR OWN MONEY in this startup. "
            "Score 8+ ONLY if you would write a check today. Score 3 or below if you see "
            "red flags that would make you walk away. Be decisive - VCs don't give 5/10 scores, "
            "they either fund or pass. What's your conviction level?"
        ),
        "customer": (
            "You are a potential BUYER of this product. Would you pay for it? "
            "Would you switch from your current solution? Score based on your actual "
            "purchase intent: 8+ means you'd sign today, 3 or below means you'd never use it. "
            "Think about price, switching cost, and whether this solves a real pain you have."
        ),
        "operator": (
            "You would be BUILDING and RUNNING this company. Score based on execution feasibility. "
            "What breaks first at scale? Can this team actually ship? Score 8+ only if you'd quit "
            "your job to join. Score 3 or below if you see fundamental execution problems. "
            "Be specific about what would fail."
        ),
        "analyst": (
            "You are writing a PUBLISHED REPORT on this company for institutional investors. "
            "Compare this to the top 3 companies in the space. Score relative to market leaders, "
            "not in isolation. Score 8+ only for clear category leaders. Score 3 or below for "
            "companies with no defensible position. Your reputation depends on accuracy."
        ),
        "contrarian": (
            "Your job is to find the FATAL FLAW. What will kill this company in 18 months? "
            "Default to skepticism - score 5 or below unless the startup proves you wrong. "
            "Look for: regulatory risk, competitive moats that don't exist, unit economics that "
            "don't work, team gaps, timing problems. Be the person who saved investors from Juicero."
        ),
        "wildcard": (
            "React from your unique life experience. Don't try to be balanced or professional. "
            "Would this startup matter to someone like you? Score based on gut feeling - "
            "high if it excites you, low if it feels like a solution looking for a problem. "
            "The most valuable feedback is the unexpected kind."
        ),
    }

    @staticmethod
    def _generate_personas(count: int, zone: str = "wildcard", startup_industry: str = "",
                           priority_roles: Optional[List[str]] = None,
                           target_market: str = "") -> List[Persona]:
        """Generate personas with behavioral depth across 11 dimensions.
        priority_roles: if provided, 60% of slots use these roles (industry-curated)."""
        personas = []
        zone_roles = ZONE_ROLES.get(zone, [])
        zone_pressure = PersonaEngine.ZONE_PROMPTS.get(zone, PersonaEngine.ZONE_PROMPTS["wildcard"])
        focus_industry = startup_industry if startup_industry else random.choice(INDUSTRY_FOCUS)

        # Zone-specific pools
        fund_pool = FUND_CONTEXT.get(zone, [])
        backstory_pool = BACKSTORIES.get(zone, [])
        framework_pool = DECISION_FRAMEWORKS.get(zone, [])

        # Priority role selection: first 60% use curated roles
        priority_cutoff = int(count * 0.6) if priority_roles else 0
        used_roles = set()  # Dedup: avoid repeat roles within a zone

        for i in range(count):
            if i < priority_cutoff and priority_roles:
                valid_priority = [r for r in priority_roles if r in zone_roles] if zone_roles else priority_roles
                if valid_priority:
                    role = valid_priority[i % len(valid_priority)]
                else:
                    role = random.choice(zone_roles) if zone_roles else random.choice(ROLES)
            else:
                # Random slot — filter out extreme industry mismatches
                available = list(zone_roles) if zone_roles else list(ROLES)
                if startup_industry:
                    ind_key = PersonaEngine._match_industry_key(startup_industry)
                    exclusions = INDUSTRY_ROLE_EXCLUSIONS.get(ind_key, [])
                    if exclusions:
                        available = [r for r in available if not any(ex.lower() in r.lower() for ex in exclusions)]
                    if not available:
                        available = list(zone_roles) if zone_roles else list(ROLES)
                role = random.choice(available)

            # Dedup: try to pick a unique role (up to 5 retries)
            attempts = 0
            all_available = list(zone_roles) if zone_roles else list(ROLES)
            while role in used_roles and attempts < 5 and len(all_available) > len(used_roles):
                role = random.choice(all_available)
                attempts += 1
            used_roles.add(role)
            mbti = random.choice(MBTI_TYPES)
            risk = random.choice(RISK_PROFILES)
            # Geography — weight customer zone toward target market
            if zone == 'customer' and target_market:
                region = PersonaEngine._match_geo_region(target_market)
                region_geos = GEO_REGIONS.get(region, []) if region else []
                if region_geos and random.random() < 0.7:
                    geo = random.choice(region_geos)
                else:
                    geo = random.choice(GEOGRAPHIC_LENS)
            else:
                geo = random.choice(GEOGRAPHIC_LENS)

            # Experience with role compatibility
            min_exp_idx = ROLE_MIN_EXPERIENCE.get(role, 0)
            valid_exp = EXPERIENCE_LEVELS[min_exp_idx:]
            exp = random.choice(valid_exp)

            # Bias and framework with anti-redundancy
            bias_text, bias_cat = random.choice(BIASES)
            if framework_pool:
                # Filter to frameworks in different categories
                compatible = [(f, c) for f, c in framework_pool if c != bias_cat]
                if not compatible:
                    compatible = framework_pool  # fallback if all same category
                framework_text, _ = random.choice(compatible)
            else:
                framework_text = ""

            # MBTI behavioral description
            mbti_desc = MBTI_BEHAVIORAL.get(mbti, "")

            # Geographic behavioral note
            geo_desc = GEO_BEHAVIORAL.get(geo, "")

            # Fund/budget context
            fund_context = random.choice(fund_pool) if fund_pool else ""

            # Portfolio composition (investor-only)
            portfolio_context = ""
            if zone == "investor":
                portfolio_context = " " + random.choice(PORTFOLIO_CONTEXT)

            # Backstory
            backstory = random.choice(backstory_pool) if backstory_pool else ""

            # Name: concise for PDF display
            name = f"{role} ({mbti}, {geo})"
            if len(name) > 80:
                max_role = 80 - len(f" ({mbti}, {geo})")
                name = f"{role[:max_role]}.. ({mbti}, {geo})"

            # Build the rich prompt
            parts = [f"You are a {role} based in {geo} with {exp} of experience.{fund_context}{portfolio_context}"]

            if geo_desc:
                parts.append(f"\nYour geographic lens: {geo_desc}")

            if mbti_desc:
                parts.append(f"\nYour evaluation style: {mbti_desc}")

            parts.append(f"\nYour risk profile: {risk}.")
            parts.append(f"\nYour natural bias: you are {bias_text}.")

            if backstory:
                parts.append(f'\nYour experience: "{backstory}"')

            if framework_text:
                parts.append(f'\nYour decision framework: "{framework_text}"')

            parts.append(f"\nYour primary industry focus is {focus_industry}.")
            parts.append(f"\n{zone_pressure}")
            parts.append(LANE_DIRECTIVE)

            prompt = "\n".join(parts)

            personas.append(Persona(
                name=name,
                prompt=prompt,
                source="generated",
                labels=[role, focus_industry, geo],
                zone=zone,
            ))
        return personas

    @staticmethod
    def _match_industry_key(industry: str) -> Optional[str]:
        """Fuzzy-match an industry string to an INDUSTRY_ROLE_PRIORITY key."""
        if not industry:
            return None
        industry_lower = industry.lower().strip()
        # Direct match
        if industry_lower in INDUSTRY_ROLE_PRIORITY:
            return industry_lower
        # Keyword match
        for key, keywords in INDUSTRY_KEYWORDS.items():
            if any(kw in industry_lower for kw in keywords):
                return key
        return None

    @staticmethod
    def _match_geo_region(target_market: str) -> Optional[str]:
        """Match target market text to a geographic region for persona weighting."""
        if not target_market:
            return None
        tm = target_market.lower()
        if any(w in tm for w in ['us', 'united states', 'america', 'midwest', 'conservation district', 'municipality', 'municipal']):
            if any(w in tm for w in ['midwest', 'upper midwest', 'dakota', 'minnesota', 'iowa', 'wisconsin']):
                return 'midwest_us'
            return 'us'
        if any(w in tm for w in ['india', 'bangalore', 'mumbai', 'delhi']):
            return 'india'
        if any(w in tm for w in ['europe', 'eu', 'uk', 'london', 'germany', 'france', 'nordic']):
            return 'europe'
        if any(w in tm for w in ['china', 'beijing', 'shanghai', 'japan', 'tokyo', 'korea', 'seoul']):
            return 'east_asia'
        if any(w in tm for w in ['singapore', 'indonesia', 'vietnam', 'thailand', 'southeast asia']):
            return 'southeast_asia'
        if any(w in tm for w in ['dubai', 'saudi', 'uae', 'israel', 'tel aviv']):
            return 'middle_east'
        if any(w in tm for w in ['brazil', 'mexico', 'latin america', 'latam']):
            return 'latam'
        if any(w in tm for w in ['africa', 'nigeria', 'kenya', 'lagos']):
            return 'africa'
        return None

    def select_personas_by_zone(self, count: int, industry: str = "",
                                 product: str = "") -> List[Persona]:
        dist_key = min(ZONE_DISTRIBUTION.keys(), key=lambda x: abs(x - count))
        distribution = ZONE_DISTRIBUTION[dist_key]

        total_dist = sum(distribution.values())
        if total_dist != count:
            scale = count / total_dist
            scaled = {z: max(1, round(n * scale)) for z, n in distribution.items()}
            diff = count - sum(scaled.values())
            if diff > 0:
                scaled["wildcard"] += diff
            elif diff < 0:
                for z in ["wildcard", "analyst", "contrarian"]:
                    remove = min(-diff, scaled[z] - 1)
                    scaled[z] -= remove
                    diff += remove
                    if diff >= 0:
                        break
            distribution = scaled

        # Look up industry-specific priority roles
        industry_key = self._match_industry_key(industry)
        industry_priorities = INDUSTRY_ROLE_PRIORITY.get(industry_key, {}) if industry_key else {}
        if industry_key:
            logger.info(f"[Personas] Industry match: '{industry}' -> '{industry_key}' (curated roles active)")

        all_personas: List[Persona] = []

        for zone, zone_count in distribution.items():
            if zone == "wildcard":
                wild = self.select_personas(zone_count, industry, product)
                for p in wild:
                    p.zone = "wildcard"
                all_personas.extend(wild)
            else:
                zone_priority = industry_priorities.get(zone, None)
                zone_personas = self._generate_personas(
                    zone_count, zone=zone, startup_industry=industry,
                    priority_roles=zone_priority, target_market=product
                )
                all_personas.extend(zone_personas)

        logger.info(f"[Personas] Zone distribution: {', '.join(f'{z}={n}' for z, n in distribution.items())}")
        random.shuffle(all_personas)
        return all_personas[:count]
