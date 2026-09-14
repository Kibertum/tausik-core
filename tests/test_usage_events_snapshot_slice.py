"""usage_events: the session mirror is one row, and a zero is not a measurement.

`session_usage_record` writes a session's CUMULATIVE total into
`session_usage_metrics` (UPSERT) and mirrors it into `usage_events` tagged
`source='session_record'`. The mirror was APPENDED, so the slice its own
docstring recommends — "session totals only: WHERE source = 'session_record'" —
filled with snapshots of the same fact. Measured in session #228: 15,517 rows
for 155 sessions, summing to 88x the truth. A documented query that lies is
worse than an undocumented one, because following the documentation is what
produces the wrong number.

Three more things this pins, all measured on the live database:

  * The per-task cost table printed `0.0000` for EVERY task. The PostToolUse
    payload carries no usage — 76 of this project's 54,855 posttool rows have
    any tokens at all — so per-task spend is unobserved, and a zero there reads
    as "this task was free" (decision #334).
  * `LLM Usage by Model` named `claude-opus-4-7` as the project's only model and
    gave it all the spend, because it read the posttool slice where `model_id`
    is filled in exactly ONE row of 54,855. The work had been running on
    `claude-opus-5` and `claude-sonnet-5` for months.
  * A model whose rows were recorded before it had a price row stores
    `cost_usd = 0.0`. Asking today's price table whether the model is priceable
    answers a different question than "was this metered".
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from model_pinning import _cost_cell, format_model_usage_section  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402


def _service(tmp_path: Path) -> ProjectService:
    return ProjectService(SQLiteBackend(str(tmp_path / "tausik.db")))


def _record(svc: ProjectService, **kw):
    base = dict(
        tokens_input=1000,
        tokens_output=250,
        tokens_total=1250,
        cost_usd=0.0125,
        tool_calls=3,
        model="claude-opus-5",
    )
    base.update(kw)
    return svc.metrics_record_session(**base)


class TestTheSessionMirrorIsOneRow:
    def test_repeated_recording_leaves_exactly_one_mirror_row(self, tmp_path):
        """THE defect: session #227 had 39 rows, all claiming the same spend."""
        svc = _service(tmp_path)
        try:
            svc.session_start()
            for _ in range(5):
                _record(svc)
            rows = svc.be._q("SELECT * FROM usage_events WHERE source='session_record'")
            assert len(rows) == 1
        finally:
            svc.be.close()

    def test_the_surviving_row_is_the_latest_not_the_sum(self, tmp_path):
        svc = _service(tmp_path)
        try:
            svc.session_start()
            _record(svc, tokens_total=1250, cost_usd=0.0125)
            _record(svc, tokens_total=9000, cost_usd=0.9)
            row = svc.be._q("SELECT * FROM usage_events WHERE source='session_record'")[0]
            assert row["tokens_total"] == 9000
            assert abs(float(row["cost_usd"]) - 0.9) < 1e-9
        finally:
            svc.be.close()

    def test_the_documented_slice_equals_the_authoritative_table(self, tmp_path):
        """Two tables describing one fact are supposed to agree; they did not."""
        svc = _service(tmp_path)
        try:
            svc.session_start()
            for _ in range(4):
                _record(svc, tokens_total=1250, cost_usd=0.0125)
            svc.session_end()
            svc.session_start()
            for _ in range(3):
                _record(svc, tokens_total=700, cost_usd=0.007)
            mirror = svc.be._q(
                "SELECT COALESCE(SUM(tokens_total),0) t, COALESCE(SUM(cost_usd),0) c "
                "FROM usage_events WHERE source='session_record'"
            )[0]
            authoritative = svc.be._q(
                "SELECT COALESCE(SUM(tokens_total),0) t, COALESCE(SUM(cost_usd),0) c "
                "FROM session_usage_metrics"
            )[0]
            assert mirror["t"] == authoritative["t"] == 1950
            assert abs(float(mirror["c"]) - float(authoritative["c"])) < 1e-9
        finally:
            svc.be.close()

    def test_replacing_one_session_leaves_other_sessions_and_sources_alone(self, tmp_path):
        """The DELETE is scoped by session AND source — prove both halves."""
        svc = _service(tmp_path)
        try:
            svc.session_start()
            _record(svc)
            svc.metrics_log_usage_event(
                tokens_input=5,
                tokens_output=5,
                tokens_total=10,
                cost_usd=0.001,
                tool_calls=1,
                model="claude-opus-5",
                task_slug=None,
            )
            svc.session_end()
            svc.session_start()
            _record(svc)
            _record(svc)  # the replace runs here
            by_source = {
                r["source"]: r["n"]
                for r in svc.be._q("SELECT source, COUNT(*) n FROM usage_events GROUP BY source")
            }
            assert by_source["session_record"] == 2  # one per session, both kept
            assert by_source["manual"] == 1  # untouched by the replace
        finally:
            svc.be.close()


