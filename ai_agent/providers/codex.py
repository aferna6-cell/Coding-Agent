from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from typing import List


@dataclass
class ProviderResult:
    provider: str
    exit_code: int
    logs: str


STDIN_TTY_ERROR_MARKERS = (
    "stdin is not a terminal",
    "not a tty",
    "input is not a terminal",
)


def is_stdin_tty_error(logs: str) -> bool:
    """Detect the 'stdin is not a terminal' failure pattern.

    Returns True when the error is a retriable provider error caused by
    the Codex CLI expecting an interactive TTY on stdin.
    """
    lower = logs.lower()
    return any(marker in lower for marker in STDIN_TTY_ERROR_MARKERS)


def _headless_env() -> dict[str, str]:
    """Build an environment dict that forces non-interactive (headless) mode."""
    env = {**os.environ, "CI": "1"}
    return env


class CodexRunner:
    def __init__(self, command: List[str], repo_path: str) -> None:
        self.command = command
        self.repo_path = repo_path

    def run(self, prompt: str) -> ProviderResult:
        # Pass the prompt via a --prompt argument so stdin can be /dev/null.
        # This avoids the "stdin is not a terminal" error entirely.
        cmd = list(self.command) + ["--prompt", prompt]
        completed = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            text=True,
            capture_output=True,
            cwd=self.repo_path,
            env=_headless_env(),
        )
        logs = (completed.stdout or "") + (completed.stderr or "")

        # Tag retriable stdin/TTY errors so the caller can decide to retry.
        if completed.returncode != 0 and is_stdin_tty_error(logs):
            return ProviderResult(
                provider="codex",
                exit_code=completed.returncode,
                logs=logs,
            )

        return ProviderResult(provider="codex", exit_code=completed.returncode, logs=logs)
