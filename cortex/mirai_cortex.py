import asyncio
import subprocess
import json
import re
import sys
import os

import requests
from openai import OpenAI

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

# ── LLM / Gateway configuration ─────────────────────────────────
_LLM_API_KEY = os.environ.get("LLM_API_KEY", "openclaw")
_LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:3000/v1")
_GATEWAY_URL = _LLM_BASE_URL.replace("/v1", "")
_GATEWAY_HEALTH_CHECK_INTERVAL = 10  # Check gateway every N cycles
_OPENCLAW_WHATSAPP_NUMBER = os.environ.get("OPENCLAW_WHATSAPP_NUMBER", "")


class MiraiBrain:
    """
    Connects to the local OpenClaw Gateway via the OpenAI SDK.
    By default, uses Claude Opus 4.6 via OAuth for zero-cost reasoning.
    """

    def __init__(self, model="anthropic/claude-opus-4-6"):
        self.model = model
        self.client = OpenAI(api_key=_LLM_API_KEY, base_url=_LLM_BASE_URL)
        print(f"[MiraiBrain] Initialized Neural Link to Gateway via {self.model}")

    def think(self, prompt: str) -> str:
        """Send a prompt to the selected model via the OpenAI SDK."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You must reply ONLY in strict JSON."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=4096,
                temperature=0.7,
                extra_body={"thinking": {"type": "enabled", "budget_tokens": 10000}},
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"[ERROR] Cortex LLM call failed: {e}")
            return '{"action": "standby", "reason": "Brain disconnected"}'


# ── Gateway Management ───────────────────────────────────────────

class GatewayManager:
    """
    Manages gateway health checks and messaging.
    LLM calls go through the OpenAI SDK; only messaging still uses the CLI.
    """

    def __init__(self):
        self.gateway_url = _GATEWAY_URL
        self._healthy = False

    def check_health(self) -> bool:
        """Check if the gateway is responding."""
        try:
            resp = requests.get(f"{self.gateway_url}/health", timeout=5)
            self._healthy = resp.status_code == 200
            return self._healthy
        except Exception:
            self._healthy = False
            return False

    def watchdog(self, cycle_number: int) -> None:
        """
        Gateway watchdog — runs every N cycles.
        Checks gateway health and logs a warning if it's down.
        """
        if cycle_number % _GATEWAY_HEALTH_CHECK_INTERVAL != 0:
            return

        if not self.check_health():
            print("[GATEWAY] Warning: gateway not responding. Restart it manually.")

    def send_message(self, text: str, to: str = "") -> str:
        """
        Send a message using `openclaw message send` (only remaining CLI call).
        Falls back to logging if the CLI is unavailable.
        """
        recipient = to or _OPENCLAW_WHATSAPP_NUMBER or "WhatsApp"

        try:
            result = subprocess.run(
                ["openclaw", "message", "send", "--to", recipient, "--message", text],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return f"Message sent to {recipient}: {text}"
        except FileNotFoundError:
            pass
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            pass

        # Fallback: log the message (gateway HTTP messaging can be added later)
        print(f"[COMMS] Message (not delivered — no messaging backend): {text}")
        return f"Message logged (no messaging backend available): {text}"


class MiraiCortex:
    """
    The main autonomous loop (The Heartbeat).
    Orchestrates the Browser (Hands), the Brain (LLM), and the Subconscious (MiroFish).
    Now with self-learning: experience memory, reflection, skill gap detection, market radar.
    Gateway health monitoring and E2B sandbox for code execution.
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

        # Gateway management
        self.gateway = GatewayManager()

        # E2B sandbox runner (lazy-initialized)
        self._sandbox_runner = None
        self._sandbox_checked = False

    # ── Sandbox Runner ─────────────────────────────────────────────

    def _get_sandbox(self):
        """Lazy-init E2B sandbox runner."""
        if not self._sandbox_checked:
            self._sandbox_checked = True
            try:
                from sandbox_runner import SandboxRunner
                self._sandbox_runner = SandboxRunner()
            except Exception as e:
                print(f"[WARNING] Sandbox runner unavailable: {e}")
        return self._sandbox_runner

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
        elif action_type == "analyze_business":
            self._handle_analyze_business(action_data)
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

        # Route through E2B sandbox if available
        sandbox = self._get_sandbox()
        if sandbox:
            result = sandbox.execute(
                command=command,
                timeout=30,
                cwd=working_dir,
            )
            stdout = result.get("stdout", "")
            stderr = result.get("stderr", "")
            exit_code = result.get("exit_code", -1)
            method = result.get("execution_method", "unknown")

            output = f"Exit code: {exit_code} (via {method})"
            if stdout:
                output += f"\nSTDOUT:\n{stdout}"
            if stderr:
                output += f"\nSTDERR:\n{stderr}"

            print(f"[HANDS] Command result (exit={exit_code}, method={method}): {stdout[:200]}")
            self.last_action_result = output
            return

        # Fallback: direct subprocess (original behavior)
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

    # ── analyze_business ────────────────────────────────────────

    def _handle_analyze_business(self, data: dict):
        exec_summary = data.get("exec_summary", "")
        depth = data.get("depth", "standard")
        print(f"[SUBCONSCIOUS] Business intelligence analysis: {exec_summary[:100]}")

        try:
            resp = requests.post(
                f"{_SWARM_URL}/api/bi/analyze",
                json={"exec_summary": exec_summary, "research_depth": depth},
                timeout=180,
            )
            result = resp.json()

            # Handle needs_more_info (422) — not enough data to analyze
            if result.get("status") == "needs_more_info":
                missing = result.get("missing_critical", [])
                quality = result.get("data_quality", 0)
                self.last_action_result = (
                    f"BI: Insufficient data (quality: {quality:.0%}). "
                    f"Missing critical fields: {', '.join(missing)}. "
                    f"Need at minimum: company name, industry, product description.\n"
                    f"Suggested template:\n{result.get('template', '')}"
                )
                return

            resp.raise_for_status()

            if result.get("success"):
                analysis = result.get("analysis", {})
                prediction = analysis.get("prediction", {})
                plan = analysis.get("plan", {})
                data_quality = analysis.get("data_quality", 1.0)

                verdict = prediction.get("verdict", "Unknown")
                score = prediction.get("overall_score", 0)
                reasoning = prediction.get("reasoning", "")

                # Format top dimension scores
                dims = prediction.get("dimensions", [])
                dim_lines = "\n".join(
                    f"  - {d['name']}: {d['score']}/10 — {d['reasoning'][:80]}"
                    for d in dims[:7]
                )

                # Format top next moves
                moves = plan.get("next_moves", [])
                move_lines = "\n".join(
                    f"  {i+1}. {m.get('action', '')}"
                    for i, m in enumerate(moves[:3])
                )

                quality_note = ""
                if data_quality < 0.7:
                    quality_note = (
                        f"\n\n[WARNING] Data quality: {data_quality:.0%} — "
                        f"results may be less reliable."
                    )

                # Council info
                council_note = ""
                council = prediction.get("council", {})
                if council.get("used"):
                    models = ", ".join(council.get("models", []))
                    contested = council.get("contested_dimensions", [])
                    council_note = f"\n\nLLM Council: {models}"
                    if contested:
                        contest_lines = ", ".join(
                            f"{c['dimension']} (spread: {c['spread']})"
                            for c in contested
                        )
                        council_note += f"\nContested: {contest_lines}"
                    else:
                        council_note += "\nAll models agree — high conviction."

                # Data sources
                sources = analysis.get("data_sources_used", [])
                sources_note = ""
                if sources:
                    sources_note = f"\n\nData sources: {', '.join(sources)}"

                output = (
                    f"BI Verdict: {verdict} (score: {score}/10)\n"
                    f"Data Quality: {data_quality:.0%}\n"
                    f"Reasoning: {reasoning[:300]}\n\n"
                    f"Dimension Scores:\n{dim_lines}\n\n"
                    f"Top Recommendations:\n{move_lines}"
                    f"{council_note}"
                    f"{sources_note}"
                    f"{quality_note}"
                )
                self.last_action_result = output[:3000]
            else:
                self.last_action_result = f"BI analysis failed: {result.get('error', 'unknown')}"

        except Exception as e:
            self.last_action_result = (
                f"BI analysis failed (is MiroFish running on {_SWARM_URL}?): {e}"
            )

    # ── message_human ────────────────────────────────────────────

    def _handle_message_human(self, data: dict):
        message_text = data.get("text", "")
        recipient = data.get("to", "")
        print(f"[COMMS] Messaging Human: {message_text}")
        result = self.gateway.send_message(text=message_text, to=recipient)
        self.last_action_result = result

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

        # ── Gateway health check at boot ──────────────────────────
        if not self.gateway.check_health():
            print("[GATEWAY] Warning: gateway not responding at boot. LLM calls will fail.")

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

            # ── Gateway watchdog ───────────────────────────────────
            self.gateway.watchdog(self.cycle_number)

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
    print("1. Claude Opus 4.6 via OAuth (Recommended - Best Logic, Zero Cost)")
    print("2. GPT-5.4 via OAuth (Zero Cost)")
    print("3. Custom OpenClaw Model String")

    choice = input("\nEnter choice [1]: ").strip()

    if choice == "2":
        return "openai/gpt-5.4"
    elif choice == "3":
        return input("Enter OpenClaw model string (e.g., openai/gpt-5.4): ").strip()
    else:
        return "anthropic/claude-opus-4-6"


if __name__ == "__main__":
    selected_model = choose_model()
    mirai = MiraiCortex(model=selected_model)
    asyncio.run(mirai.run_forever())
