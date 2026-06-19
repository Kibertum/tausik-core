"""Journal-overwrite guard for ``task_update`` (qa-task-update-notes-guard).

A task's ``notes`` column is an append-only, crash-safe journal written by
``task log``. A blind ``task_update(notes=…)`` would clobber the entire history
(memory #160 footgun). This module owns the single check so the large
``service_task`` module stays under the 400-line filesize cap, and the rule is
unit-testable in isolation.
"""

from __future__ import annotations

from typing import Any


def guard_notes_overwrite(slug: str, existing_notes: str | None, fields: dict[str, Any]) -> None:
    """Pop ``notes_overwrite`` from *fields*; raise if it would clobber history.

    No-op when ``notes`` is not being set, the journal is empty/blank, or the
    caller passed ``notes_overwrite=True``. Otherwise raises ``ServiceError``
    (imported lazily to avoid a circular import) steering the caller to
    ``task log``.
    """
    allow = bool(fields.pop("notes_overwrite", False))
    if fields.get("notes") is None or allow:
        return
    if not (existing_notes or "").strip():
        return
    from project_service import ServiceError

    raise ServiceError(
        f"task_update(notes=…) would OVERWRITE the existing journal of "
        f"'{slug}' (task notes are append-only history). Append with "
        f'`.tausik/tausik task log {slug} "…"` instead, or pass '
        f"notes_overwrite=true (CLI: --notes-overwrite) to replace it on purpose."
    )
