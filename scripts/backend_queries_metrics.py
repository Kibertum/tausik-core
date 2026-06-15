"""TAUSIK backend metrics queries — status + SENAR delivery metrics.

Extracted from backend_queries.py for filesize compliance. Mixed into
SQLiteBackend via BackendQueriesMixin, which inherits this mixin, so the public
surface (``backend.get_metrics()`` etc.) is unchanged. Pure code move — the SQL
and aggregation logic is identical to the previous in-place implementation.
"""

from __future__ import annotations

from typing import Any


def _session_hours(stats: dict | None) -> float:
    return round(stats["hours"], 1) if stats and stats.get("hours") else 0


class BackendQueriesMetricsMixin:
    """Status snapshot + SENAR delivery metrics (FPSR/DER/cycle/lead/throughput)."""

    def get_status_data(self) -> dict[str, Any]:
        tasks = self._q("SELECT status, COUNT(*) as cnt FROM tasks GROUP BY status")  # type: ignore[attr-defined]
        return {
            "task_counts": {r["status"]: r["cnt"] for r in tasks},
            "epics": self.epic_list(),  # type: ignore[attr-defined]
            "session": self.session_current(),  # type: ignore[attr-defined]
        }

    def get_metrics(self) -> dict[str, Any]:
        task_counts = {
            r["status"]: r["cnt"]
            for r in self._q("SELECT status, COUNT(*) as cnt FROM tasks GROUP BY status")  # type: ignore[attr-defined]
        }
        total = sum(task_counts.values())
        done = task_counts.get("done", 0)

        combined = (
            self._q1(  # type: ignore[attr-defined]
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
            round(combined["cycle_hours"], 1) if combined.get("cycle_hours") is not None else None
        )
        lead_hours = (
            round(combined["lead_hours"], 1) if combined.get("lead_hours") is not None else None
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
        session_stats = self._q1(  # type: ignore[attr-defined]
            "SELECT COUNT(*) as total, "
            "SUM((julianday(COALESCE(ended_at, datetime('now'))) - julianday(started_at)) * 24) as hours "
            "FROM sessions"
        )
        sessions_total = session_stats["total"] if session_stats else 0
        throughput = round(done / sessions_total, 2) if sessions_total else 0

        # Query 3: Cost per Task by complexity
        cost_by_complexity = {}
        for row in self._q(  # type: ignore[attr-defined]
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

        story_counts = {
            r["status"]: r["cnt"]
            for r in self._q("SELECT status, COUNT(*) as cnt FROM stories GROUP BY status")  # type: ignore[attr-defined]
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
            "per_tier": per_tier_metrics(self._q),  # type: ignore[attr-defined]
            "calibration_drift": calibration_drift(self._q),  # type: ignore[attr-defined]
            "avg_task_hours": avg_hours,
            "sessions_total": sessions_total,
            "session_hours": _session_hours(session_stats),
            "stories": story_counts,
            "session_usage": self.session_usage_summary(),  # type: ignore[attr-defined]
        }

    def session_capacity_summary(self, capacity: int) -> dict[str, Any]:
        from backend_tier_metrics import session_capacity_summary as _s

        return _s(self._q, self._q1, capacity)  # type: ignore[attr-defined]
