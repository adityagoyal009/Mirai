# Mirai (未来) — System Architecture

## Overview

Mirai is an autonomous, perpetual, predictive AI system with three subsystems:

```
┌─────────────────────────────────────────────────────────────────┐
│                     mirai_cortex.py                             │
│               (10-second heartbeat loop)                        │
│                                                                 │
│  ┌───────────┐   ┌────────────────┐   ┌──────────────────────┐  │
│  │   Brain    │   │     Hands      │   │    Subconscious      │  │
│  │ (OpenClaw) │   │ (browser-use)  │   │    (MiroFish)        │  │
│  │→ Claude 3  │   │→ Playwright    │   │→ Swarm simulations   │  │
│  │   Opus     │   │→ CDP/WebSocket │   │→ ChromaDB memory     │  │
│  │            │   │→ Vision DOM    │   │→ Autoresearch (Lab)  │  │
│  └─────┬─────┘   └───────┬────────┘   └──────────┬───────────┘  │
│        │                 │                        │              │
└────────┼─────────────────┼────────────────────────┼──────────────┘
         │                 │                        │
    OpenClaw CLI     Chromium CDP            Flask API (port 5000)
         │                 │                        │
    Claude OAuth     Browser Engine          ChromaDB + LLM
```

## Directory Structure

```
Mirai/
├── cortex/                      # THE BRAIN + HANDS
│   ├── mirai_cortex.py          # Main heartbeat loop (async)
│   ├── system_prompt.py         # LLM personality & JSON action schemas
│   └── browser_engine/          # Ported from browser-use (with fixes)
│       ├── agent/               # Agent orchestrator (service, prompts, views)
│       ├── browser/             # Playwright wrapper, session mgmt, watchdogs
│       ├── dom/                 # DOM serialization + CDP session caching
│       ├── llm/                 # Multi-provider LLM abstraction (15+ providers)
│       ├── tools/               # Tool registry + structured extraction
│       ├── mcp/                 # Model Context Protocol server/client
│       ├── screenshots/         # Vision-based screenshot service
│       ├── sandbox/             # Code execution sandbox
│       └── config.py            # Comprehensive config management
│
├── subconscious/                # THE SUBCONSCIOUS
│   ├── memory/                  # ChromaDB episodic memory (local, persistent)
│   │   ├── __init__.py
│   │   └── episodic_store.py    # EpisodicMemoryStore class
│   │
│   ├── swarm/                   # MiroFish social simulation engine (Flask)
│   │   ├── __init__.py          # Flask app factory
│   │   ├── config.py            # Configuration (LLM, ChromaDB, OASIS)
│   │   ├── api/                 # REST endpoints
│   │   │   ├── graph.py         # Ontology + graph construction
│   │   │   ├── simulation.py    # Simulation CRUD + execution
│   │   │   ├── report.py        # Report generation
│   │   │   └── predict.py       # Quick-predict endpoint for cortex
│   │   ├── models/              # Data models (Project, Task)
│   │   ├── services/            # Business logic
│   │   │   ├── graph_builder.py          # ChromaDB graph construction
│   │   │   ├── simulation_manager.py     # Simulation lifecycle
│   │   │   ├── simulation_runner.py      # Background process execution
│   │   │   ├── simulation_ipc.py         # File-based IPC
│   │   │   ├── ontology_generator.py     # LLM-based ontology extraction
│   │   │   ├── oasis_profile_generator.py # Agent persona generation
│   │   │   ├── simulation_config_generator.py # Smart config generation
│   │   │   ├── report_agent.py           # LLM-powered analysis reports
│   │   │   └── text_processor.py         # Text chunking
│   │   └── utils/               # Shared utilities
│   │       ├── llm_client.py    # OpenAI-compatible API wrapper
│   │       ├── file_parser.py   # PDF/MD/TXT extraction
│   │       ├── logger.py        # Rotating file + console logging
│   │       └── retry.py         # Exponential backoff decorators
│   │
│   └── lab/                     # Autoresearch (self-improvement)
│       ├── prepare.py           # Data download + tokenizer training
│       ├── train.py             # GPT model (Flash Attention 3, RoPE, Muon)
│       ├── program.md           # Agent instructions for autonomous experiments
│       └── analysis.ipynb       # Experiment tracking + visualization
│
├── gateway/                     # OpenClaw Node.js proxy (started externally)
├── Dockerfile                   # Container: Python 3.10 + Node 20 + Playwright
├── mirai_sandbox.sb             # macOS Seatbelt sandbox profile (deny-default)
└── README.md                    # Project overview
```

## Action Flow

The cortex heartbeat loop processes these JSON actions from the LLM:

| Action | Handler | Description |
|--------|---------|-------------|
| `browser_navigate` | browser-use Agent | Navigate + interact with web pages autonomously |
| `terminal_command` | subprocess.run() | Execute shell commands within sandbox |
| `swarm_predict` | HTTP → Flask API | Wargame scenarios via MiroFish simulation |
| `message_human` | OpenClaw CLI | Send WhatsApp messages to operator |
| `standby` | (no-op) | Idle state |

## Key Integration Points

1. **Cortex ↔ Brain**: OpenClaw CLI subprocess (`openclaw agent --message ...`)
2. **Cortex ↔ Hands**: browser-use Agent with persistent BrowserSession (async)
3. **Cortex ↔ Subconscious**: HTTP calls to MiroFish Flask backend (port 5000)
4. **Swarm ↔ Memory**: ChromaDB PersistentClient for graph storage and semantic search
5. **Swarm ↔ LLM**: OpenAI-compatible API for ontology/profile/config generation

## Security Model

- **macOS**: `mirai_sandbox.sb` (Seatbelt) — deny-default, blocks ~/Documents, ~/Desktop, etc.
- **Docker**: Non-root `mirai_user` with limited permissions
- **Terminal commands**: Python-level blocklist for dangerous patterns
- **Network**: Allowed for Claude OAuth + browser automation only

## Data Flow for Simulation

```
Documents → Ontology (LLM) → Knowledge Graph (ChromaDB) → Entity Extraction
    → Agent Profiles (LLM) → Simulation Config (LLM) → OASIS Simulation
    → Agent Actions → Memory Updates (ChromaDB) → Analysis Reports (LLM)
```
