"""What a task cost, apportioned — and never quietly promoted to measured.

WHY THE REPORT EXISTS. `cost_actual_usd` is filled on 0 tasks of 1675 and `tokens_actual`
on 27, because the per-call hook records the CALL and not the tokens while the session-level
rows carry tokens and no task slug. The rollup joins on the slug, finds nothing, and writes
NULL — correctly. The question "is a task getting dearer" therefore went unanswered for five
releases although both halves of the answer were in the database.

WHAT THESE TESTS GUARD. An apportioned number is useful exactly as long as everyone knows
it is apportioned, and exactly as long as a session that recorded nothing is reported absent
instead of contributing a zero that pulls every median towards free. Both are negative
properties, so most of what is below is about what the report refuses to say.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import task_cost_report as report  # noqa: E402


def _db(sessions=(), calls=(), tasks=()) -> sqlite3.Connection:
    """A tree-shaped fixture: session totals, per-call rows, closed tasks."""
    from conftest import canonical_ddl

    conn = sqlite3.connect(":memory:")
    # The REAL DDL, not a copy of it: a hand-written fixture schema drifts from the
    # database in silence, and the report would then be tested against a table the
    # project does not have.
    for table in ("usage_events", "tasks"):
        conn.executescript(canonical_ddl(table))
    for session_id, tokens, tool_calls in sessions:
        conn.execute(
            "INSERT INTO usage_events (session_id, tokens_total, tool_calls, source, "
            "recorded_at) VALUES (?, ?, ?, ?, '2026-05-01T00:00:00Z')",
            (session_id, tokens, tool_calls, report.SESSION_SOURCE),
        )
    for session_id, slug, n in calls:
        for _ in range(n):
            conn.execute(
                "INSERT INTO usage_events (session_id, task_slug, source, recorded_at) "
                "VALUES (?, ?, ?, '2026-05-01T00:00:00Z')",
                (session_id, slug, report.CALL_SOURCE),
            )
    for row in tasks:
        slug, done = row[0], row[1]
        complexity = row[2] if len(row) > 2 else "medium"
        conn.execute(
            "INSERT INTO tasks (slug, title, status, completed_at, created_at, updated_at, "
            "complexity) VALUES (?, ?, 'done', ?, '2026-05-01T00:00:00Z', "
            "'2026-05-01T00:00:00Z', ?)",
            (slug, slug, done, complexity),
        )
    return conn


class TestTheApportionment:
    def test_a_task_is_charged_its_share_of_the_session(self):
        """One task with a third of the calls carries a third of the tokens."""
        conn = _db(
            sessions=[(1, 900, 30)],
            calls=[(1, "a", 10), (1, "b", 20)],
            tasks=[("a", "2026-05-01"), ("b", "2026-05-02")],
        )
        got = report.build(conn).per_task
        assert got["a"] == pytest.approx(300)
        assert got["b"] == pytest.approx(600)

    def test_a_task_worked_across_two_sessions_carries_both_shares(self):
        conn = _db(
            sessions=[(1, 100, 10), (2, 400, 20)],
            calls=[(1, "a", 5), (2, "a", 5)],
            tasks=[("a", "2026-05-01")],
        )
        assert report.build(conn).per_task["a"] == pytest.approx(50 + 100)

    def test_an_open_task_is_not_in_the_report(self):
        """The subject is what a CLOSED task cost; an open one has not finished spending."""
        conn = _db(sessions=[(1, 100, 10)], calls=[(1, "a", 10)], tasks=[])
        assert report.build(conn).per_task == {}


class TestAbsenceIsNeverAZero:
    def test_a_task_whose_sessions_recorded_no_tokens_is_absent(self):
        """NEGATIVE, AC-3. Charging it zero would say the work was free and would drag
        every median containing it towards free — the exact lie a NULL avoids."""
        conn = _db(sessions=[], calls=[(1, "a", 10)], tasks=[("a", "2026-05-01")])
        got = report.build(conn)
        assert got.per_task == {}
        assert got.absent == 1

    @pytest.mark.parametrize(
        ("tokens", "calls"),
        # No (100, None) case: the canonical schema forbids a NULL tool_calls, so that
        # state cannot occur in the database and a test of it would guard nothing.
        [(0, 10), (100, 0), (None, 10)],
        ids=["no_tokens", "no_calls", "null_tokens"],
    )
    def test_a_session_missing_either_half_cannot_be_divided(self, tokens, calls):
        """NEGATIVE, AC-4. Calls of zero is the one that would raise; the others would
        contribute a zero. Neither is allowed to reach a median."""
        conn = _db(sessions=[(1, tokens, calls)], calls=[(1, "a", 5)], tasks=[("a", "2026-05-01")])
        got = report.build(conn)
        assert got.per_task == {}, "nothing was charged from an undividable session"
        assert got.absent == 1

    def test_the_report_states_how_far_it_reaches(self):
        """AC-2. A number without its coverage reads as if it covered everything."""
        conn = _db(
            sessions=[(1, 100, 10)],
            calls=[(1, "a", 10), (1, "b", 5)],
            tasks=[("a", "2026-05-01"), ("b", "2026-05-02")],
        )
        conn.execute(
            "INSERT INTO tasks (slug, title, status, completed_at, created_at, updated_at) "
            "VALUES ('c', 'c', 'done', '2026-05-03', '2026-05-01T00:00:00Z', '2026-05-01T00:00:00Z')"
        )
        text = report.render(report.build(conn), closed_total=3)
        assert "COVERAGE:" in text
        assert "of 3 closed task(s)" in text


class TestItNeverCallsTheNumberMeasured:
    def test_the_header_says_apportioned(self):
        """AC-5. The estimate is useful as long as everyone knows it is one."""
        conn = _db(sessions=[(1, 100, 10)], calls=[(1, "a", 10)], tasks=[("a", "2026-05-01")])
        text = report.render(report.build(conn), closed_total=1)
        assert "APPORTIONED, not measured per task" in text
        assert "share of that session's calls" in text, "the rule itself is stated"

    def test_it_warns_that_dollars_would_report_the_price_list(self):
        """The confound that inverts the answer: the price per million tokens moved
        $74.43 -> $10.32 -> $15.76, so cost in dollars fell while the work grew."""
        conn = _db(sessions=[(1, 100, 10)], calls=[(1, "a", 10)], tasks=[("a", "2026-05-01")])
        text = report.render(report.build(conn), closed_total=1)
        assert "price per million tokens" in text
        assert "TOKENS, not dollars" in text

    def test_the_trend_is_called_descriptive(self):
        """Two months of medians invite a forecast; the task mix is not held constant
        between them, so the line says what it is."""
        conn = _db(
            sessions=[(1, 100, 10), (2, 400, 10)],
            calls=[(1, "a", 10), (2, "b", 10)],
            tasks=[("a", "2026-05-01"), ("b", "2026-09-01")],
        )
        text = report.render(report.build(conn), closed_total=2)
        assert "Descriptive, not a forecast" in text
        assert "2026-05 -> 2026-09" in text

    def test_a_single_month_gets_no_trend_line(self):
        """A ratio needs two points. Printing one anyway is how a table becomes a claim."""
        conn = _db(sessions=[(1, 100, 10)], calls=[(1, "a", 10)], tasks=[("a", "2026-05-01")])
        assert "->" not in report.render(report.build(conn), closed_total=1).split("month")[1]


class TestTheMonthlyRollup:
    def test_months_come_out_sorted_with_their_counts(self):
        conn = _db(
            sessions=[(1, 100, 10), (2, 100, 10)],
            calls=[(1, "a", 10), (2, "b", 5), (2, "c", 5)],
            tasks=[("a", "2026-09-01"), ("b", "2026-05-01"), ("c", "2026-05-02")],
        )
        months = report.build(conn).months
        assert [m.month for m in months] == ["2026-05", "2026-09"]
        assert [m.tasks for m in months] == [2, 1]


class TestTheTrendIsSplitByComplexity:
    """The defect this class was added for: a single median per month mixes "the work got
    heavier" with "the work got dearer", and the first reader it misled was the author.
    Measured on this project: blended 41k -> 79k (1.9x), while simple went 27k -> 22k and
    complex 68k -> 130k, with the mix moving from 50/43/11 to 25/73/33."""

    @staticmethod
    def _spread(month: str, complexity: str, n: int, tokens: int):
        """n tasks of one class in one month, each charged `tokens`."""
        sessions = [(hash((month, complexity)) % 10**6, tokens * n, n)]
        calls = [(sessions[0][0], f"{complexity}-{month}-{i}", 1) for i in range(n)]
        tasks = [(f"{complexity}-{month}-{i}", month + "-01", complexity) for i in range(n)]
        return sessions, calls, tasks

    def _db_two_months(self):
        sessions, calls, tasks = [], [], []
        for month, simple, complex_ in (("2026-05", 20, 100), ("2026-09", 10, 400)):
            for complexity, value in (("simple", simple), ("complex", complex_)):
                s, c, k = self._spread(month, complexity, 10, value)
                sessions += s
                calls += c
                tasks += k
        return _db(sessions=sessions, calls=calls, tasks=tasks)

    def test_each_month_carries_a_figure_per_class(self):
        """AC-1 and AC-2: the class, how many tasks it held, and its median."""
        months = report.build(self._db_two_months()).months
        assert [c.complexity for c in months[0].cells] == ["simple", "complex"]
        assert all(c.tasks == 10 for c in months[0].cells)
        assert months[0].cells[0].median == pytest.approx(20)
        assert months[1].cells[1].median == pytest.approx(400)

    def test_the_rendered_trend_names_each_class_separately(self):
        text = report.render(report.build(self._db_two_months()), closed_total=40)
        assert "simple       20 -> 10" not in text, "figures are printed in thousands"
        assert "READ THE PER-COMPLEXITY FIGURES INSTEAD" in text
        for complexity in ("simple", "complex"):
            assert f"  {complexity:12}" in text, f"{complexity} has its own trend line"

    def test_a_thin_class_reports_absence_but_still_shows_its_count(self):
        """NEGATIVE, AC-3. A median over three tasks wearing a trend's clothes is exactly
        the misreading this whole class exists against — but hiding the count as well would
        say the class was never worked."""
        sessions, calls, tasks = self._spread("2026-05", "complex", report.MIN_SAMPLE - 1, 50)
        s2, c2, k2 = self._spread("2026-05", "simple", report.MIN_SAMPLE, 10)
        cells = report.build(_db(sessions + s2, calls + c2, tasks + k2)).months[0].cells
        thin = next(c for c in cells if c.complexity == "complex")
        assert thin.median is None and thin.p90 is None
        assert thin.tasks == report.MIN_SAMPLE - 1
        text = report.render(report.build(_db(sessions + s2, calls + c2, tasks + k2)), 15)
        assert "median absent" in text

    def test_a_task_with_no_declared_complexity_gets_its_own_line(self):
        """NEGATIVE, AC-4. Folding it into a class it never claimed would move that class's
        median on a guess, and dropping it would lose the task."""
        conn = _db(
            sessions=[(1, 100, 10)],
            calls=[(1, "a", 10)],
            tasks=[("a", "2026-05-01", None)],
        )
        cells = report.build(conn).months[0].cells
        assert [c.complexity for c in cells] == [report.UNDECLARED]
        assert cells[0].tasks == 1

    def test_the_blended_line_warns_that_the_mix_moved(self):
        """AC-5. It stays, because someone will quote it — so it carries its own warning."""
        text = report.render(report.build(self._db_two_months()), closed_total=40)
        assert "BLENDED" in text
        assert "task mix is not constant" in text
