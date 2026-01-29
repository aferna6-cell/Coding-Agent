from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .clients import ConsoleClient, PromptDelivery
from .notifier import SmsNotifier
from .prompts import build_prompts
from .queue import Task


@dataclass
class AgentRunner:
    notifier: SmsNotifier
    client: ConsoleClient

    def run(self, tasks: Iterable[Task]) -> None:
        for task in tasks:
            prompts = build_prompts(task)
            self.client.send(PromptDelivery(channel="primary", prompt=prompts.primary_prompt))
            self.client.send(PromptDelivery(channel="claude", prompt=prompts.claude_prompt))

            completion_message = (
                f"Task '{task.title}' ({task.task_id}) completed. "
                "Moving to the next queued task."
            )
            self.notifier.send(completion_message)
