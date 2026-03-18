# Mirai (未来)
**An Autonomous, Perpetual, Predictive AI System**

Mirai represents a convergence of three state-of-the-art open-source architectures:
1. **The Brain (OpenClaw):** Handles the zero-cost Claude 3 Opus OAuth connection, system presence, and human messaging interfaces (WhatsApp, Telegram).
2. **The Hands (Browser-use):** A computer-vision-based Playwright engine that physically navigates websites autonomously, with fixed WebSocket persistence.
3. **The Subconscious (MiroFish):** A local swarm intelligence engine that spawns background AI agents to wargame and predict the outcomes of actions before Mirai executes them.

## Architecture

```text
Mirai/
├── cortex/               # Main autonomous loop powered by Claude 3 Opus
│   ├── mirai_cortex.py   # The central Heartbeat loop
│   └── browser_engine/   # Ported from browser-use (with fixed CDP/WebSockets)
├── subconscious/         # Background prediction engine (MiroFish)
│   ├── memory/           # Local ChromaDB integration (replacing Zep Cloud)
│   └── lab/              # Autoresearch engine where Mirai trains its own local models
└── gateway/              # The OpenClaw Node.js proxy server
```

## Getting Started

1. Start the OpenClaw Gateway locally and authenticate with your Claude subscription:
   ```bash
   openclaw onboard
   openclaw gateway
   ```
2. In a separate terminal, launch the Mirai Cortex:
   ```bash
   python cortex/mirai_cortex.py
   ```

## Development Goals
- [x] Establish Claude 3 Opus connection via OpenClaw CLI proxy.
- [x] Migrate `browser-use` core logic into `cortex/browser_engine` and fix the WebSocket restart issue.
- [x] Setup `subconscious/lab/` (autoresearch) for self-improvement and local LLM training.
- [ ] Migrate `MiroFish` simulation logic to `subconscious/`, stripping out Zep Cloud dependency.
- [ ] Build the ChromaDB local episodic memory system.
