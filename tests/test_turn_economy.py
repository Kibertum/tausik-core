"""A finished task is priced in TURNS, because that is the unit the billing follows.

THE MEASUREMENT THAT PICKS THE UNIT. Over 5,964 telemetry rows the input side was 99.5%
`cache_read` — 2,876,911,173 tokens against 22,099 of fresh input. The prefix is re-sent on
every call, so one extra CALL costs about 482,000 tokens while shortening the prompt saves a
few hundred. An edit that trims the request and adds a turn loses by about a hundred to one.

WHAT THE LIVE TREE SAYS, and it is why this module exists rather than another prose-length
lever: the median closed task went from 6 calls in April to 32 in September, p90 from 35 to
114, and `Bash` is 87.6% of all measured calls.

Absence is absence on both halves — `call_actual` lives in this project's database and the
sidecar is written by a hook on this machine. Neither travels, so a fresh clone gets words
saying so rather than a zero somebody could average.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import turn_economy as te  # noqa: E402

from conftest import canonical_ddl  # noqa: E402


@pytest.fixture
def db(tmp_path):
    """A database whose closed tasks carry call counts."""

    def build(rows):
        path = tmp_path / "t.db"
        conn = sqlite3.connect(path)
        conn.executescript(canonical_ddl("tasks"))
        for i, (completed, calls) in enumerate(rows):
            conn.execute(
                "INSERT INTO tasks (slug, title, status, completed_at, call_actual, "
                "created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
                (
                    f"t{i}",
                    f"T{i}",
                    "done",
                    completed,
                    calls,
                    "2026-01-01T00:00:00Z",
                    "2026-01-01T00:00:00Z",
                ),
            )
        conn.commit()
        conn.close()
        return str(path)

    return build


@pytest.fixture
def sidecar(tmp_path):
    def build(lines):
        path = tmp_path / "token_metrics.jsonl"
        path.write_text("".join(lines), encoding="utf-8")
        return str(path)

    return build


def _rows(n, calls, month="2026-09"):
    return [(f"{month}-1{i % 9}T00:00:00Z", calls) for i in range(n)]


class TestTurnsPerFinishedTask:
    def test_the_median_and_p90_come_from_closed_tasks_with_a_count(self, db):
        got = te.calls_per_task(db(_rows(30, 10)))
        assert got["tasks"] == 30 and got["median"] == 10 and got["p90"] == 10

    def test_a_task_without_a_count_is_not_a_zero(self, db, tmp_path):
        """A task closed before the counter existed has no count, and averaging it in as
        zero would say the work got cheaper when only the record got thinner."""
        path = db(_rows(5, 8))
        conn = sqlite3.connect(path)
        conn.execute(
            "INSERT INTO tasks (slug, title, status, completed_at, call_actual, created_at, "
            "updated_at) VALUES ('old','Old','done','2026-01-01T00:00:00Z',NULL,"
            "'2026-01-01T00:00:00Z','2026-01-01T00:00:00Z')"
        )
        conn.commit()
        conn.close()
        assert te.calls_per_task(path)["tasks"] == 5

    def test_the_trend_is_reported_by_month(self, db):
        rows = _rows(10, 5, "2026-04") + _rows(10, 40, "2026-09")
        got = te.calls_per_task(db(rows))
        months = got["by_month"]
        assert months["2026-04"]["median"] == 5
        assert months["2026-09"]["median"] == 40


class TestWhereTheTurnsGo:
    def test_the_mix_is_ranked_by_calls_and_carries_the_read_cost(self, sidecar):
        lines = [
            json.dumps({"tool_name": "Bash", "cache_read": 500_000}) + "\n" for _ in range(8)
        ] + [json.dumps({"tool_name": "Edit", "cache_read": 100_000}) + "\n" for _ in range(2)]
        got = te.tool_mix(sidecar(lines))
        assert got["calls"] == 10
        assert got["tools"][0]["tool"] == "Bash" and got["tools"][0]["share"] == 80.0
        assert got["tools"][0]["cache_read"] == 4_000_000

    def test_a_half_written_tail_line_is_skipped_not_refused(self, sidecar):
        """The file is append-only and a session may be writing into it right now."""
        got = te.tool_mix(sidecar([json.dumps({"tool_name": "Bash"}) + "\n", '{"tool_na']))
        assert got["calls"] == 1


class TestAbsenceIsStatedInWords:
    def test_no_database_is_absent_not_zero(self, tmp_path):
        assert te.calls_per_task(str(tmp_path / "none.db")) == {}
        text = te.render(te.report(str(tmp_path / "none.db"), str(tmp_path / "none.jsonl")))
        assert "absent, not zero" in text

    def test_too_few_closures_says_so_instead_of_giving_a_median(self, db, tmp_path):
        rep = te.report(db(_rows(te.MIN_TASKS - 1, 12)), str(tmp_path / "none.jsonl"))
        text = te.render(rep)
        assert "describe the sample" in text
        assert "median" not in text.split("Tool mix")[0].replace("a median", "")

    def test_no_sidecar_is_absent_while_the_task_half_still_reports(self, db, tmp_path):
        """The two halves fail independently: a machine can have closures recorded and no
        sidecar, and the report must still give the number it does have."""
        text = te.render(te.report(db(_rows(30, 12)), str(tmp_path / "none.jsonl")))
        assert "no telemetry sidecar" in text
        assert "Turns per finished task over 30" in text


class TestTheConclusionFollowsTheMeasurement:
    def test_the_report_says_fewer_turns_not_shorter_ones(self, db, sidecar):
        """AC-4. The 99.5% cache_read measurement makes a shorter-request lever worth a few
        hundred tokens and an extra turn worth about 482,000; a report that recommended the
        first would contradict the number it prints two lines above."""
        text = te.render(te.report(db(_rows(30, 12)), sidecar([])))
        assert "fewer, larger turns" in text
        assert "hundred to one" in text

    def test_the_money_line_uses_the_measured_price_of_a_turn(self, db, tmp_path):
        """The constant and the sentence that spends it, checked together: a price pinned
        in one place and printed from another is two numbers waiting to disagree."""
        assert te.CACHE_READ_PER_CALL == 482_000
        text = te.render(te.report(db(_rows(30, 10)), str(tmp_path / "none.jsonl")))
        assert "4.8M per median task" in text


class TestTheLiveTree:
    def test_the_report_runs_on_this_machine_and_says_something(self):
        rep = te.report(
            str(_REPO / ".tausik" / "tausik.db"), str(_REPO / ".tausik" / "token_metrics.jsonl")
        )
        text = te.render(rep)
        if not rep.get("per_task"):
            pytest.skip("this checkout records no call counts")
        assert "Turns per finished task" in text
        assert rep["per_task"]["median"] > 0
