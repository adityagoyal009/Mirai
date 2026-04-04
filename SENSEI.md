# Sensei (先生) — AI Mentor Sessions

**A VCLabs.org product. Walk into a room of AI mentors who know your startup.**

## What Is Sensei?

Sensei is an interactive AI mentoring platform where startup founders have 15-minute one-on-one conversations with AI mentors — each with a distinct professional background, personality, and domain expertise. Mentors are pre-briefed on your startup through automated research, so conversations are grounded in real market data, not generic advice.

Think of it as having a room full of VCs, CTOs, customers, and industry experts — all available in one session, each bringing a perspective no single advisor could.

## How It Works

```
1. Walk into the lobby → Upload your executive summary at the intake desk
2. AI researches your market (uses cached Mirai analysis if available, ~5s)
3. Choose 3-6 mentors from 18 types (investors, customers, operators, experts)
4. Walk into each mentor's room → 15-minute chat session
5. Mentors ask probing questions, challenge assumptions, give specific advice
6. Session summary consolidates all advice at the end
```

## The Experience

You control a pixel-art character in a Gather Town-like office. Walk up to the intake desk, upload your startup's executive summary (or paste it), then pick your mentors. Each mentor sits in their own room. Walk in, and the conversation starts.

The mentor speaks first — grounded in research about your market, competitors, and product. You respond. They push back, ask follow-up questions, and give domain-specific advice. After 15 minutes (or when you choose to leave), walk to the next mentor's room.

At the end, a session summary consolidates the key advice from every mentor you talked to.

## 18 Mentor Types

### Investor Mentors
| Mentor | What They Help With |
|--------|-------------------|
| **Seed VC** | Should you raise? How much? From whom? Round structure, pitch strategy |
| **Growth VC** | Scaling from $1M to $10M ARR. Metrics that matter. Team building at scale |
| **Angel Investor** | Is your story compelling enough for a check? Conviction in one meeting |

### Customer Mentors
| Mentor | What They Help With |
|--------|-------------------|
| **Enterprise Buyer** | Would I buy this? Procurement process, budget approval, integration concerns |
| **SMB Owner** | Would my 50-person company use this? Immediate ROI, ease of adoption |
| **Target End-User** | Does this solve my daily pain? UX, switching cost, willingness to pay |

### Operator Mentors
| Mentor | What They Help With |
|--------|-------------------|
| **CTO** | Can you build this? Tech stack, scalability, hiring, technical debt |
| **CMO / Growth** | How to acquire first 100 customers? Channels, CAC, PLG vs sales-led |
| **CFO** | Do your numbers work? Unit economics, burn rate, runway, projections |

### Expert Mentors
| Mentor | What They Help With |
|--------|-------------------|
| **Industry Analyst** | Market landscape, TAM, competitive positioning, adoption lifecycle |
| **Domain Expert** | Deep expertise matched to your specific industry |
| **Regulatory Expert** | Legal/compliance risks, regulatory timelines, compliance as moat |

### Challenge Mentors
| Mentor | What They Help With |
|--------|-------------------|
| **Devil's Advocate** | Here's why this will fail. Stress-tests every assumption |
| **Competitor CEO** | I'm your biggest competitor. What stops me from crushing you? |

### Perspective Mentors
| Mentor | What They Help With |
|--------|-------------------|
| **Behavioral Economist** | Will users actually change their behavior? Adoption friction, habits |
| **Brand Strategist** | What's your narrative? Positioning, differentiation, brand equity |
| **Market Timer** | Is now the right moment? Too early? Too late? Adoption curve signals |
| **Impact Investor** | Social/environmental angle. Impact measurement, dual-return thesis |

## What Makes Each Mentor Unique

Every mentor is generated with **16 behavioral dimensions** — not just a role name:

1. **Role** — Their professional position (e.g., "Seed VC at a $5M fund")
2. **MBTI behavioral type** — Shapes communication style (INTJ = analytical, ENFP = enthusiastic)
3. **Risk profile** — Ultra-conservative to ultra-aggressive
4. **Experience level** — 3 years to 30+ years
5. **Cognitive bias** — What they naturally focus on (unit economics, vision, moats)
6. **Geographic lens** — Silicon Valley vs Berlin vs Lagos perspective
7. **Industry focus** — Matched to your startup's sector
8. **Fund/budget context** — Size of checks they write, budget they manage
9. **Backstory** — Formative experiences that shape their judgment
10. **Decision framework** — How they decide (thesis-driven, data-driven, relationship-led)
11. **Portfolio composition** — What's already in their portfolio
12. **Investment thesis style** — Thesis-driven, opportunistic, contrarian
13. **Technical depth** — Can they evaluate architecture, or just business?
14. **Failure scar tissue** — Past losses that make them cautious about specific risks
15. **Network strength** — Well-connected insider vs analytical outsider
16. **Decision speed** — Fast conviction vs methodical diligence

This means a "Seed VC Mentor" in one session is fundamentally different from a "Seed VC Mentor" in the next session — different personality, different backstory, different biases. Just like meeting different VCs in real life.

## Research Briefing

Before any conversation starts, mentors are briefed on your startup. Sensei reuses Mirai's research cache when available:

- **Market data** — TAM, growth rates, regulatory landscape
- **Competitors** — Who they are, their funding, positioning
- **Trends** — Industry shifts, recent news
- **Your details** — Product, business model, traction, team, pricing

If you've already run a Mirai analysis, the research is instant (cached). If not, Sensei uses your executive summary directly — mentors are still effective but less grounded in external data.

