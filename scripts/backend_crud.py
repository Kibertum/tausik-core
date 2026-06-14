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


# Tool-call budget thresholds for agent-native task tiers (SENAR sizing).
# Inclusive upper bound per tier; budgets above 'deep' threshold cap at 'deep'.
_TIER_THRESHOLDS: tuple[tuple[int, str], ...] = (
    (10, "trivial"),
    (25, "light"),
    (60, "moderate"),
    (150, "substantial"),
    (400, "deep"),
)


def derive_tier_from_budget(budget: int | None) -> str | None:
    """Map a call-budget integer to a tier label.

    Returns None for None or 0 (no plan recorded). Negative budgets are
    rejected upstream — this helper assumes a normalised, non-negative
    int. Budgets exceeding the 'deep' threshold are capped at 'deep'.
    """
    if budget is None or budget <= 0:
        return None
    for upper, label in _TIER_THRESHOLDS:
        if budget <= upper:
            return label
    return _TIER_THRESHOLDS[-1][1]


class BackendCrudMixin:
    """Session, decision, memory, meta, and events CRUD. Mixed into SQLiteBackend."""

    # Type stubs for mixin
    if TYPE_CHECKING:

        def _q(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]: ...
        def _q1(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None: ...
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

    # --- Reviews (SENAR Rule 10.15: track L1/L2/L3 runs) ---

    def review_record(
        self,
        task_slug: str,
        run_type: str,
        critical_findings: int = 0,
        warnings: int = 0,
        notes: str | None = None,
    ) -> int:
        return self._ins(
            "INSERT INTO reviews(task_slug, run_type, critical_findings, "
            "warnings, run_at, notes) VALUES(?,?,?,?,?,?)",
            (task_slug, run_type, int(critical_findings), int(warnings), utcnow_iso(), notes),
        )

    def review_list(
        self, task_slug: str | None = None, run_type: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        sql = "SELECT * FROM reviews WHERE 1=1"
        params: list[Any] = []
        if task_slug:
            sql += " AND task_slug=?"
            params.append(task_slug)
        if run_type:
            sql += " AND run_type=?"
            params.append(run_type)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        return self._q(sql, tuple(params))

    def review_metrics(self) -> dict[str, Any]:
        """ADR (Adversarial Defect Rate) = critical_findings / L3_reviewed_tasks * 100."""
        row = self._q1(
            "SELECT COUNT(DISTINCT task_slug) AS l3_tasks, "
            "COALESCE(SUM(critical_findings),0) AS l3_critical "
            "FROM reviews WHERE run_type='L3'"
        )
        l3_tasks = (row or {}).get("l3_tasks") or 0
        l3_critical = (row or {}).get("l3_critical") or 0
        adr = (l3_critical / l3_tasks * 100.0) if l3_tasks else 0.0
        return {
            "l3_reviewed_tasks": int(l3_tasks),
            "l3_critical_findings": int(l3_critical),
            "adr_pct": round(adr, 2),
        }

    # --- Brain usage events (v22, r14-brain-metrics) — see backend_crud_brain ---

    def brain_event_record(
        self,
        event_type: str,
        query: str | None = None,
        result_count: int = 0,
        session_id: int | None = None,
    ) -> int:
        from backend_crud_brain import brain_event_record as _impl

        return _impl(self, event_type, query, result_count, session_id)

    def brain_event_metrics(self, session_id: int | None = None) -> dict[str, Any]:
        from backend_crud_brain import brain_event_metrics as _impl

        return _impl(self, session_id)

    # --- Sessions ---

    def session_start(self) -> int:
        # SENAR Rule 10.13: capture the agent model on session creation so
        # FPSR / cost / throughput can be re-calibrated when the user
        # switches between Sonnet / Opus / GPT / Composer mid-project.
        # Source priority: explicit env vars > generic agent env > unset.
        # `TAUSIK_AGENT_MODEL` covers the typical "I want to override"
        # case; the others are read-only signals from popular hosts.
        import os as _os

        model_id = (
            _os.environ.get("TAUSIK_AGENT_MODEL")
            or _os.environ.get("CLAUDE_MODEL")
            or _os.environ.get("ANTHROPIC_MODEL")
            or _os.environ.get("OPENAI_MODEL")
            or _os.environ.get("CURSOR_MODEL")
            or None
        )
        model_version = _os.environ.get("TAUSIK_AGENT_MODEL_VERSION") or None
        return self._ins(
            "INSERT INTO sessions(started_at, model_id, model_version) VALUES(?, ?, ?)",
            (utcnow_iso(), model_id, model_version),
        )

    def session_end(self, sid: int, summary: str | None = None) -> None:
        self._ex(
            "UPDATE sessions SET ended_at=?, summary=? WHERE id=?",
            (utcnow_iso(), summary, sid),
        )

    def session_current(self) -> dict[str, Any] | None:
        return self._q1("SELECT * FROM sessions WHERE ended_at IS NULL ORDER BY id DESC LIMIT 1")

    def session_list(self, n: int = 10) -> list[dict[str, Any]]:
        return self._q("SELECT * FROM sessions ORDER BY id DESC LIMIT ?", (n,))

    def session_update_handoff(self, sid: int, handoff: dict[str, Any]) -> None:
        self._ex("UPDATE sessions SET handoff=? WHERE id=?", (json.dumps(handoff), sid))

    def session_last_handoff(self) -> dict[str, Any] | None:
        return self._q1("SELECT * FROM sessions WHERE handoff IS NOT NULL ORDER BY id DESC LIMIT 1")

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

    def meta_delete(self, key: str) -> None:
        """Remove a key from the meta table (no-op if absent)."""
        self._ex("DELETE FROM meta WHERE key=?", (key,))

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
        return self._q("SELECT * FROM task_logs WHERE task_slug=? ORDER BY id", (task_slug,))

    def task_log_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        """Most recent task_logs across ALL tasks — feeds memory_compact aggregation."""
        return self._q("SELECT * FROM task_logs ORDER BY id DESC LIMIT ?", (int(limit),))

    # --- Agent-native planning units (call budget / actual / tier) ---

    def task_set_call_budget(self, slug: str, budget: int | None) -> bool:
        """Set planned tool-call budget for a task; auto-derives tier.

        budget=None clears both call_budget and tier. Negative budgets rejected.
        Returns True if a row was updated, False if slug not found.
        """
        if budget is not None and budget < 0:
            raise ValueError(f"call_budget must be >=0 or None, got {budget}")
        tier = derive_tier_from_budget(budget)
        rows = self._ex(
            "UPDATE tasks SET call_budget=?, tier=?, updated_at=? WHERE slug=?",
            (budget, tier, utcnow_iso(), slug),
        )
        return rows > 0

    def task_set_call_actual(self, slug: str, actual: int | None) -> bool:
        """Record observed tool-call count for a task. Does not touch tier."""
        if actual is not None and actual < 0:
            raise ValueError(f"call_actual must be >=0 or None, got {actual}")
        rows = self._ex(
            "UPDATE tasks SET call_actual=?, updated_at=? WHERE slug=?",
            (actual, utcnow_iso(), slug),
        )
        return rows > 0

    def _task_set_numeric_field(self, slug: str, column: str, value: float | int | None) -> bool:
        """Shared writer for cost/token budget+actual columns (v14c)."""
        if value is not None and value < 0:
            raise ValueError(f"{column} must be >=0 or None, got {value}")
        rows = self._ex(
            f"UPDATE tasks SET {column}=?, updated_at=? WHERE slug=?",
            (value, utcnow_iso(), slug),
        )
        return rows > 0

    def task_set_cost_budget(self, slug: str, budget_usd: float | None) -> bool:
        v = float(budget_usd) if budget_usd is not None else None
        return self._task_set_numeric_field(slug, "cost_budget_usd", v)

    def task_set_cost_actual(self, slug: str, actual_usd: float | None) -> bool:
        v = float(actual_usd) if actual_usd is not None else None
        return self._task_set_numeric_field(slug, "cost_actual_usd", v)

    def task_set_token_budget(self, slug: str, tokens: int | None) -> bool:
        return self._task_set_numeric_field(slug, "token_budget", tokens)

    def task_set_tokens_actual(self, slug: str, tokens: int | None) -> bool:
        return self._task_set_numeric_field(slug, "tokens_actual", tokens)

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
