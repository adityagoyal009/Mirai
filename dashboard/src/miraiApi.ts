/**
 * Mirai WebSocket bridge — replaces VS Code extension messaging.
 * Connects the dashboard to Mirai's Flask backend for real-time swarm visualization.
 */

export type SwarmMessage =
  | { type: 'swarmStarted'; totalAgents: number; execSummary: string }
  | { type: 'agentSpawned'; id: number; persona: string; model: string }
  | { type: 'agentActive'; id: number; activity: 'researching' | 'evaluating' | 'reading' }
  | { type: 'agentVoted'; id: number; vote: 'positive' | 'negative'; overall: number; scores: Record<string, number>; confidence: number; reasoning: string }
  | { type: 'agentDone'; id: number }
  | { type: 'agentError'; id: number; error: string }
  | { type: 'swarmProgress'; agentsCompleted: number; totalAgents: number; positivePct: number; negativePct: number; avgConfidence: number }
  | { type: 'swarmComplete'; result: SwarmResult }
  | { type: 'connected' }
  | { type: 'layoutLoaded'; layout: unknown }
  | { type: 'characterSpritesLoaded'; sprites: unknown[] }
  | { type: 'floorTilesLoaded'; tiles: unknown[] }
  | { type: 'wallTilesLoaded'; tiles: unknown[] }
  | { type: 'furnitureAssetsLoaded'; catalog: unknown[]; sprites: Record<string, unknown> }

export interface SwarmResult {
  totalAgents: number
  verdict: string
  avg_scores: Record<string, number>
  median_overall: number
  std_overall: number
  score_distribution: Record<string, number>
  positivePct: number
  negativePct: number
  avgConfidence: number
  keyThemesPositive: string[]
  keyThemesNegative: string[]
  contestedThemes: string[]
  modelsUsed: string[]
  executionTimeSeconds: number
}

type MessageHandler = (msg: SwarmMessage) => void

export class MiraiConnection {
  private socket: WebSocket | null = null
  private handlers: Set<MessageHandler> = new Set()
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private _connected = false

  get connected() { return this._connected }

  connect(url: string) {
    if (this.socket?.readyState === WebSocket.OPEN) return

    this.socket = new WebSocket(url)

    this.socket.onopen = () => {
      this._connected = true
      this.emit({ type: 'connected' })
      console.log('[mirai] WebSocket connected')
    }

    this.socket.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data) as SwarmMessage
        this.emit(msg)
      } catch (err) {
        console.warn('[mirai] Failed to parse message:', e.data)
      }
    }

    this.socket.onclose = () => {
      this._connected = false
      console.log('[mirai] WebSocket closed, reconnecting in 3s...')
      this.reconnectTimer = setTimeout(() => this.connect(url), 3000)
    }

    this.socket.onerror = (err) => {
      console.error('[mirai] WebSocket error:', err)
    }
  }

  disconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    this.socket?.close()
    this._connected = false
  }

  onMessage(handler: MessageHandler) {
    this.handlers.add(handler)
    return () => { this.handlers.delete(handler) }
  }

  send(msg: Record<string, unknown>) {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(msg))
    }
  }

  startSwarm(execSummary: string, agentCount: number) {
    this.send({ type: 'startSwarm', execSummary, agentCount })
  }

  saveLayout(layout: unknown) {
    this.send({ type: 'saveLayout', layout })
  }

  private emit(msg: SwarmMessage) {
    for (const handler of this.handlers) {
      try { handler(msg) } catch (e) { console.error('[mirai] Handler error:', e) }
    }
  }
}

// Singleton connection
export const mirai = new MiraiConnection()
