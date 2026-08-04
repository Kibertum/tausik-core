"""TAUSIK KnowledgeCrudMixin — decisions + memory CRUD (the slug-bearing entities).

Extracted from backend_crud.py to keep it under the 400-line filesize cap: the
v42 slug identity (state-git-stable-ids) and its race-safe insert path pushed the
decisions/memory block over. Mixed into SQLiteBackend alongside BackendCrudMixin;
relies on the composed backend's ``_ins`` / ``_q`` / ``_q1`` / ``_ex`` helpers.

Decisions and memory are exactly the entities that carry a stable slug and travel
in the git-native projection, so grouping their CRUD here also co-locates the
slug-allocation concern (`insert_with_slug`, the UNIQUE index as source of truth).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from slug_util import first_line, insert_with_slug
from tausik_utils import utcnow_iso


class KnowledgeCrudMixin:
    """CRUD for decisions and memory (stable-slug entities)."""

    # Type stubs for mixin -- actual methods provided by SQLiteBackend
    if TYPE_CHECKING:

        def _ins(self, sql: str, params: tuple[Any, ...] = ()) -> int: ...
        def _ex(self, sql: str, params: tuple[Any, ...] = ()) -> int: ...
        def _q(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]: ...
        def _q1(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None: ...
        def _delete_projected_by_id(self, table: str, row_id: int) -> int: ...
        def task_get(self, slug: str) -> dict[str, Any] | None: ...

    def _resolve_task_slug(self, task_slug: str | None) -> str | None:
        """Validate task_slug exists, return None if not found."""
        if not task_slug:
            return None
        if self.task_get(task_slug):
            return task_slug
        return None

    def _add_slugged(self, table, sql, params_of, text, fallback) -> int:
        """INSERT a slug-bearing row race-safely (UNIQUE index is the guarantee;
        `insert_with_slug` retries on a concurrent clash). `params_of(slug)`
        builds the row's params — recomputed per retry, which is cheap."""
        return int(
            insert_with_slug(self._q, lambda s: self._ins(sql, params_of(s)), table, text, fallback)
        )

    # --- Decisions ---

    def decision_add(
        self, text: str, task_slug: str | None = None, rationale: str | None = None
    ) -> int:
        now = utcnow_iso()
        return self._add_slugged(
            "decisions",
            "INSERT INTO decisions(decision,task_slug,rationale,created_at,slug) VALUES(?,?,?,?,?)",
            lambda s: (text, self._resolve_task_slug(task_slug), rationale, now, s),
            first_line(text),
            f"decision-{now}",
        )

    def decision_list(self, n: int = 20) -> list[dict[str, Any]]:
        return self._q("SELECT * FROM decisions ORDER BY id DESC LIMIT ?", (n,))

    def decision_get(self, decision_id: int) -> dict[str, Any] | None:
        """Get a single decision by ID."""
        return self._q1("SELECT * FROM decisions WHERE id=?", (decision_id,))

    def decisions_for_task(self, slug: str) -> list[dict[str, Any]]:
        return self._q("SELECT * FROM decisions WHERE task_slug=? ORDER BY id", (slug,))

    def decision_count_for_task(self, slug: str) -> int:
        """Count decisions linked to a task."""
        row = self._q1("SELECT COUNT(*) as cnt FROM decisions WHERE task_slug=?", (slug,))
        return row["cnt"] if row else 0

    # --- Memory ---

    def memory_add(
        self,
        mem_type: str,
        title: str,
        content: str,
        tags: list[str] | None = None,
        task_slug: str | None = None,
    ) -> int:
        now = utcnow_iso()
        tags_json = json.dumps(tags) if tags else None
        task = self._resolve_task_slug(task_slug)
        return self._add_slugged(
            "memory",
            "INSERT INTO memory(type,title,content,tags,task_slug,created_at,updated_at,slug) "
            "VALUES(?,?,?,?,?,?,?,?)",
            lambda s: (mem_type, title, content, tags_json, task, now, now, s),
            title,
            f"memory-{now}",
        )

    def memory_list(
        self,
        mem_type: str | None = None,
        n: int = 50,
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        sql = "SELECT * FROM memory WHERE 1=1"
        params: list[Any] = []
        if not include_archived:
            sql += " AND archived_at IS NULL"
        if mem_type:
            sql += " AND type=?"
            params.append(mem_type)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(n)
        return self._q(sql, tuple(params))

    def memory_get(self, mid: int) -> dict[str, Any] | None:
        return self._q1("SELECT * FROM memory WHERE id=?", (mid,))

    def memory_delete(self, mid: int) -> int:
        return self._delete_projected_by_id("memory", mid)

    # NO `decision_delete` here, and that is a decision rather than an omission.
    # It was written, and the class-surface ratchet refused it: `SQLiteBackend`
    # already exposes 129 public members, and the gate exists precisely to stop
    # the 130th being added for a single caller. Decisions are removed by exactly
    # one module — `brain_move`, handing a record over — and it reaches
    # `_delete_projected_by_id` directly. What the defect actually needed was a
    # write-layer path that PROJECTS; a public method was one way to spell that,
    # not the requirement.

    def memory_count_for_task(self, slug: str) -> int:
        """Count memories linked to a task."""
        row = self._q1("SELECT COUNT(*) as cnt FROM memory WHERE task_slug=?", (slug,))
        return row["cnt"] if row else 0
