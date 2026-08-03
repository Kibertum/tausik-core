"""TAUSIK SQLiteBackend -- CRUD. Single-file SQLite, zero deps."""

from __future__ import annotations

import logging
import os
import sqlite3
from typing import Any

from backend_crud import BackendCrudMixin
from backend_crud_adapts import AdaptsCrudMixin
from backend_crud_knowledge import KnowledgeCrudMixin
from backend_crud_reasoning import ReasoningCrudMixin
from backend_crud_specs import SpecsCrudMixin
from backend_events_chain import BackendEventsChainMixin
from backend_graph import BackendGraphMixin
from backend_init import init_schema
from backend_queries import BackendQueriesMixin
from tausik_utils import utcnow_iso

logger = logging.getLogger("tausik.backend")

# Column whitelists for safe UPDATE operations
_EPIC_FIELDS = frozenset({"title", "status", "description"})
_STORY_FIELDS = frozenset({"title", "status", "description"})
_TASK_FIELDS = frozenset(
    {
        "title",
        "status",
        "stack",
        "complexity",
        "role",
        "score",
        "goal",
        "plan",
        "notes",
        "acceptance_criteria",
        "scope",
        "relevant_files",
        "started_at",
        "completed_at",
        "blocked_at",
        "attempts",
        "story_id",
        "claimed_by",
        "defect_of",
        "updated_at",
        "scope_exclude",
        "call_budget",
        "call_actual",
        "tier",
        "rollback_plan",
        "scope_paths",
        "scope_tools",
        "risk_score",
        "risk_json",
        "started_model_id",
        "started_model_version",
        "done_model_id",
        "done_model_version",
        "model_mismatch",
        "no_file_changes_declared",
    }
)


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


