# OASIS Infrastructure — Status & Context

## TL;DR

There are **two entirely separate OASIS systems** in this directory. Only one is used by the main pipeline.

---

## System A — Active (Main Pipeline)

**File:** `oasis_simulator.py`

A deep-default, self-contained 6-round market trajectory simulator built specifically for Mirai.

- Runs 6 simulated "months" of market reaction after the council/swarm verdict
- Each round fetches live news events through the gateway search stack (Claude CLI first, OpenClaw fallback)
- Uses structured startup + research context, carries timeline state forward, and avoids reusing the same sourced headline across rounds
- Produces a trajectory (`improving` / `stable` / `declining`) that can adjust the final verdict
- Called from the real FastAPI analysis path in `app.py` and from the legacy live dashboard path in `api/websocket.py`

This is what "OASIS" means in the context of a Mirai analysis.

---

## System B — Inactive (Reference / Future Work)

**Files:**
- `simulation_runner.py` (~800 lines)
- `simulation_manager.py` (~400 lines)
- `oasis_profile_generator.py` (~800 lines)

These files implement a **full OASIS simulation framework** imported from a prior research prototype. They are **NOT connected to the main pipeline** and are never called from `app.py`, `api/websocket.py`, `swarm_predictor.py`, or any other active production service.

### What they contain

| File | Purpose |
|------|---------|
| `simulation_runner.py` | External Python subprocess runner with IPC client, action log parsing, batch/global interviews, agent statistics, timeline generation, and process cleanup |
| `simulation_manager.py` | High-level orchestration for multi-platform simulations (Twitter/Reddit), agent provisioning, ChromaDB storage, Zep memory integration |
| `oasis_profile_generator.py` | Agent profile generation for the full OASIS framework; creates personas with memory embeddings and social graph relationships |

### Why they're here

These files were imported as a starting point for a full OASIS integration — one that would run real multi-agent social simulations with Twitter/Reddit platform emulation, Zep knowledge graphs, and ChromaDB storage.

That full integration was never completed. The main pipeline uses `oasis_simulator.py` instead because it requires zero external simulation infrastructure.

### Language note

`oasis_profile_generator.py` contains **Chinese-language comments** throughout. This is from the original academic research implementation of OASIS (a paper from a Chinese research group). Examples:
- `# 优化改进：` (Optimization improvements)
- `# 通用字段` (Common fields)
- `# 移除特殊 characters，转换为小写` (Remove special characters, convert to lowercase)

Contributors unfamiliar with Chinese should be aware of this when reading or modifying that file.

---

## Future Integration Path

If full OASIS integration is desired:

1. `simulation_manager.py` + `simulation_runner.py` provide the orchestration layer
2. `oasis_profile_generator.py` maps Mirai personas → OASIS agent profiles
3. Requires: Zep Cloud credentials, ChromaDB, and the `oasis` Python library
4. The active `oasis_simulator.py` could be replaced or run in parallel

For now, **do not delete** these files — they represent significant reference work for future integration.