## Session Rules

- **15 minutes per mentor** — Timer visible in the chat UI
- **3-6 mentors per session** — Pick the perspectives most relevant to your stage
- **Mentors ask questions** — They don't just lecture. They probe, challenge, push back
- **Grounded in data** — Mentors reference specific competitors, market sizes, regulations
- **Domain terminology** — Each mentor uses vocabulary specific to their role
- **Last 3 minutes** — Mentor wraps up with their single most important piece of advice

## Architecture

```
Frontend (Phaser game + React overlay)
  └── /game/ on vclabs.org
      ├── Pixel-art world with rooms
      ├── Intake desk → exec summary upload
      ├── Mentor selection menu (React)
      └── Chat interface (React)

Backend (FastAPI + native WebSocket)
  └── /ws/sensei in subconscious/swarm/app.py
      ├── Research cache lookup (from Mirai)
      ├── PersonaEngine (16-dimension mentor generation)
      ├── MentorSession (multi-turn LLM chat)
      └── Transcript tracking

LLM (via Mirai Gateway :19789)
  └── Claude Opus 4.6 for mentor conversations
      ├── System prompt: persona + research briefing + session rules
      ├── Conversation history: full multi-turn context
      └── Time awareness: wraps up in last 3 minutes
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Game engine | Phaser 3.87 (pixel-art, 800x600) |
| UI overlays | React 19 + TypeScript |
| Backend | FastAPI + native WebSocket |
| LLM | Claude Opus 4.6 via Mirai Gateway |
| Persona engine | 16-dimension trait generator (shared with Mirai) |
| Research | Cached from Mirai analysis or exec summary fallback |
| Build | Vite |

## File Structure

```
dashboard-game/src/sensei/
├── index.ts              — Exports
├── mentorDefs.ts         — 18 mentor types, 6 categories, icons, colors
├── senseiSocket.ts       — WebSocket client for /ws/sensei
├── MentorMenu.tsx        — Mentor selection grid (pick 3-6)
├── MentorChat.tsx        — Chat interface (timer, messages, send)
├── SessionSummary.tsx    — End-of-session consolidated advice
├── SenseiApp.tsx         — Main flow orchestrator
└── useSenseiBridge.ts    — Phaser game world integration

subconscious/swarm/services/
├── mentor_session.py     — MentorSession class (multi-turn chat)
└── (persona_engine.py)   — Shared 16-dimension persona generator

subconscious/swarm/
└── app.py                — FastAPI route for /ws/sensei + session orchestration
```

## WebSocket Protocol

### Client → Server
| Message | Fields | Description |
|---------|--------|-------------|
| `startSession` | `execSummary`, `selectedMentors[]` | Begin session with chosen mentors |
| `chatMessage` | `mentorId`, `message` | Send message to active mentor |
| `endMentorChat` | `mentorId` | End current mentor session, get transcript |
| `endSession` | — | End all sessions, get consolidated summary |
| `getMentorTypes` | — | Request available mentor type list |

### Server → Client
| Message | Fields | Description |
|---------|--------|-------------|
| `researchStarted` | — | Research/briefing phase starting |
| `researchProgress` | `status` | Progress update |
| `researchComplete` | `status` | Mentors are briefed |
| `mentorsReady` | `mentors[]` | Mentor list with IDs, names, rooms |
| `mentorResponse` | `mentorId`, `message`, `timeRemaining` | Mentor's reply |
| `mentorEnded` | `mentorId`, `transcript` | Session transcript |
| `sessionSummary` | `transcripts[]`, `totalMentors` | All session data |
| `mentorTypes` | `mentors[]` | Available mentor types |
| `error` | `error` | Error message |

## Why This Product

**The problem**: Founders need diverse feedback before pitching. Currently they get:
- 1 VC meeting (2 weeks to schedule, 30 minutes, one perspective)
- 1 customer call (another week, one data point)
- Expensive consultants ($500/hr for domain expertise)
- Friends who are too nice to be honest

**Sensei**: 6 specialized mentors × 15 minutes each = 90 minutes of diverse, expert feedback. Available instantly. Each mentor has a real personality, real domain expertise, and real knowledge of your market. The Devil's Advocate will tell you what your friends won't. The Enterprise Buyer will tell you what your VC doesn't know. The CTO will find the technical gaps your pitch deck hides.

**Nobody does this.** AI chat exists (ChatGPT, Claude). Mentor platforms exist (MentorCruise, GrowthMentor). Game-based learning exists (various). But walking into a pixel-art office and having 6 deeply personalized mentor conversations grounded in real market research about YOUR startup — that's new.

## Relationship to Mirai

| | Mirai (未来) | Sensei (先生) |
|---|---|---|
| **Purpose** | Due diligence report | Interactive mentoring |
| **User** | Investor evaluating | Founder preparing |
| **Mode** | One-shot analysis → PDF | Multi-turn conversations |
| **Output** | Score + verdict + report | Advice + transcripts |
| **Interaction** | Upload → wait → read | Upload → pick mentors → talk |
| **URL** | vclabs.org/dashboard/ | vclabs.org/game/ |
| **Shared** | Research pipeline, persona engine, gateway | — |

Both products run on the same infrastructure. Mirai's research cache feeds Sensei's mentor briefings. The same 16-dimension persona engine generates both swarm agents and mentor personalities.

---

*Built by VCLabs.org. Powered by Mirai's research pipeline and persona engine.*
