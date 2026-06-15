"""Regression guard for the usage_events double-count hazard.

v14b-defect-usage-events-double-count: usage_events is written by two paths
that record the same cost twice in different shapes:

- `posttool_usage` writes one row per tool call (source='posttool',
  task_slug bound to the active task at that moment).
- `session_usage_record` writes one cumulative row per session
  (source='session_record', task_slug=None).

The cumulative session_record row equals the sum of posttool rows for that
session. Any aggregator that sums cost_usd across usage_events without
filtering by source or task_slug will double-count by ~2x.

These tests pin the contract:

1. The current per-task rollup (`usage_events_cost_rollup_by_task`) excludes
   session_record rows correctly via `WHERE task_slug IS NOT NULL`.
2. A naive aggregator that omits the source/task filter WOULD double-count —
   pinned numerically here so any future refactor that breaks the safety
   clause fails this test.
3. session_record rows still have NULL task_slug after the fix
   (the docstring contract relies on that invariant).
"""

from __future__ import annotations

from pathlib import Path

from project_backend import SQLiteBackend
from project_service import ProjectService


def _make_service(tmp_path: Path) -> ProjectService:
    return ProjectService(SQLiteBackend(str(tmp_path / "tausik.db")))


def _seed_posttool_and_session_record(svc: ProjectService, task_slug: str = "t-defect"):
    """Simulate: 3 tool calls written by posttool_usage, plus a session_record
    row equal to their sum (as session_metrics would produce on session-end).
    """
    svc.session_start()
    sess_id = int(svc.be.session_current()["id"])

    # Create the task row so usage_events FK accepts the slug.
    # We do NOT start the task — QG-0 isn't relevant here; we only need the
    # row to exist in `tasks` so `usage_event_append` can satisfy its FK.
    svc.task_quick(task_slug, "double-count regression task")

    posttool_rows = [
        {
            "tokens_input": 100,
            "tokens_output": 50,
            "tokens_total": 150,
            "cost_usd": 0.0015,
            "tool_calls": 1,
        },
        {
            "tokens_input": 200,
            "tokens_output": 100,
            "tokens_total": 300,
            "cost_usd": 0.0030,
            "tool_calls": 1,
        },
        {
            "tokens_input": 300,
            "tokens_output": 150,
            "tokens_total": 450,
            "cost_usd": 0.0045,
            "tool_calls": 1,
        },
    ]
    for r in posttool_rows:
        svc.be.usage_event_append(
            session_id=sess_id,
            task_slug=task_slug,
            tokens_input=r["tokens_input"],
            tokens_output=r["tokens_output"],
            tokens_total=r["tokens_total"],
            cost_usd=r["cost_usd"],
            tool_calls=r["tool_calls"],
            model_id="claude-sonnet-4-6",
            source="posttool",
            tool_name="Test",
        )

    # Cumulative session-record (matches sum of posttool rows above)
    svc.metrics_record_session(
        tokens_input=600,
        tokens_output=300,
        tokens_total=900,
        cost_usd=0.0090,
        tool_calls=3,
        model="claude-sonnet-4-6",
    )
    return sess_id, posttool_rows


def test_per_task_rollup_excludes_session_record(tmp_path: Path) -> None:
    """Existing rollup must remain safe — task_slug filter excludes session_record."""
    svc = _make_service(tmp_path)
    try:
        _seed_posttool_and_session_record(svc)
        rollup = svc.usage_cost_rollup_by_task()
        assert len(rollup) == 1
        r = rollup[0]
        assert r["task_slug"] == "t-defect"
        # 3 posttool rows → event_count=3, NOT 4 (session_record excluded).
        assert int(r["event_count"]) == 3
        assert int(r["tokens_total"]) == 900
        assert abs(float(r["cost_usd"]) - 0.0090) < 1e-9
    finally:
        svc.be.close()


def test_naive_unfiltered_sum_would_double_count(tmp_path: Path) -> None:
    """NEGATIVE pin: SUM(cost_usd) without filter is 2x the truth.

    This test exists so that if anyone introduces a `SELECT SUM(cost_usd)
    FROM usage_events` aggregator without a source clause, this regression
    test makes the hazard visible — change the assertion intentionally if
    you accept the new shape.
    """
    svc = _make_service(tmp_path)
    try:
        _seed_posttool_and_session_record(svc)

        truth_cost = 0.0090  # what the session actually spent

        unfiltered = svc.be._q1("SELECT COALESCE(SUM(cost_usd),0) AS s FROM usage_events")
        unfiltered_sum = float(unfiltered["s"])
        # Naive sum = posttool ($0.009) + session_record ($0.009) = ~$0.018.
        assert abs(unfiltered_sum - 2 * truth_cost) < 1e-9, (
            f"naive unfiltered SUM should be 2x the truth ({2 * truth_cost}); "
            f"got {unfiltered_sum}. If usage_events double-write is removed "
            "in a follow-up, update this test along with the docstring "
            "contract on session_usage_record."
        )

        posttool_only = svc.be._q1(
            "SELECT COALESCE(SUM(cost_usd),0) AS s FROM usage_events WHERE source='posttool'"
        )
        assert abs(float(posttool_only["s"]) - truth_cost) < 1e-9

        session_only = svc.be._q1(
            "SELECT COALESCE(SUM(cost_usd),0) AS s FROM usage_events WHERE source='session_record'"
        )
        assert abs(float(session_only["s"]) - truth_cost) < 1e-9
    finally:
        svc.be.close()


def test_session_record_row_has_null_task_slug(tmp_path: Path) -> None:
    """The safety clause `task_slug IS NOT NULL` only works because
    session_record rows reliably have NULL task_slug. Pin the invariant.
    """
    svc = _make_service(tmp_path)
    try:
        _seed_posttool_and_session_record(svc)
        sess_rows = svc.be._q("SELECT task_slug FROM usage_events WHERE source='session_record'")
        assert sess_rows, "session_record row must exist after metrics_record_session"
        for r in sess_rows:
            assert r["task_slug"] is None, (
                "session_record rows MUST have NULL task_slug — this is the "
                "exclusivity invariant that keeps usage_events_cost_rollup_by_task "
                "double-count-safe."
            )
    finally:
        svc.be.close()
