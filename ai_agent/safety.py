from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

DEFAULT_DENYLIST = (
    r"\brm\s+-rf\b",
    r"\bdd\b",
    r"\bmkfs\b",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bpoweroff\b",
    r"\bmkfs\.",
)


@dataclass(frozen=True)
class SafetyResult:
    ok: bool
    reason: str


class SafetyGuard:
    def __init__(self, patterns: Iterable[str] = DEFAULT_DENYLIST) -> None:
        self.patterns = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]

    def check(self, text: str, dangerous_ok: bool) -> SafetyResult:
        if dangerous_ok:
            return SafetyResult(ok=True, reason="dangerous_ok set")
        for pattern in self.patterns:
            if pattern.search(text):
                return SafetyResult(ok=False, reason=f"Denied by pattern: {pattern.pattern}")
        return SafetyResult(ok=True, reason="")
