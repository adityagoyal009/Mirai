/**
 * Sensei (先生) — WebSocket client for mentor sessions.
 * Connects to /ws/sensei on the FastAPI backend.
 */

export interface MentorInfo {
  id: string
  name: string
  type: string
  tagline: string
  zone: string
  room: number
}

export interface ChatMessage {
  role: 'mentor' | 'user'
  content: string
  timestamp: number
}

export interface SenseiState {
  phase: 'idle' | 'connecting' | 'researching' | 'selecting' | 'mentoring' | 'summary'
  connected: boolean
  mentors: MentorInfo[]
  activeMentorId: string | null
  chatHistory: Map<string, ChatMessage[]>
  timeRemaining: number
  researchStatus: string
  error: string | null
}

type SenseiListener = (state: SenseiState) => void

class SenseiSocket {
  private socket: WebSocket | null = null
  private listeners: Set<SenseiListener> = new Set()
  private pingTimer: ReturnType<typeof setInterval> | null = null

  state: SenseiState = {
    phase: 'idle',
    connected: false,
    mentors: [],
    activeMentorId: null,
    chatHistory: new Map(),
    timeRemaining: 15 * 60,
    researchStatus: '',
    error: null,
  }

  connect(url?: string) {
    const wsUrl = url || this._detectUrl()
    if (this.socket?.readyState === WebSocket.OPEN) return

    this.socket = new WebSocket(wsUrl)
    this._update({ phase: 'connecting' })

    this.socket.onopen = () => {
      this._update({ connected: true, phase: 'idle', error: null })
      this.pingTimer = setInterval(() => {
        if (this.socket?.readyState === WebSocket.OPEN) {
          this.socket.send(JSON.stringify({ type: 'ping' }))
        }
      }, 25000)
    }

    this.socket.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        this._handleMessage(msg)
      } catch {
        console.warn('[Sensei] Failed to parse message:', e.data)
      }
    }

    this.socket.onclose = () => {
      this._update({ connected: false })
      if (this.pingTimer) { clearInterval(this.pingTimer); this.pingTimer = null }
    }

    this.socket.onerror = () => {
      this._update({ error: 'Connection failed' })
    }
  }

  disconnect() {
    if (this.pingTimer) { clearInterval(this.pingTimer); this.pingTimer = null }
    this.socket?.close()
    this.socket = null
    this._update({ connected: false, phase: 'idle' })
  }

  send(msg: Record<string, unknown>) {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(msg))
    }
  }

  // ── Actions ──

  startSession(execSummary: string, selectedMentors: string[]) {
    this._update({ phase: 'researching', researchStatus: 'Starting research...' })
    this.send({ type: 'startSession', execSummary, selectedMentors })
  }

  sendChat(mentorId: string, message: string) {
    // Add user message to local history immediately
    const history = this.state.chatHistory.get(mentorId) || []
    history.push({ role: 'user', content: message, timestamp: Date.now() })
    this.state.chatHistory.set(mentorId, history)
    this._notify()
    // Send to backend
    this.send({ type: 'chatMessage', mentorId, message })
  }

  endMentorChat(mentorId: string) {
    this.send({ type: 'endMentorChat', mentorId })
  }

  endSession() {
    this.send({ type: 'endSession' })
  }

  startMentorChat(mentorId: string) {
    this._update({ activeMentorId: mentorId, timeRemaining: 15 * 60 })
  }

  getMentorTypes() {
    this.send({ type: 'getMentorTypes' })
  }

  // ── Subscriptions ──

  subscribe(fn: SenseiListener): () => void {
    this.listeners.add(fn)
    return () => this.listeners.delete(fn)
  }

  // ── Internal ──

  private _handleMessage(msg: Record<string, unknown>) {
    const type = msg.type as string

    switch (type) {
      case 'researchStarted':
        this._update({ phase: 'researching', researchStatus: 'Research starting...' })
        break
      case 'researchProgress':
        this._update({ researchStatus: msg.status as string || 'Researching...' })
        break
      case 'researchComplete':
        this._update({ phase: 'selecting', researchStatus: 'Research complete' })
        break
      case 'mentorsReady':
        this._update({
          phase: 'selecting',
          mentors: msg.mentors as MentorInfo[],
        })
        break
      case 'mentorOpening': {
        const mid = msg.mentorId as string
        const history = this.state.chatHistory.get(mid) || []
        history.push({ role: 'mentor', content: msg.message as string, timestamp: Date.now() })
        this.state.chatHistory.set(mid, history)
        this._update({ phase: 'mentoring', activeMentorId: mid })
        break
      }
      case 'mentorResponse': {
        const mid = msg.mentorId as string
        const history = this.state.chatHistory.get(mid) || []
        history.push({ role: 'mentor', content: msg.message as string, timestamp: Date.now() })
        this.state.chatHistory.set(mid, history)
        this._update({ timeRemaining: msg.timeRemaining as number || 0 })
        break
      }
      case 'mentorEnded':
        // Mentor session ended, stay in mentoring phase for next mentor
        break
      case 'sessionSummary':
        this._update({ phase: 'summary' })
        break
      case 'error':
        this._update({ error: msg.error as string })
        break
      case 'pong':
        break
    }
  }

  private _update(partial: Partial<SenseiState>) {
    Object.assign(this.state, partial)
    this._notify()
  }

  private _notify() {
    for (const fn of this.listeners) {
      try { fn(this.state) } catch (e) { console.error('[Sensei] Listener error:', e) }
    }
  }

  private _detectUrl(): string {
    const loc = window.location
    const proto = loc.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = loc.hostname === 'localhost' || loc.hostname === '127.0.0.1'
      ? `${loc.hostname}:5000`
      : loc.host
    return `${proto}//${host}/ws/sensei`
  }
}

export const senseiSocket = new SenseiSocket()
