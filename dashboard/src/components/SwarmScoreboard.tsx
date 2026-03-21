import { useState, useEffect } from 'react'
import { mirai, type SwarmResult } from '../miraiApi'

interface SwarmState {
  running: boolean
  totalAgents: number
  agentsCompleted: number
  positivePct: number
  negativePct: number
  avgConfidence: number
  recentVotes: Array<{ id: number; persona: string; vote: string; confidence: number; reasoning: string }>
  result: SwarmResult | null
}

interface StartupForm {
  companyName: string
  industry: string
  product: string
  targetMarket: string
  businessModel: string
  stage: string
  fundingRaised: string
  traction: string
  team: string
  ask: string
  competitiveAdvantage: string
}

const INDUSTRIES = [
  'SaaS', 'FinTech', 'HealthTech', 'EdTech', 'LegalTech', 'CleanTech',
  'DeepTech', 'AI/ML', 'Cybersecurity', 'E-Commerce', 'Marketplace',
  'Consumer', 'Enterprise', 'BioTech', 'PropTech', 'InsurTech',
  'AgriTech', 'FoodTech', 'Gaming', 'Media', 'HRTech', 'Web3',
  'Robotics', 'Logistics', 'SpaceTech', 'RetailTech', 'Other',
]

const STAGES = [
  'Pre-seed', 'Seed', 'Series A', 'Series B', 'Series C', 'Growth', 'Pre-IPO',
]

const EMPTY_FORM: StartupForm = {
  companyName: '', industry: '', product: '', targetMarket: '',
  businessModel: '', stage: '', fundingRaised: '', traction: '',
  team: '', ask: '', competitiveAdvantage: '',
}

function formToExecSummary(f: StartupForm): string {
  const lines = [
    `Company: ${f.companyName}`,
    `Industry: ${f.industry}`,
    `Product: ${f.product}`,
    `Target Market: ${f.targetMarket}`,
    `Business Model: ${f.businessModel}`,
    `Stage: ${f.stage}`,
  ]
  if (f.fundingRaised) lines.push(`Funding Raised: ${f.fundingRaised}`)
  if (f.traction) lines.push(`Traction: ${f.traction}`)
  if (f.team) lines.push(`Team: ${f.team}`)
  if (f.ask) lines.push(`Ask: ${f.ask}`)
  if (f.competitiveAdvantage) lines.push(`Competitive Advantage: ${f.competitiveAdvantage}`)
  return lines.join('. ')
}

function isFormValid(f: StartupForm): boolean {
  return !!(f.companyName.trim() && f.industry.trim() && f.product.trim() &&
    f.targetMarket.trim() && f.businessModel.trim() && f.stage.trim())
}

// Shared styles
const inputStyle: React.CSSProperties = {
  background: '#0d0d1a', color: '#e0e0e0', border: '1px solid #333',
  padding: '9px 12px', fontSize: 15, borderRadius: 5, outline: 'none',
  width: '100%', boxSizing: 'border-box',
}
const labelStyle: React.CSSProperties = {
  fontSize: 13, color: '#999', marginBottom: 4, display: 'block', fontWeight: 500,
}
const requiredDot: React.CSSProperties = {
  color: '#ff4444', marginLeft: 2,
}
const stopProp = {
  onPointerDown: (e: React.PointerEvent) => e.stopPropagation(),
  onMouseDown: (e: React.MouseEvent) => e.stopPropagation(),
}

