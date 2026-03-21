"""
Mirai Cortex API Server — Python-Node bridge.

Exposes the cortex capabilities as HTTP endpoints so the Mirai gateway
(Node.js) can call into the Python cortex.

Run alongside mirai_cortex.py:
    python cortex/api_server.py

Listens on port 8100 by default (configurable via MIRAI_API_PORT).
"""

import os
import sys
import json
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import threading

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Shared state — the cortex instance can register itself here
_cortex_state = {
    "cycle_number": 0,
    "objective": "Not yet initialized",
    "last_action_result": "",
    "model": "unknown",
    "learning_enabled": False,
    "experience_count": 0,
}
_cortex_ref = None  # Will hold reference to MiraiCortex if available
_main_loop = None   # Reference to the cortex's asyncio event loop


def update_state(cortex):
    """Called by cortex to update shared state."""
    global _cortex_ref
    _cortex_ref = cortex
    _cortex_state.update({
        "cycle_number": getattr(cortex, "cycle_number", 0),
        "objective": getattr(cortex, "objective", ""),
        "last_action_result": getattr(cortex, "last_action_result", "")[:500],
        "model": getattr(cortex.brain, "model", "unknown") if hasattr(cortex, "brain") else "unknown",
        "learning_enabled": cortex.experience_store is not None,
        "experience_count": cortex.experience_store.get_count() if cortex.experience_store else 0,
    })


# ── Browser research helpers ──────────────────────────────────────

async def _async_browse(url: str, task: str, max_steps: int = 5) -> dict:
    """
    Use the full browser-use Agent to navigate a URL and extract content.
    Reuses the cortex's BrowserSession if available, otherwise creates one.
    """
    from browser_engine import Agent, BrowserSession, BrowserProfile

    # Reuse cortex's persistent session if available
    session = None
    if _cortex_ref and hasattr(_cortex_ref, '_browser_session') and _cortex_ref._browser_session:
        session = _cortex_ref._browser_session
    else:
        profile = BrowserProfile(headless=True)
        session = BrowserSession(browser_profile=profile)
        await session.start()

    try:
        agent = Agent(
            task=f"Navigate to {url} and {task}",
            browser_session=session,
        )
        history = await agent.run(max_steps=max_steps)
        final = history.final_result() if hasattr(history, "final_result") else str(history)
        content = str(final)[:5000]
        return {"success": True, "url": url, "content": content}
    except Exception as e:
        return {"success": False, "url": url, "error": str(e)}


async def _async_browse_batch(urls: list, task: str, max_steps: int = 5) -> dict:
    """Browse multiple URLs sequentially using the same browser session."""
    from browser_engine import BrowserSession, BrowserProfile

    session = None
    if _cortex_ref and hasattr(_cortex_ref, '_browser_session') and _cortex_ref._browser_session:
        session = _cortex_ref._browser_session
    else:
        profile = BrowserProfile(headless=True)
        session = BrowserSession(browser_profile=profile)
        await session.start()

    results = []
    for url in urls:
        try:
            from browser_engine import Agent
            agent = Agent(
                task=f"Navigate to {url} and {task}",
                browser_session=session,
            )
            history = await agent.run(max_steps=max_steps)
            final = history.final_result() if hasattr(history, "final_result") else str(history)
            content = str(final)[:5000]
            results.append({"url": url, "content": content, "success": True})
        except Exception as e:
            results.append({"url": url, "error": str(e), "success": False})

    return {"success": True, "results": results, "count": len(results)}


def _run_browse(url: str, task: str, max_steps: int = 5) -> dict:
    """Bridge sync API handler → async browser engine."""
    if _main_loop and _main_loop.is_running():
        # Submit to the cortex's event loop
        future = asyncio.run_coroutine_threadsafe(
            _async_browse(url, task, max_steps), _main_loop
        )
        return future.result(timeout=120)
    else:
        # No cortex loop — create a temporary one
        return asyncio.run(_async_browse(url, task, max_steps))


def _run_browse_batch(urls: list, task: str, max_steps: int = 5) -> dict:
    """Bridge sync API handler → async browser engine (batch)."""
    if _main_loop and _main_loop.is_running():
        future = asyncio.run_coroutine_threadsafe(
            _async_browse_batch(urls, task, max_steps), _main_loop
        )
        return future.result(timeout=300)
    else:
        return asyncio.run(_async_browse_batch(urls, task, max_steps))


class CortexAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the cortex API."""

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/api/status":
            if _cortex_ref:
                update_state(_cortex_ref)
            self._send_json({"success": True, "data": _cortex_state})

        elif path == "/api/journal":
            try:
                from learning import ReflectionEngine
                engine = ReflectionEngine()
                journal = engine.load_strategy_journal()
                self._send_json({"success": True, "journal": journal})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, 500)

        elif path == "/health":
            self._send_json({"status": "ok", "service": "Mirai Cortex API"})

        else:
            self._send_json({"error": "Not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._read_body()

        if path == "/api/think":
            prompt = body.get("prompt", "")
            if not prompt:
                self._send_json({"error": "Missing 'prompt'"}, 400)
                return
            try:
                from mirai_cortex import MiraiBrain
                brain = _cortex_ref.brain if _cortex_ref else MiraiBrain()
                result = brain.think(prompt)
                self._send_json({"success": True, "response": result})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, 500)

        elif path == "/api/memory/search":
            query = body.get("query", "")
            limit = body.get("limit", 5)
            if not query:
                self._send_json({"error": "Missing 'query'"}, 400)
                return
            try:
                from learning import ExperienceStore
                store = ExperienceStore()
                results = store.recall_similar(query, limit=limit)
                self._send_json({
                    "success": True,
                    "results": [e.to_dict() for e in results],
                })
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, 500)

        elif path == "/api/memory/store":
            try:
                from learning import ExperienceStore
                store = ExperienceStore()
                exp_id = store.store_experience(
                    situation=body.get("situation", ""),
                    action=body.get("action", ""),
                    action_type=body.get("action_type", "manual"),
                    outcome=body.get("outcome", ""),
                    success=body.get("success", True),
                    score=body.get("score", 1.0),
                    lesson=body.get("lesson", ""),
                )
                self._send_json({"success": True, "id": exp_id})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, 500)

        elif path == "/api/objective":
            new_objective = body.get("objective", "")
            if not new_objective:
                self._send_json({"error": "Missing 'objective'"}, 400)
                return
            if _cortex_ref:
                _cortex_ref.objective = new_objective
                self._send_json({"success": True, "objective": new_objective})
            else:
                self._send_json({"error": "Cortex not connected"}, 503)

        elif path == "/api/browse":
            url = body.get("url", "")
            task = body.get("task", "Extract the main text content from this page")
            max_steps = body.get("max_steps", 5)
            if not url:
                self._send_json({"error": "Missing 'url'"}, 400)
                return
            try:
                result = _run_browse(url, task, max_steps)
                self._send_json(result)
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, 500)

        elif path == "/api/browse/batch":
            # Batch browse: multiple URLs in parallel
            urls = body.get("urls", [])
            task = body.get("task", "Extract the main text content from this page")
            max_steps = body.get("max_steps", 5)
            if not urls:
                self._send_json({"error": "Missing 'urls' list"}, 400)
                return
            try:
                result = _run_browse_batch(urls, task, max_steps)
                self._send_json(result)
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, 500)

        else:
            self._send_json({"error": "Not found"}, 404)

    def log_message(self, format, *args):
        # Suppress default HTTP logging
        pass


def start_api_server(port=None, cortex=None):
    """Start the API server in a background thread."""
    global _cortex_ref, _main_loop
    if cortex:
        _cortex_ref = cortex
    # Capture the running event loop so browse endpoints can submit async tasks
    try:
        _main_loop = asyncio.get_running_loop()
    except RuntimeError:
        _main_loop = None

    port = port or int(os.environ.get("MIRAI_API_PORT", "8100"))
    server = HTTPServer(("0.0.0.0", port), CortexAPIHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"[API] Cortex API server running on http://localhost:{port}")
    return server


if __name__ == "__main__":
    port = int(os.environ.get("MIRAI_API_PORT", "8100"))
    print(f"Starting Mirai Cortex API server on port {port}...")
    server = HTTPServer(("0.0.0.0", port), CortexAPIHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down API server...")
        server.shutdown()
