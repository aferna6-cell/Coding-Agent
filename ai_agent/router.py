from __future__ import annotations

from typing import Tuple

from .providers.claude_code import ClaudeCodeRunner, ProviderResult
from .providers.codex import CodexRunner

RATE_LIMIT_KEYWORDS = (
    "rate limit",
    "usage cap",
    "quota",
    "exceeded",
    "too many requests",
    "429",
    "capacity",
    "overloaded",
)


class ProviderRouter:
    def __init__(self, claude: ClaudeCodeRunner, codex: CodexRunner) -> None:
        self.claude = claude
        self.codex = codex

    def run(self, prompt: str) -> Tuple[ProviderResult, bool]:
        primary = self.claude.run(prompt)
        if self._is_rate_limited(primary):
            fallback = self.codex.run(prompt)
            return fallback, fallback.exit_code == 0
        if primary.exit_code != 0:
            # Non-rate-limit failure from Claude — try Codex
            fallback = self.codex.run(prompt)
            return fallback, fallback.exit_code == 0
        return primary, True

    def _is_rate_limited(self, result: ProviderResult) -> bool:
        logs = result.logs.lower() if result.logs else ""
        return any(keyword in logs for keyword in RATE_LIMIT_KEYWORDS)
