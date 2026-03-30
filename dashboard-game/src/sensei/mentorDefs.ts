/**
 * Sensei (先生) — Mentor Type Definitions
 *
 * 18 mentor types organized by category.
 * Maps to backend MENTOR_TYPES in mentor_session.py.
 */

export interface MentorDef {
  id: string
  name: string
  tagline: string
  zone: string
  category: 'investor' | 'customer' | 'operator' | 'expert' | 'challenge' | 'perspective'
  icon: string  // emoji for menu display
  color: string // accent color
}

export const MENTOR_DEFS: MentorDef[] = [
  // Investor Mentors
  { id: 'seed_vc', name: 'Seed VC Mentor', tagline: 'Should you raise? How much? From whom?', zone: 'investor', category: 'investor', icon: '💰', color: '#2e7d32' },
  { id: 'growth_vc', name: 'Growth VC Mentor', tagline: 'How to scale from $1M to $10M ARR', zone: 'investor', category: 'investor', icon: '📈', color: '#2e7d32' },
  { id: 'angel', name: 'Angel Investor Mentor', tagline: 'Is your story compelling enough for a check?', zone: 'investor', category: 'investor', icon: '👼', color: '#2e7d32' },

  // Customer Mentors
  { id: 'enterprise_buyer', name: 'Enterprise Buyer', tagline: 'Would I buy this? What\'s my objection?', zone: 'customer', category: 'customer', icon: '🏢', color: '#1565c0' },
  { id: 'smb_owner', name: 'SMB Owner', tagline: 'Would my 50-person company use this?', zone: 'customer', category: 'customer', icon: '🏪', color: '#1565c0' },
  { id: 'end_user', name: 'Target End-User', tagline: 'Does this solve my daily pain?', zone: 'customer', category: 'customer', icon: '👤', color: '#1565c0' },

  // Operator Mentors
  { id: 'startup_cto', name: 'CTO Mentor', tagline: 'Can you build this? What breaks at scale?', zone: 'operator', category: 'operator', icon: '⚙️', color: '#e65100' },
  { id: 'cmo_growth', name: 'CMO / Growth Mentor', tagline: 'How do you acquire your first 100 customers?', zone: 'operator', category: 'operator', icon: '📣', color: '#e65100' },
  { id: 'startup_cfo', name: 'CFO Mentor', tagline: 'Do your numbers work? What\'s your burn?', zone: 'operator', category: 'operator', icon: '📊', color: '#e65100' },

  // Expert Mentors
  { id: 'industry_analyst', name: 'Industry Analyst', tagline: 'Where does this fit in the market landscape?', zone: 'analyst', category: 'expert', icon: '🔬', color: '#6a1b9a' },
  { id: 'domain_expert', name: 'Domain Expert', tagline: 'Deep expertise in your specific industry', zone: 'analyst', category: 'expert', icon: '🎓', color: '#6a1b9a' },
  { id: 'regulatory_expert', name: 'Regulatory Expert', tagline: 'What legal/compliance risks should you know?', zone: 'analyst', category: 'expert', icon: '⚖️', color: '#6a1b9a' },

  // Challenge Mentors
  { id: 'devils_advocate', name: 'Devil\'s Advocate', tagline: 'Here\'s why this will fail. Convince me otherwise.', zone: 'contrarian', category: 'challenge', icon: '😈', color: '#c62828' },
  { id: 'competitor_ceo', name: 'Competitor CEO', tagline: 'I\'m your biggest competitor. What stops me?', zone: 'contrarian', category: 'challenge', icon: '🥊', color: '#c62828' },

  // Perspective Mentors
  { id: 'behavioral_economist', name: 'Behavioral Economist', tagline: 'Will users actually change their behavior?', zone: 'wildcard', category: 'perspective', icon: '🧠', color: '#00838f' },
  { id: 'brand_strategist', name: 'Brand Strategist', tagline: 'What\'s your narrative? Can you build a brand?', zone: 'wildcard', category: 'perspective', icon: '✨', color: '#00838f' },
  { id: 'market_timer', name: 'Market Timer', tagline: 'Is now the right moment? Too early? Too late?', zone: 'wildcard', category: 'perspective', icon: '⏰', color: '#00838f' },
  { id: 'impact_investor', name: 'Impact Investor', tagline: 'What\'s the social/environmental angle?', zone: 'investor', category: 'perspective', icon: '🌍', color: '#00838f' },
]

export const MENTOR_CATEGORIES = [
  { key: 'investor', label: 'Investor Mentors', description: 'Fundraising, valuation, investor relations' },
  { key: 'customer', label: 'Customer Mentors', description: 'Purchase intent, pricing, adoption' },
  { key: 'operator', label: 'Operator Mentors', description: 'Building, scaling, team, finances' },
  { key: 'expert', label: 'Expert Mentors', description: 'Market analysis, domain, regulatory' },
  { key: 'challenge', label: 'Challenge Mentors', description: 'Stress-test your assumptions' },
  { key: 'perspective', label: 'Perspective Mentors', description: 'Unconventional viewpoints' },
]

export const MAX_MENTORS = 6
export const MIN_MENTORS = 3
export const SESSION_DURATION_MINUTES = 15