export function SwarmScoreboard() {
  const [state, setState] = useState<SwarmState>({
    running: false, totalAgents: 0, agentsCompleted: 0,
    positivePct: 0, negativePct: 0, avgConfidence: 0,
    recentVotes: [], result: null,
  })
  const [form, setForm] = useState<StartupForm>(EMPTY_FORM)
  const [agentCount, setAgentCount] = useState(100)
  const [connected, setConnected] = useState(false)

  const updateField = (field: keyof StartupForm, value: string) =>
    setForm(prev => ({ ...prev, [field]: value }))

  useEffect(() => {
    mirai.connect(`ws://${window.location.hostname}:5000/ws/swarm`)
    const unsub = mirai.onMessage((msg) => {
      switch (msg.type) {
        case 'connected': setConnected(true); break
        case 'swarmStarted':
          setState(prev => ({ ...prev, running: true, totalAgents: msg.totalAgents,
            agentsCompleted: 0, positivePct: 0, negativePct: 0, recentVotes: [], result: null }))
          break
        case 'agentVoted':
          setState(prev => ({ ...prev, agentsCompleted: prev.agentsCompleted + 1,
            recentVotes: [
              { id: msg.id, persona: '', vote: msg.vote, confidence: msg.confidence, reasoning: msg.reasoning },
              ...prev.recentVotes.slice(0, 14),
            ]}))
          break
        case 'swarmProgress':
          setState(prev => ({ ...prev, agentsCompleted: msg.agentsCompleted,
            positivePct: msg.positivePct, negativePct: msg.negativePct, avgConfidence: msg.avgConfidence }))
          break
        case 'swarmComplete':
          setState(prev => ({ ...prev, running: false, result: msg.result,
            positivePct: msg.result.positivePct, negativePct: msg.result.negativePct,
            avgConfidence: msg.result.avgConfidence, agentsCompleted: msg.result.totalAgents }))
          break
      }
    })
    return () => { unsub(); mirai.disconnect() }
  }, [])

  const handleStart = () => {
    if (!isFormValid(form)) return
    mirai.startSwarm(formToExecSummary(form), agentCount)
  }

  const progressPct = state.totalAgents > 0
    ? Math.round((state.agentsCompleted / state.totalAgents) * 100) : 0

  return (
    <div
      className="mirai-panel"
      onPointerDown={(e) => e.stopPropagation()}
      onMouseDown={(e) => e.stopPropagation()}
      onClick={(e) => e.stopPropagation()}
      style={{
        position: 'fixed', top: 0, right: 0,
        width: 'min(480px, 40vw)', minWidth: 340,
        height: '100vh', background: 'rgba(8, 8, 24, 0.97)',
        color: '#e0e0e0',
        fontSize: 'clamp(13px, 1.3vw, 17px)',
        padding: 'clamp(14px, 2vw, 26px)',
        overflowY: 'auto', borderLeft: '3px solid #1a1a4e', zIndex: 1000,
        display: 'flex', flexDirection: 'column',
        gap: 'clamp(10px, 1.2vw, 18px)',
        boxShadow: '-4px 0 20px rgba(0, 0, 0, 0.5)',
      }}>

      {/* Header */}
      <div style={{ textAlign: 'center', borderBottom: '1px solid #222', paddingBottom: 12 }}>
        <div style={{ fontSize: 'clamp(18px, 2vw, 24px)', fontWeight: 'bold', color: '#00ff88', letterSpacing: 4 }}>
          MIRAI SWARM
        </div>
        <div style={{ fontSize: 11, marginTop: 4, color: connected ? '#00ff88' : '#ff4444' }}>
          {connected ? '● CONNECTED' : '○ DISCONNECTED'}
        </div>
      </div>

      {/* ── Structured Form ── */}
      {!state.running && !state.result && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ fontSize: 13, color: '#aaa', fontWeight: 'bold' }}>Startup Details</div>

          {/* Company Name */}
          <div>
            <label style={labelStyle}>Company Name<span style={requiredDot}>*</span></label>
            <input value={form.companyName} onChange={e => updateField('companyName', e.target.value)}
              placeholder="e.g. LegalLens AI" style={inputStyle} {...stopProp} />
          </div>

          {/* Industry */}
          <div>
            <label style={labelStyle}>Industry<span style={requiredDot}>*</span></label>
            <select value={form.industry} onChange={e => updateField('industry', e.target.value)}
              style={{ ...inputStyle, cursor: 'pointer' }} {...stopProp}>
              <option value="">Select industry...</option>
              {INDUSTRIES.map(i => <option key={i} value={i}>{i}</option>)}
            </select>
          </div>

          {/* Product */}
          <div>
            <label style={labelStyle}>Product / Service<span style={requiredDot}>*</span></label>
            <textarea value={form.product} onChange={e => updateField('product', e.target.value)}
              placeholder="What does your product do? Key differentiator?"
              rows={2} style={{ ...inputStyle, resize: 'vertical' }} {...stopProp} />
          </div>

          {/* Target Market */}
          <div>
            <label style={labelStyle}>Target Market<span style={requiredDot}>*</span></label>
            <input value={form.targetMarket} onChange={e => updateField('targetMarket', e.target.value)}
              placeholder="e.g. Mid-size law firms (50-200 attorneys)"
              style={inputStyle} {...stopProp} />
          </div>

          {/* Business Model */}
          <div>
            <label style={labelStyle}>Business Model<span style={requiredDot}>*</span></label>
            <input value={form.businessModel} onChange={e => updateField('businessModel', e.target.value)}
              placeholder="e.g. SaaS, $500/seat/month"
              style={inputStyle} {...stopProp} />
          </div>

          {/* Stage */}
          <div>
            <label style={labelStyle}>Stage<span style={requiredDot}>*</span></label>
            <select value={form.stage} onChange={e => updateField('stage', e.target.value)}
              style={{ ...inputStyle, cursor: 'pointer' }} {...stopProp}>
              <option value="">Select stage...</option>
              {STAGES.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>

          {/* Funding */}
          <div>
            <label style={labelStyle}>Funding Raised</label>
            <input value={form.fundingRaised} onChange={e => updateField('fundingRaised', e.target.value)}
              placeholder="e.g. $2M seed round" style={inputStyle} {...stopProp} />
          </div>

          {/* Traction */}
          <div>
            <label style={labelStyle}>Traction</label>
            <textarea value={form.traction} onChange={e => updateField('traction', e.target.value)}
              placeholder="Customers, ARR, retention, growth rate..."
              rows={2} style={{ ...inputStyle, resize: 'vertical' }} {...stopProp} />
          </div>

          {/* Team */}
          <div>
            <label style={labelStyle}>Team</label>
            <input value={form.team} onChange={e => updateField('team', e.target.value)}
              placeholder="Key team backgrounds" style={inputStyle} {...stopProp} />
          </div>

          {/* Ask */}
          <div>
            <label style={labelStyle}>Ask</label>
            <input value={form.ask} onChange={e => updateField('ask', e.target.value)}
              placeholder="e.g. Series A, $10M at $40M pre-money"
              style={inputStyle} {...stopProp} />
          </div>

          {/* Competitive Advantage */}
          <div>
            <label style={labelStyle}>Competitive Advantage</label>
            <input value={form.competitiveAdvantage} onChange={e => updateField('competitiveAdvantage', e.target.value)}
              placeholder="Moat, proprietary tech, unique data..."
              style={inputStyle} {...stopProp} />
          </div>

          {/* Agent Count + Start */}
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginTop: 4 }}>
            <select value={agentCount} onChange={e => setAgentCount(Number(e.target.value))}
              style={{ ...inputStyle, width: 'auto', cursor: 'pointer' }} {...stopProp}>
              {[50, 100, 250, 500, 1000].map(n => (
                <option key={n} value={n}>{n} agents</option>
              ))}
            </select>
            <button onClick={handleStart} disabled={!isFormValid(form)}
              style={{
                flex: 1, background: isFormValid(form) ? '#00ff88' : '#222',
                color: isFormValid(form) ? '#000' : '#555', border: 'none',
                padding: '10px 16px', fontSize: 15, fontWeight: 'bold',
                cursor: isFormValid(form) ? 'pointer' : 'default',
                borderRadius: 6, letterSpacing: 2, transition: 'background 0.2s',
              }}>
              START PREDICTION
            </button>
          </div>

          <div style={{ fontSize: 10, color: '#444', textAlign: 'center' }}>
            <span style={{ color: '#ff4444' }}>*</span> Required fields
          </div>
        </div>
      )}

      {/* ── Running / Results ── */}
      {(state.running || state.result) && (
        <>
          {/* Progress Bar */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 13 }}>
              <span>PROGRESS</span>
              <span style={{ color: '#ffaa00' }}>{state.agentsCompleted} / {state.totalAgents}</span>
            </div>
            <div style={{ background: '#0d0d1a', height: 18, borderRadius: 4, overflow: 'hidden', border: '1px solid #222' }}>
              <div style={{
                width: `${progressPct}%`, height: '100%',
                background: state.running
                  ? 'linear-gradient(90deg, #ff8800, #ffaa00)'
                  : 'linear-gradient(90deg, #00cc66, #00ff88)',
                transition: 'width 0.3s',
              }} />
            </div>
          </div>

          {/* Consensus */}
          <div style={{
            display: 'flex', gap: 16, justifyContent: 'center',
            padding: '14px 0', borderTop: '1px solid #1a1a2e', borderBottom: '1px solid #1a1a2e',
          }}>
            <div style={{ textAlign: 'center', flex: 1 }}>
              <div style={{ fontSize: 'clamp(24px, 3vw, 40px)', fontWeight: 'bold', color: '#00ff88' }}>
                {state.positivePct}%
              </div>
              <div style={{ fontSize: 11, color: '#00cc66', letterSpacing: 2 }}>POSITIVE</div>
            </div>
            <div style={{ width: 1, background: '#222' }} />
            <div style={{ textAlign: 'center', flex: 1 }}>
              <div style={{ fontSize: 'clamp(24px, 3vw, 40px)', fontWeight: 'bold', color: '#ff4444' }}>
                {state.negativePct}%
              </div>
              <div style={{ fontSize: 11, color: '#cc3333', letterSpacing: 2 }}>NEGATIVE</div>
            </div>
            <div style={{ width: 1, background: '#222' }} />
            <div style={{ textAlign: 'center', flex: 1 }}>
              <div style={{ fontSize: 'clamp(24px, 3vw, 40px)', fontWeight: 'bold', color: '#ffaa00' }}>
                {state.avgConfidence > 0 ? (state.avgConfidence * 100).toFixed(0) : '—'}%
              </div>
              <div style={{ fontSize: 11, color: '#cc8800', letterSpacing: 2 }}>CONFIDENCE</div>
            </div>
          </div>

          {/* Final Results */}
          {state.result && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div>
                <div style={{ color: '#00ff88', fontSize: 12, fontWeight: 'bold', marginBottom: 6 }}>POSITIVE THEMES</div>
                {state.result.keyThemesPositive.slice(0, 6).map((t, i) => (
                  <div key={i} style={{ color: '#aaa', padding: '2px 0 2px 10px', fontSize: 12, borderLeft: '2px solid #00ff88' }}>{t}</div>
                ))}
              </div>
              <div>
                <div style={{ color: '#ff4444', fontSize: 12, fontWeight: 'bold', marginBottom: 6 }}>NEGATIVE THEMES</div>
                {state.result.keyThemesNegative.slice(0, 6).map((t, i) => (
                  <div key={i} style={{ color: '#aaa', padding: '2px 0 2px 10px', fontSize: 12, borderLeft: '2px solid #ff4444' }}>{t}</div>
                ))}
              </div>
              {state.result.contestedThemes.length > 0 && (
                <div>
                  <div style={{ color: '#ffaa00', fontSize: 12, fontWeight: 'bold', marginBottom: 6 }}>CONTESTED</div>
                  {state.result.contestedThemes.map((t, i) => (
                    <div key={i} style={{ color: '#aaa', padding: '2px 0 2px 10px', fontSize: 12, borderLeft: '2px solid #ffaa00' }}>{t}</div>
                  ))}
                </div>
              )}
              <div style={{ fontSize: 11, color: '#555', borderTop: '1px solid #1a1a2e', paddingTop: 8 }}>
                <div>Models: {state.result.modelsUsed.join(', ')}</div>
                <div>Time: {state.result.executionTimeSeconds}s</div>
              </div>
              <button
                onClick={() => { setState(prev => ({ ...prev, result: null, running: false, agentsCompleted: 0, totalAgents: 0 })); setForm(EMPTY_FORM) }}
                style={{
                  width: '100%', background: '#1a1a2e', color: '#e0e0e0',
                  border: '1px solid #333', padding: '10px 16px', fontSize: 13,
                  cursor: 'pointer', borderRadius: 6,
                }}>
                NEW PREDICTION
              </button>
            </div>
          )}

          {/* Live Feed */}
          {state.running && state.recentVotes.length > 0 && (
            <div>
              <div style={{ fontSize: 12, fontWeight: 'bold', marginBottom: 6, color: '#888' }}>LIVE FEED</div>
              {state.recentVotes.map((v, i) => (
                <div key={i} style={{
                  fontSize: 11, padding: '3px 0', lineHeight: 1.3,
                  color: v.vote === 'positive' ? '#00ff88' : '#ff4444',
                  opacity: 1 - i * 0.05, borderBottom: '1px solid #0d0d1a',
                }}>
                  <span style={{ color: '#555' }}>#{v.id}</span>{' '}
                  <span style={{ fontWeight: 'bold' }}>{v.vote.toUpperCase()}</span>{' '}
                  <span style={{ color: '#666' }}>({(v.confidence * 100).toFixed(0)}%)</span>{' '}
                  <span style={{ color: '#555' }}>— {v.reasoning.slice(0, 70)}</span>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
