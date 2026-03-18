# Mirai Changelog

## [Unreleased] — Implementation Sprint

### Planned
- ChromaDB episodic memory system (`subconscious/memory/`)
- Strip Zep Cloud dependency from MiroFish (replace with local ChromaDB)
- Wire `swarm_predict` action to MiroFish Flask backend
- Implement `terminal_command` action handler with sandboxing
- Fix WebSocket/CDP session persistence in browser engine
- Implement `browser_navigate` action handler with browser-use Agent
- Convert cortex heartbeat loop to async

---

## [0.1.0] — 2025-03-17 (Initial Scaffold)

### Added
- `cortex/mirai_cortex.py` — Main heartbeat loop with OpenClaw LLM integration
- `cortex/system_prompt.py` — Mirai personality and JSON action schemas
- `cortex/browser_engine/` — Full port of browser-use library with CDP session caching fix
- `subconscious/swarm/` — MiroFish Flask backend (ontology, graph, simulation, reports)
- `subconscious/lab/` — Autoresearch framework (prepare.py, train.py, analysis.ipynb)
- `Dockerfile` — Container with Python 3.10, Node.js 20, Playwright
- `mirai_sandbox.sb` — macOS Seatbelt sandbox profile (deny-default)
- `README.md` — Project overview and getting started
