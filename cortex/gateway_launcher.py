"""
Gateway Launcher — starts the Mirai gateway (Node.js) as a subprocess.
"""
import os
import shutil
import signal
import subprocess
import time

import requests

_MIRAI_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_GATEWAY_DIR = os.path.join(_MIRAI_ROOT, "gateway")
_GATEWAY_ENTRY = os.path.join(_GATEWAY_DIR, "mirai.mjs")
_GATEWAY_PORT = int(os.environ.get("MIRAI_GATEWAY_PORT", "19789"))


class GatewayLauncher:
    """Starts and monitors the Node.js gateway process."""

    def __init__(self, port=None):
        self.port = port or _GATEWAY_PORT
        self.process = None
        self._log_file = None

    def is_running(self) -> bool:
        if self.process is None:
            return False
        return self.process.poll() is None

    def health_check(self) -> bool:
        try:
            resp = requests.get(
                f"http://localhost:{self.port}/health", timeout=5
            )
            return resp.status_code == 200
        except Exception:
            return False

    def start(self, timeout=30) -> bool:
        """Start the gateway subprocess. Returns True if it becomes healthy."""
        if self.health_check():
            print(f"[GATEWAY] Already running on port {self.port}")
            return True

        if not os.path.exists(_GATEWAY_ENTRY):
            print(f"[GATEWAY] Entry point not found: {_GATEWAY_ENTRY}")
            print("[GATEWAY] Run 'cd gateway && pnpm install && pnpm build' first.")
            return False

        node_path = shutil.which("node")
        if not node_path:
            print("[GATEWAY] Node.js not found. Install Node.js 22+.")
            return False

        # Ensure chat completions HTTP endpoint is enabled in config
        self._ensure_http_endpoint_enabled()

        print(f"[GATEWAY] Starting Mirai gateway on port {self.port}...")
        log_path = os.path.join(_GATEWAY_DIR, "gateway.log")
        self._log_file = open(log_path, "a")

        env = os.environ.copy()
        env["PORT"] = str(self.port)

        self.process = subprocess.Popen(
            [node_path, _GATEWAY_ENTRY, "gateway", "run",
             "--port", str(self.port), "--bind", "loopback"],
            cwd=_GATEWAY_DIR,
            stdout=self._log_file,
            stderr=self._log_file,
            env=env,
        )

        for _ in range(timeout):
            if self.health_check():
                print(f"[GATEWAY] Running on http://localhost:{self.port}")
                return True
            if not self.is_running():
                print("[GATEWAY] Process exited unexpectedly. Check gateway/gateway.log")
                return False
            time.sleep(1)

        print(f"[GATEWAY] Timed out after {timeout}s. Check gateway/gateway.log")
        return False

    def stop(self):
        if self.process and self.is_running():
            self.process.send_signal(signal.SIGTERM)
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
        if self._log_file:
            self._log_file.close()

    @staticmethod
    def _ensure_http_endpoint_enabled():
        """Ensure the gateway config has chatCompletions HTTP endpoint enabled."""
        import json
        config_path = os.path.join(os.path.expanduser("~"), ".openclaw", "openclaw.json")
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
        except (IOError, json.JSONDecodeError):
            return

        gw = config.setdefault("gateway", {})
        http = gw.setdefault("http", {})
        endpoints = http.setdefault("endpoints", {})
        cc = endpoints.setdefault("chatCompletions", {})

        if cc.get("enabled") is not True:
            cc["enabled"] = True
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)
            print("[GATEWAY] Enabled HTTP chat completions endpoint")
