from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import List, Optional

from .db import Database


@dataclass
class FollowupSpec:
    title: str
    request: str
    repo_path: Optional[str] = None
    constraints: Optional[str] = None
    acceptance: Optional[str] = None
    depends_on: Optional[str] = None  # "this" means depends on parent
    priority: int = 0


def parse_followups(logs: str) -> List[FollowupSpec]:
    """Extract follow-up task specs from LLM output.

    Looks for a JSON block with key "followups" containing an array of task
    objects. Example LLM output:

        ```json
        {"followups":[{"title":"...","request":"..."}]}
        ```
    """
    if not logs:
        return []

    # try to find a JSON block containing "followups"
    # handle both fenced code blocks and bare JSON
    patterns = [
        r"```(?:json)?\s*(\{[^`]*\"followups\"[^`]*\})\s*```",
        r"(\{[^\n]*\"followups\"[^\n]*\})",
    ]

    for pattern in patterns:
        match = re.search(pattern, logs, re.DOTALL | re.IGNORECASE)
        if match:
            try:
                data = json.loads(match.group(1))
                raw_list = data.get("followups", [])
                specs = []
                for item in raw_list:
                    if not isinstance(item, dict):
                        continue
                    title = item.get("title", "").strip()
                    request = item.get("request", "").strip()
                    if not title or not request:
                        continue
                    specs.append(
                        FollowupSpec(
                            title=title,
                            request=request,
                            repo_path=item.get("repo_path"),
                            constraints=item.get("constraints"),
                            acceptance=item.get("acceptance"),
                            depends_on=item.get("depends_on"),
                            priority=int(item.get("priority", 0)),
                        )
                    )
                return specs
            except (json.JSONDecodeError, ValueError, TypeError):
                continue
    return []


def enqueue_followups(
    db: Database,
    parent_task_id: int,
    chain_group_id: int,
    default_repo_path: str,
    default_provider: str,
    specs: List[FollowupSpec],
) -> List[int]:
    """Insert follow-up tasks into the queue and return their IDs."""
    created_ids: List[int] = []
    for spec in specs:
        depends_on = parent_task_id if spec.depends_on == "this" else None
        task_id = db.add_task(
            title=spec.title,
            repo_path=spec.repo_path or default_repo_path,
            request=spec.request,
            constraints=spec.constraints,
            acceptance=spec.acceptance,
            preferred_provider=default_provider,
            parent_task_id=parent_task_id,
            chain_group_id=chain_group_id,
            depends_on_task_id=depends_on,
            priority=spec.priority,
        )
        created_ids.append(task_id)
    return created_ids
