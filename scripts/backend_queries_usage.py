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
        session_id: int | None,
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
        """Insert one usage_events row; return new row id.

        ``session_id`` is optional since v48. The row's attribution is the
        TASK — that is what carries ``cost_actual_usd``/``tokens_actual`` — and
        the session is a derived report of activity mileage. Before v48 the
        column was ``NOT NULL``, so a caller with a known task but no open
        session had nowhere to put the event and dropped it whole
        (usage-attribution-is-keyed-by-task-not-session).
        """
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
                    None if session_id is None else int(session_id),
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
          This is a denormalized copy for unified event-stream analytics, and it
          REPLACES the session's previous copy rather than joining it. The row
          carries the session's CUMULATIVE total, so appending made the slice a
          pile of snapshots: measured in session #228, 15,517 rows for 155
          sessions — about a hundred per session — and summing the slice this
          docstring recommends below returned 88x the truth. A snapshot that
          accumulates is not an event stream; it is the same fact written down
          again, and the mirror of an UPSERT must be an UPSERT.

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
        # ONE transaction, not three commits. `_ex` commits immediately unless an
        # explicit transaction is open, so a crash between the DELETE and the
        # INSERT left the authoritative table holding the session's total while
        # the mirror had NO row for it — and an ENDED session never records again,
        # so that gap was permanent. The by-model report reads the mirror, so such
        # a session would silently vanish from the model breakdown.
        # `transaction()` owns a transaction here and nests as a SAVEPOINT when a
        # caller already opened one — which is why it is used instead of a
        # hand-written `owns_tx = not self._in_tx` (its docstring explains what
        # that hand-written form gets wrong).
        with self.transaction():  # type: ignore[attr-defined]
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
            # Replace, do not append: the mirror row carries the session's running
            # total, so a second call would leave two rows claiming the same spend.
            # Deleting first keeps the slice one-row-per-session without a schema
            # change, and it is scoped by BOTH session_id and source so no other
            # session and no `posttool` row can be touched.
            self._ex(  # type: ignore[attr-defined]
                "DELETE FROM usage_events WHERE session_id = ? AND source = 'session_record'",
                (int(session_id),),
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
                "SUM(CASE WHEN tokens_total IS NOT NULL OR cost_usd IS NOT NULL "
                "THEN 1 ELSE 0 END) AS measured_event_count, "
                "SUM(tokens_total) AS tokens_total, "
                "SUM(cost_usd) AS cost_usd "
                f"FROM usage_events WHERE {where_sql}",
                tuple(params),
            )
            or {}
        )
        # NO `COALESCE(..., 0)`. SUM returns NULL when every input is NULL, and
        # that NULL is the answer: nothing about this task was measured. Folding
        # it to 0 here is precisely how `tasks.cost_actual_usd` came to read
        # $0.0000 on 669 tasks — a price nobody observed, presented as a fact.
        # `measured_event_count` gives the denominator, so a caller can say
        # "0 of 120 events carried a measurement" instead of guessing.
        tokens = row.get("tokens_total")
        cost = row.get("cost_usd")
        return {
            "task_slug": slug,
            "event_count": int(row.get("event_count") or 0),
            "measured_event_count": int(row.get("measured_event_count") or 0),
            "tokens_total": None if tokens is None else int(tokens),
            "cost_usd": None if cost is None else float(cost),
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
        """Aggregate tokens/cost/count by model_id, over the SESSION slice.

        It reads ``source='session_record'`` — the opposite of what it did, and
        for a measured reason. The `posttool` slice was the source, and on this
        project `model_id` is filled in exactly ONE of its 54,855 rows, because
        the PostToolUse payload carries no usage. So the report named
        `claude-opus-4-7` as this project's only model and attributed all spend
        to it, while the work had been running on `claude-opus-5` and
        `claude-sonnet-5` for months and said so in every session record. A
        report that is merely incomplete makes a reader ask; one that confidently
        names the wrong model makes them stop asking.

        The session slice is one row per session (see `session_usage_record`),
        so grouping it double-counts nothing — the exclusivity contract below is
        still honoured, just from the other side of it.
        """
        clauses = ["source = 'session_record'", "model_id IS NOT NULL"]
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
        # How much of that total predates the token-arithmetic correction. The
        # sum above spans two arithmetics and always will — the old rows cannot
        # be recomputed (see LAST_SESSION_ON_SUPERSEDED_TOKEN_ARITHMETIC), so the
        # only honest option left is to say how large the superseded share is.
        # The count retires itself: once no row sits at or below the boundary it
        # is 0 and the report stops mentioning it.
        from token_accounting import LAST_SESSION_ON_SUPERSEDED_TOKEN_ARITHMETIC

        superseded = (
            self._q1(  # type: ignore[attr-defined]
                "SELECT COUNT(*) AS n, COALESCE(SUM(tokens_total),0) AS tokens, "
                "COALESCE(SUM(cost_usd),0) AS cost_usd "
                "FROM session_usage_metrics WHERE session_id <= ?",
                (LAST_SESSION_ON_SUPERSEDED_TOKEN_ARITHMETIC,),
            )
            or {}
        )
        return {
            "sessions_with_usage": int(agg.get("sessions_with_usage") or 0),
            "tokens_input": int(agg.get("tokens_input") or 0),
            "tokens_output": int(agg.get("tokens_output") or 0),
            "tokens_total": int(agg.get("tokens_total") or 0),
            "cost_usd": round(float(agg.get("cost_usd") or 0.0), 4),
            "tool_calls": int(agg.get("tool_calls") or 0),
            "last_session": last,
            "superseded_sessions": int(superseded.get("n") or 0),
            "superseded_tokens": int(superseded.get("tokens") or 0),
            "superseded_cost_usd": round(float(superseded.get("cost_usd") or 0.0), 4),
        }


def usage_events_unattributed_rollup(
    backend: Any,
    since: str | None = None,
    until: str | None = None,
) -> dict[str, Any]:
    """The «вне задачи» bucket: real events that no task claims.

    WHY A MODULE-LEVEL FUNCTION AND NOT A BACKEND METHOD. `SQLiteBackend` is one
    of the two classes baselined by the class-surface ratchet (tausik/gates.json,
    129 members), and that baseline may only turn DOWN — a 130th public member is
    exactly the regression the gate exists to catch. Renaming it private to slip
    under the count would evade the rule instead of honouring it. So the query
    stays in the layer it belongs to (this module owns the usage_events SQL) but
    stops being API on a class that is already too wide.

    WHY IT EXISTS AT ALL. The per-task rollup answers `WHERE task_slug IS NOT
    NULL`, which is correct for what it reports and is the reason it never
    double-counts. But it means the complement — an event with no task — is
    invisible in every report we print. Until v48 that hardly mattered, because
    the hook dropped such an event before it reached the table; now that the row
    is written, silence here would trade one silent drop for another, which is
    the very thing that task set out to stop.

    WHAT IT COUNTS. `task_slug IS NULL` AND `source <> 'session_record'`. The
    source filter is not cosmetic: `session_usage_record` writes a MIRROR row of
    the session total, always with a NULL task_slug. Counting those here would
    report the session's whole spend a second time — the ~2x error
    `tests/test_usage_events_double_count.py` was written to pin. So the bucket
    holds only genuine, unclaimed work.

    WHY `sessionless_events` IS BROKEN OUT. Two different situations wear the
    same NULL task_slug: work done inside a session but outside any task, and
    work done with neither. The second is what v48 newly made representable, so
    the report has to be able to name it rather than fold it into one anonymous
    total.
    """
    clauses = ["task_slug IS NULL", "source <> 'session_record'"]
    params: list[Any] = []
    if since:
        clauses.append("recorded_at >= ?")
        params.append(since)
    if until:
        clauses.append("recorded_at <= ?")
        params.append(until)
    where_sql = " AND ".join(clauses)
    row = (
        backend._q1(
            "SELECT COUNT(*) AS event_count, "
            "COALESCE(SUM(tokens_total), 0) AS tokens_total, "
            "COALESCE(SUM(cost_usd), 0) AS cost_usd, "
            "COALESCE(SUM(CASE WHEN session_id IS NULL THEN 1 ELSE 0 END), 0) "
            "AS sessionless_events "
            f"FROM usage_events WHERE {where_sql}",
            tuple(params),
        )
        or {}
    )
    return {
        "event_count": int(row.get("event_count") or 0),
        "tokens_total": int(row.get("tokens_total") or 0),
        "cost_usd": float(row.get("cost_usd") or 0.0),
        "sessionless_events": int(row.get("sessionless_events") or 0),
    }
