from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PromptDelivery:
    channel: str
    prompt: str


class ConsoleClient:
    def send(self, delivery: PromptDelivery) -> None:
        print(f"\n[{delivery.channel}] prompt:\n{delivery.prompt}\n")
