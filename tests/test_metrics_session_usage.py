from __future__ import annotations

from pathlib import Path

import pytest

from project_backend import SQLiteBackend
from project_parser import build_parser
from project_service import ProjectService
from tausik_utils import ServiceError


def _make_service(tmp_path: Path) -> ProjectService:
    db_path = tmp_path / "tausik.db"
    be = SQLiteBackend(str(db_path))
    return ProjectService(be)


def test_metrics_record_session_persists_usage(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    try:
        svc.session_start()
        msg = svc.metrics_record_session(
            tokens_input=1000,
            tokens_output=250,
            tokens_total=1250,
            cost_usd=0.0125,
            tool_calls=3,
            model="claude-sonnet-4-6",
        )
        assert "Session usage recorded" in msg

        m = svc.get_metrics()
        usage = m.get("session_usage") or {}
        assert usage["sessions_with_usage"] == 1
        assert usage["tokens_input"] == 1000
        assert usage["tokens_output"] == 250
        assert usage["tokens_total"] == 1250
        assert usage["cost_usd"] == 0.0125
        last = usage.get("last_session") or {}
        assert last.get("model") == "claude-sonnet-4-6"

        rows = svc.be._q("SELECT * FROM usage_events ORDER BY id")
        assert len(rows) == 1
        ev = rows[0]
        assert ev["source"] == "session_record"
        assert ev["tokens_total"] == 1250
        assert ev["session_id"] == int(svc.be.session_current()["id"])
    finally:
        svc.be.close()


def test_metrics_record_session_negative_tokens_rejected(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    try:
        svc.session_start()
        with pytest.raises(ServiceError, match="tokens_input cannot be negative"):
            svc.metrics_record_session(
                tokens_input=-1,
                tokens_output=0,
                tokens_total=0,
                cost_usd=0.0,
            )
    finally:
        svc.be.close()


def test_metrics_each_record_replaces_the_session_mirror(tmp_path: Path) -> None:
    """The mirror row carries the session's RUNNING TOTAL, so it replaces.

    This test used to assert the opposite — two calls, two rows — and that is
    exactly how the slice `session_usage_record` documents as safe
    ("session totals only: WHERE source = 'session_record'") filled with
    snapshots of one fact. Measured in session #228: 15,517 rows for 155
    sessions, summing to 88x the truth.
    """
    svc = _make_service(tmp_path)
    try:
        svc.session_start()
        svc.metrics_record_session(
            tokens_input=10,
            tokens_output=5,
            tokens_total=15,
            cost_usd=0.001,
        )
        svc.metrics_record_session(
            tokens_input=20,
            tokens_output=10,
            tokens_total=30,
            cost_usd=0.002,
        )
        n = svc.be._q1("SELECT COUNT(*) as c FROM usage_events") or {}
        assert int(n.get("c") or 0) == 1
        row = svc.be._q("SELECT * FROM usage_events")[0]
        assert row["tokens_total"] == 30  # the latest total, not 15 and not 45
        assert row["source"] == "session_record"
    finally:
        svc.be.close()


def test_metrics_log_usage_manual_skips_session_usage_metrics(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    try:
        svc.session_start()
        n0 = svc.be._q1("SELECT COUNT(*) as c FROM session_usage_metrics") or {}
        assert int(n0.get("c") or 0) == 0
        msg = svc.metrics_log_usage_event(
            tokens_input=3,
            tokens_output=4,
            tokens_total=7,
            cost_usd=0.0007,
            tool_calls=1,
            model="x",
        )
        assert "usage_events #" in msg
        assert "manual" in msg or "manual log" in msg
        n1 = svc.be._q1("SELECT COUNT(*) as c FROM session_usage_metrics") or {}
        assert int(n1.get("c") or 0) == 0
        ev_rows = svc.be._q("SELECT source FROM usage_events")
        assert len(ev_rows) == 1
        assert ev_rows[0]["source"] == "manual"
    finally:
        svc.be.close()


def test_metrics_log_usage_with_task_slug(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    try:
        svc.session_start()
        svc.task_add(None, "t-usage-log", "T", goal="g")
        svc.metrics_log_usage_event(
            tokens_input=10,
            tokens_output=5,
            tokens_total=15,
            cost_usd=0.015,
            task_slug="t-usage-log",
        )
        row = svc.be._q1("SELECT task_slug, source FROM usage_events")
        assert row is not None
        assert row["task_slug"] == "t-usage-log"
        assert row["source"] == "manual"
    finally:
        svc.be.close()


def test_usage_cost_rollup_by_task_aggregates(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    try:
        svc.session_start()
        svc.task_add(None, "t-roll", "R", goal="g")
        svc.metrics_log_usage_event(
            tokens_input=1, tokens_output=1, tokens_total=2, cost_usd=0.01, task_slug="t-roll"
        )
        svc.metrics_log_usage_event(
            tokens_input=2, tokens_output=3, tokens_total=5, cost_usd=0.02, task_slug="t-roll"
        )
        rows = svc.usage_cost_rollup_by_task()
        assert len(rows) == 1
        r = rows[0]
        assert r["task_slug"] == "t-roll"
        assert int(r["event_count"]) == 2
        assert int(r["tokens_total"]) == 7
        assert abs(float(r["cost_usd"]) - 0.03) < 1e-9
    finally:
        svc.be.close()


def test_usage_cost_rollup_session_record_without_task_excluded(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    try:
        svc.session_start()
        svc.metrics_record_session(
            tokens_input=1,
            tokens_output=1,
            tokens_total=2,
            cost_usd=0.001,
        )
        assert svc.usage_cost_rollup_by_task() == []
    finally:
        svc.be.close()


def test_usage_cost_rollup_invalid_since_raises(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    try:
        with pytest.raises(ServiceError, match="Invalid since"):
            svc.usage_cost_rollup_by_task(since="bogus")
        with pytest.raises(ServiceError, match="since"):
            svc.usage_cost_rollup_by_task(
                since="2026-06-01T00:00:00Z",
                until="2026-05-01T00:00:00Z",
            )
    finally:
        svc.be.close()


def test_metrics_log_usage_requires_existing_task_slug(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    try:
        svc.session_start()
        with pytest.raises(ServiceError, match="not found"):
            svc.metrics_log_usage_event(
                tokens_input=1,
                tokens_output=0,
                tokens_total=1,
                cost_usd=0.0,
                task_slug="missing-task",
            )
    finally:
        svc.be.close()


def test_metrics_record_session_cli_args_are_supported() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "metrics",
            "record-session",
            "--tokens-input",
            "10",
            "--tokens-output",
            "5",
            "--tokens-total",
            "15",
            "--cost-usd",
            "0.0003",
            "--tool-calls",
            "2",
            "--model",
            "claude-haiku-4-5",
        ]
    )
    assert args.command == "metrics"
    assert args.metrics_cmd == "record-session"
    assert args.tokens_total == 15
    assert args.model == "claude-haiku-4-5"


def test_metrics_cli_log_usage_and_cost_parsers() -> None:
    p = build_parser()
    al = p.parse_args(
        [
            "metrics",
            "log-usage",
            "--tokens-input",
            "1",
            "--tokens-output",
            "2",
            "--tokens-total",
            "3",
            "--cost-usd",
            "0.5",
            "--task-slug",
            "t1",
            "--session-id",
            "42",
        ]
    )
    assert al.command == "metrics"
    assert al.metrics_cmd == "log-usage"
    assert al.tokens_total == 3
    assert al.task_slug == "t1"
    assert al.session_id == 42

    ac = p.parse_args(["metrics", "cost", "--since", "2026-05-01", "--until", "2026-05-31T23:59:59Z"])
    assert ac.metrics_cmd == "cost"
    assert ac.since == "2026-05-01"
    assert ac.until == "2026-05-31T23:59:59Z"

    ad = p.parse_args(["metrics", "--cost"])
    assert ad.metrics_cmd is None
    assert ad.cost is True


class TestSupersededArithmeticIsNamedNotHidden:
    """Two arithmetics in one column are tolerable only if the reader is told.

    `sum_usage_tokens` counted every message twice (measured 1.9999x over 23,836
    live messages) until session
    `token_accounting.LAST_SESSION_ON_SUPERSEDED_TOKEN_ARITHMETIC`. Those rows
    cannot be recomputed — transcripts survive for a fraction of the sessions,
    and rows predating the API's `iterations` field were never doubled at all —
    so the all-time total will span two scales forever. The report must say so.
    """

    def test_summary_counts_the_superseded_share_from_the_db(self, tmp_path: Path) -> None:
        svc = _make_service(tmp_path)
        try:
            svc.session_start()
            svc.metrics_record_session(
                tokens_input=1000,
                tokens_output=250,
                tokens_total=1250,
                cost_usd=0.0125,
                tool_calls=3,
                model="claude-opus-5",
            )
            usage = (svc.get_metrics() or {}).get("session_usage") or {}
            # Session 1 is at or below the boundary, so it is on the old scale.
            assert usage["superseded_sessions"] == 1
            assert usage["superseded_tokens"] == 1250
            assert usage["superseded_cost_usd"] == 0.0125
        finally:
            svc.be.close()

    def test_report_names_the_superseded_share(self) -> None:
        from render_metrics import _usage_lines

        lines = _usage_lines(
            {
                "session_usage": {
                    "sessions_with_usage": 156,
                    "tokens_total": 132_652_885,
                    "cost_usd": 1485.8401,
                    "superseded_sessions": 156,
                    "superseded_tokens": 132_652_885,
                    "superseded_cost_usd": 1485.8401,
                }
            }
        )
        text = "\n".join(lines)
        assert "superseded arithmetic" in text
        assert "156 session(s)" in text
        assert "132,652,885" in text

    def test_the_caveat_retires_itself_when_no_old_row_remains(self) -> None:
        """It is a self-clearing statement of fact, not permanent boilerplate."""
        from render_metrics import _usage_lines

        lines = _usage_lines(
            {
                "session_usage": {
                    "sessions_with_usage": 3,
                    "tokens_total": 100,
                    "cost_usd": 1.0,
                    "superseded_sessions": 0,
                    "superseded_tokens": 0,
                    "superseded_cost_usd": 0.0,
                }
            }
        )
        text = "\n".join(lines)
        assert "superseded" not in text
        assert "Sessions tracked: 3" in text

    def test_a_summary_without_the_new_keys_does_not_crash_the_report(self) -> None:
        """Old callers and old payloads keep rendering — absence is not zero-crash."""
        from render_metrics import _usage_lines

        lines = _usage_lines(
            {"session_usage": {"sessions_with_usage": 1, "tokens_total": 5, "cost_usd": 0.5}}
        )
        assert any("Sessions tracked: 1" in ln for ln in lines)
        assert not any("superseded" in ln for ln in lines)

    def test_the_boundary_is_a_session_id_not_a_date(self) -> None:
        """A calendar threshold rots on its own; a max-session-id cannot.

        This is the same failure class that billed Sonnet 5 at another model's
        rate for months — a number justified by a date nobody re-measured.
        """
        from token_accounting import LAST_SESSION_ON_SUPERSEDED_TOKEN_ARITHMETIC as boundary

        assert isinstance(boundary, int)
        assert boundary > 0
