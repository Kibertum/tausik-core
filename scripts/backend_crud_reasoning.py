"""TAUSIK ReasoningCrudMixin — RENAR reasoning-trace CRUD.

Extracted from backend_crud.py to keep it under the 400-line filesize cap
(v16r-reasoning-steps-table). Mixed into SQLiteBackend alongside
BackendCrudMixin; relies on the composed backend's ``_ins`` / ``_q`` helpers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tausik_utils import utcnow_iso


class ReasoningCrudMixin:
    """Append-only reasoning steps for a task (RENAR reasoning trace)."""

    # Type stubs for mixin -- actual methods provided by SQLiteBackend
    if TYPE_CHECKING:

        def _ins(self, sql: str, params: tuple[Any, ...] = ()) -> int: ...
        def _q(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]: ...

    def reasoning_step_add(
        self,
        task_slug: str,
        kind: str,
        content: str,
        seq: int | None = None,
    ) -> int:
        """Append a reasoning step; returns the assigned ``seq``.

        ``seq`` auto-increments per task when omitted. ``kind`` is enforced as
        a closed list by the table CHECK constraint (intent | premise | action
        | verification) — an invalid value raises sqlite3.IntegrityError rather
        than being silently stored.
        """
        if seq is None:
            row = self._q(
                "SELECT COALESCE(MAX(seq), 0) + 1 AS next FROM reasoning_steps WHERE task_slug=?",
                (task_slug,),
            )
            seq = int(row[0]["next"]) if row else 1
        seq = int(seq)
        self._ins(
            "INSERT INTO reasoning_steps(task_slug,seq,kind,content,created_at) VALUES(?,?,?,?,?)",
            (task_slug, seq, kind, content, utcnow_iso()),
        )
        return seq

    def reasoning_step_list(self, task_slug: str) -> list[dict[str, Any]]:
        """Reasoning trace for a task, ordered by seq then id."""
        return self._q(
            "SELECT * FROM reasoning_steps WHERE task_slug=? ORDER BY seq, id",
            (task_slug,),
        )