class SQLiteBackend(
    BackendQueriesMixin,
    BackendGraphMixin,
    BackendCrudMixin,
    KnowledgeCrudMixin,
    ReasoningCrudMixin,
    SpecsCrudMixin,
    AdaptsCrudMixin,
    BackendEventsChainMixin,
):
    """All DB operations for TAUSIK. Single SQLite file, FTS5 search."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._conn = sqlite3.connect(db_path, timeout=10, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._in_tx = False
        # (table, slug) pairs written inside the open transaction, projected when
        # it commits. See _project_write for why a mid-transaction write is wrong.
        self._pending_projection: list[tuple[str, str]] = []
        init_schema(self._conn)

    def close(self) -> None:
        """Close connection with WAL checkpoint."""
        try:
            self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception as e:  # noqa: BLE001 — best-effort: maintenance/IO, non-fatal to the surrounding op
            logger.warning("WAL checkpoint failed: %s", e)
        self._conn.close()

    def __enter__(self) -> "SQLiteBackend":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # --- helpers ---

    def _checkpoint(self) -> None:
        """Flush WAL to main DB file so .db is self-contained without -shm/-wal."""
        try:
            self._conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
        except Exception:  # noqa: BLE001 — best-effort: maintenance/IO, non-fatal to the surrounding op
            pass

    def _q(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        return [_row_to_dict(r) for r in self._conn.execute(sql, params)]

    def _q1(self, sql: str, params: tuple = ()) -> dict[str, Any] | None:
        row = self._conn.execute(sql, params).fetchone()
        return _row_to_dict(row) if row else None

    def _ex(self, sql: str, params: tuple = ()) -> int:
        cur = self._conn.execute(sql, params)
        if not self._in_tx:
            self._conn.commit()
        return cur.rowcount

    def _ins(self, sql: str, params: tuple = ()) -> int:
        cur = self._conn.execute(sql, params)
        if not self._in_tx:
            self._conn.commit()
        return cur.lastrowid or 0

    def begin_tx(self) -> None:
        """Begin explicit transaction for multi-step operations."""
        if self._in_tx:
            return  # already in transaction, no nesting
        self._conn.execute("BEGIN IMMEDIATE")
        self._in_tx = True

    def commit_tx(self) -> None:
        """Commit explicit transaction."""
        self._conn.commit()
        self._in_tx = False
        self._checkpoint()
        self._flush_pending_projection()

    def rollback_tx(self) -> None:
        """Rollback explicit transaction."""
        self._conn.rollback()
        self._in_tx = False
        # Discarded, not projected: these rows no longer exist as written.
        self._pending_projection.clear()

    def _project_write(self, table: str, slug: str) -> None:
        """Keep the git-native projection in step with THIS write. Never raises.

        Deferred while a transaction is open. Projecting mid-transaction would
        write a file describing state a rollback then throws away, leaving the
        tree ahead of the DB — the same class of divergence this hook exists to
        remove, with the sign flipped.

        "Never raises" covers the IMPORT too, which it did not: `auto_export_write`
        guards its own body completely, but the deferred import sat outside any
        try. This function is called from `_update`, so an ImportError would have
        broken the DB write itself rather than just its projection — a
        best-effort hook taking down the thing it is best-effort ABOUT.
        """
        if self._in_tx:
            self._pending_projection.append((table, slug))
            return
        try:
            from state_triggers import auto_export_write

            auto_export_write(self, table, slug)
        except Exception:  # noqa: BLE001 — FAIL-OPEN: the row is already written
            logger.warning("projection import/dispatch failed for %s/%s", table, slug)

    def _dependent_tables(self, parent: str) -> list[tuple[str, str, str]]:
        """Projected tables whose rows the ENGINE touches when a `parent` row goes.

        Read out of the schema (`PRAGMA foreign_key_list`), never listed here: a
        sixth projected kind with a cascading FK is covered by the migration that
        adds it, not by someone remembering this function. `SET NULL` counts too —
        such a row is not deleted but IS rewritten, so its file is stale either way.
        """
        from state_import import ENTITY_DIRS

        out: list[tuple[str, str, str]] = []
        for child in ENTITY_DIRS:
            for fk in self._q(f"PRAGMA foreign_key_list({child})"):
                if fk.get("table") != parent:
                    continue
                if (fk.get("on_delete") or "").upper() not in ("CASCADE", "SET NULL"):
                    continue
                out.append((child, str(fk["from"]), str(fk["to"] or "id")))
        return out

    def _projection_victims(self, table: str, slug: str) -> list[tuple[str, str]]:
        """Every projected row a delete of (table, slug) will take with it.

        SQLite performs `ON DELETE CASCADE` itself, so Python never learns which
        children went — which is why deleting an epic used to leave its stories
        and tasks on disk as GHOSTS, files describing rows the DB no longer has.
        The descendants are therefore collected BEFORE the delete, transitively.
        """
        from state_import import ENTITY_DIRS

        if table not in ENTITY_DIRS:
            return []
        victims: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = {(table, slug)}  # also breaks self-referencing FKs
        frontier = [(table, slug)]
        while frontier:
            parent, pslug = frontier.pop()
            for child, fk_col, parent_col in self._dependent_tables(parent):
                rows = self._q(
                    f"SELECT slug FROM {child} WHERE {fk_col} IN "  # noqa: S608 — names from ENTITY_DIRS/PRAGMA
                    f"(SELECT {parent_col} FROM {parent} WHERE slug=?)",
                    (pslug,),
                )
                for r in rows:
                    key = (child, str(r["slug"]))
                    if r.get("slug") and key not in seen:
                        seen.add(key)
                        victims.append(key)
                        frontier.append(key)
        return victims

    def _delete_projected(self, table: str, slug: str, sql: str, params: tuple) -> int:
        """DELETE, then let the projection shrink by exactly as much as the DB did."""
        victims = self._projection_victims(table, slug)
        removed = self._ex(sql, params)
        if removed:
            self._project_write(table, slug)
            for child_table, child_slug in victims:
                self._project_write(child_table, child_slug)
        return removed

    # Closed set, not whatever the caller passes — the table name reaches SQL as
    # text, and "internal callers only" describes today's callers.
    _ID_DELETABLE = ("decisions", "memory")

    def _delete_projected_by_id(self, table: str, row_id: int) -> int:
        """DELETE a slug-bearing row by id; the tree shrinks with it.

        Sits next to `_delete_projected`, which takes a slug — every caller here
        holds an id, and resolving it is the step they forgot: raw
        `DELETE ... WHERE id = ?` in `brain_move` removed rows and left their
        files as GHOSTS, describing entries the DB no longer had.

        ORDER IS LOAD-BEARING — the slug is read BEFORE the delete, because
        afterwards there is no row to read it from. Reversed, this projects
        nothing and says nothing: the same ghost, one layer further down.
        """
        if table not in self._ID_DELETABLE:
            raise ValueError(f"_delete_projected_by_id: {table!r} is not a slug-bearing kind")
        row = self._q1(f"SELECT slug FROM {table} WHERE id=?", (int(row_id),))  # noqa: S608
        slug = (row or {}).get("slug")
        removed = self._ex(f"DELETE FROM {table} WHERE id=?", (int(row_id),))  # noqa: S608
        if removed and slug:
            self._project_write(table, str(slug))
        return removed

    def _flush_pending_projection(self) -> None:
        """Project everything the just-committed transaction touched. Never raises.

        De-duplicated (first write wins the position): `state import` updates
        thousands of rows in one transaction and would otherwise re-render the
        same entity once per field-touching statement.

        The import is inside the guard for the same reason as in `_project_write`
        — this runs from `commit_tx`, so an unguarded ImportError would turn a
        best-effort projection into a failed commit.
        """
        pending, self._pending_projection = self._pending_projection, []
        if not pending:
            return
        try:
            from state_triggers import auto_export_write

            for table, slug in dict.fromkeys(pending):
                auto_export_write(self, table, slug)
        except Exception:  # noqa: BLE001 — FAIL-OPEN: the transaction is committed
            logger.warning("projection flush failed for %d queued write(s)", len(pending))

    def _update(
        self,
        table: str,
        allowed: frozenset[str],
        slug_col: str,
        slug: str,
        **fields: Any,
    ) -> int:
        """Safe UPDATE -- only whitelisted columns allowed."""
        if "updated_at" in allowed:
            fields["updated_at"] = utcnow_iso()
        bad = set(fields) - allowed
        if bad:
            raise ValueError(
                f"Invalid fields for {table}: {bad}. Valid: {', '.join(sorted(allowed))}"
            )
        sets = ", ".join(f"{k}=?" for k in fields)
        vals = tuple(fields.values()) + (slug,)
        changed = self._ex(f"UPDATE {table} SET {sets} WHERE {slug_col}=?", vals)
        # The projection follows the WRITE, not the caller's memory. `slug_col`
        # is checked because the exporter identifies entities by slug: keyed on
        # anything else, `slug` here is not the name it would look up.
        if changed and slug_col == "slug":
            self._project_write(table, slug)
        return changed

    def epic_add(self, slug: str, title: str, description: str | None = None) -> None:
        self._ins(
            "INSERT INTO epics(slug,title,description,created_at) VALUES(?,?,?,?)",
            (slug, title, description, utcnow_iso()),
        )

    def epic_get(self, slug: str) -> dict[str, Any] | None:
        return self._q1("SELECT * FROM epics WHERE slug=?", (slug,))

    def epic_list(self) -> list[dict[str, Any]]:
        return self._q("SELECT * FROM epics ORDER BY created_at")

    def epic_update(self, slug: str, **fields: Any) -> int:
        return self._update("epics", _EPIC_FIELDS, "slug", slug, **fields)

    def epic_delete(self, slug: str) -> int:
        return self._delete_projected("epics", slug, "DELETE FROM epics WHERE slug=?", (slug,))

    def story_add(
        self, epic_slug: str, slug: str, title: str, description: str | None = None
    ) -> None:
        epic = self.epic_get(epic_slug)
        if not epic:
            raise ValueError(f"Epic '{epic_slug}' not found")
        self._ins(
            "INSERT INTO stories(epic_id,slug,title,description,created_at) VALUES(?,?,?,?,?)",
            (epic["id"], slug, title, description, utcnow_iso()),
        )

    def story_get(self, slug: str) -> dict[str, Any] | None:
        return self._q1(
            "SELECT s.*, e.slug AS epic_slug FROM stories s "
            "JOIN epics e ON s.epic_id=e.id WHERE s.slug=?",
            (slug,),
        )

    def story_list(self, epic_slug: str | None = None) -> list[dict[str, Any]]:
        if epic_slug:
            return self._q(
                "SELECT s.*, e.slug AS epic_slug FROM stories s "
                "JOIN epics e ON s.epic_id=e.id WHERE e.slug=? ORDER BY s.created_at",
                (epic_slug,),
            )
        return self._q(
            "SELECT s.*, e.slug AS epic_slug FROM stories s "
            "JOIN epics e ON s.epic_id=e.id ORDER BY s.created_at"
        )

    def story_update(self, slug: str, **fields: Any) -> int:
        return self._update("stories", _STORY_FIELDS, "slug", slug, **fields)

    def story_delete(self, slug: str) -> int:
        return self._delete_projected("stories", slug, "DELETE FROM stories WHERE slug=?", (slug,))

    def task_add(
        self,
        story_slug: str | None,
        slug: str,
        title: str,
        stack: str | None = None,
        complexity: str | None = None,
        score: int | None = None,
        goal: str | None = None,
        role: str | None = None,
        defect_of: str | None = None,
    ) -> str:
        story_id = None
        if story_slug:
            story = self.story_get(story_slug)
            if not story:
                raise ValueError(f"Story '{story_slug}' not found")
            story_id = story["id"]
        now = utcnow_iso()
        self._ins(
            "INSERT INTO tasks(story_id,slug,title,stack,complexity,score,goal,role,"
            "defect_of,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                story_id,
                slug,
                title,
                stack,
                complexity,
                score,
                goal,
                role,
                defect_of,
                now,
                now,
            ),
        )
        return slug

    def task_next_candidate(self) -> dict[str, Any] | None:
        """Get highest-score unclaimed planning task (single SQL query)."""
        return self._q1(
            "SELECT * FROM tasks WHERE status='planning' AND claimed_by IS NULL "
            "ORDER BY score DESC LIMIT 1"
        )

    def task_get(self, slug: str) -> dict[str, Any] | None:
        return self._q1("SELECT * FROM tasks WHERE slug=?", (slug,))

    def task_get_full(self, slug: str) -> dict[str, Any] | None:
        return self._q1(
            "SELECT t.*, s.slug AS story_slug, e.slug AS epic_slug "
            "FROM tasks t LEFT JOIN stories s ON t.story_id=s.id "
            "LEFT JOIN epics e ON s.epic_id=e.id WHERE t.slug=?",
            (slug,),
        )

    def task_list(
        self,
        status: str | None = None,
        story: str | None = None,
        epic: str | None = None,
        role: str | None = None,
        stack: str | None = None,
        limit: int | None = None,
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        sql = (
            "SELECT t.*, s.slug AS story_slug, e.slug AS epic_slug "
            "FROM tasks t LEFT JOIN stories s ON t.story_id=s.id "
            "LEFT JOIN epics e ON s.epic_id=e.id WHERE 1=1"
        )
        params: list[Any] = []
        if not include_archived:
            sql += " AND t.archived_at IS NULL"
        if status:
            placeholders = ",".join("?" for _ in status.split(","))
            sql += f" AND t.status IN ({placeholders})"
            params.extend(status.split(","))
        if story:
            sql += " AND s.slug=?"
            params.append(story)
        if epic:
            sql += " AND e.slug=?"
            params.append(epic)
        if role:
            sql += " AND t.role=?"
            params.append(role)
        if stack:
            sql += " AND t.stack=?"
            params.append(stack)
        sql += " ORDER BY t.created_at"
        if limit:
            sql += " LIMIT ?"
            params.append(limit)
        return self._q(sql, tuple(params))

    def task_update(self, slug: str, **fields: Any) -> int:
        return self._update("tasks", _TASK_FIELDS, "slug", slug, **fields)

    def task_append_notes(self, slug: str, message: str) -> None:
        """Append a timestamped log entry to task notes (atomic, no read-modify-write)."""
        now = utcnow_iso()
        entry = f"[{now}] {message}"
        rows = self._ex(
            "UPDATE tasks SET notes = CASE WHEN notes IS NULL OR notes = '' "
            "THEN ? ELSE notes || char(10) || ? END, updated_at=? WHERE slug=?",
            (entry, entry, now, slug),
        )
        if rows == 0:
            raise ValueError(f"Task '{slug}' not found")

    def task_claim(self, slug: str, agent_id: str, now: str) -> int:
        """Atomic claim: only succeeds if unclaimed or same agent."""
        rows = self._ex(
            "UPDATE tasks SET claimed_by=?, updated_at=? "
            "WHERE slug=? AND (claimed_by IS NULL OR claimed_by=?)",
            (agent_id, now, slug, agent_id),
        )
        if rows == 0:
            task = self.task_get(slug)
            claimed_by = task["claimed_by"] if task else "unknown"
            raise ValueError(f"Task '{slug}' already claimed by '{claimed_by}'")
        return rows

    def task_delete(self, slug: str) -> int:
        return self._delete_projected("tasks", slug, "DELETE FROM tasks WHERE slug=?", (slug,))

    # Mixins: BackendCrudMixin (crud), BackendGraphMixin (graph), BackendQueriesMixin (queries)
