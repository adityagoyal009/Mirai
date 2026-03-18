"""
E2B Sandbox Runner — safe code execution for LLM-generated code.

Routes LLM-generated code through E2B Firecracker microVMs for sandboxed
execution. Safe commands (ls, cat, git, etc.) still run via subprocess
for low latency. Only code the LLM generates goes through the sandbox.

Usage:
    runner = SandboxRunner()
    result = runner.execute("print('hello world')", language="python")
    # → {"stdout": "hello world\n", "stderr": "", "exit_code": 0}
"""

import os
import re
import subprocess
from typing import Dict, Any, Optional

import logging

logger = logging.getLogger("mirai.sandbox")

# Commands considered safe for direct subprocess execution
_SAFE_COMMAND_PREFIXES = (
    "ls", "cat", "head", "tail", "wc", "echo", "pwd", "whoami",
    "date", "uname", "hostname", "env", "printenv",
    "git status", "git log", "git diff", "git branch", "git show",
    "pip list", "pip show", "python --version", "node --version",
    "which", "type", "file", "stat", "df", "du",
    "curl -s", "wget -q",
)

# Patterns that indicate code execution (not a simple shell command)
_CODE_PATTERNS = [
    r"python\s+-c\s+",
    r"python3?\s+\S+\.py",
    r"node\s+-e\s+",
    r"node\s+\S+\.js",
    r"exec\s*\(",
    r"eval\s*\(",
    r"import\s+",
    r"from\s+\S+\s+import",
    r"def\s+\w+",
    r"class\s+\w+",
    r"function\s+\w+",
]
_CODE_RE = re.compile("|".join(_CODE_PATTERNS), re.IGNORECASE)


class SandboxRunner:
    """
    Hybrid code execution: safe commands via subprocess, LLM-generated code via E2B.
    Falls back to subprocess with warning if E2B is not available.
    """

    def __init__(self):
        self._e2b_available = None
        self._sandbox = None

    def _ensure_e2b(self) -> bool:
        """Lazy-check E2B availability."""
        if self._e2b_available is not None:
            return self._e2b_available

        try:
            from e2b_code_interpreter import Sandbox
            # Check for API key
            api_key = os.environ.get("E2B_API_KEY")
            if not api_key:
                self._e2b_available = False
                logger.warning(
                    "[E2B] No E2B_API_KEY set. Sandbox unavailable. "
                    "Get a key at https://e2b.dev"
                )
                return False
            self._e2b_available = True
            logger.info("[E2B] Sandbox available")
        except ImportError:
            self._e2b_available = False
            logger.warning("[E2B] Not installed. Run: pip install e2b-code-interpreter")

        return self._e2b_available

    def is_safe_command(self, command: str) -> bool:
        """
        Determine if a command is safe for direct subprocess execution.
        Safe = simple read-only shell commands, not code execution.
        """
        stripped = command.strip()

        # Check against safe prefixes
        for prefix in _SAFE_COMMAND_PREFIXES:
            if stripped.startswith(prefix):
                return True

        # Check if it looks like code execution
        if _CODE_RE.search(stripped):
            return False

        # Simple single commands without pipes to unknown programs are generally safe
        # But be conservative — default to sandbox for anything uncertain
        return False

    def execute_subprocess(
        self, command: str, timeout: int = 30, cwd: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a command via subprocess (for safe commands)."""
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=timeout, cwd=cwd,
            )
            return {
                "stdout": result.stdout[:3000] if result.stdout else "",
                "stderr": result.stderr[:1000] if result.stderr else "",
                "exit_code": result.returncode,
                "execution_method": "subprocess",
            }
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds",
                "exit_code": -1,
                "execution_method": "subprocess",
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "exit_code": -1,
                "execution_method": "subprocess",
            }

    def execute_e2b(
        self,
        code: str,
        language: str = "python",
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """Execute code in E2B sandbox."""
        if not self._ensure_e2b():
            # Fallback to subprocess with warning
            logger.warning(
                "[E2B] Sandbox unavailable — falling back to subprocess. "
                "This is less secure for LLM-generated code."
            )
            if language == "python":
                command = f'python3 -c {repr(code)}'
            elif language in ("javascript", "js"):
                command = f'node -e {repr(code)}'
            else:
                command = code
            return self.execute_subprocess(command, timeout=timeout)

        try:
            from e2b_code_interpreter import Sandbox

            sandbox = Sandbox(timeout=timeout)
            try:
                execution = sandbox.run_code(code, language=language)
                stdout = ""
                stderr = ""

                if execution.logs:
                    stdout = "\n".join(
                        line.line for line in (execution.logs.stdout or [])
                    )
                    stderr = "\n".join(
                        line.line for line in (execution.logs.stderr or [])
                    )

                if execution.error:
                    stderr += f"\n{execution.error.name}: {execution.error.value}"
                    if execution.error.traceback:
                        stderr += f"\n{execution.error.traceback}"

                return {
                    "stdout": stdout[:3000],
                    "stderr": stderr[:1000],
                    "exit_code": 0 if not execution.error else 1,
                    "execution_method": "e2b_sandbox",
                }
            finally:
                sandbox.kill()

        except Exception as e:
            logger.warning(f"[E2B] Sandbox execution failed: {e}")
            return {
                "stdout": "",
                "stderr": f"Sandbox execution failed: {e}",
                "exit_code": -1,
                "execution_method": "e2b_sandbox",
            }

    def execute(
        self,
        command: str,
        timeout: int = 30,
        cwd: Optional[str] = None,
        force_sandbox: bool = False,
    ) -> Dict[str, Any]:
        """
        Smart execution: routes safe commands to subprocess, code to E2B.

        Args:
            command: Command or code to execute.
            timeout: Max execution time in seconds.
            cwd: Working directory (subprocess only).
            force_sandbox: Force E2B sandbox even for safe commands.

        Returns:
            Dict with stdout, stderr, exit_code, execution_method.
        """
        if not force_sandbox and self.is_safe_command(command):
            logger.info(f"[Sandbox] Safe command → subprocess: {command[:80]}")
            return self.execute_subprocess(command, timeout=timeout, cwd=cwd)

        logger.info(f"[Sandbox] Code execution → E2B sandbox: {command[:80]}")
        return self.execute_e2b(command, timeout=timeout)
