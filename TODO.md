# Mirai TODO — Implementation Plan

## Status Legend
- [ ] Not started
- [~] In progress
- [x] Complete

---

## Phase 1: ChromaDB Episodic Memory System
**Status**: COMPLETE

- [x] Create `subconscious/memory/__init__.py` — package init
- [x] Create `subconscious/memory/episodic_store.py` — `EpisodicMemoryStore` class
  - `PersistentClient` (survives restarts) at `subconscious/memory/.chromadb_data/`
  - Collections: `{graph_id}_nodes`, `{graph_id}_edges`, `{graph_id}_episodes`
  - Methods: `create_graph`, `add_episodes`, `search`, `add_nodes`, `add_edges`, `get_all_nodes`, `get_all_edges`, `get_node_edges`
  - Semantic search via ChromaDB's built-in sentence-transformer embeddings

## Phase 2: Strip Zep Cloud Dependency
**Status**: COMPLETE

- [x] `subconscious/swarm/config.py` — removed `ZEP_API_KEY`, added `CHROMADB_PERSIST_PATH`
- [x] `subconscious/swarm/utils/zep_paging.py` — rewritten to delegate to `EpisodicMemoryStore`
- [x] `subconscious/swarm/services/graph_builder.py` — uses `EpisodicMemoryStore`
- [x] `subconscious/swarm/services/zep_entity_reader.py` — uses `EpisodicMemoryStore`
- [x] `subconscious/swarm/services/zep_graph_memory_updater.py` — uses `EpisodicMemoryStore`
- [x] `subconscious/swarm/services/zep_tools.py` — replaced `Zep` client with ChromaDB search
- [x] `subconscious/swarm/services/oasis_profile_generator.py` — replaced Zep with ChromaDB
- [x] `subconscious/swarm/services/ontology_generator.py` — removed Zep import reference
- [x] `subconscious/swarm/api/graph.py` — removed `ZEP_API_KEY` guards
- [x] `subconscious/swarm/api/simulation.py` — removed `ZEP_API_KEY` guards

## Phase 3: Wire `swarm_predict` to Cortex
**Status**: COMPLETE

- [x] Created `subconscious/swarm/api/predict.py` — `POST /api/predict`
- [x] Updated `subconscious/swarm/api/__init__.py` — registered `predict_bp`
- [x] Updated `subconscious/swarm/__init__.py` — registered blueprint at `/api/predict`
- [x] Updated `cortex/mirai_cortex.py` — `swarm_predict` handler calls Flask via HTTP

## Phase 4: Implement `terminal_command` Handler
**Status**: COMPLETE

- [x] `cortex/mirai_cortex.py` — `subprocess.run()` with 30s timeout, stdout/stderr capture
- [x] Regex blocklist for dangerous commands (rm -rf /, shutdown, dd, fork bomb, curl|bash, etc.)
- [x] Command output fed back to LLM in next cycle via `self.last_action_result`
- [x] `cortex/system_prompt.py` — added `working_directory` field

## Phase 5: Fix WebSocket Persistence
**Status**: COMPLETE

- [x] `cortex/browser_engine/dom/service.py`
  - Stale-session recovery in `_get_cdp_session()` with fallback to fresh session
  - `clear_cdp_cache()` method for reconnect/target-detach scenarios
  - `__aexit__` clears cache on context manager exit

## Phase 6: Implement `browser_navigate` Handler
**Status**: COMPLETE

- [x] Converted `cortex/mirai_cortex.py` to async (`asyncio.run()`)
- [x] `brain.think()` wrapped in `asyncio.to_thread()` for non-blocking calls
- [x] Lazy-init persistent headless `BrowserSession`
- [x] browser-use `Agent` with URL + task, result fed back to LLM
- [x] `cortex/system_prompt.py` — added `task` field to `browser_navigate` schema

---

## Future Improvements

- [ ] Add cross-encoder reranker for better semantic search quality
- [ ] LLM-based entity extraction from episodes (automatic knowledge graph enrichment)
- [ ] ChromaDB → PostgreSQL migration for production scale
- [ ] Docker-compose for cortex + swarm co-deployment
- [ ] WhatsApp/Telegram integration testing with OpenClaw

## Design Decisions

1. **ChromaDB PersistentClient** over in-memory: data survives restarts
2. **Separate processes**: cortex <-> swarm communicate via HTTP (port 5000)
3. **Async cortex loop**: required for browser-use (Playwright is async)
4. **No cross-encoder reranker for MVP**: ChromaDB cosine similarity is sufficient
5. **Minimal browser engine changes**: only session cache fix in dom/service.py
