"""Session time and call capacity are SIGNALS, not gates (decision #376, 1.10).

Task `qg0-does-not-refuse-work-for-session-time-or-capacity`, story E of 1.10.
Measured over 70 sessions (#196–#265) one crossed the 180 active-minute limit
(#241) and the capacity gate ended 13 of them; neither check has a declared
prevented effect on the task record QG-0 examines (SENAR 1.5 §8.1, §8.6(a)).
These tests hold the new contract from four sides: the gate function, the
service, the retired flag, and the two documents that state the rule.
"""

from __future__ import annotations

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.join(_ROOT, "bootstrap"))

from gate_qg0_check import check_qg0_start  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "sig.db")))
    s.epic_add("e", "Epic")
    s.story_add("e", "s", "Story")
    yield s
    s.be.close()


def _ready(svc, slug: str, *, budget: int | None = None) -> None:
    svc.task_add("s", slug, "T", role="developer", goal="g", call_budget=budget)
    svc.be.task_update(slug, acceptance_criteria="Returns 400 on invalid input.")


class TestTheGateFunction:
    def test_a_session_overrun_is_a_warning_not_a_refusal(self):
        task = {"goal": "g", "acceptance_criteria": "Returns 400 on invalid input."}
        warnings = check_qg0_start(
            "t", task, session_check_duration_fn=lambda: "Session #1 has 200 min active"
        )
        assert any(w.startswith("SESSION:") and "200 min active" in w for w in warnings)

    def test_the_task_record_is_still_gated(self):
        """NEGATIVE: what QG-0 is FOR did not move — a missing goal still refuses,
        with or without a session warning on the side."""
        with pytest.raises(ServiceError, match="goal"):
            check_qg0_start(
                "t",
                {"goal": "", "acceptance_criteria": "Returns 400 on invalid input."},
                session_check_duration_fn=lambda: "Session #1 has 200 min active",
            )


class TestTheService:
    def test_over_capacity_starts_and_says_so(self, svc):
        svc.session_start()
        _ready(svc, "big", budget=300)
        out = svc.task_start("big")
        assert svc.be.task_get("big")["status"] == "active"
        assert "exceeds remaining" in out
        assert "session-active-time.md" in out  # the basis is named (§9.4(c))

    def test_no_session_starts_and_names_the_unmeasured_capacity(self, svc):
        _ready(svc, "t", budget=300)
        out = svc.task_start("t")
        assert svc.be.task_get("t")["status"] == "active"
        assert "no session is open" in out
        assert "tausik session start" in out

    def test_force_is_refused_with_the_reason_and_changes_nothing(self, svc):
        """NEGATIVE: the retired flag is not silently accepted."""
        svc.session_start()
        _ready(svc, "t", budget=300)
        with pytest.raises(ServiceError, match="retired"):
            svc.task_start("t", force=True)
        assert svc.be.task_get("t")["status"] == "planning"
        actions = [e["action"] for e in svc.be.events_list(entity_type="task", entity_id="t")]
        assert "capacity_force_start" not in actions

    def test_unblock_force_is_refused_too(self, svc):
        svc.session_start()
        _ready(svc, "t", budget=300)
        svc.be.task_update("t", status="blocked")
        with pytest.raises(ServiceError, match="retired"):
            svc.task_unblock("t", force=True)
        assert svc.be.task_get("t")["status"] == "blocked"

    def test_the_capacity_force_event_is_never_written(self, svc):
        svc.session_start()
        _ready(svc, "big", budget=300)
        svc.task_start("big")
        svc.be.task_update("big", status="blocked")
        svc.task_unblock("big")
        actions = [e["action"] for e in svc.be.events_list(entity_type="task", entity_id="big")]
        assert "capacity_force_start" not in actions


class TestTheRuleIsStatedInBothPlaces:
    """CLAUDE.md of the core and the consumer template carry the same rule;
    a test holds them together so the two cannot drift apart again."""

    def test_core_claude_md_states_the_signal_rule(self):
        text = open(os.path.join(_ROOT, "CLAUDE.md"), encoding="utf-8").read()
        assert "сигнал, не ворота" in text
        assert "180 мин ACTIVE" not in text

    def test_consumer_template_states_the_signal_rule(self):
        from bootstrap_templates import HARD_CONSTRAINTS

        assert "Context pressure is a signal, not a gate" in HARD_CONSTRAINTS
        assert "Session limit: 180 min" not in HARD_CONSTRAINTS

    def test_the_cli_help_says_the_flag_is_retired(self):
        from project_parser import build_parser

        parser = build_parser()
        task_p = parser._subparsers._group_actions[0].choices["task"]
        start_p = task_p._subparsers._group_actions[0].choices["start"]
        assert "Retired in 1.10" in start_p.format_help()
