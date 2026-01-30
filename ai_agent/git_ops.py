from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .config import GitConfig


@dataclass
class GitResult:
    branch_name: Optional[str] = None
    commit_hash: Optional[str] = None
    push_ok: bool = False
    log: str = ""


def _run_git(args: list[str], cwd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git"] + args,
        cwd=cwd,
        text=True,
        capture_output=True,
    )


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower())
    return slug.strip("-")[:50]


def is_git_repo(repo_path: str) -> bool:
    result = _run_git(["rev-parse", "--is-inside-work-tree"], cwd=repo_path)
    return result.returncode == 0


def pre_task_git(config: GitConfig, task_id: int, title: str, repo_path: str) -> GitResult:
    """Set up git branch before task execution. Returns the branch name."""
    result = GitResult()
    if not config.enabled:
        return result

    if not is_git_repo(repo_path):
        result.log = "Not a git repo; skipping git operations."
        return result

    if not config.auto_branch:
        # just record current branch
        out = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path)
        if out.returncode == 0:
            result.branch_name = out.stdout.strip()
        return result

    branch_name = f"{config.branch_prefix}task-{task_id}-{_slugify(title)}"
    result.branch_name = branch_name

    # check if branch exists locally
    check = _run_git(["rev-parse", "--verify", branch_name], cwd=repo_path)
    if check.returncode == 0:
        _run_git(["checkout", branch_name], cwd=repo_path)
    else:
        _run_git(["checkout", "-b", branch_name], cwd=repo_path)

    result.log = f"Checked out branch {branch_name}"
    return result


def post_task_git(config: GitConfig, task_id: int, title: str, repo_path: str, branch_name: Optional[str]) -> GitResult:
    """Commit and optionally push after task execution."""
    result = GitResult(branch_name=branch_name)
    if not config.enabled:
        return result

    if not is_git_repo(repo_path):
        result.log = "Not a git repo; skipping post-task git."
        return result

    if not config.auto_commit:
        return result

    # check for changes
    status = _run_git(["status", "--porcelain"], cwd=repo_path)
    if status.returncode != 0 or not status.stdout.strip():
        result.log = "No changes to commit."
        return result

    # stage and commit
    _run_git(["add", "-A"], cwd=repo_path)
    commit_msg = f"agent: task {task_id} {title}"
    commit = _run_git(["commit", "-m", commit_msg], cwd=repo_path)
    if commit.returncode != 0:
        result.log = f"Commit failed: {commit.stderr}"
        return result

    # capture commit hash
    rev = _run_git(["rev-parse", "HEAD"], cwd=repo_path)
    if rev.returncode == 0:
        result.commit_hash = rev.stdout.strip()

    result.log = f"Committed {result.commit_hash or '(unknown)'}"

    # push if configured
    if config.auto_push and branch_name:
        push = _run_git(["push", "-u", config.remote, branch_name], cwd=repo_path)
        result.push_ok = push.returncode == 0
        if result.push_ok:
            result.log += f"; pushed to {config.remote}/{branch_name}"
        else:
            result.log += f"; push failed: {push.stderr}"

    return result