class TestTheByModelReportNamesTheRunningModel:
    def test_two_sessions_on_two_models_produce_two_rows(self, tmp_path):
        svc = _service(tmp_path)
        try:
            svc.session_start()
            _record(svc, model="claude-opus-5", tokens_total=1000, cost_usd=1.0)
            svc.session_end()
            svc.session_start()
            _record(svc, model="claude-sonnet-5", tokens_total=500, cost_usd=0.25)
            rows = {r["model_id"]: r for r in svc.be.usage_events_cost_rollup_by_model()}
            assert set(rows) == {"claude-opus-5", "claude-sonnet-5"}
            assert rows["claude-opus-5"]["tokens_total"] == 1000
            assert rows["claude-sonnet-5"]["tokens_total"] == 500
        finally:
            svc.be.close()

    def test_repeated_recording_does_not_multiply_a_models_spend(self, tmp_path):
        """The report read a slice that grew with every SessionEnd firing."""
        svc = _service(tmp_path)
        try:
            svc.session_start()
            for _ in range(6):
                _record(svc, model="claude-opus-5", tokens_total=1000, cost_usd=1.0)
            rows = svc.be.usage_events_cost_rollup_by_model()
            assert len(rows) == 1
            assert rows[0]["tokens_total"] == 1000
            assert rows[0]["event_count"] == 1
        finally:
            svc.be.close()

    def test_the_posttool_slice_is_not_mixed_into_the_model_view(self, tmp_path):
        """The exclusivity contract still holds — from the other side of it."""
        svc = _service(tmp_path)
        try:
            svc.session_start()
            _record(svc, model="claude-opus-5", tokens_total=1000, cost_usd=1.0)
            svc.metrics_log_usage_event(
                tokens_input=1,
                tokens_output=1,
                tokens_total=2,
                cost_usd=0.5,
                tool_calls=1,
                model="claude-opus-5",
                task_slug=None,
            )
            rows = svc.be.usage_events_cost_rollup_by_model()
            assert len(rows) == 1
            assert rows[0]["tokens_total"] == 1000  # not 1002
        finally:
            svc.be.close()


class TestAZeroCostIsNotAMeasurement:
    def test_tokens_with_a_stored_zero_report_as_unmetered(self):
        """claude-fable-5-1: 4,282,326 tokens at $0.0000 because it had no price
        row when those sessions were recorded, and acquired one afterwards."""
        cell = _cost_cell("claude-opus-5", 4_282_326, 0.0)
        assert "not priced" in cell
        assert "$0.0000" not in cell

    def test_a_real_price_still_prints_as_money(self):
        assert _cost_cell("claude-opus-5", 1000, 12.5) == "$12.5000"

    def test_zero_tokens_is_a_real_zero(self):
        """Not everything absent is unmeasured — a measured nothing stays 0."""
        assert _cost_cell("claude-opus-5", 0, 0.0) == "$0.0000"

    def test_the_section_renders_the_absence_marker(self):
        lines = format_model_usage_section(
            [
                {
                    "model_id": "claude-fable-5-1",
                    "event_count": 2,
                    "tokens_total": 999,
                    "cost_usd": 0.0,
                }
            ]
        )
        text = "\n".join(lines)
        assert "not priced" in text
        assert "$0.0000" not in text


