/**
 * Sensei (先生) — Mentor Selection Menu
 *
 * User picks 3-6 mentors from 18 types before starting sessions.
 */

import { useState } from 'react'
import { MENTOR_DEFS, MENTOR_CATEGORIES, MAX_MENTORS, MIN_MENTORS, type MentorDef } from './mentorDefs'

interface Props {
  onStart: (selected: string[]) => void
  onBack: () => void
}

export function MentorMenu({ onStart, onBack }: Props) {
  const [selected, setSelected] = useState<Set<string>>(new Set())

  const toggle = (id: string) => {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else if (next.size < MAX_MENTORS) {
        next.add(id)
      }
      return next
    })
  }

  const canStart = selected.size >= MIN_MENTORS

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.85)',
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', zIndex: 1000, color: '#fff',
      fontFamily: "'Inter', -apple-system, sans-serif",
    }}>
      <div style={{
        maxWidth: 900, width: '90%', maxHeight: '85vh', overflow: 'auto',
        background: '#0a0a18', borderRadius: 16, padding: '32px 40px',
        border: '1px solid #1a1a2e',
      }}>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <div style={{ fontSize: 12, letterSpacing: 3, color: '#666', marginBottom: 8 }}>先生 SENSEI</div>
          <h1 style={{ margin: 0, fontSize: 28, color: '#fff' }}>Choose Your Mentors</h1>
          <p style={{ color: '#888', fontSize: 13, marginTop: 8 }}>
            Select {MIN_MENTORS}-{MAX_MENTORS} mentors for your session. Each brings a unique perspective.
          </p>
        </div>

        {MENTOR_CATEGORIES.map(cat => {
          const mentors = MENTOR_DEFS.filter(m => m.category === cat.key)
          if (!mentors.length) return null
          return (
            <div key={cat.key} style={{ marginBottom: 20 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>
                {cat.label}
                <span style={{ fontWeight: 400, color: '#666', textTransform: 'none', letterSpacing: 0, marginLeft: 8 }}>{cat.description}</span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 8 }}>
                {mentors.map(m => (
                  <MentorCard key={m.id} mentor={m} selected={selected.has(m.id)} onToggle={() => toggle(m.id)} disabled={!selected.has(m.id) && selected.size >= MAX_MENTORS} />
                ))}
              </div>
            </div>
          )
        })}

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 24, paddingTop: 16, borderTop: '1px solid #1a1a2e' }}>
          <button onClick={onBack} style={{
            background: 'transparent', border: '1px solid #333', color: '#888',
            padding: '10px 24px', borderRadius: 8, cursor: 'pointer', fontSize: 13,
          }}>
            Back
          </button>
          <div style={{ color: '#666', fontSize: 12 }}>
            {selected.size}/{MAX_MENTORS} selected {selected.size < MIN_MENTORS && `(need ${MIN_MENTORS - selected.size} more)`}
          </div>
          <button onClick={() => onStart(Array.from(selected))} disabled={!canStart} style={{
            background: canStart ? '#0f3460' : '#1a1a2e',
            border: canStart ? '1px solid #1a5090' : '1px solid #1a1a2e',
            color: canStart ? '#fff' : '#555',
            padding: '12px 32px', borderRadius: 8, cursor: canStart ? 'pointer' : 'not-allowed',
            fontSize: 14, fontWeight: 600, letterSpacing: 1,
          }}>
            START SESSION ({selected.size} mentors)
          </button>
        </div>
      </div>
    </div>
  )
}

function MentorCard({ mentor, selected, onToggle, disabled }: { mentor: MentorDef; selected: boolean; onToggle: () => void; disabled: boolean }) {
  return (
    <div
      onClick={disabled ? undefined : onToggle}
      style={{
        padding: '12px 16px', borderRadius: 10, cursor: disabled ? 'not-allowed' : 'pointer',
        background: selected ? 'rgba(15, 52, 96, 0.3)' : 'rgba(255,255,255,0.02)',
        border: selected ? `2px solid ${mentor.color}` : '2px solid transparent',
        opacity: disabled ? 0.4 : 1,
        transition: 'all 0.15s ease',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ fontSize: 20 }}>{mentor.icon}</span>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: selected ? '#fff' : '#ccc' }}>{mentor.name}</div>
          <div style={{ fontSize: 11, color: '#888', marginTop: 2 }}>{mentor.tagline}</div>
        </div>
        {selected && <span style={{ marginLeft: 'auto', color: mentor.color, fontSize: 18 }}>✓</span>}
      </div>
    </div>
  )
}
