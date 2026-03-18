"""
Mirai Cortex API Server — Python-Node bridge.

Exposes the cortex capabilities as HTTP endpoints so the OpenClaw fork
(Node.js gateway) can call into the Python cortex.

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

        else:
            self._send_json({"error": "Not found"}, 404)

    def log_message(self, format, *args):
        # Suppress default HTTP logging
        pass


def start_api_server(port=None, cortex=None):
    """Start the API server in a background thread."""
    global _cortex_ref
    if cortex:
        _cortex_ref = cortex

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
