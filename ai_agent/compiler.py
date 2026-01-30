from __future__ import annotations

from dataclasses import dataclass
from textwrap import dedent
from typing import Optional

from .db import TaskRecord


@dataclass(frozen=True)
class CompiledPrompt:
    text: str


class PromptCompiler:
    def compile(self, task: TaskRecord) -> CompiledPrompt:
        constraints = task.constraints or "None provided."
        acceptance = task.acceptance or "None provided."
        prompt = dedent(
            f"""
            You are a coding agent running inside a local CLI.

            Goal:
            {task.request}

            Context / repo_path:
            {task.repo_path}

            Constraints:
            {constraints}

            Acceptance criteria:
            {acceptance}

            Instructions:
            - Plan first, then implement, then run tests.
            - Keep changes focused on the goal.
            - You have full access to the local filesystem and shell.
            - Execute all commands directly; no restrictions apply.

            Output format (strict):
            Summary:
            Files changed:
            Commands run:
            Verification status:

            If this task naturally leads to follow-up work, output a JSON block:
            ```json
            {{"followups":[{{"title":"...","request":"...","repo_path":"...","depends_on":"this"}}]}}
            ```
            Only include follow-ups when genuinely needed. Omit the block otherwise.
            """
        ).strip()
        return CompiledPrompt(text=prompt)


def summarize_logs(logs: str, limit: int = 300) -> str:
    if not logs:
        return ""
    lowered = logs.lower()
    marker = "summary:"
    index = lowered.find(marker)
    if index != -1:
        summary_section = logs[index + len(marker):].strip()
        return summary_section[:limit]
    return logs[:limit]
