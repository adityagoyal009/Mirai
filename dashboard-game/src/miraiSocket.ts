// WebSocket client for Mirai backend — mirrors dashboard/src/miraiApi.ts

export type Phase =
  | "idle"
  | "research"
  | "council"
  | "swarm"
  | "plan"
  | "oasis"
  | "narrative"
  | "complete";

export type Vote = "positive" | "negative";
export type Zone =
  | "investor"
  | "customer"
  | "operator"
  | "analyst"
  | "contrarian"
  | "wildcard"
  | "council"
  | "archive";

export interface AgentData {
  id: number;
  persona: string;
  zone: Zone;
  model: string;
  activity: string;
  vote?: Vote;
  reasoning?: string;
  overall?: number;
  confidence?: number;
  scores?: Record<string, number>;
}

export interface CouncilResult {
  overall: number;
  verdict: string;
  confidence: number;
  dimensions: { name: string; score: number }[];
  contestedDimensions: string[];
  models: string[];
}

export interface SwarmResult {
  totalAgents: number;
  verdict: string;
  avg_scores: Record<string, number>;
  positivePct: number;
  negativePct: number;
  avgConfidence: number;
  keyThemesPositive: string[];
  keyThemesNegative: string[];
  contestedThemes: string[];
  executionTimeSeconds: number;
  score_distribution: Record<string, number>;
}

export interface MiraiState {
  phase: Phase;
  agents: Map<number, AgentData>;
  council: CouncilResult | null;
  swarmResult: SwarmResult | null;
  researchSummary: string;
  totalAgents: number;
  agentsCompleted: number;
  positivePct: number;
  negativePct: number;
  avgConfidence: number;
  planRisks: string[];
  planMoves: string[];
  oasisTimeline: { month: number; event: string; sentimentPct: number; confidenceLow?: number; confidenceHigh?: number }[];
  narrative: string;
  error: string | null;
  faithfulnessScore?: number;
  factVerification?: { verified: number; contradicted: number; unverified: number; trustScore: number };
  oasisUncertaintyBand?: { low: number; high: number; avg_std: number };
}

type Listener = (state: MiraiState) => void;

// Auto-detect backend URL: if served from Flask (same origin), use relative path.
// In dev mode (Vite on :3001/:3003), point to Flask on :5000.
const DEFAULT_URL = (() => {
  if (typeof window === "undefined") return "ws://localhost:5000/ws/swarm";
  const loc = window.location;
  if (loc.port === "5000" || loc.pathname.startsWith("/game")) {
    // Served from Flask — same host
    return `ws://${loc.hostname}:5000/ws/swarm`;
  }
  return `ws://${loc.hostname}:5000/ws/swarm`;
})();

class MiraiSocket {
  private ws: WebSocket | null = null;
  private listeners = new Set<Listener>();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private url = DEFAULT_URL;

  state: MiraiState = this.freshState();

  private freshState(): MiraiState {
    return {
      phase: "idle",
      agents: new Map(),
      council: null,
      swarmResult: null,
      researchSummary: "",
      totalAgents: 0,
      agentsCompleted: 0,
      positivePct: 0,
      negativePct: 0,
      avgConfidence: 0,
      planRisks: [],
      planMoves: [],
      oasisTimeline: [],
      narrative: "",
      error: null,
    };
  }

  connect(url?: string) {
    if (url) this.url = url;
    if (this.ws) this.ws.close();

    this.ws = new WebSocket(this.url);
    this.ws.onmessage = (e) => this.handleMessage(JSON.parse(e.data));
    this.ws.onclose = () => {
      this.reconnectTimer = setTimeout(() => this.connect(), 3000);
    };
    this.ws.onerror = () => this.ws?.close();
  }

  disconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.ws?.close();
    this.ws = null;
  }

  subscribe(fn: Listener) {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  private notify() {
    this.listeners.forEach((fn) => fn(this.state));
  }

  send(msg: Record<string, unknown>) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    }
  }

  startAnalysis(
    execSummary: string,
    agentCount: number,
    depth: string = "standard"
  ) {
    this.state = this.freshState();
    this.notify();
    this.send({ type: "startAnalysis", execSummary, agentCount, depth });
  }

  private handleMessage(data: Record<string, unknown>) {
    const s = this.state;

    switch (data.type) {
      case "researchStarted":
        s.phase = "research";
        break;

      case "researchComplete":
        s.researchSummary = (data.summary as string) || "";
        s.faithfulnessScore = data.faithfulnessScore as number | undefined;
        break;

      case "councilStarted":
        s.phase = "council";
        break;

      case "councilComplete":
        s.council = {
          overall: data.overall as number,
          verdict: data.verdict as string,
          confidence: data.confidence as number,
          dimensions: (data.dimensions as CouncilResult["dimensions"]) || [],
          contestedDimensions:
            (data.contestedDimensions as string[]) || [],
          models: (data.models as string[]) || [],
        };
        s.factVerification = data.factVerification as MiraiState["factVerification"];
        break;

      case "swarmStarted":
        s.phase = "swarm";
        s.totalAgents = (data.totalAgents as number) || 0;
        break;

      case "agentSpawned": {
        const agent: AgentData = {
          id: data.id as number,
          persona: (data.persona as string) || "Agent",
          zone: (data.zone as Zone) || "analyst",
          model: (data.model as string) || "",
          activity: "spawning",
        };
        s.agents.set(agent.id, agent);
        break;
      }

      case "agentActive": {
        const a = s.agents.get(data.id as number);
        if (a) a.activity = (data.activity as string) || "thinking";
        break;
      }

      case "agentVoted": {
        const a = s.agents.get(data.id as number);
        if (a) {
          a.vote = data.vote as Vote;
          a.overall = data.overall as number;
          a.confidence = data.confidence as number;
          a.reasoning = (data.reasoning as string) || "";
          a.scores = data.scores as Record<string, number>;
          a.activity = `voted ${data.vote}`;
        }
        break;
      }

      case "swarmProgress":
        s.agentsCompleted = (data.agentsCompleted as number) || 0;
        s.positivePct = (data.positivePct as number) || 0;
        s.negativePct = (data.negativePct as number) || 0;
        s.avgConfidence = (data.avgConfidence as number) || 0;
        break;

      case "swarmComplete":
        s.swarmResult = data.result as SwarmResult;
        if (s.swarmResult) {
          s.positivePct = s.swarmResult.positivePct;
          s.negativePct = s.swarmResult.negativePct;
        }
        break;

      case "deliberationStarted":
        // visual hint only
        break;

      case "planStarted":
        s.phase = "plan";
        break;

      case "planComplete":
        s.planRisks = (data.risks as string[]) || [];
        s.planMoves = (data.moves as string[]) || [];
        break;

      case "oasisStarted":
        s.phase = "oasis";
        break;

      case "oasisRound":
        s.oasisTimeline.push({
          month: data.month as number,
          event: data.event as string,
          sentimentPct: data.sentimentPct as number,
          confidenceLow: data.confidenceLow as number | undefined,
          confidenceHigh: data.confidenceHigh as number | undefined,
        });
        break;

      case "narrativeStarted":
        s.phase = "narrative";
        break;

      case "analysisComplete":
        s.phase = "complete";
        s.narrative =
          (data.fullResult as Record<string, unknown>)?.narrative as string || "";
        s.oasisUncertaintyBand = data.uncertaintyBand as MiraiState["oasisUncertaintyBand"];
        break;

      case "error":
        s.error = (data.error as string) || "Unknown error";
        break;
    }

    this.notify();
  }

  // Demo mode — simulate the full pipeline with fake data
  simulateDemo() {
    this.state = this.freshState();
    this.notify();

    const delay = (ms: number) =>
      new Promise<void>((r) => setTimeout(r, ms));

    const zones: Zone[] = [
      "investor",
      "customer",
      "operator",
      "analyst",
      "contrarian",
      "wildcard",
    ];
    const personas = [
      "Venture Capitalist",
      "Product Manager",
      "Growth Hacker",
      "Risk Analyst",
      "Market Researcher",
      "Devil's Advocate",
      "CTO",
      "Angel Investor",
      "Domain Expert",
      "Economics Professor",
      "Serial Entrepreneur",
      "Industry Veteran",
    ];

    (async () => {
      this.handleMessage({ type: "researchStarted" });
      await delay(1500);
      this.handleMessage({
        type: "researchComplete",
        findings: 14,
        competitors: 6,
        summary: "Market shows strong B2B SaaS demand in the compliance automation sector...",
      });
      await delay(800);

      this.handleMessage({
        type: "councilStarted",
        modelCount: 3,
        models: ["Claude-Opus", "GPT-4", "Gemini-Pro"],
      });
      await delay(2000);
      this.handleMessage({
        type: "councilComplete",
        overall: 7.4,
        verdict: "Likely Hit",
        confidence: 0.78,
        dimensions: [
          { name: "Market Size", score: 8 },
          { name: "Team Quality", score: 7 },
          { name: "Product Fit", score: 7 },
          { name: "Timing", score: 8 },
          { name: "Competition", score: 6 },
        ],
        contestedDimensions: ["Competition"],
        models: ["Claude-Opus", "GPT-4", "Gemini-Pro"],
      });
      await delay(600);

      const totalAgents = 25;
      this.handleMessage({
        type: "swarmStarted",
        totalAgents,
        execSummary: "Demo analysis",
      });

      for (let i = 1; i <= totalAgents; i++) {
        await delay(150 + Math.random() * 200);
        this.handleMessage({
          type: "agentSpawned",
          id: i,
          persona: personas[i % personas.length],
          zone: zones[i % zones.length],
          model: ["claude", "gpt-4", "gemini"][i % 3],
        });
      }

      for (let i = 1; i <= totalAgents; i++) {
        await delay(80);
        this.handleMessage({
          type: "agentActive",
          id: i,
          activity: "evaluating",
        });
      }

      for (let i = 1; i <= totalAgents; i++) {
        await delay(200 + Math.random() * 300);
        const vote = Math.random() > 0.35 ? "positive" : "negative";
        this.handleMessage({
          type: "agentVoted",
          id: i,
          vote,
          overall: Math.floor(Math.random() * 4) + (vote === "positive" ? 6 : 3),
          confidence: +(0.5 + Math.random() * 0.5).toFixed(2),
          reasoning:
            vote === "positive"
              ? "Strong market fundamentals and experienced team suggest high probability of success."
              : "Competitive landscape is crowded; differentiation unclear at this stage.",
          scores: { market: 7, team: 7, product: 6, timing: 8, overall: 7 },
        });
        const completed = i;
        const pos = [...this.state.agents.values()].filter(
          (a) => a.vote === "positive"
        ).length;
        const neg = completed - pos;
        this.handleMessage({
          type: "swarmProgress",
          agentsCompleted: completed,
          totalAgents,
          positivePct: Math.round((pos / completed) * 100),
          negativePct: Math.round((neg / completed) * 100),
          avgConfidence: 0.72,
        });
      }

      await delay(500);
      this.handleMessage({
        type: "swarmComplete",
        result: {
          totalAgents,
          verdict: "Likely Hit",
          avg_scores: { market: 7.2, team: 7.0, product: 6.5, timing: 7.8, overall: 7.1 },
          positivePct: 68,
          negativePct: 32,
          avgConfidence: 0.74,
          keyThemesPositive: ["Strong market timing", "Experienced team"],
          keyThemesNegative: ["Crowded market", "Unclear moat"],
          contestedThemes: ["Pricing strategy"],
          executionTimeSeconds: 42,
          score_distribution: {
            strong_hit: 4,
            likely_hit: 9,
            uncertain: 5,
            likely_miss: 5,
            strong_miss: 2,
          },
        },
      });

      await delay(800);
      this.handleMessage({ type: "planStarted" });
      await delay(1200);
      this.handleMessage({
        type: "planComplete",
        risks: [
          "Market consolidation by larger players",
          "Regulatory changes in compliance space",
          "Customer acquisition cost escalation",
        ],
        moves: [
          "Secure 3 enterprise design partners within 90 days",
          "File provisional patent on core algorithm",
          "Raise bridge round to extend runway to 18 months",
        ],
      });

      await delay(600);
      this.handleMessage({ type: "narrativeStarted" });
      await delay(1500);
      this.handleMessage({
        type: "analysisComplete",
        fullResult: {
          narrative:
            "The compliance automation space presents a compelling opportunity with strong tailwinds...",
        },
      });
    })();
  }
}

export const mirai = new MiraiSocket();
