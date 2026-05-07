"""Exploration operations (SENAR Section 5.1).

Extracted from service_knowledge.py to keep that file under the 400-line gate.
Mirrors the service_knowledge_aggregates.py / service_knowledge_hygiene.py
split pattern: thin delegators in KnowledgeMixin, real logic here.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from tausik_utils import ServiceError, slugify, validate_length

if TYPE_CHECKING:
    from project_backend import SQLiteBackend


def exploration_start(be: SQLiteBackend, title: str, time_limit_min: int = 30) -> str:
    current = be.exploration_current()
    if current:
        return f"Exploration #{current['id']} already active: {current['title']}"
    validate_length("title", title)
    time_limit_min = max(1, min(480, time_limit_min))  # clamp 1-480 min
    eid = be.exploration_start(title, time_limit_min)
    return f"Exploration #{eid} started ({time_limit_min} min limit): {title}"


def exploration_end(
    be: SQLiteBackend, summary: str | None = None, create_task: bool = False
) -> str:
    current = be.exploration_current()
    if not current:
        raise ServiceError("No active exploration")
    if create_task and not summary:
        raise ServiceError("--create-task requires --summary")
    task_slug = None
    be.begin_tx()
    try:
        msgs = [f"Exploration #{current['id']} ended."]
        if create_task and summary:
            slug = slugify(current["title"]) or "explore"
            if be.task_get(slug):
                slug = f"{slug[:44]}-{os.urandom(3).hex()}"
            be.task_add(None, slug, current["title"], goal=summary)
            task_slug = slug
            msgs.append(f"Task '{slug}' created from exploration.")
        be.exploration_end(current["id"], summary, task_slug)
        be.commit_tx()
    except Exception:
        be.rollback_tx()
        raise
    if summary:
        msgs.append(f"Summary: {summary}")
    return " ".join(msgs)


def exploration_current(be: SQLiteBackend) -> dict[str, Any] | None:
    exp = be.exploration_current()
    if exp:
        try:
            started = datetime.fromisoformat(exp["started_at"].replace("Z", "+00:00"))
            elapsed = (datetime.now(timezone.utc) - started).total_seconds() / 60
            exp["elapsed_min"] = round(elapsed, 1)
            exp["over_limit"] = elapsed > (exp.get("time_limit_min") or 30)
        except (ValueError, TypeError):
            pass
    return exp
