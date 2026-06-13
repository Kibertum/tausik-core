"""TAUSIK SpecsCrudMixin — RENAR SPEC-artifact CRUD.

Extracted from backend_crud.py to keep it under the 400-line filesize cap
(v16r-spec-types). Mixed into SQLiteBackend alongside BackendCrudMixin; relies
on the composed backend's ``_ins`` / ``_q`` / ``_q1`` / ``_ex`` helpers.

``type`` and ``relation`` are CLOSED lists enforced by table CHECK constraints —
an invalid value raises sqlite3.IntegrityError rather than being stored.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tausik_utils import utcnow_iso


class SpecsCrudMixin:
    """CRUD for RENAR SPEC artifacts and their task links."""

    # Type stubs for mixin -- actual methods provided by SQLiteBackend
    if TYPE_CHECKING:

        def _ins(self, sql: str, params: tuple[Any, ...] = ()) -> int: ...
        def _ex(self, sql: str, params: tuple[Any, ...] = ()) -> int: ...
        def _q(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]: ...
        def _q1(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None: ...

    def spec_add(
        self,
        slug: str,
        type_: str,
        title: str,
        version: str,
        content_ref: str | None = None,
        status: str = "draft",
    ) -> int:
        """Insert a SPEC; returns the new row id.

        ``type_`` and ``status`` are enforced as closed lists by the table
        CHECK constraints; a duplicate ``slug`` raises IntegrityError on the
        UNIQUE index.
        """
        now = utcnow_iso()
        return self._ins(
            "INSERT INTO specs(slug, type, title, content_ref, version, status, "
            "created_at, updated_at) VALUES(?,?,?,?,?,?,?,?)",
            (slug, type_, title, content_ref, version, status, now, now),
        )

    def spec_get(self, slug: str) -> dict[str, Any] | None:
        """Return a SPEC row by slug, or None."""
        return self._q1("SELECT * FROM specs WHERE slug=?", (slug,))

    def spec_list(self, type_: str | None = None) -> list[dict[str, Any]]:
        """List SPECs, optionally filtered by type, newest first."""
        if type_:
            return self._q(
                "SELECT * FROM specs WHERE type=? ORDER BY created_at DESC, id DESC",
                (type_,),
            )
        return self._q("SELECT * FROM specs ORDER BY created_at DESC, id DESC")

    def spec_update(
        self,
        slug: str,
        title: str | None = None,
        version: str | None = None,
        content_ref: str | None = None,
        status: str | None = None,
    ) -> int:
        """Patch mutable SPEC fields; returns affected row count.

        Only non-None args are written. ``type`` and ``slug`` are immutable
        (a SPEC's identity); change them by deleting and re-adding.
        """
        sets: list[str] = []
        params: list[Any] = []
        for col, val in (
            ("title", title),
            ("version", version),
            ("content_ref", content_ref),
            ("status", status),
        ):
            if val is not None:
                sets.append(f"{col}=?")
                params.append(val)
        if not sets:
            return 0
        sets.append("updated_at=?")
        params.append(utcnow_iso())
        params.append(slug)
        return self._ex(f"UPDATE specs SET {', '.join(sets)} WHERE slug=?", tuple(params))

    def spec_delete(self, slug: str) -> int:
        """Delete a SPEC by slug; returns affected row count.

        task_specs rows referencing it cascade-delete (FK ON DELETE CASCADE).
        """
        return self._ex("DELETE FROM specs WHERE slug=?", (slug,))

    def spec_link(self, task_slug: str, spec_slug: str, relation: str = "implements") -> int:
        """Link a task to a SPEC; returns the link rowid.

        ``relation`` is a closed list ('implements' | 'constrained_by') enforced
        by CHECK. The PRIMARY KEY (task_slug, spec_slug, relation) makes a
        duplicate link raise IntegrityError. Both FKs guarantee the task and
        SPEC exist (else IntegrityError) — no silent dangling link.
        """
        return self._ins(
            "INSERT INTO task_specs(task_slug, spec_slug, relation, created_at) VALUES(?,?,?,?)",
            (task_slug, spec_slug, relation, utcnow_iso()),
        )

    def spec_unlink(self, task_slug: str, spec_slug: str, relation: str = "implements") -> int:
        """Remove a task↔SPEC link; returns affected row count."""
        return self._ex(
            "DELETE FROM task_specs WHERE task_slug=? AND spec_slug=? AND relation=?",
            (task_slug, spec_slug, relation),
        )

    def specs_for_task(self, task_slug: str) -> list[dict[str, Any]]:
        """SPECs linked to a task, with the link relation, newest link first."""
        return self._q(
            "SELECT s.*, ts.relation AS relation FROM task_specs ts "
            "JOIN specs s ON s.slug = ts.spec_slug "
            "WHERE ts.task_slug=? ORDER BY ts.created_at DESC",
            (task_slug,),
        )

    def tasks_for_spec(self, spec_slug: str) -> list[dict[str, Any]]:
        """Tasks linked to a SPEC, with the link relation, newest link first."""
        return self._q(
            "SELECT t.slug, t.title, t.status, ts.relation AS relation "
            "FROM task_specs ts JOIN tasks t ON t.slug = ts.task_slug "
            "WHERE ts.spec_slug=? ORDER BY ts.created_at DESC",
            (spec_slug,),
        )

    def spec_search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """FTS5 search over SPEC slug/title/content_ref, ranked by bm25."""
        return self._q(
            "SELECT s.*, snippet(fts_specs, 1, '>>>', '<<<', '...', 32) AS _snippet "
            "FROM specs s JOIN fts_specs f ON s.id=f.rowid "
            "WHERE fts_specs MATCH ? ORDER BY bm25(fts_specs, 5.0, 10.0, 2.0) LIMIT ?",
            (query, limit),
        )
