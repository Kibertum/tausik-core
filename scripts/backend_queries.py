"""TAUSIK backend queries -- complex aggregations and search.

Separated from project_backend.py to keep CRUD layer clean.
These are mixed into SQLiteBackend via BackendQueriesMixin.

v14b-filesize-debt-paydown: usage_events/session_usage_metrics methods extracted
to backend_queries_usage.py (BackendQueriesUsageMixin). BackendQueriesMixin
inherits from it so the public surface on SQLiteBackend is unchanged.
"""

from __future__ import annotations

import re
from typing import Any

from backend_queries_fts import BackendQueriesFtsMixin
from backend_queries_metrics import BackendQueriesMetricsMixin
from backend_queries_usage import BackendQueriesUsageMixin

_FTS5_TOKEN_SPECIAL_RE = re.compile(r"[\.\-/@#]")


def _sanitize_fts5(query: str) -> str:
    """Sanitize ``query`` for FTS5 MATCH.

    Three things happen:
    1. Quoted phrases (``"foo bar"``) are extracted and re-emitted as
       phrase tokens.
    2. Operator characters (``"``, ``(``, ``)``, ``*``, ``:``, ``^``) and
       the FTS5 boolean/proximity keywords (``AND``, ``OR``, ``NOT``,
       ``NEAR``) are stripped from the unquoted remainder.
    3. Each leftover bare token is inspected. Tokens that contain a
       column-separator (``.``), hyphen (``-``), slash, ``@`` or ``#``
       — anything that would make FTS5 raise ``syntax error near "..."``
       — are wrapped in their own phrase quotes. The default
       ``unicode61`` / ``simple`` tokenizer then splits the inner string
       on those same characters so the practical effect is a phrase
       search across the resulting word sequence (``tausik.tech`` →
       phrase ``"tausik tech"``).
    """
    phrases: list[str] = []

    def _extract_phrase(m: re.Match) -> str:
        text = m.group(1).strip()
        if text:
            phrases.append(f'"{text}"')
        return " "

    # Extract "quoted phrases" before stripping
    remaining = re.sub(r'"([^"]*)"', _extract_phrase, query)
    # Strip FTS5 operators, special chars, AND leftover unpaired quotes
    remaining = re.sub(r'["\(\)\*\:\^]', " ", remaining)
    # Remove FTS5 boolean/proximity operators as whole words
    remaining = re.sub(r"\b(AND|OR|NOT|NEAR)\b", " ", remaining)
    # Per-token: wrap any token with column-separator-like chars in quotes
    # so FTS5 treats it as a phrase instead of trying to parse syntax.
    wrapped: list[str] = []
    for tok in remaining.split():
        if _FTS5_TOKEN_SPECIAL_RE.search(tok):
            clean = _FTS5_TOKEN_SPECIAL_RE.sub(" ", tok).strip()
            if clean:
                wrapped.append(f'"{clean}"')
        else:
            wrapped.append(tok)
    parts = wrapped + phrases
    return " ".join(parts) if parts else ""


