/**
 * Sensei (先生) — Session Summary
 *
 * Shows consolidated advice from all mentor sessions.
 */

import type { ChatMessage, MentorInfo } from './senseiSocket'
import { MENTOR_DEFS } from './mentorDefs'

interface Props {
  mentors: MentorInfo[]
  chatHistory: Map<string, ChatMessage[]>
  onClose: () => void
}

export function SessionSummary({ mentors, chatHistory, onClose }: Props) {
  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.9)',
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', zIndex: 1000, color: '#fff',
      fontFamily: "'Inter', -apple-system, sans-serif",
    }}>
      <div style={{
        maxWidth: 800, width: '90%', maxHeight: '85vh', overflow: 'auto',
        background: '#0a0a18', borderRadius: 16, padding: '32px 40px',
        border: '1px solid #1a1a2e',
      }}>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <div style={{ fontSize: 12, letterSpacing: 3, color: '#666', marginBottom: 8 }}>先生 SENSEI</div>
          <h1 style={{ margin: 0, fontSize: 24, color: '#fff' }}>Session Complete</h1>
          <p style={{ color: '#888', fontSize: 13, marginTop: 8 }}>
            {mentors.length} mentor sessions completed
          </p>
        </div>

        {mentors.map(m => {
          const def = MENTOR_DEFS.find(d => d.id === m.type)
          const messages = chatHistory.get(m.id) || []
          const mentorMessages = messages.filter(msg => msg.role === 'mentor')
          const lastAdvice = mentorMessages.length > 0 ? mentorMessages[mentorMessages.length - 1].content : ''

          return (
            <div key={m.id} style={{
              marginBottom: 16, padding: '16px 20px',
              background: 'rgba(255,255,255,0.02)', borderRadius: 10,
              border: `1px solid ${def?.color || '#333'}22`,
              borderLeft: `3px solid ${def?.color || '#333'}`,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                <span style={{ fontSize: 18 }}>{def?.icon || '🎓'}</span>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 600 }}>{m.name}</div>
                  <div style={{ fontSize: 11, color: '#888' }}>{messages.length} messages exchanged</div>
                </div>
              </div>
              {lastAdvice && (
                <div style={{ fontSize: 12, color: '#aaa', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                  <strong style={{ color: '#888' }}>Last advice:</strong> {lastAdvice.slice(0, 300)}
                  {lastAdvice.length > 300 && '...'}
                </div>
              )}
            </div>
          )
        })}

        <div style={{ textAlign: 'center', marginTop: 24 }}>
          <button onClick={onClose} style={{
            background: '#0f3460', border: '1px solid #1a5090', color: '#fff',
            padding: '12px 32px', borderRadius: 8, cursor: 'pointer',
            fontSize: 14, fontWeight: 600,
          }}>
            Return to Lobby
          </button>
        </div>
      </div>
    </div>
  )
}
