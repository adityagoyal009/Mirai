/**
 * Sensei (先生) — Mentor Chat Interface
 *
 * Multi-turn conversation with a persona-grounded AI mentor.
 * 15-minute timer per session.
 */

import { useState, useRef, useEffect } from 'react'
import type { ChatMessage, MentorInfo } from './senseiSocket'
import { MENTOR_DEFS } from './mentorDefs'

interface Props {
  mentor: MentorInfo
  messages: ChatMessage[]
  timeRemaining: number
  onSend: (message: string) => void
  onEnd: () => void
  onBack: () => void
}

export function MentorChat({ mentor, messages, timeRemaining, onSend, onEnd, onBack }: Props) {
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const chatEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const def = MENTOR_DEFS.find(m => m.id === mentor.type)
  const mins = Math.floor(timeRemaining / 60)
  const secs = timeRemaining % 60
  const isLow = timeRemaining < 180
  const isExpired = timeRemaining <= 0

  // Auto-scroll on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    // Detect mentor response arrived
    if (messages.length > 0 && messages[messages.length - 1].role === 'mentor') {
      setSending(false)
    }
  }, [messages])

  // Auto-focus input
  useEffect(() => { inputRef.current?.focus() }, [])

  const handleSend = () => {
    const text = input.trim()
    if (!text || sending || isExpired) return
    setSending(true)
    onSend(text)
    setInput('')
    setTimeout(() => inputRef.current?.focus(), 50)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.9)',
      display: 'flex', flexDirection: 'column', zIndex: 1000,
      fontFamily: "'Inter', -apple-system, sans-serif",
    }}>
      {/* Header */}
      <div style={{
        padding: '16px 24px', background: '#0a0a18',
        borderBottom: '1px solid #1a1a2e',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button onClick={onBack} style={{
            background: 'transparent', border: 'none', color: '#888',
            fontSize: 18, cursor: 'pointer', padding: '4px 8px',
          }}>←</button>
          <span style={{ fontSize: 20 }}>{def?.icon || '🎓'}</span>
          <div>
            <div style={{ fontSize: 15, fontWeight: 600, color: '#fff' }}>{mentor.name}</div>
            <div style={{ fontSize: 11, color: '#888' }}>{def?.tagline}</div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{
            fontSize: 18, fontWeight: 700, fontVariantNumeric: 'tabular-nums',
            color: isExpired ? '#d32f2f' : isLow ? '#f57c00' : '#2e7d32',
          }}>
            {mins}:{secs.toString().padStart(2, '0')}
          </div>
          <button onClick={onEnd} style={{
            background: '#1a1a2e', border: '1px solid #333', color: '#ccc',
            padding: '8px 16px', borderRadius: 8, cursor: 'pointer', fontSize: 12,
          }}>
            End Session
          </button>
        </div>
      </div>

      {/* Chat Messages */}
      <div style={{
        flex: 1, overflow: 'auto', padding: '20px 24px',
        display: 'flex', flexDirection: 'column', gap: 16,
      }}>
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', color: '#555', marginTop: 40, fontSize: 13 }}>
            Waiting for {mentor.name} to start the conversation...
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} style={{
            display: 'flex', flexDirection: 'column',
            alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start',
            maxWidth: '85%',
            alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
          }}>
            <div style={{
              fontSize: 10, color: '#666', marginBottom: 4, fontWeight: 600,
              textTransform: 'uppercase', letterSpacing: 1,
            }}>
              {msg.role === 'mentor' ? mentor.name : 'You'}
            </div>
            <div style={{
              padding: '12px 16px', borderRadius: 12,
              background: msg.role === 'user' ? '#0f3460' : 'rgba(255,255,255,0.05)',
              color: msg.role === 'user' ? '#e0e0ff' : '#ddd',
              fontSize: 13, lineHeight: 1.7,
              border: msg.role === 'mentor' ? '1px solid #1a1a2e' : 'none',
              whiteSpace: 'pre-wrap',
            }}>
              {msg.content}
            </div>
          </div>
        ))}
        {sending && (
          <div style={{ color: '#666', fontSize: 12, fontStyle: 'italic' }}>
            {mentor.name} is thinking...
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Input */}
      <div style={{
        padding: '16px 24px', background: '#0a0a18',
        borderTop: '1px solid #1a1a2e',
        display: 'flex', gap: 12, alignItems: 'flex-end',
      }}>
        <textarea
          ref={inputRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isExpired ? 'Session ended' : 'Type your response... (Enter to send, Shift+Enter for newline)'}
          disabled={isExpired || sending}
          rows={2}
          style={{
            flex: 1, background: '#111', border: '1px solid #1a1a2e',
            borderRadius: 12, padding: '12px 16px', color: '#ddd',
            fontSize: 13, resize: 'none', outline: 'none',
            fontFamily: 'inherit', lineHeight: 1.5,
            opacity: isExpired ? 0.5 : 1,
          }}
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || sending || isExpired}
          style={{
            background: input.trim() && !sending ? '#0f3460' : '#1a1a2e',
            border: 'none', color: input.trim() && !sending ? '#fff' : '#555',
            padding: '12px 20px', borderRadius: 12, cursor: input.trim() ? 'pointer' : 'not-allowed',
            fontSize: 14, fontWeight: 600,
          }}
        >
          Send ↵
        </button>
      </div>
    </div>
  )
}
