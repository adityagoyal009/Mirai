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
    Now with self-learning: experience memory, reflection, skill gap detection, market radar.
    """

    def __init__(self, model: str):
        self.brain = MiraiBrain(model=model)
        self.objective = (
            "Initialize systems, map local environment, "
            "and await user directives via WhatsApp."
        )
        self.last_action_result = ""
        self._browser_session = None

        # Learning system (lazy-initialized)
        self.cycle_number = 0
        self._learning_initialized = False
        self.experience_store = None
        self.reflection_engine = None
        self.skill_forge = None
        self.market_radar = None

    # ── Learning System Init ─────────────────────────────────────

    def _init_learning(self):
        """Lazy-initialize the self-learning modules."""
        if self._learning_initialized:
            return
        self._learning_initialized = True

        try:
            from learning import ExperienceStore, ReflectionEngine, SkillForge, MarketRadar
            self.experience_store = ExperienceStore()
            self.reflection_engine = ReflectionEngine()
            self.skill_forge = SkillForge()
            self.market_radar = MarketRadar()
            print("[LEARNING] Self-learning system initialized")
            print(f"[LEARNING] Experience count: {self.experience_store.get_count()}")
            if self.reflection_engine.load_strategy_journal():
                print("[LEARNING] Strategy journal loaded from previous session")
        except Exception as e:
            print(f"[WARNING] Learning system unavailable: {e}")

    # ── Action Parsing ───────────────────────────────────────────

    @staticmethod
    def _parse_action(thought: str) -> dict:
        """Parse LLM response into action dict. Returns empty dict on failure."""
        try:
            text = thought.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            return json.loads(text.strip())
        except (json.JSONDecodeError, ValueError):
            return {}

    # ── Action Dispatch ──────────────────────────────────────────

    async def execute_action(self, action_data: dict):
        """Execute a parsed action dict."""
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

    # ── browser_navigate ─────────────────────────────────────────

    async def _handle_browser_navigate(self, data: dict):
        url = data.get("url", "")
        task = data.get("task", f"Navigate to {url} and extract the main content")
        print(f"[HANDS] Navigating to: {url} | Task: {task}")

        try:
            sys.path.insert(0, os.path.dirname(__file__))
            from browser_engine import Agent, BrowserSession, BrowserProfile

            if self._browser_session is None:
                profile = BrowserProfile(headless=True)
                self._browser_session = BrowserSession(browser_profile=profile)
                await self._browser_session.start()

            agent = Agent(task=task, browser_session=self._browser_session)
            history = await agent.run(max_steps=10)

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

        if _BLOCKED_RE.search(command):
            msg = f"BLOCKED: Command matched a dangerous pattern: {command}"
            print(f"[SECURITY] {msg}")
            self.last_action_result = msg
            return

        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=30, cwd=working_dir,
            )
            stdout = result.stdout[:3000] if result.stdout else ""
            stderr = result.stderr[:1000] if result.stderr else ""
            output = f"Exit code: {result.returncode}"
            if stdout:
                output += f"\nSTDOUT:\n{stdout}"
            if stderr:
                output += f"\nSTDERR:\n{stderr}"

            print(f"[HANDS] Command result (exit={result.returncode}): {stdout[:200]}")
            self.last_action_result = output

        except subprocess.TimeoutExpired:
            self.last_action_result = "Command timed out after 30 seconds"
        except Exception as e:
            self.last_action_result = f"Command execution failed: {e}"

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

        except Exception as e:
            self.last_action_result = f"Swarm prediction failed (is MiroFish running on {_SWARM_URL}?): {e}"

    # ── message_human ────────────────────────────────────────────

    def _handle_message_human(self, data: dict):
        message_text = data.get("text", "")
        print(f"[COMMS] Messaging Human: {message_text}")
        try:
            subprocess.run(
                ["openclaw", "agent", "--message", message_text, "--to", "WhatsApp"],
                capture_output=True, check=True, timeout=30,
            )
            self.last_action_result = f"Message sent to human: {message_text}"
        except Exception as e:
            self.last_action_result = f"Messaging failed: {e}"

    # ── Experience formatting ────────────────────────────────────

    @staticmethod
    def _format_experiences(experiences) -> str:
        """Format past experiences for system prompt injection."""
        if not experiences:
            return ""
        lines = []
        for exp in experiences[:5]:
            status = "OK" if exp.success else "FAIL"
            lines.append(
                f"- [{status}] {exp.action_type}: {exp.situation[:60]} → {exp.outcome[:80]}"
            )
        return (
            "\n--- RELEVANT PAST EXPERIENCES ---\n"
            + "\n".join(lines)
            + "\n--- END EXPERIENCES ---\n"
        )

    # ── Main Loop (The Heartbeat) ────────────────────────────────

    async def run_forever(self):
        print("\n=============================================")
        print("          M I R A I   O N L I N E          ")
        print(f"     Architecture: {self.brain.model} Cortex     ")
        print("=============================================\n")

        # Start the API server for OpenClaw bridge
        try:
            from api_server import start_api_server
            start_api_server(cortex=self)
        except Exception as e:
            print(f"[WARNING] API server failed to start: {e}")

        while True:
            self._init_learning()
            self.cycle_number += 1

            print(f"[*] Cycle {self.cycle_number} | Objective: {self.objective}")

            # ── PRE-ACTION: Recall past experiences ──────────────
            past_experiences_text = ""
            if self.experience_store:
                try:
                    similar = self.experience_store.recall_similar(self.objective, limit=3)
                    past_experiences_text = self._format_experiences(similar)
                except Exception:
                    pass

            # ── PRE-ACTION: Load strategy journal ────────────────
            journal_text = ""
            if self.reflection_engine:
                try:
                    raw_journal = self.reflection_engine.load_strategy_journal()
                    if raw_journal:
                        journal_text = (
                            "\n--- SELF-LEARNED RULES ---\n"
                            + raw_journal[:1500]
                            + "\n--- END RULES ---\n"
                        )
                except Exception:
                    pass

            # ── BUILD PROMPT ─────────────────────────────────────
            system_prompt = MIRAI_SYSTEM_PROMPT.format(
                objective=self.objective,
                strategy_journal=journal_text,
                past_experiences=past_experiences_text,
            )
            if self.last_action_result:
                system_prompt += (
                    f"\n\nResult of your last action:\n"
                    f"{self.last_action_result[:2000]}"
                )

            # ── THINK ────────────────────────────────────────────
            print(f"[CORTEX] Querying {self.brain.model}...")
            thought = await asyncio.to_thread(self.brain.think, system_prompt)
            print(f"[CORTEX] Decision Received: {thought[:300]}")

            # ── PARSE + ACT ──────────────────────────────────────
            action_data = self._parse_action(thought)
            if action_data:
                await self.execute_action(action_data)
            else:
                print(f"[WARNING] Non-JSON response: {thought[:200]}")
                self.last_action_result = "Failed to parse LLM response as JSON."

            # ── POST-ACTION: Store experience ────────────────────
            if self.experience_store and action_data:
                try:
                    action_type = action_data.get("action", "unknown")
                    outcome = self.last_action_result[:500]
                    # Heuristic success check
                    lower_outcome = outcome.lower()
                    success = not any(
                        kw in lower_outcome
                        for kw in ("error", "failed", "blocked", "timed out", "unavailable")
                    )
                    self.experience_store.store_experience(
                        situation=self.objective[:300],
                        action=json.dumps(action_data)[:500],
                        action_type=action_type,
                        outcome=outcome,
                        success=success,
                        score=1.0 if success else 0.0,
                        cycle_number=self.cycle_number,
                    )
                except Exception as e:
                    print(f"[LEARNING] Failed to store experience: {e}")

            # ── PERIODIC: Reflection ─────────────────────────────
            if (
                self.reflection_engine
                and self.experience_store
                and self.reflection_engine.should_reflect(self.cycle_number)
            ):
                try:
                    print(f"[LEARNING] Reflection triggered at cycle {self.cycle_number}")
                    recent = self.experience_store.get_recent(n=50)
                    result = self.reflection_engine.reflect(recent)
                    self.reflection_engine.update_strategy_journal(result)

                    # Also detect skill gaps
                    if self.skill_forge:
                        failures = self.experience_store.get_failure_patterns(limit=20)
                        if failures:
                            self.skill_forge.detect_capability_gaps(failures)
                except Exception as e:
                    print(f"[LEARNING] Reflection failed: {e}")

            # ── PERIODIC: Market Radar ───────────────────────────
            if self.market_radar and self.market_radar.should_check(self.cycle_number):
                try:
                    signals = self.market_radar.check_all()
                    if signals:
                        signal_text = "\n".join(
                            f"- [{s.source}] {s.query}: {s.findings[:100]}"
                            for s in signals
                        )
                        self.last_action_result += f"\n\nMarket signals:\n{signal_text}"
                except Exception as e:
                    print(f"[LEARNING] Market radar check failed: {e}")

            # ── HEARTBEAT SLEEP ──────────────────────────────────
            print(f"[SYSTEM] Cortical sleep cycle (10 seconds)...\n")
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
