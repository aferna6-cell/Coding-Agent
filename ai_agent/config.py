from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

DEFAULT_CONFIG_DIR = ".task_queue_ai_agent"
DEFAULT_CONFIG_NAME = "config.json"
DEFAULT_DB_NAME = "agent.db"


def default_config_dir(base_dir: Optional[Path] = None) -> Path:
    root = base_dir or Path.cwd()
    return root / DEFAULT_CONFIG_DIR


@dataclass
class ProviderConfig:
    claude_command: List[str] = field(default_factory=lambda: ["claude"])
    codex_command: List[str] = field(default_factory=lambda: ["codex"])


@dataclass
class TelegramConfig:
    bot_token: str = ""
    chat_id: str = ""


@dataclass
class AppConfig:
    db_path: Path
    provider: ProviderConfig = field(default_factory=ProviderConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)

    def to_dict(self) -> dict:
        return {
            "db_path": str(self.db_path),
            "provider": {
                "claude_command": self.provider.claude_command,
                "codex_command": self.provider.codex_command,
            },
            "telegram": {
                "bot_token": self.telegram.bot_token,
                "chat_id": self.telegram.chat_id,
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AppConfig":
        db_path = Path(data["db_path"]) if data.get("db_path") else Path(DEFAULT_DB_NAME)
        provider = data.get("provider", {})
        telegram = data.get("telegram", {})
        return cls(
            db_path=db_path,
            provider=ProviderConfig(
                claude_command=list(provider.get("claude_command", ["claude"])),
                codex_command=list(provider.get("codex_command", ["codex"])),
            ),
            telegram=TelegramConfig(
                bot_token=telegram.get("bot_token", ""),
                chat_id=telegram.get("chat_id", ""),
            ),
        )


class ConfigManager:
    def __init__(self, path: Path) -> None:
        self.path = path

    def exists(self) -> bool:
        return self.path.exists()

    def load(self) -> AppConfig:
        data = json.loads(self.path.read_text())
        return AppConfig.from_dict(data)

    def save(self, config: AppConfig) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(config.to_dict(), indent=2))


def resolve_config_path(explicit_path: Optional[str] = None) -> Path:
    if explicit_path:
        return Path(explicit_path).expanduser().resolve()
    base_dir = Path(os.getenv("TASK_QUEUE_AGENT_HOME", Path.cwd()))
    return (base_dir / DEFAULT_CONFIG_DIR / DEFAULT_CONFIG_NAME).resolve()


def default_app_config(config_path: Path) -> AppConfig:
    db_path = config_path.parent / DEFAULT_DB_NAME
    return AppConfig(db_path=db_path)
