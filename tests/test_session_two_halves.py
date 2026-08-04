"""The "session" concept is TWO things. This file pins the boundary.

v2-session-split-and-drop, decision #223. `sessions` glues together:

  (1) WORK CONTINUITY — the handoff: what was done, what is in flight, what to
      do next, what to watch out for. A property of the WORK.
  (2) AGENT CONTEXT HYGIENE — the 180 active-minute limit (SENAR 9.2), the
      200-call capacity budget, the checkpoint counter (SENAR 9.3). A property
      of the AGENT's context window.

The task these tests come from proposed DROPPING (1) on the grounds that the
git-native projection had taken over its role. That premise was measured and
REFUTED — see `TestTheDropConditionIsNotMet` below, which is the executable
form of decision #223. Half (1) stays; the COUPLING between the halves goes.

These are not unit tests of a function. They are the boundary itself, written
down somewhere a change has to walk past.
"""

from __future__ import annotations

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPTS = os.path.join(_ROOT, "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402


@pytest.fixture
def svc(tmp_path):
    return ProjectService(SQLiteBackend(str(tmp_path / "t.db")))


class TestTheDropConditionIsNotMet:
    """Decision #223, as a gate rather than as prose.

    Continuity may be dropped only once the tree genuinely carries it. Each
    test below is one half of that condition. If one ever goes RED, that is not
    a regression — it is the signal that the condition has changed and #223 is
    due for review. The failure messages say so.
    """

    def test_sessions_are_not_a_projected_kind(self):
        from state_serialize import ENTITY_DIRS

        assert "sessions" not in ENTITY_DIRS, (
            "sessions became a projected kind. Decision #223 refused to drop "
            "work continuity BECAUSE the tree did not carry it; that reason may "
            "no longer hold. Re-open v2-session-split-and-drop rather than "
            "deleting this assertion."
        )

    def test_the_projection_is_off_unless_a_project_opts_in(self, tmp_path):
        """The other half of the condition. Even if sessions became projected,
        a default-off mechanism cannot be the sole home of a document every
        project needs."""
        from state_triggers import _auto_export_enabled

        assert _auto_export_enabled(str(tmp_path / ".tausik")) is False, (
            "state.auto_export now defaults ON for a project with no config. "
            "See decision #223 before relying on it."
        )

    def test_handoff_carries_fields_the_tree_has_no_column_for(self, svc):
        """`next_steps` and `warnings` live nowhere but `sessions.handoff`. The
        tree carries what CHANGED (task status, journal, decisions, memory); it
        does not carry where someone STOPPED."""
        svc.session_start()
        svc.session_handoff(
            {
                "summary": "s",
                "next_steps": ["do the thing"],
                "warnings": ["mind the other thing"],
            }
        )
        got = svc.session_last_handoff()
        assert got["next_steps"] == ["do the thing"]
        assert got["warnings"] == ["mind the other thing"]


class TestContinuityDoesNotDependOnTheHygieneWindow:
    """Half (1) must survive half (2) being over. That is the whole point of
    calling them two things."""

    def test_handoff_survives_a_closed_session(self, svc):
        svc.session_start()
        svc.session_end("done for now")
        msg = svc.session_handoff({"summary": "after the window closed"})
        assert "Handoff saved" in msg
        assert svc.session_last_handoff()["summary"] == "after the window closed"

    def test_saving_a_handoff_does_not_touch_the_checkpoint_counter(self, svc):
        """The counter is HYGIENE. It used to be reset as a side effect of
        writing the continuity document — two halves in one function."""
        svc.session_start()
        svc.be.meta_set("tool_call_count", "37")
        svc.session_handoff({"summary": "s"})
        assert svc.be.meta_get("tool_call_count") == "37"

    def test_the_counter_reset_exists_as_its_own_named_operation(self, svc):
        sys.path.insert(0, os.path.join(_ROOT, "harness", "claude", "mcp", "project"))
        from handlers_session import reset_checkpoint_counter

        svc.be.meta_set("tool_call_count", "37")
        reset_checkpoint_counter(svc)
        assert svc.be.meta_get("tool_call_count") == "0"


class TestHygieneDoesNotFailOpen:
    """Half (2) must refuse when it cannot measure, not wave things through."""

    def test_capacity_gate_refuses_without_a_session(self, svc):
        svc.epic_add("e", "E")
        svc.story_add("e", "s", "S")
        svc.task_add("s", "t", "T", goal="g", role="developer")
        svc.task_update(
            "t",
            acceptance_criteria="1. works\n2. Returns an error on invalid input",
            call_budget=300,
        )
        with pytest.raises(ServiceError, match="no session is open"):
            svc.task_start("t")


class TestNothingWasDeleted:
    """#223 split the concept; it removed nothing. The session-keyed metrics
    that exist keep existing — a refactor that quietly emptied them would have
    traded a silent failure for a different silent failure."""

    def test_session_keyed_metrics_still_populate(self, svc):
        svc.session_start()
        svc.session_end("S1")
        metrics = svc.be.get_metrics()
        assert metrics["sessions_total"] >= 1
        assert "session_hours" in metrics

    def test_audit_cadence_still_counts_sessions(self, svc):
        """SENAR Rule 9.5 counts SESSIONS since the last audit — one of the
        things that genuinely needs the session as a unit."""
        svc.session_start()
        svc.audit_mark()
        svc.session_end("S1")
        for _ in range(3):
            svc.session_start()
            svc.session_end("more")
        assert svc.be.session_current() is None
        svc.session_start()
        assert svc.audit_overdue_sessions() >= 3
