from __future__ import annotations

from typing import Tuple

from .providers.claude_code import ClaudeCodeRunner
from .providers.codex import CodexRunner, is_stdin_tty_error

RATE_LIMIT_KEYWORDS = (
    "rate limit",
    "usage cap",
    "quota",
    "exceeded",
    "too many requests",
)

RETRIABLE_KEYWORDS = (
    *RATE_LIMIT_KEYWORDS,
)


def extract_error_message(result: object) -> str:
    """Build a descriptive error message from a failed provider result."""
    if result.exit_code == 0:
        return ""
    parts = [f"Provider '{result.provider}' exited with code {result.exit_code}."]
    if result.logs and is_stdin_tty_error(result.logs):
        parts.append("Retriable: stdin/TTY error detected.")
    stderr_snippet = (result.logs or "")[-500:]
    if stderr_snippet:
        parts.append(f"Tail: {stderr_snippet}")
    return " ".join(parts)


class ProviderRouter:
    def __init__(self, claude: ClaudeCodeRunner, codex: CodexRunner) -> None:
        self.claude = claude
        self.codex = codex

    def run(self, prompt: str) -> Tuple[object, bool]:
        primary = self.claude.run(prompt)
        if self._should_fallback(primary):
            fallback = self.codex.run(prompt)
            return fallback, fallback.exit_code == 0
        return primary, primary.exit_code == 0

    def _should_fallback(self, result: object) -> bool:
        if result.exit_code != 0:
            return True
        logs = result.logs.lower() if result.logs else ""
        return any(keyword in logs for keyword in RATE_LIMIT_KEYWORDS)
