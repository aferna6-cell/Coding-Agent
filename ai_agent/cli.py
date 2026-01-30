from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Iterable, Optional

from .config import ConfigManager, default_app_config, resolve_config_path
from .db import Database, TaskRecord

STATUS_VALUES = ("queued", "running", "done", "failed", "canceled")


def load_config(config_path: Path) -> ConfigManager:
    return ConfigManager(config_path)


def ensure_repo_path(path: str) -> None:
    repo = Path(path).expanduser()
    if not repo.exists():
        raise SystemExit(f"Repo path does not exist: {repo}")


def print_tasks(tasks: Iterable[TaskRecord]) -> None:
    for task in tasks:
        print(f"[{task.id}] {task.status} | {task.title} | {task.repo_path}")


def print_task_detail(task: TaskRecord) -> None:
    data = {
        "id": task.id,
        "title": task.title,
        "repo_path": task.repo_path,
        "request": task.request,
        "constraints": task.constraints,
        "acceptance": task.acceptance,
        "preferred_provider": task.preferred_provider,
        "status": task.status,
        "provider_used": task.provider_used,
        "created_at": task.created_at,
        "started_at": task.started_at,
        "finished_at": task.finished_at,
        "attempts": task.attempts,
        "last_error": task.last_error,
        "logs": task.logs,
        "parent_task_id": task.parent_task_id,
        "chain_group_id": task.chain_group_id,
        "depends_on_task_id": task.depends_on_task_id,
        "run_after": task.run_after,
        "priority": task.priority,
        "branch_name": task.branch_name,
        "commit_hash": task.commit_hash,
    }
    print(json.dumps(data, indent=2))


def handle_init(args: argparse.Namespace) -> None:
    config_path = resolve_config_path(args.config)
    manager = load_config(config_path)
    config = default_app_config(config_path)
    manager.save(config)
    db = Database(config.db_path)
    db.init()
    print(f"Initialized config at {config_path}")
    print(f"Database at {config.db_path}")


def handle_add(args: argparse.Namespace) -> None:
    config_path = resolve_config_path(args.config)
    manager = load_config(config_path)
    if not manager.exists():
        raise SystemExit("Config not found. Run 'agent init' first.")
    config = manager.load()
    ensure_repo_path(args.repo_path)
    db = Database(config.db_path)
    db.init()
    constraints = "\n".join(args.constraints) if args.constraints else None
    acceptance = "\n".join(args.acceptance) if args.acceptance else None
    task_id = db.add_task(
        title=args.title,
        repo_path=args.repo_path,
        request=args.request,
        constraints=constraints,
        acceptance=acceptance,
        preferred_provider=args.preferred_provider,
        parent_task_id=args.parent_task_id,
        depends_on_task_id=args.depends_on,
        priority=args.priority,
    )
    print(f"Added task {task_id}")


def handle_list(args: argparse.Namespace) -> None:
    config_path = resolve_config_path(args.config)
    manager = load_config(config_path)
    if not manager.exists():
        raise SystemExit("Config not found. Run 'agent init' first.")
    config = manager.load()
    db = Database(config.db_path)
    db.init()
    print_tasks(db.list_tasks())


def handle_show(args: argparse.Namespace) -> None:
    config_path = resolve_config_path(args.config)
    manager = load_config(config_path)
    if not manager.exists():
        raise SystemExit("Config not found. Run 'agent init' first.")
    config = manager.load()
    db = Database(config.db_path)
    task = db.get_task(args.task_id)
    if not task:
        raise SystemExit(f"Task {args.task_id} not found")
    print_task_detail(task)


def handle_cancel(args: argparse.Namespace) -> None:
    config_path = resolve_config_path(args.config)
    manager = load_config(config_path)
    if not manager.exists():
        raise SystemExit("Config not found. Run 'agent init' first.")
    config = manager.load()
    db = Database(config.db_path)
    if db.cancel_task(args.task_id):
        print(f"Canceled task {args.task_id}")
    else:
        print(f"Task {args.task_id} not canceled (not queued or missing)")


def handle_doctor(args: argparse.Namespace) -> None:
    config_path = resolve_config_path(args.config)
    manager = load_config(config_path)
    checks = []
    python_ok = sys.version_info >= (3, 11)
    checks.append((python_ok, f"Python {sys.version.split()[0]}"))
    if manager.exists():
        config = manager.load()
        db_exists = config.db_path.exists()
        checks.append((db_exists, f"DB exists at {config.db_path}"))
        telegram_ready = bool(config.telegram.bot_token and config.telegram.chat_id)
        checks.append((telegram_ready, "Telegram configuration"))
        checks.append((shutil.which(config.provider.claude_command[0]) is not None, "Claude CLI"))
        checks.append((shutil.which(config.provider.codex_command[0]) is not None, "Codex CLI"))
        checks.append((True, f"Git enabled: {config.git.enabled}"))
    else:
        checks.append((False, "Config missing: run agent init"))

    for ok, label in checks:
        status = "OK" if ok else "MISSING"
        print(f"[{status}] {label}")


def handle_run(args: argparse.Namespace) -> None:
    config_path = resolve_config_path(args.config)
    manager = load_config(config_path)
    if not manager.exists():
        raise SystemExit("Config not found. Run 'agent init' first.")
    config = manager.load()
    db = Database(config.db_path)
    db.init()

    from .worker import run_workers

    run_workers(config=config, db=db, num_workers=args.workers)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent", description="Task Queue AI Agent")
    parser.add_argument("--config", help="Path to config.json")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create DB and config")
    init_parser.set_defaults(func=handle_init)

    add_parser = subparsers.add_parser("add", help="Add a task to the queue")
    add_parser.add_argument("--title", required=True)
    add_parser.add_argument("--repo-path", required=True)
    add_parser.add_argument("--request", required=True)
    add_parser.add_argument("--constraints", action="append", default=[])
    add_parser.add_argument("--acceptance", action="append", default=[])
    add_parser.add_argument(
        "--preferred-provider",
        default="claude_first",
        choices=["claude_first"],
    )
    add_parser.add_argument("--parent-task-id", type=int, default=None, help="Parent task ID for chaining")
    add_parser.add_argument("--depends-on", type=int, default=None, help="Task ID this task depends on")
    add_parser.add_argument("--priority", type=int, default=0, help="Priority (higher runs first)")
    add_parser.set_defaults(func=handle_add)

    list_parser = subparsers.add_parser("list", help="List tasks")
    list_parser.set_defaults(func=handle_list)

    run_parser = subparsers.add_parser("run", help="Run queued tasks")
    run_parser.add_argument("--workers", type=int, default=1, help="Number of parallel workers (default: 1)")
    run_parser.set_defaults(func=handle_run)

    show_parser = subparsers.add_parser("show", help="Show task details")
    show_parser.add_argument("task_id", type=int)
    show_parser.set_defaults(func=handle_show)

    cancel_parser = subparsers.add_parser("cancel", help="Cancel queued task")
    cancel_parser.add_argument("task_id", type=int)
    cancel_parser.set_defaults(func=handle_cancel)

    doctor_parser = subparsers.add_parser("doctor", help="Check environment")
    doctor_parser.set_defaults(func=handle_doctor)

    return parser


def main(argv: Optional[list[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
