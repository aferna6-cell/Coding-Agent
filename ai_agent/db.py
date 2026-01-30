from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

ISO_FORMAT = "%Y-%m-%dT%H:%M:%S"


@dataclass
class TaskRecord:
    id: int
    title: str
    repo_path: str
    request: str
    constraints: Optional[str]
    acceptance: Optional[str]
    preferred_provider: str
    status: str
    provider_used: str
    created_at: str
    started_at: Optional[str]
    finished_at: Optional[str]
    attempts: int
    last_error: Optional[str]
    logs: Optional[str]


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def init(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    repo_path TEXT NOT NULL,
                    request TEXT NOT NULL,
                    constraints TEXT,
                    acceptance TEXT,
                    preferred_provider TEXT DEFAULT 'claude_first',
                    status TEXT DEFAULT 'queued',
                    provider_used TEXT DEFAULT 'none',
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    attempts INTEGER DEFAULT 0,
                    last_error TEXT,
                    logs TEXT
                )
                """
            )

    def add_task(
        self,
        title: str,
        repo_path: str,
        request: str,
        constraints: Optional[str],
        acceptance: Optional[str],
        preferred_provider: str,
    ) -> int:
        created_at = datetime.utcnow().strftime(ISO_FORMAT)
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO tasks (
                    title,
                    repo_path,
                    request,
                    constraints,
                    acceptance,
                    preferred_provider,
                    status,
                    provider_used,
                    created_at,
                    attempts
                ) VALUES (?, ?, ?, ?, ?, ?, 'queued', 'none', ?, 0)
                """,
                (
                    title,
                    repo_path,
                    request,
                    constraints,
                    acceptance,
                    preferred_provider,
                    created_at,
                ),
            )
            return int(cursor.lastrowid)

    def list_tasks(self) -> Iterable[TaskRecord]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM tasks ORDER BY id DESC"
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def get_task(self, task_id: int) -> Optional[TaskRecord]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM tasks WHERE id = ?",
                (task_id,),
            ).fetchone()
        return self._row_to_record(row) if row else None

    def cancel_task(self, task_id: int) -> bool:
        with self.connect() as conn:
            cursor = conn.execute(
                """
                UPDATE tasks
                SET status = 'canceled'
                WHERE id = ? AND status = 'queued'
                """,
                (task_id,),
            )
            return cursor.rowcount > 0

    def claim_next_task(self) -> Optional[TaskRecord]:
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """
                SELECT * FROM tasks
                WHERE status = 'queued'
                ORDER BY created_at ASC
                LIMIT 1
                """
            ).fetchone()
            if not row:
                conn.execute("COMMIT")
                return None
            started_at = datetime.utcnow().strftime(ISO_FORMAT)
            conn.execute(
                """
                UPDATE tasks
                SET status = 'running',
                    started_at = ?,
                    attempts = attempts + 1
                WHERE id = ?
                """,
                (started_at, row["id"]),
            )
            conn.execute("COMMIT")
            return self._row_to_record(row)

    def peek_next_task(self) -> Optional[TaskRecord]:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM tasks
                WHERE status = 'queued'
                ORDER BY created_at ASC
                LIMIT 1
                """
            ).fetchone()
        return self._row_to_record(row) if row else None

    def update_task(
        self,
        task_id: int,
        status: str,
        provider_used: str,
        logs: Optional[str],
        last_error: Optional[str],
    ) -> None:
        finished_at = datetime.utcnow().strftime(ISO_FORMAT)
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE tasks
                SET status = ?,
                    provider_used = ?,
                    logs = ?,
                    last_error = ?,
                    finished_at = ?
                WHERE id = ?
                """,
                (status, provider_used, logs, last_error, finished_at, task_id),
            )

    def _row_to_record(self, row: sqlite3.Row) -> TaskRecord:
        return TaskRecord(
            id=row["id"],
            title=row["title"],
            repo_path=row["repo_path"],
            request=row["request"],
            constraints=row["constraints"],
            acceptance=row["acceptance"],
            preferred_provider=row["preferred_provider"],
            status=row["status"],
            provider_used=row["provider_used"],
            created_at=row["created_at"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
            attempts=row["attempts"],
            last_error=row["last_error"],
            logs=row["logs"],
        )