class TestTheThreeWritesAreOneTransaction:
    """UPSERT, DELETE and INSERT describe ONE fact, so they commit together.

    `SQLiteBackend._ex` commits immediately unless an explicit transaction is
    open, and none was. A crash between the DELETE and the INSERT left
    `session_usage_metrics` holding the session's total while `usage_events` had
    no mirror row for it — and an ENDED session never records again, so the gap
    was permanent. Since the by-model report reads the mirror, that session's
    spend would have vanished from the model breakdown without a trace.

    The window predates the replace: before it, the UPSERT committed and then the
    INSERT could fail, losing the mirror the same way. The DELETE widened it; it
    did not create it.
    """

    def test_a_failing_mirror_insert_leaves_no_partial_state(self, tmp_path, monkeypatch):
        svc = _service(tmp_path)
        try:
            svc.session_start()
            _record(svc, tokens_total=1250, cost_usd=0.0125)

            def boom(*_a, **_kw):
                raise RuntimeError("disk went away mid-write")

            monkeypatch.setattr(type(svc.be), "usage_event_append", boom, raising=True)
            with pytest.raises(RuntimeError):
                _record(svc, tokens_total=9999, cost_usd=9.99)
            monkeypatch.undo()

            # The UPSERT must NOT have landed on its own...
            authoritative = svc.be._q("SELECT * FROM session_usage_metrics")[0]
            assert authoritative["tokens_total"] == 1250
            # ...and the previous mirror must NOT have been deleted.
            mirror = svc.be._q("SELECT * FROM usage_events WHERE source='session_record'")
            assert len(mirror) == 1
            assert mirror[0]["tokens_total"] == 1250
        finally:
            svc.be.close()

    def test_the_call_nests_inside_a_transaction_the_caller_owns(self, tmp_path):
        """A SAVEPOINT, not a commit: the outer writer still decides."""
        svc = _service(tmp_path)
        try:
            svc.session_start()
            svc.be.begin_tx()
            _record(svc, tokens_total=4242, cost_usd=4.2)
            assert svc.be._in_tx is True  # not committed out from under the caller
            svc.be.rollback_tx()
            assert svc.be._q("SELECT * FROM usage_events WHERE source='session_record'") == []
            assert svc.be._q("SELECT * FROM session_usage_metrics") == []
        finally:
            svc.be.close()

    def test_a_committed_outer_transaction_keeps_the_record(self, tmp_path):
        """The other half of nesting: commit must carry the nested write through."""
        svc = _service(tmp_path)
        try:
            svc.session_start()
            svc.be.begin_tx()
            _record(svc, tokens_total=4242, cost_usd=4.2)
            svc.be.commit_tx()
            mirror = svc.be._q("SELECT * FROM usage_events WHERE source='session_record'")
            assert len(mirror) == 1
            assert mirror[0]["tokens_total"] == 4242
        finally:
            svc.be.close()

    def test_the_happy_path_still_leaves_exactly_one_mirror_row(self, tmp_path):
        """The cure must not undo the replace it was added on top of."""
        svc = _service(tmp_path)
        try:
            svc.session_start()
            for _ in range(4):
                _record(svc, tokens_total=1250, cost_usd=0.0125)
            assert len(svc.be._q("SELECT * FROM usage_events WHERE source='session_record'")) == 1
        finally:
            svc.be.close()

    def test_a_rollback_does_not_touch_other_sessions_or_sources(self, tmp_path, monkeypatch):
        """Scope holds on the failing path too, not only on the happy one."""
        svc = _service(tmp_path)
        try:
            svc.session_start()
            _record(svc, tokens_total=100, cost_usd=0.1)
            svc.metrics_log_usage_event(
                tokens_input=5,
                tokens_output=5,
                tokens_total=10,
                cost_usd=0.001,
                tool_calls=1,
                model="claude-opus-5",
                task_slug=None,
            )
            svc.session_end()
            svc.session_start()

            def boom(*_a, **_kw):
                raise RuntimeError("nope")

            monkeypatch.setattr(type(svc.be), "usage_event_append", boom, raising=True)
            with pytest.raises(RuntimeError):
                _record(svc, tokens_total=777, cost_usd=7.7)
            monkeypatch.undo()

            by_source = {
                r["source"]: r["n"]
                for r in svc.be._q("SELECT source, COUNT(*) n FROM usage_events GROUP BY source")
            }
            assert by_source["session_record"] == 1  # the first session's, intact
            assert by_source["manual"] == 1  # never in scope, never touched
        finally:
            svc.be.close()
