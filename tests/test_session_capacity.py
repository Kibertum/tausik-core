"""Tests for agent-native session capacity gate."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend
from project_service import ProjectService


def _make_service(db_path: str) -> ProjectService:
    return ProjectService(SQLiteBackend(db_path))


@pytest.fixture
def svc(tmp_path):
    s = _make_service(str(tmp_path / "cap.db"))
    s.epic_add("e", "Epic")
    s.story_add("e", "s", "Story")
    yield s
    s.be.close()


def _ready_task(svc, slug: str, *, budget: int | None = None) -> None:
    svc.task_add("s", slug, "T", role="developer", goal="g", call_budget=budget)
    svc.be.task_update(slug, acceptance_criteria="Returns 400 on invalid input.")


# === Backend session_capacity_summary ===


class TestSummary:
    def test_no_active_session(self, svc):
        out = svc.be.session_capacity_summary(200)
        assert out["session"] is None
        assert out["used"] == 0
        assert out["remaining"] == 200

    def test_with_session_no_tasks(self, svc):
        svc.session_start()
        out = svc.be.session_capacity_summary(200)
        assert out["session"] is not None
        assert out["used"] == 0
        assert out["planned_active"] == 0
        assert out["remaining"] == 200

    def test_planned_active_counted(self, svc):
        svc.session_start()
        _ready_task(svc, "t1", budget=80)
        svc.task_start("t1")
        out = svc.be.session_capacity_summary(200)
        assert out["planned_active"] == 80
        assert out["remaining"] == 120


# === task_start enforcement ===


class TestEnforcement:
    """Capacity is a SIGNAL since 1.10 (decision #376): the numbers are printed
    with the start and never refuse it. Until 1.10 every test here asserted a
    refusal; measured over 70 sessions the refusal ended 13 of them and drove
    nine restarts in a row, while the gate had no declared prevented effect
    (SENAR 1.5 §8.6(a)) and so was never a Quality Gate."""

    # The "overshoot starts with an advisory" case lives once, in
    # tests/test_session_signal_not_gate.py — the dedupe gate counts shapes.

    def test_passes_under_budget(self, svc):
        svc.session_start()
        _ready_task(svc, "small", budget=50)
        result = svc.task_start("small")
        assert svc.be.task_get("small")["status"] == "active"
        assert "Session capacity" not in result

    def test_no_session_is_named_not_passed_over_in_silence(self, svc):
        """v2-session-split-and-drop kept one thing from the refusal era: an
        absent session is UNMEASURED capacity, not unlimited, and the agent is
        told so. What changed in 1.10 is the consequence — the task starts."""
        _ready_task(svc, "t", budget=300)
        result = svc.task_start("t")
        assert svc.be.task_get("t")["status"] == "active"
        assert "no session is open" in result

    def test_the_advisory_names_what_else_a_missing_session_switches_off(self, svc):
        """A missing session also silences token metrics, model pinning and the
        per-session brain slice — all of which fail by recording nothing. The
        advisory is the only place an agent is told, so it has to say it."""
        _ready_task(svc, "t", budget=300)
        result = svc.task_start("t")
        assert "tausik session start" in result
        assert "model pinning" in result

    def test_a_budgetless_task_still_starts_without_a_session(self, svc):
        """The gate only has an opinion about tasks that declared a budget —
        widening it to every task would make a session mandatory for work that
        never asked to be accounted."""
        _ready_task(svc, "no-budget")
        svc.task_start("no-budget")
        assert svc.be.task_get("no-budget")["status"] == "active"

    def test_no_block_without_budget(self, svc):
        svc.session_start()
        _ready_task(svc, "no-budget")
        svc.task_start("no-budget")
        assert svc.be.task_get("no-budget")["status"] == "active"

    def test_zero_budget_no_block(self, svc):
        svc.session_start()
        _ready_task(svc, "zero", budget=0)
        svc.task_start("zero")
        assert svc.be.task_get("zero")["status"] == "active"


# v1.3.4 (med-batch-2-qg #4): task_unblock also checks capacity.


class TestUnblockEnforcement:
    """Pre-v1.3.4 bypass: agent could block-then-unblock to dodge the
    session capacity check that fires on task_start. task_unblock now
    runs the same check. Since v77 every unblock states its criterion
    (`--criterion-met`); the capacity fixtures below carry one."""

    def test_unblock_overshoot_is_an_advisory_not_a_refusal(self, svc):
        svc.session_start()
        _ready_task(svc, "big", budget=300)
        # Burn capacity with a smaller task that's allowed to start
        _ready_task(svc, "small", budget=150)
        svc.task_start("small")
        # A blocked state created directly — the task was blocked before the
        # capacity was burned.
        svc.be.task_update("big", status="blocked")
        msg = svc.task_unblock("big", criterion_met="capacity fixture: criterion met")
        assert "unblocked" in msg
        assert "exceeds remaining" in msg
        assert svc.be.task_get("big")["status"] == "active"

    # The force-retired route (TypeError before any service code runs) lives
    # ONCE, in tests/test_session_signal_not_gate.py — the dedupe gate counts
    # shapes, and this file already carried an identical one until v77.

    def test_unblock_passes_when_under_capacity(self, svc):
        """Capacity available → unblock proceeds normally."""
        svc.session_start()
        _ready_task(svc, "small", budget=80)
        svc.be.task_update("small", status="blocked")
        msg = svc.task_unblock("small", criterion_met="capacity fixture: criterion met")
        assert "unblocked" in msg
        assert svc.be.task_get("small")["status"] == "active"

    def test_unblock_without_session_names_the_absent_session(self, svc):
        """Unblocking returns a task to active, so it gets the same signal a
        start gets: an absent session is named, not passed over in silence."""
        _ready_task(svc, "t", budget=300)
        svc.be.task_update("t", status="blocked")
        msg = svc.task_unblock("t", criterion_met="capacity fixture: criterion met")
        assert "unblocked" in msg
        assert "no session is open" in msg
        assert svc.be.task_get("t")["status"] == "active"


# === The gauge counts THIS shift, not a closed task's whole life ===


class TestCapacityCountsThisShiftOnly:
    """OBSERVED IN SESSION #236, on live data. Sixteen minutes and about
    twenty-five tool calls into a shift, `tausik status` printed:

        Capacity: 419/200 used, 0 planned, -219 remaining ⚠ overshoot

    The gauge summed `call_actual` over tasks CLOSED since the session started,
    and `call_actual` is a task's WHOLE LIFE. `release-18-breaking-change-notes`
    had accrued 395 calls since session #177 against a budget of 12; closing it
    dropped all 395 onto a shift that had barely begun.

    WHY IT MATTERS: the operating rule is "end the shift on capacity, do not
    force it". A gauge reading 419 after twenty-five calls stops work for no
    reason — and does it exactly when a long-standing task is finally closed,
    which is the moment the shift was most productive.

    WHY IT SURVIVED: "lifetime calls of tasks closed this shift" and "calls made
    this shift" agree whenever a task opens and closes inside one shift, which
    is the ordinary case.
    """

    def _record_calls(self, svc, session_id: int, n: int) -> None:
        for _ in range(n):
            svc.be._ex(
                # `source` is a closed list in the schema; `posttool` is the one
                # a real tool call carries, so the fixture writes what production does.
                "INSERT INTO usage_events(session_id, source, recorded_at) VALUES(?,?,?)",
                (session_id, "posttool", "2026-09-08T00:00:00Z"),
            )

    def test_a_long_lived_task_does_not_dump_its_life_on_this_shift(self, svc):
        svc.session_start()
        out = svc.be.session_capacity_summary(200)
        session_id = out["session"]

        _ready_task(svc, "old", budget=12)
        svc.task_start("old")
        # The task's lifetime counter, as it stood after several shifts.
        svc.be.task_update("old", call_actual=395)
        svc.be.task_update("old", status="done", completed_at="2099-01-01T00:00:00Z")

        self._record_calls(svc, session_id, 56)

        out = svc.be.session_capacity_summary(200)
        assert out["used"] == 56, (
            f"used={out['used']} — the closed task's 395 lifetime calls leaked into a "
            "shift that made 56"
        )
        assert out["remaining"] == 200 - 56

    def test_calls_from_another_session_are_not_counted(self, svc):
        """Two REAL sessions, because `usage_events.session_id` is a foreign key
        and a fabricated id is refused — the schema making the point for us."""
        svc.session_start()
        first = svc.be.session_capacity_summary(200)["session"]
        self._record_calls(svc, first, 40)
        svc.session_end()

        svc.session_start()
        second = svc.be.session_capacity_summary(200)["session"]
        assert second != first
        self._record_calls(svc, second, 5)

        assert svc.be.session_capacity_summary(200)["used"] == 5, (
            "the previous shift's calls were charged to this one"
        )

    def test_no_session_still_yields_the_full_capacity(self, svc):
        """AC3. "Nothing measured" and "nothing spent" must not collapse: with
        no open session the gauge reports no session at all, rather than zero
        usage against a shift that does not exist."""
        out = svc.be.session_capacity_summary(200)
        assert out["session"] is None
        assert out["used"] == 0
        assert out["remaining"] == 200

    def test_an_empty_ledger_is_zero_used_but_a_session_is_still_named(self, svc):
        """AC6. Distinguishable from the state above: the shift exists and has
        spent nothing yet."""
        svc.session_start()
        out = svc.be.session_capacity_summary(200)
        assert out["session"] is not None
        assert out["used"] == 0

    def test_planned_is_still_the_budget_of_active_tasks(self, svc):
        """AC4. `planned_active` is about the FUTURE and does not depend on the
        shift, so this change must leave it exactly as it was."""
        svc.session_start()
        session_id = svc.be.session_capacity_summary(200)["session"]
        _ready_task(svc, "t9", budget=80)
        svc.task_start("t9")
        self._record_calls(svc, session_id, 7)

        out = svc.be.session_capacity_summary(200)
        assert out["planned_active"] == 80
        assert out["used"] == 7
        assert out["remaining"] == 200 - 7 - 80
