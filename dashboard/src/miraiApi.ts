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
  // Full pipeline events
  | { type: 'researchStarted' }
  | { type: 'researchComplete'; findings: number; competitors: number; summary: string; faithfulnessScore?: number; citedFacts?: number }
  | { type: 'councilStarted'; modelCount: number; models: string[] }
  | { type: 'councilComplete'; overall: number; verdict: string; confidence: number; dimensions: Array<{name: string; score: number}>; contestedDimensions: string[]; models: string[]; factVerification?: {verified: number; contradicted: number; unverified: number; trustScore: number}; divergence?: any; deliberation?: any }
  | { type: 'planStarted' }
  | { type: 'planComplete'; risks: any[]; moves: any[] }
  | { type: 'analysisComplete'; fullResult: any }
  | { type: 'agentChatResponse'; agentId: number; response?: string; error?: string }
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
  divergence?: any
  deliberation?: any
}

type MessageHandler = (msg: SwarmMessage) => void

export class MiraiConnection {
  private socket: WebSocket | null = null
  private handlers: Set<MessageHandler> = new Set()
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private pingTimer: ReturnType<typeof setInterval> | null = null
  private _connected = false
  private _url: string = ''

  get connected() { return this._connected }

  connect(url: string) {
    this._url = url
    if (this.socket?.readyState === WebSocket.OPEN) return

    this.socket = new WebSocket(url)

    this.socket.onopen = () => {
      this._connected = true
      this.emit({ type: 'connected' })
      console.log('[mirai] WebSocket connected')
      // Keep-alive ping every 30s to prevent idle disconnect
      if (this.pingTimer) clearInterval(this.pingTimer)
      this.pingTimer = setInterval(() => {
        if (this.socket?.readyState === WebSocket.OPEN) {
          this.socket.send(JSON.stringify({ type: 'ping' }))
        }
      }, 30000)
    }

    this.socket.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data) as SwarmMessage
        if ((msg as any).type === 'pong') return // ignore pong replies
        this.emit(msg)
      } catch (err) {
        console.warn('[mirai] Failed to parse message:', e.data)
      }
    }

    this.socket.onclose = () => {
      this._connected = false
      if (this.pingTimer) { clearInterval(this.pingTimer); this.pingTimer = null }
      console.log('[mirai] WebSocket closed, reconnecting in 1s...')
      this.reconnectTimer = setTimeout(() => this.connect(this._url), 1000)
    }

    this.socket.onerror = (err) => {
      console.error('[mirai] WebSocket error:', err)
    }
  }

  disconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    if (this.pingTimer) { clearInterval(this.pingTimer); this.pingTimer = null }
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

  startAnalysis(execSummary: string, agentCount: number, depth: string = 'deep') {
    this.send({ type: 'startAnalysis', execSummary, agentCount, depth })
  }

  chatWithAgent(agentId: number, message: string, persona: string, zone: string,
                previousVote: string, previousReasoning: string, analysisContext: string) {
    this.send({ type: 'chatWithAgent', agentId, message, persona, zone,
                previousVote, previousReasoning, analysisContext })
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
