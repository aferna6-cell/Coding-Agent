from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


@dataclass(frozen=True)
class Task:
    task_id: str
    title: str
    description: str
    acceptance_criteria: List[str]


@dataclass
class TaskQueue:
    destination_number: str
    tasks: List[Task]

    @classmethod
    def from_file(cls, path: Path) -> "TaskQueue":
        payload = json.loads(path.read_text())
        destination_number = payload.get("destination_number", "")
        tasks: List[Task] = []
        for raw in payload.get("tasks", []):
            tasks.append(
                Task(
                    task_id=raw.get("id", ""),
                    title=raw.get("title", ""),
                    description=raw.get("description", ""),
                    acceptance_criteria=list(raw.get("acceptance_criteria", [])),
                )
            )
        return cls(destination_number=destination_number, tasks=tasks)

    def __iter__(self) -> Iterable[Task]:
        return iter(self.tasks)
