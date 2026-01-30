from __future__ import annotations

from dataclasses import dataclass

import requests

from .config import TelegramConfig


@dataclass
class NotificationResult:
    ok: bool
    message: str


class TelegramNotifier:
    def __init__(self, config: TelegramConfig) -> None:
        self.config = config

    def send(self, text: str) -> NotificationResult:
        if not self.config.bot_token or not self.config.chat_id:
            return NotificationResult(ok=False, message="Telegram not configured.")
        url = f"https://api.telegram.org/bot{self.config.bot_token}/sendMessage"
        payload = {"chat_id": self.config.chat_id, "text": text}
        try:
            response = requests.post(url, json=payload, timeout=10)
        except requests.RequestException as exc:
            return NotificationResult(ok=False, message=f"Telegram request failed: {exc}")
        if response.status_code != 200:
            return NotificationResult(
                ok=False,
                message=f"Telegram error {response.status_code}: {response.text}",
            )
        return NotificationResult(ok=True, message="Notification sent.")
