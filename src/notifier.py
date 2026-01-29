from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class SmsConfig:
    destination_number: str
    account_sid: Optional[str] = None
    auth_token: Optional[str] = None
    from_number: Optional[str] = None

    @classmethod
    def from_env(cls, destination_number: str) -> "SmsConfig":
        return cls(
            destination_number=destination_number,
            account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
            auth_token=os.getenv("TWILIO_AUTH_TOKEN"),
            from_number=os.getenv("TWILIO_FROM_NUMBER"),
        )


class SmsNotifier:
    def __init__(self, config: SmsConfig) -> None:
        self._config = config

    def send(self, message: str) -> bool:
        try:
            from twilio.base.exceptions import TwilioRestException
            from twilio.rest import Client
        except ImportError:
            print("[notifier] Twilio client library not installed; skipping SMS notification.")
            return False

        if not self._config.account_sid or not self._config.auth_token or not self._config.from_number:
            print("[notifier] Twilio not configured; skipping SMS notification.")
            return False

        client = Client(self._config.account_sid, self._config.auth_token)
        try:
            client.messages.create(
                body=message,
                from_=self._config.from_number,
                to=self._config.destination_number,
            )
        except TwilioRestException as exc:
            print(f"[notifier] Failed to send SMS: {exc}")
            return False

        return True
