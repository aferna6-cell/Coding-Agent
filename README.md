# Task Queue AI Agent

A local task queue runner that compiles coding requests into high-quality prompts, runs them through Claude Code CLI first, and falls back to OpenAI Codex CLI when needed. Tasks are stored persistently in SQLite, and completion notifications are sent via a free Telegram bot.

**All commands run directly on the host system. No sandboxing or safety restrictions are applied. This agent is intended for trusted local execution only.**

## Features
- **Parallel workers** — run N workers concurrently with `--workers N`.
- **Auto git workflow** — per-task branch creation, auto-commit, optional push.
- **Task chaining** — LLM output can enqueue follow-up tasks with dependency ordering.
- **Priority queue** — tasks execute by priority DESC, then FIFO.
- **Provider fallback** — Claude-first routing with automatic Codex fallback on failure or rate limit.
- **Dependency awareness** — tasks with `depends_on` wait until the dependency completes.
- **Repo locking** — parallel workers acquire per-repo locks so git operations don't conflict.
- SQLite persistence with WAL mode for safe concurrent access.
- Telegram bot notifications with branch/commit info.
- CLI commands: init, add, list, run, show, cancel, doctor.

---

## WSL2 + Ubuntu setup (Windows)

1. **Install WSL2**
   - Open PowerShell as Administrator:
     ```powershell
     wsl --install
     ```
   - Reboot if prompted.

2. **Install Ubuntu**
   - From the Microsoft Store, install **Ubuntu 22.04 LTS** (or newer).
   - Launch Ubuntu and complete the user setup.

3. **Update packages & install Python 3.11+**
   ```bash
   sudo apt update
   sudo apt install -y python3.11 python3.11-venv python3-pip
   ```

4. **Clone this repo in WSL2**
   ```bash
   git clone <your-repo-url>
   cd Coding-Agent
   ```

> **WSL path caveat:**
> - Linux-native paths (e.g. `/home/you/projects/foo`) are fastest and most reliable.
> - Windows-mounted paths (e.g. `/mnt/c/Users/you/...`) work, but file I/O is slower and can cause extra latency for AI CLIs.

---

## Python environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Install / verify AI CLIs

The agent expects **Claude Code** and **Codex** CLIs to be available in `$PATH`. You can change the command names in the config file.

Verify:
```bash
which claude
which codex
```

If your commands differ (e.g., `claude-code`), update `config.json` after running `agent init`.

---

## Telegram bot notifications (free)

1. **Create a bot**
   - Open Telegram and message `@BotFather`.
   - Run `/newbot` and follow the instructions.
   - Copy the bot token.

2. **Get your chat_id**
   - Start a chat with your new bot and send any message.
   - Open this URL in a browser (replace `<TOKEN>`):
     ```
     https://api.telegram.org/bot<TOKEN>/getUpdates
     ```
   - Look for `"chat":{"id":<chat_id>}`.

3. **Configure**
   - Run `agent init` (see below).
   - Edit `.task_queue_ai_agent/config.json` and set:
     ```json
     {
       "telegram": {
         "bot_token": "YOUR_TOKEN",
         "chat_id": "YOUR_CHAT_ID"
       }
     }
     ```

---

## CLI usage

All commands run from the repo root:

### Initialize
```bash
python -m ai_agent.cli init
```

### Add a task
```bash
python -m ai_agent.cli add \
  --title "Add CSV export" \
  --repo-path /home/you/projects/example \
  --request "Add a CSV export button on the reports page" \
  --constraints "Use existing table data; no new dependencies" \
  --acceptance "Button appears on Reports" \
  --acceptance "CSV downloads with headers"
```

### Add a task with priority and dependency
```bash
python -m ai_agent.cli add \
  --title "Write integration tests" \
  --repo-path /home/you/projects/example \
  --request "Write integration tests for the CSV export feature" \
  --depends-on 1 \
  --priority 5
```

### List tasks
```bash
python -m ai_agent.cli list
```

### Run worker (single, default)
```bash
python -m ai_agent.cli run
```

### Run with parallel workers
```bash
python -m ai_agent.cli run --workers 4
```

### Show a task (details + logs)
```bash
python -m ai_agent.cli show 1
```

### Cancel a queued task
```bash
python -m ai_agent.cli cancel 1
```

### Environment checks
```bash
python -m ai_agent.cli doctor
```

---

## Auto git workflow

Each task can automatically create a branch, commit changes, and push.

Configure in `.task_queue_ai_agent/config.json`:

```json
{
  "git": {
    "enabled": true,
    "auto_branch": true,
    "auto_commit": true,
    "auto_push": false,
    "branch_prefix": "agent/",
    "remote": "origin"
  }
}
```

**Behavior:**
- On task start: creates branch `agent/task-{id}-{slugified-title}` (or checks it out if it exists).
- After execution: runs `git add -A && git commit -m "agent: task {id} {title}"`.
- If `auto_push` is true: pushes to `{remote}/{branch}`.
- Branch name and commit hash are stored in the task record and included in Telegram notifications.
- If the repo path is not a git repository, git operations are skipped.

---

## Task chaining

Tasks can enqueue follow-up tasks. The LLM output is scanned for a JSON block:

```json
{"followups":[{"title":"...","request":"...","repo_path":"...","depends_on":"this"}]}
```

Follow-ups are automatically enqueued with:
- `parent_task_id` set to the originating task
- `chain_group_id` for grouping related tasks
- `depends_on_task_id` set to the parent if `depends_on` is `"this"`

You can also manually chain tasks via the CLI:

```bash
python -m ai_agent.cli add \
  --title "Deploy feature" \
  --repo-path /home/you/projects/app \
  --request "Deploy the new feature to staging" \
  --parent-task-id 1 \
  --depends-on 1
```

---

## Configuration file

Generated at `.task_queue_ai_agent/config.json` after `init`.

```json
{
  "db_path": ".task_queue_ai_agent/agent.db",
  "provider": {
    "claude_command": ["claude"],
    "codex_command": ["codex"]
  },
  "telegram": {
    "bot_token": "",
    "chat_id": ""
  },
  "git": {
    "enabled": true,
    "auto_branch": true,
    "auto_commit": true,
    "auto_push": false,
    "branch_prefix": "agent/",
    "remote": "origin"
  }
}
```

---

## Execution model

This agent runs in **UNRESTRICTED MODE** for trusted local use:

- Commands run directly on the host system via `subprocess.run()`.
- No sandboxing, safety guards, or approval prompts are applied.
- No command filtering, allowlists, or denylists are enforced.
- AI-generated shell commands execute immediately.
- Failures produce real errors — nothing is silently blocked.

**Use this agent only in environments where you trust the inputs and repositories.**

---

## File tree

```
ai_agent/
  __init__.py
  chaining.py       # Follow-up task parsing and enqueuing
  cli.py            # CLI entry point
  compiler.py       # Prompt compilation
  config.py         # Configuration management
  db.py             # SQLite database with task schema
  git_ops.py        # Auto git branch/commit/push
  notify.py         # Telegram notifications
  router.py         # Claude-first provider routing with fallback
  worker.py         # Parallel worker loop with repo locking
  providers/
    claude_code.py   # Claude Code CLI runner
    codex.py         # OpenAI Codex CLI runner
README.md
requirements.txt
```
