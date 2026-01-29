# Coding-Agent

A simple task runner that converts feature requests into AI-friendly prompts for two agents ("you" and "Claude Code"), processes tasks in sequence, and sends an SMS notification when each task completes.

## Features
- Reads a queue of tasks from a JSON file.
- Builds role-specific prompts for a primary agent ("you") and Claude Code.
- Runs tasks sequentially, marking each task as completed.
- Sends an SMS on completion (Twilio via environment variables).

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py --tasks tasks.json
```

## Configuration

The SMS notifier uses Twilio if the following environment variables are set:

- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_FROM_NUMBER`

The default destination number is set in `tasks.json`, but can be overridden with `--to`.

## Task format

```json
{
  "destination_number": "+12032322876",
  "tasks": [
    {
      "id": "task-1",
      "title": "Example task",
      "description": "Describe the task here",
      "acceptance_criteria": ["First outcome", "Second outcome"]
    }
  ]
}
```

## Notes
- Prompt delivery is currently implemented as console output. Swap `ConsoleClient` for a real API client if desired.
- SMS delivery is best-effort; if Twilio is not configured, it logs a warning and continues.
