from __future__ import annotations

import threading
import time
from typing import Optional

from .chaining import enqueue_followups, parse_followups
from .compiler import PromptCompiler, summarize_logs
from .config import AppConfig
from .db import Database, TaskRecord
from .git_ops import post_task_git, pre_task_git
from .notify import TelegramNotifier
from .providers.claude_code import ClaudeCodeRunner
from .providers.codex import CodexRunner
from .router import ProviderRouter

# Per-repo locks so parallel workers don't run git ops on the same repo
# simultaneously.
_repo_locks: dict[str, threading.Lock] = {}
_repo_locks_guard = threading.Lock()


def _get_repo_lock(repo_path: str) -> threading.Lock:
    with _repo_locks_guard:
        if repo_path not in _repo_locks:
            _repo_locks[repo_path] = threading.Lock()
        return _repo_locks[repo_path]


def _execute_task(
    task: TaskRecord,
    config: AppConfig,
    db: Database,
    compiler: PromptCompiler,
    notifier: TelegramNotifier,
    worker_id: int,
) -> None:
    repo_lock = _get_repo_lock(task.repo_path)
    with repo_lock:
        _execute_task_inner(task, config, db, compiler, notifier, worker_id)


def _execute_task_inner(
    task: TaskRecord,
    config: AppConfig,
    db: Database,
    compiler: PromptCompiler,
    notifier: TelegramNotifier,
    worker_id: int,
) -> None:
    # --- pre-task git ---
    git_pre = pre_task_git(config.git, task.id, task.title, task.repo_path)
    if git_pre.branch_name:
        db.set_branch(task.id, git_pre.branch_name)

    # --- run provider ---
    prompt = compiler.compile(task)
    claude_runner = ClaudeCodeRunner(config.provider.claude_command, task.repo_path)
    codex_runner = CodexRunner(config.provider.codex_command, task.repo_path)
    router = ProviderRouter(claude_runner, codex_runner)
    result, success = router.run(prompt.text)

    # --- post-task git ---
    git_post = post_task_git(
        config.git, task.id, task.title, task.repo_path, git_pre.branch_name
    )

    # --- update task record ---
    status = "done" if success else "failed"
    last_error = None if success else "Provider failed"
    db.update_task(
        task_id=task.id,
        status=status,
        provider_used=result.provider,
        logs=result.logs,
        last_error=last_error,
        branch_name=git_pre.branch_name,
        commit_hash=git_post.commit_hash,
    )

    # --- chaining: parse and enqueue follow-ups ---
    if success:
        followups = parse_followups(result.logs or "")
        if followups:
            chain_group = task.chain_group_id or task.id
            created = enqueue_followups(
                db=db,
                parent_task_id=task.id,
                chain_group_id=chain_group,
                default_repo_path=task.repo_path,
                default_provider=task.preferred_provider,
                specs=followups,
            )
            if created:
                print(
                    f"[worker-{worker_id}] Enqueued {len(created)} follow-up task(s): {created}"
                )

    # --- notification ---
    summary = summarize_logs(result.logs or "")
    git_info = ""
    if git_pre.branch_name:
        git_info += f"\nBranch: {git_pre.branch_name}"
    if git_post.commit_hash:
        git_info += f"\nCommit: {git_post.commit_hash}"
    if git_post.push_ok:
        git_info += f"\nPushed: {config.git.remote}/{git_pre.branch_name}"

    message = (
        f"Task {task.id}: {task.title}\n"
        f"Status: {status}\n"
        f"Provider: {result.provider}\n"
        f"Worker: {worker_id}\n"
        f"Summary: {summary}"
        f"{git_info}\n"
        f"Task ID: {task.id}"
    )
    notifier.send(message)
    print(f"[worker-{worker_id}] Task {task.id} finished: {status}")


def worker_loop(
    config: AppConfig,
    db: Database,
    compiler: PromptCompiler,
    notifier: TelegramNotifier,
    worker_id: int,
    stop_event: Optional[threading.Event] = None,
) -> None:
    """Continuously claim and execute tasks until stopped."""
    print(f"[worker-{worker_id}] Started.")
    while True:
        if stop_event and stop_event.is_set():
            break
        task = db.claim_next_task()
        if not task:
            time.sleep(2)
            continue
        print(f"[worker-{worker_id}] Claimed task {task.id}: {task.title}")
        _execute_task(task, config, db, compiler, notifier, worker_id)
    print(f"[worker-{worker_id}] Stopped.")


def run_workers(
    config: AppConfig,
    db: Database,
    num_workers: int = 1,
) -> None:
    """Spawn N worker threads and wait for Ctrl+C."""
    compiler = PromptCompiler()
    notifier = TelegramNotifier(config.telegram)
    stop_event = threading.Event()

    threads: list[threading.Thread] = []
    for i in range(num_workers):
        t = threading.Thread(
            target=worker_loop,
            args=(config, db, compiler, notifier, i, stop_event),
            daemon=True,
            name=f"worker-{i}",
        )
        threads.append(t)
        t.start()

    print(f"Started {num_workers} worker(s). Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping workers...")
        stop_event.set()
        for t in threads:
            t.join(timeout=30)
        print("All workers stopped.")
