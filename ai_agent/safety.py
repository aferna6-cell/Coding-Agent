from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SafetyResult:
    ok: bool
    reason: str


class SafetyGuard:
    def check(self, text: str, dangerous_ok: bool) -> SafetyResult:
        return SafetyResult(ok=True, reason="unrestricted")
