/**
 * Sensei (先生) — Main Sensei Application Component
 *
 * Manages the full mentor session flow:
 * 1. Connect + upload exec summary (uses game lobby)
 * 2. Research runs (reuses Mirai pipeline)
 * 3. Pick mentors (MentorMenu)
 * 4. Chat sessions (MentorChat)
 * 5. Summary (SessionSummary)
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { senseiSocket, type SenseiState, type MentorInfo } from './senseiSocket'
import { MentorMenu } from './MentorMenu'
import { MentorChat } from './MentorChat'
import { SessionSummary } from './SessionSummary'

interface Props {
  execSummary: string  // passed from game lobby dialog or form
}

export function SenseiApp({ execSummary }: Props) {
  const [state, setState] = useState<SenseiState>(senseiSocket.state)
  const [selectedMentors, setSelectedMentors] = useState<string[]>([])
  const [currentMentorIdx, setCurrentMentorIdx] = useState(0)
  const [showMenu, setShowMenu] = useState(false)
  const [showChat, setShowChat] = useState(false)
  const [showSummary, setShowSummary] = useState(false)

  useEffect(() => {
    const unsub = senseiSocket.subscribe((s) => setState({ ...s }))
    if (!senseiSocket.state.connected) {
      senseiSocket.connect()
    }
    return unsub
  }, [])

  // Show menu on mount
  useEffect(() => {
    setShowMenu(true)
  }, [])

  // Watch for phase changes
  useEffect(() => {
    if (state.phase === 'mentoring' || (state.mentors.length > 0 && selectedMentors.length > 0 && !showChat && !showSummary)) {
      // Mentors are ready — start first mentor chat if not already chatting
      if (state.mentors.length > 0 && !showChat) {
        startNextMentor(0)
      }
    }
    if (state.phase === 'summary') {
      setShowChat(false)
      setShowSummary(true)
    }
  }, [state.phase, state.mentors])

  const handleStartSession = useCallback((mentorIds: string[]) => {
    setSelectedMentors(mentorIds)
    setShowMenu(false)
    senseiSocket.startSession(execSummary, mentorIds)
  }, [execSummary])

  const startNextMentor = (idx: number) => {
    if (idx >= state.mentors.length) {
      senseiSocket.endSession()
      return
    }
    setCurrentMentorIdx(idx)
    setShowChat(true)
    senseiSocket.startMentorChat(state.mentors[idx].id)
    // Request opening message
    senseiSocket.send({ type: 'chatMessage', mentorId: state.mentors[idx].id, message: '[SESSION START]' })
  }

  const handleEndMentor = () => {
    const mentor = state.mentors[currentMentorIdx]
    if (mentor) {
      senseiSocket.endMentorChat(mentor.id)
    }
    // Move to next mentor
    const nextIdx = currentMentorIdx + 1
    if (nextIdx < state.mentors.length) {
      startNextMentor(nextIdx)
    } else {
      senseiSocket.endSession()
    }
  }

  const currentMentor = state.mentors[currentMentorIdx]
  const currentMessages = currentMentor ? (state.chatHistory.get(currentMentor.id) || []) : []

  // Show research progress
  if (state.phase === 'researching') {
    return (
      <div style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.85)',
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        justifyContent: 'center', zIndex: 1000, color: '#fff',
        fontFamily: "'Inter', -apple-system, sans-serif",
      }}>
        <div style={{ fontSize: 12, letterSpacing: 3, color: '#666', marginBottom: 16 }}>先生 SENSEI</div>
        <div style={{ fontSize: 20, marginBottom: 12 }}>Briefing Your Mentors</div>
        <div style={{ fontSize: 13, color: '#888', marginBottom: 24 }}>{state.researchStatus}</div>
        <div style={{
          width: 200, height: 4, background: '#1a1a2e', borderRadius: 2, overflow: 'hidden',
        }}>
          <div style={{
            width: '60%', height: '100%', background: '#0f3460',
            animation: 'pulse 2s ease-in-out infinite',
          }} />
        </div>
      </div>
    )
  }

  // Show mentor menu
  if (showMenu || (state.phase === 'idle' && !showChat && !showSummary)) {
    return (
      <MentorMenu
        onStart={handleStartSession}
        onBack={() => setShowMenu(false)}
      />
    )
  }

  // Show chat
  if (showChat && currentMentor) {
    return (
      <MentorChat
        mentor={currentMentor}
        messages={currentMessages}
        timeRemaining={state.timeRemaining}
        onSend={(msg) => senseiSocket.sendChat(currentMentor.id, msg)}
        onEnd={handleEndMentor}
        onBack={() => {
          handleEndMentor()
        }}
      />
    )
  }

  // Show summary
  if (showSummary) {
    return (
      <SessionSummary
        mentors={state.mentors}
        chatHistory={state.chatHistory}
        onClose={() => {
          setShowSummary(false)
          setShowMenu(false)
          setShowChat(false)
          senseiSocket.disconnect()
        }}
      />
    )
  }

  // Default: show start button
  return (
    <div style={{
      position: 'fixed', bottom: 20, right: 20, zIndex: 900,
    }}>
      <button
        onClick={() => setShowMenu(true)}
        style={{
          background: '#0f3460', border: '1px solid #1a5090', color: '#fff',
          padding: '14px 28px', borderRadius: 12, cursor: 'pointer',
          fontSize: 15, fontWeight: 600, letterSpacing: 1,
          boxShadow: '0 4px 20px rgba(15,52,96,0.4)',
        }}
      >
        先生 Start Mentor Session
      </button>
    </div>
  )
}
