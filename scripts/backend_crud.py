"""TAUSIK BackendCrudMixin -- session, decision, memory, meta, events CRUD."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from tausik_utils import utcnow_iso

if TYPE_CHECKING:

    def _q(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]: ...
    def _q1(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None: ...
    def _ex(self, sql: str, params: tuple[Any, ...] = ()) -> int: ...
    def _ins(self, sql: str, params: tuple[Any, ...] = ()) -> int: ...


class BackendCrudMixin:
    """Session, decision, memory, meta, and events CRUD. Mixed into SQLiteBackend."""

    # Type stubs for mixin
    if TYPE_CHECKING:

        def _q(
            self, sql: str, params: tuple[Any, ...] = ()
        ) -> list[dict[str, Any]]: ...
        def _q1(
            self, sql: str, params: tuple[Any, ...] = ()
        ) -> dict[str, Any] | None: ...
        def _ex(self, sql: str, params: tuple[Any, ...] = ()) -> int: ...
        def _ins(self, sql: str, params: tuple[Any, ...] = ()) -> int: ...
        def task_get(self, slug: str) -> dict[str, Any] | None: ...

    # --- Hierarchy counts ---

    def story_active_task_count(self, story_slug: str) -> int:
        row = self._q1(
            "SELECT COUNT(*) as cnt FROM tasks t "
            "JOIN stories s ON t.story_id=s.id "
            "WHERE s.slug=? AND t.status NOT IN ('done')",
            (story_slug,),
        )
        return row["cnt"] if row else 0

    def epic_undone_story_count(self, epic_slug: str) -> int:
        row = self._q1(
            "SELECT COUNT(*) as cnt FROM stories s "
            "JOIN epics e ON s.epic_id=e.id "
            "WHERE e.slug=? AND s.status != 'done'",
            (epic_slug,),
        )
        return row["cnt"] if row else 0

    # --- Sessions ---

    def session_start(self) -> int:
        return self._ins("INSERT INTO sessions(started_at) VALUES(?)", (utcnow_iso(),))

    def session_end(self, sid: int, summary: str | None = None) -> None:
        self._ex(
            "UPDATE sessions SET ended_at=?, summary=? WHERE id=?",
            (utcnow_iso(), summary, sid),
        )

    def session_current(self) -> dict[str, Any] | None:
        return self._q1(
            "SELECT * FROM sessions WHERE ended_at IS NULL ORDER BY id DESC LIMIT 1"
        )

    def session_list(self, n: int = 10) -> list[dict[str, Any]]:
        return self._q("SELECT * FROM sessions ORDER BY id DESC LIMIT ?", (n,))

    def session_update_handoff(self, sid: int, handoff: dict[str, Any]) -> None:
        self._ex("UPDATE sessions SET handoff=? WHERE id=?", (json.dumps(handoff), sid))

    def session_last_handoff(self) -> dict[str, Any] | None:
        return self._q1(
            "SELECT * FROM sessions WHERE handoff IS NOT NULL ORDER BY id DESC LIMIT 1"
        )

    # --- Decisions ---

    def _resolve_task_slug(self, task_slug: str | None) -> str | None:
        """Validate task_slug exists, return None if not found."""
        if not task_slug:
            return None
        if self.task_get(task_slug):
            return task_slug
        return None

    def decision_add(
        self, text: str, task_slug: str | None = None, rationale: str | None = None
    ) -> int:
        return self._ins(
            "INSERT INTO decisions(decision,task_slug,rationale,created_at) VALUES(?,?,?,?)",
            (text, self._resolve_task_slug(task_slug), rationale, utcnow_iso()),
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
        row = self._q1(
            "SELECT COUNT(*) as cnt FROM decisions WHERE task_slug=?", (slug,)
        )
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
        return self._ins(
            "INSERT INTO memory(type,title,content,tags,task_slug,created_at,updated_at) "
            "VALUES(?,?,?,?,?,?,?)",
            (
                mem_type,
                title,
                content,
                json.dumps(tags) if tags else None,
                self._resolve_task_slug(task_slug),
                now,
                now,
            ),
        )

    def memory_list(
        self, mem_type: str | None = None, n: int = 50
    ) -> list[dict[str, Any]]:
        if mem_type:
            return self._q(
                "SELECT * FROM memory WHERE type=? ORDER BY id DESC LIMIT ?",
                (mem_type, n),
            )
        return self._q("SELECT * FROM memory ORDER BY id DESC LIMIT ?", (n,))

    def memory_get(self, mid: int) -> dict[str, Any] | None:
        return self._q1("SELECT * FROM memory WHERE id=?", (mid,))

    def memory_delete(self, mid: int) -> int:
        return self._ex("DELETE FROM memory WHERE id=?", (mid,))

    def memory_count_for_task(self, slug: str) -> int:
        """Count memories linked to a task."""
        row = self._q1("SELECT COUNT(*) as cnt FROM memory WHERE task_slug=?", (slug,))
        return row["cnt"] if row else 0

    # --- Meta key-value store ---

    def meta_get(self, key: str) -> str | None:
        """Get a value from the meta table. Returns None if key not found."""
        row = self._q1("SELECT value FROM meta WHERE key=?", (key,))
        return row["value"] if row else None

    def meta_set(self, key: str, value: str) -> None:
        """Set a value in the meta table (upsert)."""
        self._ex("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", (key, value))

    def meta_increment(self, key: str) -> None:
        """Atomically increment an integer meta value (init to 1 if missing)."""
        self._ex(
            "INSERT INTO meta(key,value) VALUES(?,'1') "
            "ON CONFLICT(key) DO UPDATE SET value = CAST(value AS INTEGER) + 1",
            (key,),
        )

    # --- Health / diagnostics ---

    def health_info(self) -> dict[str, Any]:
        """Return DB health diagnostics (table count, schema version)."""
        row = self._q1("SELECT COUNT(*) as cnt FROM sqlite_master WHERE type='table'")
        tables = row["cnt"] if row else 0
        schema_ver = int(self.meta_get("schema_version") or "0")
        return {"tables": tables, "schema_version": schema_ver}

    # --- Task logs ---

    def task_log_add(
        self,
        task_slug: str,
        message: str,
        phase: str | None = None,
        diff_stats: str | None = None,
    ) -> int:
        return self._ins(
            "INSERT INTO task_logs(task_slug,message,phase,diff_stats,created_at) "
            "VALUES(?,?,?,?,?)",
            (task_slug, message, phase, diff_stats, utcnow_iso()),
        )

    def task_log_list(
        self,
        task_slug: str,
        phase: str | None = None,
    ) -> list[dict[str, Any]]:
        if phase:
            return self._q(
                "SELECT * FROM task_logs WHERE task_slug=? AND phase=? ORDER BY id",
                (task_slug, phase),
            )
        return self._q(
            "SELECT * FROM task_logs WHERE task_slug=? ORDER BY id", (task_slug,)
        )

    # --- Events ---

    def event_add(
        self,
        entity_type: str,
        entity_id: str,
        action: str,
        details: str | None = None,
        actor: str | None = None,
    ) -> int:
        """Add an audit event."""
        return self._ins(
            "INSERT INTO events(entity_type,entity_id,action,details,actor,created_at) VALUES(?,?,?,?,?,?)",
            (entity_type, entity_id, action, details, actor, utcnow_iso()),
        )
