import asyncio
import time
import subprocess
import json
import re
import sys
import os

from system_prompt import MIRAI_SYSTEM_PROMPT

# ── Dangerous command patterns (defense-in-depth) ────────────────
_BLOCKED_COMMANDS = [
    r"\brm\s+-rf\s+/",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bmkfs\b",
    r"\bdd\s+if=",
    r"\b:(){ :|:& };:",  # fork bomb
    r"\bchmod\s+-R\s+777\s+/",
    r"\bcurl\b.*\|\s*bash",
    r"\bwget\b.*\|\s*bash",
]
_BLOCKED_RE = re.compile("|".join(_BLOCKED_COMMANDS), re.IGNORECASE)

# ── Default MiroFish backend URL ─────────────────────────────────
_SWARM_URL = os.environ.get("MIRAI_SWARM_URL", "http://localhost:5000")


class MiraiBrain:
    """
    Connects to the local OpenClaw Gateway to utilize the selected model.
    By default, uses Claude 3 Opus via OAuth for zero-cost reasoning.
    """

    def __init__(self, model="anthropic/claude-opus-4-6"):
        self.model = model
        print(f"[MiraiBrain] Initialized Neural Link to OpenClaw Gateway via {self.model}")

    def think(self, prompt: str) -> str:
        """Send a prompt to the selected model via the OpenClaw CLI."""
        try:
            result = subprocess.run(
                [
                    "openclaw", "agent",
                    "--message", prompt,
                    "--model", self.model,
                    "--thinking", "high",
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=120,
            )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            print("[ERROR] Cortex timed out waiting for LLM response")
            return '{"action": "standby", "reason": "Brain timed out"}'
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Cortex Disconnect: {e.stderr}")
            return '{"action": "standby", "reason": "Brain disconnected"}'


class MiraiCortex:
    """
    The main autonomous loop (The Heartbeat).
    Orchestrates the Browser (Hands), the Brain (LLM), and the Subconscious (MiroFish).
    """

    def __init__(self, model: str):
        self.brain = MiraiBrain(model=model)
        self.objective = (
            "Initialize systems, map local environment, "
            "and await user directives via WhatsApp."
        )
        self.last_action_result = ""
        self._browser_session = None

    # ── Action Dispatch ──────────────────────────────────────────

    async def execute_action(self, action_json: str):
        """Parse the JSON response from the LLM and take action."""
        try:
            # Strip markdown code fences
            text = action_json.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            action_data = json.loads(text)
            action_type = action_data.get("action")

            if action_type == "browser_navigate":
                await self._handle_browser_navigate(action_data)
            elif action_type == "terminal_command":
                self._handle_terminal_command(action_data)
            elif action_type == "swarm_predict":
                self._handle_swarm_predict(action_data)
            elif action_type == "message_human":
                self._handle_message_human(action_data)
            elif action_type == "standby":
                print("[SYSTEM] Standing by...")
                self.last_action_result = "Standing by — no action taken."
            else:
                print(f"[SYSTEM] Unknown action: {action_type}")
                self.last_action_result = f"Unknown action type: {action_type}"

        except json.JSONDecodeError:
            print(f"[WARNING] Cortex returned non-JSON response: {action_json[:200]}")
            self.last_action_result = "Failed to parse LLM response as JSON."

    # ── browser_navigate ─────────────────────────────────────────

    async def _handle_browser_navigate(self, data: dict):
        url = data.get("url", "")
        task = data.get("task", f"Navigate to {url} and extract the main content")
        print(f"[HANDS] Navigating to: {url} | Task: {task}")

        try:
            # Lazy import — browser_engine is heavy
            sys.path.insert(0, os.path.dirname(__file__))
            from browser_engine import Agent, BrowserSession, BrowserProfile

            if self._browser_session is None:
                profile = BrowserProfile(headless=True)
                self._browser_session = BrowserSession(browser_profile=profile)
                await self._browser_session.start()

            agent = Agent(
                task=task,
                browser_session=self._browser_session,
            )
            history = await agent.run(max_steps=10)

            # Extract result
            final = history.final_result() if hasattr(history, "final_result") else str(history)
            result_text = str(final)[:2000]
            print(f"[HANDS] Browser result: {result_text[:200]}...")
            self.last_action_result = f"Browser navigated to {url}. Result: {result_text}"

        except ImportError as e:
            msg = f"Browser engine not available: {e}"
            print(f"[ERROR] {msg}")
            self.last_action_result = msg
        except Exception as e:
            msg = f"Browser navigation failed: {e}"
            print(f"[ERROR] {msg}")
            self.last_action_result = msg

    # ── terminal_command ─────────────────────────────────────────

    def _handle_terminal_command(self, data: dict):
        command = data.get("command", "")
        working_dir = data.get("working_directory", None)
        print(f"[HANDS] Executing command: {command}")

        # Safety check
        if _BLOCKED_RE.search(command):
            msg = f"BLOCKED: Command matched a dangerous pattern: {command}"
            print(f"[SECURITY] {msg}")
            self.last_action_result = msg
            return

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=working_dir,
            )
            stdout = result.stdout[:3000] if result.stdout else ""
            stderr = result.stderr[:1000] if result.stderr else ""
            exit_code = result.returncode

            output = f"Exit code: {exit_code}"
            if stdout:
                output += f"\nSTDOUT:\n{stdout}"
            if stderr:
                output += f"\nSTDERR:\n{stderr}"

            print(f"[HANDS] Command result (exit={exit_code}): {stdout[:200]}")
            self.last_action_result = output

        except subprocess.TimeoutExpired:
            msg = "Command timed out after 30 seconds"
            print(f"[ERROR] {msg}")
            self.last_action_result = msg
        except Exception as e:
            msg = f"Command execution failed: {e}"
            print(f"[ERROR] {msg}")
            self.last_action_result = msg

    # ── swarm_predict ────────────────────────────────────────────

    def _handle_swarm_predict(self, data: dict):
        scenario = data.get("scenario", "")
        graph_id = data.get("graph_id", "")
        print(f"[SUBCONSCIOUS] Waking swarm to predict: {scenario[:100]}")

        try:
            import requests

            resp = requests.post(
                f"{_SWARM_URL}/api/predict/",
                json={"scenario": scenario, "graph_id": graph_id},
                timeout=60,
            )
            resp.raise_for_status()
            result = resp.json()

            if result.get("success"):
                prediction = result.get("prediction", "No prediction returned")
                facts = result.get("context_facts", [])
                output = f"Prediction: {prediction}"
                if facts:
                    output += f"\n\nSupporting facts ({len(facts)}):\n"
                    output += "\n".join(f"- {f}" for f in facts[:10])
                self.last_action_result = output[:3000]
            else:
                self.last_action_result = f"Swarm prediction failed: {result.get('error', 'unknown')}"

            print(f"[SUBCONSCIOUS] Prediction received ({len(self.last_action_result)} chars)")

        except Exception as e:
            msg = f"Swarm prediction failed (is MiroFish running on {_SWARM_URL}?): {e}"
            print(f"[ERROR] {msg}")
            self.last_action_result = msg

    # ── message_human ────────────────────────────────────────────

    def _handle_message_human(self, data: dict):
        message_text = data.get("text", "")
        print(f"[COMMS] Messaging Human: {message_text}")
        try:
            subprocess.run(
                [
                    "openclaw", "agent",
                    "--message", message_text,
                    "--to", "WhatsApp",
                ],
                capture_output=True,
                check=True,
                timeout=30,
            )
            self.last_action_result = f"Message sent to human: {message_text}"
        except subprocess.CalledProcessError as e:
            msg = f"Failed to message human via OpenClaw: {e.stderr}"
            print(f"[ERROR] {msg}")
            self.last_action_result = msg
        except Exception as e:
            self.last_action_result = f"Messaging failed: {e}"

    # ── Main Loop ────────────────────────────────────────────────

    async def run_forever(self):
        print("\n=============================================")
        print("          M I R A I   O N L I N E          ")
        print(f"     Architecture: {self.brain.model} Cortex     ")
        print("=============================================\n")

        while True:
            print(f"[*] Current Objective: {self.objective}")

            # Build prompt with context from last action
            system_prompt = MIRAI_SYSTEM_PROMPT.format(objective=self.objective)
            if self.last_action_result:
                system_prompt += (
                    f"\n\nResult of your last action:\n"
                    f"{self.last_action_result[:2000]}"
                )

            print(f"[CORTEX] Querying {self.brain.model}...")
            thought = await asyncio.to_thread(self.brain.think, system_prompt)

            print(f"[CORTEX] Decision Received: {thought[:300]}")
            await self.execute_action(thought)

            # Adaptive heartbeat
            print("[SYSTEM] Cortical sleep cycle (10 seconds)...\n")
            await asyncio.sleep(10)


def choose_model():
    print("=============================================")
    print("       Initialize Mirai Neural Link          ")
    print("=============================================")
    print("Select the LLM to power the Cortex:")
    print("1. Claude 3 Opus via OAuth (Recommended - Best Logic, Zero Cost)")
    print("2. ChatGPT Plus via OAuth (Zero Cost)")
    print("3. Custom OpenClaw Model String")

    choice = input("\nEnter choice [1]: ").strip()

    if choice == "2":
        return "openai-codex:oauth"
    elif choice == "3":
        return input("Enter OpenClaw model string (e.g., openai/gpt-4o): ").strip()
    else:
        return "anthropic/claude-opus-4-6"


if __name__ == "__main__":
    selected_model = choose_model()
    mirai = MiraiCortex(model=selected_model)
    asyncio.run(mirai.run_forever())
