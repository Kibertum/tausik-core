"""TAUSIK backend queries — usage_events / session_usage_metrics aggregations.

Extracted from backend_queries.py for filesize compliance
(v14b-filesize-debt-paydown). Mixed into SQLiteBackend via
BackendQueriesMixin (which inherits from BackendQueriesUsageMixin).
"""

from __future__ import annotations

from typing import Any

from tausik_utils import utcnow_iso


class BackendQueriesUsageMixin:
    """Token-usage write/read aggregations.

    Methods are mixed into SQLiteBackend through BackendQueriesMixin and rely
    on the base class for `_ex` / `_q` / `_q1` query helpers.
    """

    def usage_event_append(
        self,
        session_id: int,
        task_slug: str | None,
        tokens_input: int,
        tokens_output: int,
        tokens_total: int,
        cost_usd: float,
        tool_calls: int,
        model_id: str | None,
        source: str,
        recorded_at: str | None = None,
        tool_name: str | None = None,
    ) -> int:
        """Insert one usage_events row; return new row id."""
        when = recorded_at or utcnow_iso()
        slug = (task_slug or "").strip() or None
        ti, to, tt = int(tokens_input), int(tokens_output), int(tokens_total)
        tc = int(tool_calls)
        cu = float(cost_usd)
        mid = (model_id or "").strip() or None
        tn = (tool_name or "").strip() or None
        return int(
            self._ex(  # type: ignore[attr-defined]
                "INSERT INTO usage_events("
                "session_id,task_slug,model_id,tokens_input,tokens_output,tokens_total,"
                "cost_usd,tool_calls,source,recorded_at,tool_name"
                ") VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    int(session_id),
                    slug,
                    mid,
                    ti,
                    to,
                    tt,
                    cu,
                    tc,
                    source,
                    when,
                    tn,
                ),
            )
        )

    def session_usage_record(
        self,
        session_id: int,
        tokens_input: int,
        tokens_output: int,
        tokens_total: int,
        cost_usd: float,
        tool_calls: int = 0,
        model: str | None = None,
    ) -> None:
        """Record cumulative session totals.

        Writes to two tables intentionally:

        - ``session_usage_metrics``: one row per session_id (UPSERT). Authoritative
          source for "what did this session cost in total".
        - ``usage_events``: a NULL-task-slug row tagged ``source='session_record'``.
          This is a denormalized copy for unified event-stream analytics.

        DOUBLE-COUNT HAZARD (v14b-defect-usage-events-double-count): the
        ``posttool`` source already writes one usage_events row per tool call,
        and those rows sum to the same total this method records as a single
        ``session_record`` row. Any aggregator that sums ``cost_usd`` across
        usage_events without filtering by ``source`` (or by
        ``task_slug IS NOT NULL``) will count the same cost twice. The
        per-task rollup `usage_events_cost_rollup_by_task` is safe because it
        filters ``task_slug IS NOT NULL`` (session_record rows have NULL slug).
        New aggregators MUST explicitly choose one slice:

            posttool only:        WHERE source = 'posttool'
            session totals only:  WHERE source = 'session_record'
            never:                SUM across both without an exclusivity clause.
        """
        now = utcnow_iso()
        mid = (model or "").strip() or None
        ti, to, tt = int(tokens_input), int(tokens_output), int(tokens_total)
        tc = int(tool_calls)
        cu = float(cost_usd)
        self._ex(  # type: ignore[attr-defined]
            "INSERT INTO session_usage_metrics("
            "session_id,tokens_input,tokens_output,tokens_total,cost_usd,tool_calls,model,recorded_at"
            ") VALUES(?,?,?,?,?,?,?,?) "
            "ON CONFLICT(session_id) DO UPDATE SET "
            "tokens_input=excluded.tokens_input, "
            "tokens_output=excluded.tokens_output, "
            "tokens_total=excluded.tokens_total, "
            "cost_usd=excluded.cost_usd, "
            "tool_calls=excluded.tool_calls, "
            "model=excluded.model, "
            "recorded_at=excluded.recorded_at",
            (
                int(session_id),
                ti,
                to,
                tt,
                cu,
                tc,
                mid,
                now,
            ),
        )
        self.usage_event_append(
            int(session_id),
            None,
            ti,
            to,
            tt,
            cu,
            tc,
            mid,
            "session_record",
            recorded_at=now,
        )

    def usage_events_cost_rollup_for_task(
        self,
        slug: str,
        since: str | None = None,
        until: str | None = None,
    ) -> dict[str, Any]:
        """Rollup tokens / cost / event-count for ONE task slug.

        Mirrors the safety contract of :meth:`usage_events_cost_rollup_by_task`
        — filters ``task_slug = ?`` (and the ``IS NOT NULL`` is implicit since
        we match a literal slug), so session_record rows (NULL slug) are
        excluded automatically. Used by:

        - ``service_recording.record_cost_actual`` at task_done to write
          ``cost_actual_usd`` / ``tokens_actual`` back onto the task row.
        - ``scripts/hooks/task_cost_budget_check.py`` to compare accumulated
          spend against ``cost_budget_usd`` after every tool call.

        Returns ``{"task_slug": slug, "event_count": int, "tokens_total": int,
        "cost_usd": float}``. Always returns a dict — zero-event case yields
        zeros, never None.
        """
        clauses = ["task_slug = ?"]
        params: list[Any] = [slug]
        if since:
            clauses.append("recorded_at >= ?")
            params.append(since)
        if until:
            clauses.append("recorded_at <= ?")
            params.append(until)
        where_sql = " AND ".join(clauses)
        row = (
            self._q1(  # type: ignore[attr-defined]
                "SELECT COUNT(*) AS event_count, "
                "COALESCE(SUM(tokens_total), 0) AS tokens_total, "
                "COALESCE(SUM(cost_usd), 0) AS cost_usd "
                f"FROM usage_events WHERE {where_sql}",
                tuple(params),
            )
            or {}
        )
        return {
            "task_slug": slug,
            "event_count": int(row.get("event_count") or 0),
            "tokens_total": int(row.get("tokens_total") or 0),
            "cost_usd": float(row.get("cost_usd") or 0.0),
        }

    def usage_events_cost_rollup_by_task(
        self,
        since: str | None = None,
        until: str | None = None,
    ) -> list[dict[str, Any]]:
        """Aggregate tokens/cost/count by task_slug (NULL task_slug excluded).

        SAFETY CONTRACT: ``WHERE task_slug IS NOT NULL`` excludes session_record
        rows (which always have NULL task_slug — see ``session_usage_record``)
        so this rollup never double-counts against the per-tool ``posttool``
        rows. A naïve aggregator without that clause would add the
        session_record total on top of the posttool sum and report ~2× the
        true cost. See `tests/test_usage_events_double_count.py` for the
        regression guard.
        """
        clauses = ["task_slug IS NOT NULL"]
        params: list[Any] = []
        if since:
            clauses.append("recorded_at >= ?")
            params.append(since)
        if until:
            clauses.append("recorded_at <= ?")
            params.append(until)
        where_sql = " AND ".join(clauses)
        return self._q(  # type: ignore[attr-defined,no-any-return]
            "SELECT task_slug AS task_slug, COUNT(*) AS event_count, "
            "COALESCE(SUM(tokens_total), 0) AS tokens_total, "
            "COALESCE(SUM(cost_usd), 0) AS cost_usd "
            f"FROM usage_events WHERE {where_sql} "
            "GROUP BY task_slug ORDER BY cost_usd DESC, task_slug",
            tuple(params),
        )

    def task_model_ids(self, task_slug: str) -> list[str]:
        """Distinct non-null model_id values that did work on a task.

        The usage_events↔task link (model pinning): which models actually
        produced tool calls for this task. Used for mid-task mismatch detection.
        """
        rows = self._q(  # type: ignore[attr-defined]
            "SELECT DISTINCT model_id FROM usage_events "
            "WHERE task_slug=? AND model_id IS NOT NULL ORDER BY model_id",
            (task_slug,),
        )
        return [r["model_id"] for r in rows]

    def usage_events_cost_rollup_by_model(
        self,
        since: str | None = None,
        until: str | None = None,
    ) -> list[dict[str, Any]]:
        """Aggregate tokens/cost/count by model_id.

        Excludes ``source='session_record'`` rows (session-level aggregates)
        to avoid double-counting against the per-tool ``posttool`` rows — same
        contract as ``usage_events_cost_rollup_by_task``.
        """
        clauses = ["source <> 'session_record'", "model_id IS NOT NULL"]
        params: list[Any] = []
        if since:
            clauses.append("recorded_at >= ?")
            params.append(since)
        if until:
            clauses.append("recorded_at <= ?")
            params.append(until)
        where_sql = " AND ".join(clauses)
        return self._q(  # type: ignore[attr-defined,no-any-return]
            "SELECT model_id, COUNT(*) AS event_count, "
            "COALESCE(SUM(tokens_total), 0) AS tokens_total, "
            "COALESCE(SUM(cost_usd), 0) AS cost_usd "
            f"FROM usage_events WHERE {where_sql} "
            "GROUP BY model_id ORDER BY cost_usd DESC, model_id",
            tuple(params),
        )

    def session_usage_summary(self) -> dict[str, Any]:
        agg = (
            self._q1(  # type: ignore[attr-defined]
                "SELECT COUNT(*) as sessions_with_usage, "
                "COALESCE(SUM(tokens_input),0) as tokens_input, "
                "COALESCE(SUM(tokens_output),0) as tokens_output, "
                "COALESCE(SUM(tokens_total),0) as tokens_total, "
                "COALESCE(SUM(cost_usd),0) as cost_usd, "
                "COALESCE(SUM(tool_calls),0) as tool_calls "
                "FROM session_usage_metrics"
            )
            or {}
        )
        last = self._q1(  # type: ignore[attr-defined]
            "SELECT session_id, tokens_input, tokens_output, tokens_total, "
            "cost_usd, tool_calls, model, recorded_at "
            "FROM session_usage_metrics ORDER BY recorded_at DESC LIMIT 1"
        )
        return {
            "sessions_with_usage": int(agg.get("sessions_with_usage") or 0),
            "tokens_input": int(agg.get("tokens_input") or 0),
            "tokens_output": int(agg.get("tokens_output") or 0),
            "tokens_total": int(agg.get("tokens_total") or 0),
            "cost_usd": round(float(agg.get("cost_usd") or 0.0), 4),
            "tool_calls": int(agg.get("tool_calls") or 0),
            "last_session": last,
        }
