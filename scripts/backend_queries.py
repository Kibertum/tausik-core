"""TAUSIK backend queries -- complex aggregations and search.

Separated from project_backend.py to keep CRUD layer clean.
These are mixed into SQLiteBackend via BackendQueriesMixin.
"""

from __future__ import annotations

import re
from typing import Any


def _sanitize_fts5(query: str) -> str:
    """Sanitize query for FTS5 MATCH -- preserve phrases in quotes, escape the rest."""
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
    remaining = re.sub(r"\s+", " ", remaining).strip()
    parts = ([remaining] if remaining else []) + phrases
    return " ".join(parts) if parts else ""


class BackendQueriesMixin:
    """Complex queries: search, metrics, roadmap, events."""

    # --- Search ---

    def memory_search(self, query: str, n: int = 20) -> list[dict[str, Any]]:
        q = _sanitize_fts5(query)
        if not q:
            return []
        return self._q(
            "SELECT m.*, snippet(fts_memory, 1, '>>>', '<<<', '...', 32) AS _snippet "
            "FROM memory m JOIN fts_memory f ON m.id=f.rowid "
            "WHERE fts_memory MATCH ? ORDER BY bm25(fts_memory, 10.0, 1.0, 3.0) LIMIT ?",
            (q, n),
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

    # --- FTS Maintenance ---

    _FTS_TABLES = ("fts_tasks", "fts_memory", "fts_decisions")

    def fts_optimize(self) -> dict[str, str]:
        """Run FTS5 optimize on all full-text indexes."""
        results: dict[str, str] = {}
        for table in self._FTS_TABLES:
            try:
                self._ex(f"INSERT INTO {table}({table}) VALUES('optimize')")
                results[table] = "ok"
            except Exception as e:
                results[table] = str(e)
        return results

    # --- Status & Metrics ---

    def get_status_data(self) -> dict[str, Any]:
        tasks = self._q("SELECT status, COUNT(*) as cnt FROM tasks GROUP BY status")
        return {
            "task_counts": {r["status"]: r["cnt"] for r in tasks},
            "epics": self.epic_list(),
            "session": self.session_current(),
        }

    def get_metrics(self) -> dict[str, Any]:
        """Aggregate project metrics: SENAR mandatory + recommended."""
        task_counts = {
            r["status"]: r["cnt"]
            for r in self._q(
                "SELECT status, COUNT(*) as cnt FROM tasks GROUP BY status"
            )
        }
        total = sum(task_counts.values())
        done = task_counts.get("done", 0)

        combined = (
            self._q1(
                "SELECT "
                "  (SELECT COUNT(*) FROM tasks WHERE status='done' AND attempts=1) as first_pass, "
                "  (SELECT COUNT(DISTINCT defect_of) FROM tasks WHERE defect_of IS NOT NULL) as defect_count, "
                "  (SELECT COUNT(*) FROM tasks WHERE status='done' AND defect_of IS NULL) as non_defect_done, "
                "  (SELECT COUNT(*) FROM memory) as mem_count, "
                "  (SELECT COUNT(*) FROM memory WHERE type='dead_end') as dead_end_count, "
                "  (SELECT AVG((julianday(completed_at) - julianday(started_at)) * 24) "
                "   FROM tasks WHERE status='done' AND started_at IS NOT NULL AND completed_at IS NOT NULL) as cycle_hours, "
                "  (SELECT AVG((julianday(completed_at) - julianday(created_at)) * 24) "
                "   FROM tasks WHERE status='done' AND completed_at IS NOT NULL) as lead_hours"
            )
            or {}
        )

        avg_hours = (
            round(combined["cycle_hours"], 1)
            if combined.get("cycle_hours") is not None
            else None
        )
        lead_hours = (
            round(combined["lead_hours"], 1)
            if combined.get("lead_hours") is not None
            else None
        )
        first_pass = combined.get("first_pass", 0)
        fpsr = round(first_pass / done * 100, 1) if done else 0
        defect_count = combined.get("defect_count", 0)
        non_defect_done = combined.get("non_defect_done", 0)
        der = round(defect_count / non_defect_done * 100, 1) if non_defect_done else 0
        mem_count = combined.get("mem_count", 0)
        kcr = round(mem_count / done, 2) if done else 0
        dead_end_count = combined.get("dead_end_count", 0)
        dead_end_rate = round(dead_end_count / total * 100, 1) if total else 0

        # Query 2: Session stats
        session_stats = self._q1(
            "SELECT COUNT(*) as total, "
            "SUM((julianday(COALESCE(ended_at, datetime('now'))) - julianday(started_at)) * 24) as hours "
            "FROM sessions"
        )
        sessions_total = session_stats["total"] if session_stats else 0
        throughput = round(done / sessions_total, 2) if sessions_total else 0

        # Query 3: Cost per Task by complexity
        cost_by_complexity = {}
        for row in self._q(
            "SELECT complexity, COUNT(*) as cnt, "
            "AVG((julianday(completed_at) - julianday(started_at)) * 24) as avg_hours "
            "FROM tasks WHERE status='done' AND started_at IS NOT NULL AND completed_at IS NOT NULL "
            "GROUP BY complexity"
        ):
            c = row["complexity"] or "unknown"
            cost_by_complexity[c] = {
                "count": row["cnt"],
                "avg_hours": round(row["avg_hours"], 2) if row["avg_hours"] else 0,
            }

        # Query 4: Story counts
        story_counts = {
            r["status"]: r["cnt"]
            for r in self._q(
                "SELECT status, COUNT(*) as cnt FROM stories GROUP BY status"
            )
        }

        from backend_tier_metrics import calibration_drift, per_tier_metrics

        return {
            "tasks": task_counts,
            "tasks_total": total,
            "tasks_done": done,
            "completion_pct": round(done / total * 100, 1) if total else 0,
            "throughput": throughput,
            "lead_time_hours": lead_hours,
            "fpsr": fpsr,
            "der": der,
            "cycle_time_hours": avg_hours,
            "knowledge_capture_rate": kcr,
            "dead_end_rate": dead_end_rate,
            "dead_end_count": dead_end_count,
            "cost_per_task": cost_by_complexity,
            "per_tier": per_tier_metrics(self._q),
            "calibration_drift": calibration_drift(self._q),
            "avg_task_hours": avg_hours,
            "sessions_total": sessions_total,
            "session_hours": round(session_stats["hours"], 1)
            if session_stats and session_stats["hours"]
            else 0,
            "stories": story_counts,
        }

    def session_capacity_summary(self, capacity: int) -> dict[str, Any]:
        from backend_tier_metrics import session_capacity_summary as _s

        return _s(self._q, self._q1, capacity)

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

    def graph_resolve_nodes(
        self, node_refs: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Resolve node references to full records (batched to avoid N+1)."""
        if not node_refs:
            return []
        # Batch by type
        memory_ids = [
            ref["node_id"] for ref in node_refs if ref["node_type"] == "memory"
        ]
        decision_ids = [
            ref["node_id"] for ref in node_refs if ref["node_type"] == "decision"
        ]
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
        per-tool counter is unavailable.
        """
        row = self._q1(
            "SELECT COUNT(*) AS cnt FROM events e "
            "JOIN tasks t ON t.slug = e.entity_id "
            "WHERE e.entity_type='task' AND e.entity_id=? "
            "AND t.started_at IS NOT NULL "
            "AND e.created_at >= t.started_at "
            "AND e.created_at <= COALESCE(t.completed_at, "
            "    strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))",
            (slug,),
        )
        return int(row["cnt"]) if row else 0
