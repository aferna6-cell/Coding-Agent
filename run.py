from __future__ import annotations

import argparse
from pathlib import Path

from src.agent import AgentRunner
from src.clients import ConsoleClient
from src.notifier import SmsConfig, SmsNotifier
from src.queue import TaskQueue


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the coding agent task queue.")
    parser.add_argument("--tasks", type=Path, default=Path("tasks.json"))
    parser.add_argument("--to", type=str, default=None, help="Override destination phone number.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    queue = TaskQueue.from_file(args.tasks)
    destination = args.to or queue.destination_number
    notifier = SmsNotifier(SmsConfig.from_env(destination))
    runner = AgentRunner(notifier=notifier, client=ConsoleClient())
    runner.run(queue)


if __name__ == "__main__":
    main()
