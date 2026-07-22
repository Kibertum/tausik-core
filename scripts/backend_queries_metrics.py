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
        from backend_defect_escape import defect_escape_metrics
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
            "gate_activity": self.gate_activity_summary(),
            # l26-bypass-telemetry: how many times supervision was switched off.
            "supervision_bypasses": self.supervision_bypasses_summary(),
            # l26-complexity-self-declared: supervision that WORKED (detections,
            # not bypasses) — e.g. an understated complexity caught at close.
            "supervision_detections": self.supervision_detections_summary(),
            # hook-fail-open-db-error-telemetry: supervision that was SILENTLY
            # skipped (a guard failed open on a DB error) — neither intentional
            # bypass nor working detection.
            "supervision_degradations": self.supervision_degradations_summary(),
            # l26-defect-escape-rate: der above is the crude aggregate; this is the
            # principled, sliced outcome metric (escape rate by the escaped task's
            # own attributes) + a risk_score backtest.
            "defect_escape": defect_escape_metrics(self._q),  # type: ignore[attr-defined]
        }

    def gate_activity_summary(self) -> dict[str, Any]:
        """Per-gate run/failure counts — how well the enforcement itself works.

        Configured-but-never-run gates are listed with runs=0 rather than left
        out, so "this gate has never once fired" is visible instead of being
        rendered as silence (convention #226). Gate config is best-effort: if
        it cannot be read we still report what the table holds, but the
        never-fired list is then necessarily incomplete and says so by being
        derived only from rows that exist.
        """
        from gate_run_record import gate_activity

        known: list[str] = []
        try:
            from project_config import get_gates_for_trigger

            for trigger in ("verify", "task-done"):
                known.extend(g["name"] for g in get_gates_for_trigger(trigger))
        except Exception:  # noqa: BLE001 — metrics are read-only; config trouble must not blank them
            known = []
        return gate_activity(self._conn, sorted(set(known)))  # type: ignore[attr-defined]

    def _supervision_by_action(self, *, category: str) -> dict[str, Any]:
        """Aggregate entity_type='supervision' events by action, in ONE of three
        MUTUALLY-EXCLUSIVE categories:

          - 'bypass'      action LIKE 'bypass_%'    — INTENTIONAL weakening
                          (skip_hooks, auto_verify, gates_disable, ...).
          - 'degradation' action LIKE 'fail_open_%' — SILENT fail-open: a guard
                          could not read the DB and let the edit through. Not on
                          purpose, but unenforced all the same.
          - 'detection'  everything else           — supervision that WORKED
                          (e.g. complexity_understated caught at close).

        The three mean opposite things and must NEVER be summed. 'detection' is
        the residual bucket, so every new category MUST also be excluded here —
        otherwise degradations masquerade as detections, the inverse of the
        truth (the exact failure the l26 review flagged for bypass vs detection).
        """
        # The '_' in 'bypass_%' / 'fail_open_%' is a LIKE single-char wildcard, so
        # an ESCAPE is required for it to mean a LITERAL underscore — without it
        # 'bypassX...' for any X would match, and a future action like
        # 'bypassAuto_verify' could land in the wrong bucket, breaking the
        # MUTUALLY-EXCLUSIVE guarantee (s128 review MEDIUM-2).
        predicates = {
            "bypass": r"action LIKE 'bypass\_%' ESCAPE '\'",
            "degradation": r"action LIKE 'fail\_open\_%' ESCAPE '\'",
            "detection": (
                r"action NOT LIKE 'bypass\_%' ESCAPE '\' "
                r"AND action NOT LIKE 'fail\_open\_%' ESCAPE '\'"
            ),
        }
        try:
            where = predicates[category]
        except KeyError:
            raise ValueError(f"unknown supervision category: {category!r}") from None
        rows = self._q(  # type: ignore[attr-defined]
            f"SELECT action, COUNT(*) as cnt FROM events "
            f"WHERE entity_type='supervision' AND {where} "
            f"GROUP BY action ORDER BY cnt DESC"
        )
        by_action = {r["action"]: r["cnt"] for r in rows}
        return {"total": sum(by_action.values()), "by_action": by_action}

    def supervision_bypasses_summary(self) -> dict[str, Any]:
        """l26-bypass-telemetry: how many times supervision was bypassed/weakened.

        Counts ONLY action LIKE 'bypass_%' (skip_hooks, skip_push_hook,
        auto_verify, l3_block_downgrade, scope_hard_gate, gates_disable). A
        non-zero total means enforcement was switched off that many times — the
        metric exists so that claim is falsifiable rather than silent (release-1.8
        thesis). Detections (supervision that WORKED) and degradations (silent
        fail-open) are counted separately, never conflated here.
        """
        return self._supervision_by_action(category="bypass")

    def supervision_degradations_summary(self) -> dict[str, Any]:
        """hook-fail-open-db-error-telemetry: how many times a guard silently
        failed OPEN (action LIKE 'fail_open_%', e.g. fail_open_db_error).

        Distinct from a bypass — nobody switched it off — and from a detection —
        supervision did NOT work, it was skipped because a DB error let the edit
        through. A non-zero total means enforcement was transiently unenforced
        that many times; kept apart so it is never misread as either.
        """
        return self._supervision_by_action(category="degradation")

    def supervision_detections_summary(self) -> dict[str, Any]:
        """l26-complexity-self-declared: supervision events that are DETECTIONS
        — supervision that WORKED (e.g. complexity_understated). Excludes both
        bypass_% (intentional weakening) and fail_open_% (silent degradation) so
        the metrics reader never misreads 'the detector caught N declarations'
        as 'enforcement was weakened/skipped N times'.
        """
        return self._supervision_by_action(category="detection")

    def session_capacity_summary(self, capacity: int) -> dict[str, Any]:
        from backend_tier_metrics import session_capacity_summary as _s

        return _s(self._q, self._q1, capacity)  # type: ignore[attr-defined]