class BackendQueriesMixin(
    BackendQueriesUsageMixin, BackendQueriesMetricsMixin, BackendQueriesFtsMixin
):
    """Complex queries: search, metrics, roadmap, events."""

    # --- Search ---

    def memory_search(
        self,
        query: str,
        n: int = 20,
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        q = _sanitize_fts5(query)
        if not q:
            return []
        sql = (
            "SELECT m.*, snippet(fts_memory, 1, '>>>', '<<<', '...', 32) AS _snippet "
            "FROM memory m JOIN fts_memory f ON m.id=f.rowid "
            "WHERE fts_memory MATCH ?"
        )
        params: list[Any] = [q]
        if not include_archived:
            sql += " AND m.archived_at IS NULL"
        sql += " ORDER BY bm25(fts_memory, 10.0, 1.0, 3.0) LIMIT ?"
        params.append(n)
        return self._q(sql, tuple(params))

    def memory_archive_apply(self, before_iso: str) -> int:
        """Stamp ``archived_at`` on memory rows older than ``before_iso``.

        Idempotent: rows with non-null ``archived_at`` are skipped. Returns
        the number of newly archived rows.
        """
        from tausik_utils import utcnow_iso

        now = utcnow_iso()
        cur = self._conn.execute(
            "UPDATE memory SET archived_at=?, updated_at=? "
            "WHERE created_at < ? AND archived_at IS NULL",
            (now, now, before_iso),
        )
        self._conn.commit()
        return cur.rowcount or 0

    def memory_archive_candidates(self, before_iso: str) -> list[dict[str, Any]]:
        """Memory rows older than ``before_iso`` and not yet archived."""
        return self._q(
            "SELECT id, type, title, created_at FROM memory "
            "WHERE created_at < ? AND archived_at IS NULL "
            "ORDER BY created_at ASC",
            (before_iso,),
        )

    def search_all(
        self,
        query: str,
        scope: str = "all",
        n: int = 20,
    ) -> dict[str, list[dict[str, Any]]]:
        q = _sanitize_fts5(query)
        results: dict[str, list[dict[str, Any]]] = {}
        if not q:
            return results
        if scope in ("all", "tasks"):
            results["tasks"] = self._q(
                "SELECT t.*, snippet(fts_tasks, 1, '>>>', '<<<', '...', 32) AS _snippet "
                "FROM tasks t JOIN fts_tasks f ON t.id=f.rowid "
                "WHERE fts_tasks MATCH ? ORDER BY bm25(fts_tasks, 5.0, 10.0, 3.0, 1.0, 1.0) LIMIT ?",
                (q, n),
            )
        if scope in ("all", "memory"):
            # Pass pre-sanitized q directly to _q, avoid double-sanitization
            results["memory"] = self._q(
                "SELECT m.*, snippet(fts_memory, 1, '>>>', '<<<', '...', 32) AS _snippet "
                "FROM memory m JOIN fts_memory f ON m.id=f.rowid "
                "WHERE fts_memory MATCH ? ORDER BY bm25(fts_memory, 10.0, 1.0, 3.0) LIMIT ?",
                (q, n),
            )
        if scope in ("all", "decisions"):
            results["decisions"] = self._q(
                "SELECT d.*, snippet(fts_decisions, 0, '>>>', '<<<', '...', 32) AS _snippet "
                "FROM decisions d JOIN fts_decisions f ON d.id=f.rowid "
                "WHERE fts_decisions MATCH ? ORDER BY bm25(fts_decisions, 10.0, 1.0) LIMIT ?",
                (q, n),
            )
        return results

    # FTS Maintenance (fts_optimize, fts_maybe_optimize) moved to
    # backend_queries_fts.BackendQueriesFtsMixin (filesize cap). Inherited below.

    # Status & Metrics (get_status_data, get_metrics, session_capacity_summary)
    # moved to backend_queries_metrics.BackendQueriesMetricsMixin
    # (filesize-debt-paydown). Inherited via the class declaration above.

    # --- Roadmap ---

    def get_roadmap_data(self, include_done: bool = False) -> list[dict[str, Any]]:
        task_filter = "" if include_done else "WHERE t.status != 'done'"
        all_tasks = self._q(
            "SELECT t.*, s.slug AS story_slug, s.title AS story_title, "
            "s.status AS story_status, e.slug AS epic_slug, e.title AS epic_title, "
            "e.status AS epic_status "
            "FROM tasks t "
            "LEFT JOIN stories s ON t.story_id=s.id "
            "LEFT JOIN epics e ON s.epic_id=e.id "
            f"{task_filter} "
            "ORDER BY e.created_at, s.created_at, t.created_at"
        )
        epics = {e["slug"]: e for e in self.epic_list()}
        stories_by_epic: dict[str, list[dict[str, Any]]] = {}
        for s in self._q(
            "SELECT s.*, e.slug AS epic_slug FROM stories s "
            "JOIN epics e ON s.epic_id=e.id ORDER BY s.created_at"
        ):
            stories_by_epic.setdefault(s["epic_slug"], []).append(s)

        tree: dict[str, dict[str, Any]] = {}
        task_map: dict[str, list[dict[str, Any]]] = {}

        for t in all_tasks:
            ss = t.get("story_slug")
            if ss:
                task_map.setdefault(ss, []).append(t)

        for epic_slug, epic in epics.items():
            if not include_done and epic["status"] == "done":
                continue
            epic_data: dict[str, Any] = {**epic, "stories": []}
            for story in stories_by_epic.get(epic_slug, []):
                if not include_done and story["status"] == "done":
                    continue
                tasks = task_map.get(story["slug"], [])
                if not include_done:
                    tasks = [t for t in tasks if t["status"] != "done"]
                epic_data["stories"].append({**story, "tasks": tasks})
            tree[epic_slug] = epic_data

        return list(tree.values())

    # --- Graph Memory ---

    def graph_related(
        self,
        node_type: str,
        node_id: int,
        max_hops: int = 2,
        include_invalid: bool = False,
    ) -> list[dict[str, Any]]:
        """Find related nodes via recursive CTE graph traversal (1-N hops)."""
        max_hops = min(max_hops, 3)  # cap depth to prevent runaway
        valid_filter = "" if include_invalid else "AND e.valid_to IS NULL"
        sql = f"""
        WITH RECURSIVE reachable(node_type, node_id, depth, via_edge, via_relation) AS (
            -- seed: direct neighbors
            SELECT e.target_type, e.target_id, 1, e.id, e.relation
            FROM memory_edges e
            WHERE e.source_type=? AND e.source_id=? {valid_filter}
            UNION
            SELECT e.source_type, e.source_id, 1, e.id, e.relation
            FROM memory_edges e
            WHERE e.target_type=? AND e.target_id=? {valid_filter}
            UNION ALL
            -- recurse: neighbors of neighbors
            SELECT e.target_type, e.target_id, r.depth+1, e.id, e.relation
            FROM reachable r
            JOIN memory_edges e ON e.source_type=r.node_type AND e.source_id=r.node_id
                {valid_filter}
            WHERE r.depth < ? AND NOT (e.target_type=? AND e.target_id=?)
            UNION ALL
            SELECT e.source_type, e.source_id, r.depth+1, e.id, e.relation
            FROM reachable r
            JOIN memory_edges e ON e.target_type=r.node_type AND e.target_id=r.node_id
                {valid_filter}
            WHERE r.depth < ? AND NOT (e.source_type=? AND e.source_id=?)
        )
        SELECT DISTINCT node_type, node_id, MIN(depth) as depth,
               via_edge, via_relation
        FROM reachable
        WHERE NOT (node_type=? AND node_id=?)
        GROUP BY node_type, node_id
        ORDER BY depth, node_type, node_id
        """
        params = (
            node_type,
            node_id,
            node_type,
            node_id,
            max_hops,
            node_type,
            node_id,
            max_hops,
            node_type,
            node_id,
            node_type,
            node_id,
        )
        return self._q(sql, params)

    def graph_resolve_nodes(self, node_refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Resolve node references to full records (batched to avoid N+1)."""
        if not node_refs:
            return []
        # Batch by type
        memory_ids = [ref["node_id"] for ref in node_refs if ref["node_type"] == "memory"]
        decision_ids = [ref["node_id"] for ref in node_refs if ref["node_type"] == "decision"]
        records: dict[tuple[str, int], dict[str, Any]] = {}
        if memory_ids:
            placeholders = ",".join("?" * len(memory_ids))
            for row in self._q(
                f"SELECT * FROM memory WHERE id IN ({placeholders})", tuple(memory_ids)
            ):
                records[("memory", row["id"])] = row
        if decision_ids:
            placeholders = ",".join("?" * len(decision_ids))
            for row in self._q(
                f"SELECT * FROM decisions WHERE id IN ({placeholders})",
                tuple(decision_ids),
            ):
                records[("decision", row["id"])] = row
        results = []
        for ref in node_refs:
            key = (ref["node_type"], ref["node_id"])
            if key in records:
                results.append({**ref, "record": records[key]})
        return results

    # --- Events ---

    def events_list(
        self,
        entity_type: str | None = None,
        entity_id: str | None = None,
        n: int = 50,
    ) -> list[dict[str, Any]]:
        """List audit events with optional filters."""
        n = min(n, 1000)
        sql = "SELECT * FROM events WHERE 1=1"
        params: list[Any] = []
        if entity_type:
            sql += " AND entity_type=?"
            params.append(entity_type)
        if entity_id:
            sql += " AND entity_id=?"
            params.append(entity_id)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(n)
        return self._q(sql, tuple(params))

    def task_event_count_in_window(self, slug: str) -> int:
        """Count task lifecycle events within the task's active window.

        Counts rows in `events` where entity_type='task', entity_id=slug,
        and created_at falls between tasks.started_at and a closing bound:
        completed_at if set, otherwise current time. Returns 0 if the task
        has no started_at recorded (cannot define a window).

        Used by task_done to derive a baseline call_actual when a richer
        per-tool counter is unavailable. MED-9 review fix: comparisons
        run through julianday() so the window is robust against ISO-8601
        format drift (microseconds, +00:00 vs Z suffix).
        """
        row = self._q1(
            "SELECT COUNT(*) AS cnt FROM events e "
            "JOIN tasks t ON t.slug = e.entity_id "
            "WHERE e.entity_type='task' AND e.entity_id=? "
            "AND t.started_at IS NOT NULL "
            "AND julianday(e.created_at) >= julianday(t.started_at) "
            "AND julianday(e.created_at) <= "
            "    julianday(COALESCE(t.completed_at, 'now'))",
            (slug,),
        )
        return int(row["cnt"]) if row else 0
