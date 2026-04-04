"""Helpers for robust CLI subprocess execution.

Long-running CLI tools that spawn descendants can hang when invoked with
`subprocess.run(..., capture_output=True)`: Python waits for pipe EOF, and a
grandchild holding stdout/stderr open can stall `communicate()` even after the
direct child exits. Writing output to temp files and waiting on the direct child
avoids that failure mode.
"""

from __future__ import annotations

import os
import signal
import subprocess
import tempfile
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class CLIProcessResult:
    returncode: int
    stdout: str
    stderr: str


def run_cli_to_files(
    cmd: List[str],
    *,
    timeout: int,
    stdin_data: Optional[str] = None,
    text: bool = True,
    encoding: str = "utf-8",
) -> CLIProcessResult:
    """Run a CLI command while capturing output to temp files instead of pipes."""
    stdin_path: Optional[str] = None
    stdout_path: Optional[str] = None
    stderr_path: Optional[str] = None
    proc: Optional[subprocess.Popen] = None

    try:
        stdin_file = None
        if stdin_data is not None:
            stdin_fd, stdin_path = tempfile.mkstemp(prefix="mirai_cli_stdin_", suffix=".txt")
            with os.fdopen(stdin_fd, "w", encoding=encoding, errors="replace") as handle:
                handle.write(stdin_data)
            stdin_file = open(stdin_path, "r", encoding=encoding, errors="replace")

        stdout_fd, stdout_path = tempfile.mkstemp(prefix="mirai_cli_stdout_", suffix=".log")
        stderr_fd, stderr_path = tempfile.mkstemp(prefix="mirai_cli_stderr_", suffix=".log")

        with (
            stdin_file if stdin_file is not None else open(os.devnull, "r", encoding=encoding) as proc_stdin,
            os.fdopen(stdout_fd, "w", encoding=encoding, errors="replace") as stdout_file,
            os.fdopen(stderr_fd, "w", encoding=encoding, errors="replace") as stderr_file,
        ):
            proc = subprocess.Popen(
                cmd,
                stdin=proc_stdin,
                stdout=stdout_file,
                stderr=stderr_file,
                text=text,
                start_new_session=True,
            )
            try:
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except Exception:
                    proc.kill()
                proc.wait(timeout=5)
                raise

        with open(stdout_path, "r", encoding=encoding, errors="replace") as stdout_file:
            stdout = stdout_file.read()
        with open(stderr_path, "r", encoding=encoding, errors="replace") as stderr_file:
            stderr = stderr_file.read()

        return CLIProcessResult(
            returncode=proc.returncode if proc is not None else 1,
            stdout=stdout,
            stderr=stderr,
        )
    finally:
        for path in (stdin_path, stdout_path, stderr_path):
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
