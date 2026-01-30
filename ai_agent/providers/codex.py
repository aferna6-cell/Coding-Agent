from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import List


@dataclass
class ProviderResult:
    provider: str
    exit_code: int
    logs: str


class CodexRunner:
    def __init__(self, command: List[str], repo_path: str) -> None:
        self.command = command
        self.repo_path = repo_path

    def run(self, prompt: str) -> ProviderResult:
        completed = subprocess.run(
            self.command,
            input=prompt,
            text=True,
            capture_output=True,
            cwd=self.repo_path,
        )
        logs = (completed.stdout or "") + (completed.stderr or "")
        return ProviderResult(provider="codex", exit_code=completed.returncode, logs=logs)
