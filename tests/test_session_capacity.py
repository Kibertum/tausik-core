"""Tests for agent-native session capacity gate."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend
from project_service import ProjectService
from tausik_utils import ServiceError


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
    def test_blocks_when_overshoot(self, svc):
        svc.session_start()
        _ready_task(svc, "big", budget=300)
        with pytest.raises(ServiceError, match="capacity"):
            svc.task_start("big")

    def test_passes_under_budget(self, svc):
        svc.session_start()
        _ready_task(svc, "small", budget=50)
        svc.task_start("small")
        assert svc.be.task_get("small")["status"] == "active"

    def test_no_session_is_a_refusal_not_a_pass(self, svc):
        """v2-session-split-and-drop. This test used to assert the OPPOSITE —
        "no session_start -> capacity check is no-op" — and that pinned a
        fail-open: the 200-call gate stopped gating and said nothing. It also
        inverted the incentive, because the cheapest way past a capacity refusal
        was to end the session and never start another.

        An absent session is not unlimited capacity; it is an unmeasured one."""
        _ready_task(svc, "t", budget=300)
        with pytest.raises(ServiceError, match="no session is open"):
            svc.task_start("t")
        assert svc.be.task_get("t")["status"] == "planning"

    def test_the_refusal_names_what_else_a_missing_session_switches_off(self, svc):
        """A missing session also silences usage telemetry, token metrics and
        model pinning — all of which fail by recording nothing. The refusal is
        the only place an agent is told, so it has to say it."""
        _ready_task(svc, "t", budget=300)
        with pytest.raises(ServiceError) as exc:
            svc.task_start("t")
        assert "tausik session start" in str(exc.value)
        assert "telemetry" in str(exc.value)

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
    runs the same check."""

    def test_unblock_blocks_when_overshoot(self, svc):
        svc.session_start()
        _ready_task(svc, "big", budget=300)
        # Burn capacity with a smaller task that's allowed to start
        _ready_task(svc, "small", budget=150)
        svc.task_start("small")
        # Now manually create a blocked state on `big` (skip task_start
        # capacity check by adding+blocking via direct backend update —
        # simulates task that was blocked before capacity was burned)
        svc.be.task_update("big", status="blocked")
        with pytest.raises(ServiceError, match="capacity"):
            svc.task_unblock("big")

    def test_unblock_force_bypasses_capacity(self, svc):
        """force=True is the audit-logged escape hatch."""
        svc.session_start()
        _ready_task(svc, "big", budget=300)
        _ready_task(svc, "small", budget=150)
        svc.task_start("small")
        svc.be.task_update("big", status="blocked")
        msg = svc.task_unblock("big", force=True)
        assert "unblocked" in msg
        assert svc.be.task_get("big")["status"] == "active"

    def test_unblock_passes_when_under_capacity(self, svc):
        """Capacity available → unblock proceeds normally."""
        svc.session_start()
        _ready_task(svc, "small", budget=80)
        svc.be.task_update("small", status="blocked")
        msg = svc.task_unblock("small")
        assert "unblocked" in msg
        assert svc.be.task_get("small")["status"] == "active"

    def test_unblock_without_session_is_refused(self, svc):
        """Unblocking returns a task to active, so it consumes capacity exactly
        like a start. It used to be exempt because the gate no-oped without a
        session — same fail-open, second door."""
        _ready_task(svc, "t", budget=300)
        svc.be.task_update("t", status="blocked")
        with pytest.raises(ServiceError, match="no session is open"):
            svc.task_unblock("t")


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
