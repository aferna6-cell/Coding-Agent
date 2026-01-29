from __future__ import annotations

from dataclasses import dataclass
from textwrap import dedent

from .queue import Task


@dataclass(frozen=True)
class PromptBundle:
    primary_prompt: str
    claude_prompt: str


def build_prompts(task: Task) -> PromptBundle:
    criteria = "\n".join(f"- {item}" for item in task.acceptance_criteria)
    primary_prompt = dedent(
        f"""
        You are the primary agent. Convert the task into a plan and produce the implementation.

        Task: {task.title}
        Description: {task.description}
        Acceptance Criteria:
        {criteria}

        Provide the next concrete steps and report progress when complete.
        """
    ).strip()

    claude_prompt = dedent(
        f"""
        You are Claude Code. Provide a detailed implementation plan and highlight risks.

        Task: {task.title}
        Description: {task.description}
        Acceptance Criteria:
        {criteria}

        Return a checklist of deliverables and any open questions.
        """
    ).strip()

    return PromptBundle(primary_prompt=primary_prompt, claude_prompt=claude_prompt)
