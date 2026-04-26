"""TAUSIK SQLiteBackend -- CRUD. Single-file SQLite, zero deps."""

from __future__ import annotations

import logging
import os
import sqlite3
from typing import Any

from backend_crud import BackendCrudMixin
from backend_graph import BackendGraphMixin
from backend_queries import BackendQueriesMixin
from backend_migrations import run_migrations
from backend_schema import (
    FTS_SQL,
    FTS_TRIGGERS_SQL,
    INDEXES_SQL,
    SCHEMA_SQL,
    SCHEMA_VERSION,
)
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
    }
)


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


class SQLiteBackend(BackendQueriesMixin, BackendGraphMixin, BackendCrudMixin):
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
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self._conn.cursor()
        # Check if schema already at current version (skip DDL for performance)
        try:
            row = cur.execute(
                "SELECT value FROM meta WHERE key='schema_version'"
            ).fetchone()
            if row:
                db_ver = int(row[0])
                if db_ver == SCHEMA_VERSION:
                    self._conn.commit()
                    return  # Schema up to date, skip DDL
                if db_ver > SCHEMA_VERSION:
                    raise RuntimeError(
                        f"Database schema v{db_ver} is newer than code v{SCHEMA_VERSION}. "
                        f"Update .tausik-lib to the latest version."
                    )
        except RuntimeError:
            raise  # Re-raise schema version guard errors
        except Exception:
            pass  # Table doesn't exist yet -- run full DDL
        cur.executescript(SCHEMA_SQL)
        cur.executescript(FTS_SQL)
        cur.executescript(FTS_TRIGGERS_SQL)
        cur.executescript(INDEXES_SQL)
        row = cur.execute(
            "SELECT value FROM meta WHERE key='schema_version'"
        ).fetchone()
        if not row:
            cur.execute(
                "INSERT INTO meta(key,value) VALUES('schema_version',?)",
                (str(SCHEMA_VERSION),),
            )
            self._conn.commit()
            from backend_migrations import run_migrations as _rm

            _rm(self._conn, SCHEMA_VERSION)
        else:
            current_ver = int(row[0])
            if current_ver < SCHEMA_VERSION:
                # Backup DB before migration
                import shutil

                db_path = self._conn.execute("PRAGMA database_list").fetchone()[2]
                backup_path = f"{db_path}.bak.v{current_ver}"
                if db_path and not os.path.exists(backup_path):
                    try:
                        self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                        shutil.copy2(db_path, backup_path)
                        logger.info("Backup created: %s", backup_path)
                    except OSError as e:
                        logger.warning("Backup failed for %s: %s", db_path, e)
                new_ver = run_migrations(self._conn, current_ver)
                cur.execute(
                    "UPDATE meta SET value=? WHERE key='schema_version'",
                    (str(new_ver),),
                )
                # Rebuild FTS indexes after migration
                for fts_table in ("fts_tasks", "fts_memory", "fts_decisions"):
                    try:
                        cur.execute(
                            f"INSERT INTO {fts_table}({fts_table}) VALUES('rebuild')"
                        )
                    except Exception as e:
                        logger.warning("FTS rebuild failed for %s: %s", fts_table, e)
                logger.info("Schema migrated %d -> %d", current_ver, new_ver)
        self._conn.commit()

    def close(self) -> None:
        """Close connection with WAL checkpoint."""
        try:
            self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception as e:
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
        except Exception:
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

    def rollback_tx(self) -> None:
        """Rollback explicit transaction."""
        self._conn.rollback()
        self._in_tx = False

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
                f"Invalid fields for {table}: {bad}. "
                f"Valid: {', '.join(sorted(allowed))}"
            )
        sets = ", ".join(f"{k}=?" for k in fields)
        vals = tuple(fields.values()) + (slug,)
        return self._ex(f"UPDATE {table} SET {sets} WHERE {slug_col}=?", vals)

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
        return self._ex("DELETE FROM epics WHERE slug=?", (slug,))

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
        return self._ex("DELETE FROM stories WHERE slug=?", (slug,))

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
    ) -> list[dict[str, Any]]:
        sql = (
            "SELECT t.*, s.slug AS story_slug, e.slug AS epic_slug "
            "FROM tasks t LEFT JOIN stories s ON t.story_id=s.id "
            "LEFT JOIN epics e ON s.epic_id=e.id WHERE 1=1"
        )
        params: list[Any] = []
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
        return self._ex("DELETE FROM tasks WHERE slug=?", (slug,))

    # Mixins: BackendCrudMixin (crud), BackendGraphMixin (graph), BackendQueriesMixin (queries)
