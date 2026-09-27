"""Starting off the plan is said once, with an address, and never refused.

MEASURED on the session that filed this: 22 tasks closed, 4 from the plan that existed
beforehand, 18 filed AND closed inside the same session. Nine of the eighteen were the
owner's instructions. The other nine were findings chased because the context was warm,
four of which the owner then named as work he did not want before a release.

The mechanism is in the cycle, not in the will: `task done` prints a finding, the first
principle says file it — correctly — and then the agent STARTS it, because starting is
cheap right now. `task next` already chooses correctly and was called zero times.

So most of this file is the negative half: silence when the started task IS the plan's
choice, silence when the backlog offers nothing, silence on any internal fault. A line
printed on every start is read on none of them.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import plan_adherence  # noqa: E402


class _Report:
    """A stand-in for the backlog's own answer, in the shape `task_next_report` returns."""

    def __init__(self, payload):
        self.payload = payload

    def __call__(self, _svc):
        return self.payload


@pytest.fixture
def offers(monkeypatch):
    """Make the backlog offer whatever a case needs, without a database."""

    def _set(payload):
        import service_task_order

        monkeypatch.setattr(service_task_order, "task_next_report", _Report(payload))
        return object()

    return _set


READY = {
    "state": "ready",
    "task": {"slug": "cli-ops-residue-split-by-command"},
    "basis": "release 1.10 first, then declared order",
}


class TestItSpeaksWhenThePlanIsDisplaced:
    def test_the_displaced_task_is_named(self, offers):
        svc = offers(READY)
        line = plan_adherence.plan_advisory(svc, "some-finding-i-just-made")
        assert "cli-ops-residue-split-by-command" in line
        assert "some-finding-i-just-made" in line

    def test_the_way_back_is_a_command_and_not_a_scolding(self, offers):
        """A reproach without an address is not an action.

        The line has to end in something the reader can run, or it becomes noise that
        teaches nothing — which is how a warning gets ignored into uselessness.
        """
        svc = offers(READY)
        line = plan_adherence.plan_advisory(svc, "x")
        assert "task start cli-ops-residue-split-by-command" in line

    def test_the_basis_travels_so_the_choice_can_be_argued(self, offers):
        svc = offers(READY)
        assert "release 1.10 first" in plan_adherence.plan_advisory(svc, "x")

    def test_a_missing_basis_does_not_blank_the_line(self, offers):
        """Absence of the reason must not silence the advisory itself."""
        svc = offers({**READY, "basis": None})
        line = plan_adherence.plan_advisory(svc, "x")
        assert line.strip()
        assert "cli-ops-residue-split-by-command" in line


class TestItIsSilentWhereItShouldBe:
    def test_starting_the_planned_task_says_nothing(self, offers):
        """The common case. This is what keeps the line readable on the other one."""
        svc = offers(READY)
        assert plan_adherence.plan_advisory(svc, READY["task"]["slug"]) == ""

    @pytest.mark.parametrize("state", ["empty", "all-blocked", "all-claimed"])
    def test_an_unofferable_backlog_says_nothing(self, offers, state):
        """Nothing is being displaced, so work outside the plan is legitimate.

        Three states rather than one: a backlog that is empty, one where every task
        waits on a predecessor, and one where every task belongs to another agent are
        different facts, and none of them makes this start a departure.
        """
        svc = offers({"state": state, "task": None, "basis": "n/a"})
        assert plan_adherence.plan_advisory(svc, "anything") == ""

    def test_a_malformed_candidate_says_nothing(self, offers):
        """`state: ready` with no usable task is a bug upstream, not a departure here."""
        svc = offers({"state": "ready", "task": None, "basis": "b"})
        assert plan_adherence.plan_advisory(svc, "x") == ""


class TestItIsASignalAndNotAGate:
    def test_an_internal_fault_is_swallowed(self, monkeypatch):
        """An advisory that can break `task start` is a gate with extra steps."""
        import service_task_order

        def boom(_svc):
            raise RuntimeError("backlog exploded")

        monkeypatch.setattr(service_task_order, "task_next_report", boom)
        assert plan_adherence.plan_advisory(object(), "x") == ""

    def test_it_returns_text_and_never_raises_or_exits(self, offers):
        """The only thing it does is produce a string. Nothing to refuse with."""
        svc = offers(READY)
        assert isinstance(plan_adherence.plan_advisory(svc, "x"), str)

    def test_filing_a_finding_is_not_discouraged_only_starting_it(self, offers):
        """The wording matters as much as the trigger.

        Forbidding the FILING would bring back the silent errors this project exists
        against. What the line asks for is deferral, and it has to say so, or the next
        agent will read it as "stop reporting defects".
        """
        svc = offers(READY)
        line = plan_adherence.plan_advisory(svc, "x")
        assert "не запрет" in line.lower()
        assert "откладывать" in line.lower()


class TestItReachesTheRealTaskStart:
    """The wiring. A prompt nobody sees is a comment."""

    @pytest.fixture
    def svc(self, tmp_path):
        from project_backend import SQLiteBackend
        from project_service import ProjectService

        s = ProjectService(SQLiteBackend(str(tmp_path / "plan.db")))
        s.session_start()
        s.epic_add("e", "Epic")
        s.story_add("e", "s", "Story")
        for slug in ("first-in-order", "the-one-i-found"):
            s.task_add("s", slug, slug.replace("-", " "), role="developer", goal="g")
            s.be.task_update(
                slug,
                acceptance_criteria="Returns 400 on invalid input.",
                scope_paths='["scripts/x.py"]',
                rollback_plan="git revert",
            )
        yield s
        s.be.close()

    def test_starting_the_second_one_names_the_first(self, svc):
        offered = svc.task_next()
        assert offered, "the fixture must leave the backlog offering something"
        other = "the-one-i-found" if offered["slug"] == "first-in-order" else "first-in-order"
        out = svc.task_start(other)
        assert "Не по плану" in out
        assert offered["slug"] in out

    def test_starting_the_offered_one_adds_no_line(self, svc):
        offered = svc.task_next()
        assert "Не по плану" not in svc.task_start(offered["slug"])
