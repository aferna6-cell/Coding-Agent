# Task Queue AI Agent (MVP)

A local, sequential task queue runner that compiles coding requests into high-quality prompts, runs them through Claude Code CLI first, and falls back to OpenAI Codex CLI when needed. Tasks are stored persistently in SQLite, and completion notifications are sent via a free Telegram bot.

## Features
- Sequential queue processing with SQLite persistence.
- Prompt compilation with structured sections and strict output format.
- Claude-first routing with fallback to Codex on failure or rate limit.
- Safety guard with a denylist of destructive commands (override per task).
- Telegram bot notifications (free).
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

### List tasks
```bash
python -m ai_agent.cli list
```

### Run worker (sequential)
```bash
python -m ai_agent.cli run
```

### Dry run (compile prompt only)
```bash
python -m ai_agent.cli run --dry-run
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

## Example task (end-to-end)

```bash
python -m ai_agent.cli init
python -m ai_agent.cli add \
  --title "Refactor auth handler" \
  --repo-path /home/you/projects/app \
  --request "Refactor auth handler for clarity and add unit tests" \
  --constraints "Do not change public APIs" \
  --acceptance "All auth tests pass" \
  --acceptance "No behavior regressions"
python -m ai_agent.cli run
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
  }
}
```

---

## Safety guard

The agent checks for a denylist of destructive commands in the task request/constraints/acceptance. If a match is found and `dangerous_ok` is not set, the task is failed before running any provider.

Denylist examples:
- `rm -rf`
- `dd`
- `mkfs`
- `shutdown`
- `reboot`

To override per task:
```bash
python -m ai_agent.cli add ... --dangerous-ok
```

---

## File tree

```
ai_agent/
  __init__.py
  cli.py
  compiler.py
  config.py
  db.py
  notify.py
  router.py
  safety.py
  providers/
    claude_code.py
    codex.py
README.md
requirements.txt
```
