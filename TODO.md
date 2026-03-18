# Mirai TODO — Implementation Plan

## Status Legend
- [ ] Not started
- [~] In progress
- [x] Complete

---

## Phase 1: ChromaDB Episodic Memory System
**Priority**: Highest (foundational for Phases 2-3)

- [ ] Create `subconscious/memory/__init__.py` — package init
- [ ] Create `subconscious/memory/episodic_store.py` — `EpisodicMemoryStore` class
  - `PersistentClient` (survives restarts) at `subconscious/memory/.chromadb_data/`
  - Collections: `{graph_id}_nodes` (entities), `{graph_id}_edges` (relationships), `{graph_id}_episodes` (raw text)
  - Methods: `create_graph`, `add_episodes`, `search`, `add_nodes`, `add_edges`, `get_all_nodes`, `get_all_edges`, `get_node_edges`
  - Semantic search via ChromaDB's built-in sentence-transformer embeddings

## Phase 2: Strip Zep Cloud Dependency
**Priority**: High (unblocks MiroFish running locally)

Files to modify (remove `from zep_cloud...` imports, replace with `EpisodicMemoryStore`):

- [ ] `subconscious/swarm/config.py` — remove `ZEP_API_KEY`, add `CHROMADB_PERSIST_PATH`
- [ ] `subconscious/swarm/utils/zep_paging.py` — rewrite to delegate to `EpisodicMemoryStore`
- [ ] `subconscious/swarm/services/graph_builder.py` — use `EpisodicMemoryStore`
- [ ] `subconscious/swarm/services/zep_entity_reader.py` — use `EpisodicMemoryStore`
- [ ] `subconscious/swarm/services/zep_graph_memory_updater.py` — use `EpisodicMemoryStore`
- [ ] `subconscious/swarm/services/zep_tools.py` — replace `Zep` client with ChromaDB search (biggest change: 65KB file)
- [ ] `subconscious/swarm/api/graph.py` — remove `ZEP_API_KEY` guards
- [ ] `subconscious/swarm/api/simulation.py` — remove `ZEP_API_KEY` guards

## Phase 3: Wire `swarm_predict` to Cortex
**Priority**: High (connects brain to subconscious)

- [ ] Create `subconscious/swarm/api/predict.py` — lightweight prediction endpoint
  - `POST /api/predict` with `{"scenario": "...", "graph_id": "..."}`
  - Uses ChromaDB search for context, LLM for synthesis
- [ ] Update `subconscious/swarm/api/__init__.py` — register `predict_bp`
- [ ] Update `cortex/mirai_cortex.py` — implement `swarm_predict` handler via HTTP

## Phase 4: Implement `terminal_command` Handler
**Priority**: Medium (standalone)

- [ ] Update `cortex/mirai_cortex.py` — execute commands via `subprocess.run()`
  - Timeout: 30s, capture stdout/stderr
  - Blocklist: `rm -rf /`, `shutdown`, `reboot`, `mkfs`, `dd if=`
  - Feed output back to LLM in next cycle
- [ ] Update `cortex/system_prompt.py` — add `working_directory` field to schema

## Phase 5: Fix WebSocket Persistence
**Priority**: Medium (standalone within browser engine)

- [ ] Update `cortex/browser_engine/dom/service.py`
  - Add try/except around cached session usage with fallback to fresh session
  - Add `clear_cdp_cache()` method
  - Handle stale sessions when targets detach/reconnect

## Phase 6: Implement `browser_navigate` Handler
**Priority**: Medium (depends on Phase 5)

- [ ] Convert `cortex/mirai_cortex.py` main loop to async
  - `run_forever()` → `async run_forever()` with `asyncio.run()`
  - `brain.think()` → `await asyncio.to_thread(brain.think, ...)`
- [ ] Implement browser_navigate handler
  - Lazy-init persistent `BrowserSession` (headless)
  - Create browser-use `Agent` with URL as task
  - Return extracted content to cortex for next LLM cycle
- [ ] Update `cortex/system_prompt.py` — add `task` field to `browser_navigate` schema

---

## Design Decisions

1. **ChromaDB PersistentClient** over in-memory: data survives restarts
2. **Separate processes**: cortex ↔ swarm communicate via HTTP (port 5000)
3. **Async cortex loop**: required for browser-use (Playwright is async)
4. **No cross-encoder reranker for MVP**: ChromaDB cosine similarity is sufficient
5. **Minimal browser engine changes**: only session cache fix in dom/service.py
