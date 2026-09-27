"""The autonomous driver is a skill, so its contract is held by reading it.

A skill is prose the agent follows, which makes it the weakest kind of mechanism — and the
reason this file exists. TAUSIK's autonomy WAS prose in CLAUDE.md, and the measurement that
filed this work says asking does not work: 22 tasks closed in one session, 4 of them from
the plan that existed beforehand. So every promise the skill makes is pinned here, and a
promise that disappears from the text fails the build instead of quietly loosening.

What cannot be checked by reading is that the agent obeys. What CAN be checked is that the
text still says the things it must, names the commands it depends on, and refuses the cases
it must refuse. That is the difference between an instruction and a contract with a test.

The promises are a TABLE rather than a test each: they are the same question asked of
different sentences, and spelling that out twenty times would be the copy-paste the
project's own dedupe ratchet exists to catch — it caught this file on the first run.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SOURCE = _REPO / "harness" / "skills" / "run" / "SKILL.md"
_DEPLOYED = _REPO / ".claude" / "skills" / "run" / "SKILL.md"

CROSSCUTTING_SCOPE = ["harness/skills/", "bootstrap/"]

#: (id, pattern, why it must stay). The `why` is not decoration: it is what tells the next
#: reader whether a failing case should be fixed in the skill or retired from the table.
PROMISES: tuple[tuple[str, str, str], ...] = (
    (
        "asks_the_plan",
        r"task next",
        "the composition in the DB is the source of truth, not a plan file",
    ),
    (
        "asks_every_time",
        r"(before EVERY task|every task, not once)",
        "a list captured up front is stale by its second entry: a close can auto-close a "
        "story, unblock a dependant, or surface a defect that outranks what looked next",
    ),
    (
        "hard_stop",
        r"hard-?stop",
        "a driver that steps over a failure produces a release nobody can account for",
    ),
    (
        "no_auto_retry",
        r"Never auto-?retry",
        "a retry that works the second time hides a flake",
    ),
    (
        "arms_the_ceiling",
        r"TAUSIK_AUTONOMOUS_BUDGET_BLOCK",
        "unattended, an overrun is not information but a session spent on one task",
    ),
    (
        "reads_the_ceiling",
        r"budget-check",
        "arming without checking is decoration",
    ),
    (
        "ceiling_is_an_exit_code",
        r"(exit code|Non-?zero)",
        "the command is silent on success, so reading its output would read nothing",
    ),
    (
        "stops_between_tasks",
        r"(halfway|between tasks)",
        "edits without a close leave the next agent unable to tell what was verified",
    ),
    (
        "refuses_judgement_work",
        r"Do NOT use",
        "guessing at a judgement call produces work someone has to undo",
    ),
    (
        "names_that_class",
        r"judgement|judgment",
        "the refusal must name WHICH work, or it is advice about nothing",
    ),
    (
        "calls_the_task_skill",
        r"/task",
        "QG-0, the scope ACL and the gates live there; bypassing them closes what they "
        "would have refused",
    ),
    (
        "does_not_reimplement_it",
        r"(Never reimplement|does not skip gates)",
        "a driver with its own copy of the close path drifts from the one the gates guard",
    ),
    (
        "no_force",
        r"--force",
        "an unattended run must not carry the one flag that silences a refusal",
    ),
    (
        "does_not_start_its_findings",
        r"(Filing a finding is free|does not file tasks it finds)",
        "THE defect this whole line of work was filed against: filing is free, starting is "
        "the departure that produced 82% self-filed closures",
    ),
    (
        "one_line_between_tasks",
        r"one line",
        "prose between tasks ends the turn, and ending the turn is what this skill avoids",
    ),
    (
        "says_why_prose_is_costly",
        r"(ends a turn|Prose between tasks)",
        "without the reason the rule reads as terseness for its own sake",
    ),
    (
        "one_handoff_per_run",
        r"(once per run|one handoff)",
        "each task already wrote its own; a second per task is the same record twice",
    ),
)

#: The four states `task next` can answer with. Four, not two: 'everything is claimed' is
#: not 'nothing is left', and a driver reading the first as the second stops too early.
BACKLOG_STATES = ("ready", "all-blocked", "all-claimed", "empty")


@pytest.fixture(scope="module")
def text() -> str:
    return _SOURCE.read_text(encoding="utf-8")


class TestTheDriverIsReachable:
    def test_the_source_and_the_deployed_copy_both_exist(self):
        """Two files, one question: a skill only in `harness/` is one nobody can run."""
        assert _SOURCE.is_file(), "the driver is the mechanism; without the file it is a plan"
        assert _DEPLOYED.is_file(), "run bootstrap --ide all: the skill is not in the profile"

    def test_it_is_registered_as_a_core_skill(self):
        """Registration is what carries it into every project, not just this one."""
        cfg = (_REPO / "bootstrap" / "bootstrap_config.py").read_text(encoding="utf-8")
        block = cfg.split('"core_skills"', 1)[1].split("]", 1)[0]
        assert '"run"' in block, "not in core_skills — consumers would never get the driver"


class TestEveryPromiseIsStillInTheText:
    @pytest.mark.parametrize(("name", "pattern", "why"), PROMISES, ids=[p[0] for p in PROMISES])
    def test_the_promise_survives(self, text, name, pattern, why):
        assert re.search(pattern, text, re.IGNORECASE), f"{name} is gone from the skill — {why}"

    @pytest.mark.parametrize("state", BACKLOG_STATES)
    def test_the_state_has_a_decided_case(self, text, state):
        assert state in text, f"state {state} is unmentioned, so its case is undecided"

    def test_the_table_is_not_empty_and_not_a_stub(self):
        """A guard over an empty table passes forever.

        Seventeen promises is what the skill makes today; the floor is here so trimming the
        table to green a failing case shows up as an edit to this number.
        """
        assert len(PROMISES) >= 15
        assert all(len(why) > 30 for _n, _p, why in PROMISES), "a promise needs its reason"


class TestTheSkillStaysReadable:
    def test_it_is_not_enormous(self):
        """A driver nobody reads to the end is a driver that gets half-followed.

        A number so it can be argued with: 9,000 characters is roughly two screens, and
        this file is the contract, not a manual.
        """
        assert len(_SOURCE.read_text(encoding="utf-8")) <= 9000

    def test_it_carries_the_project_required_gotchas_section(self):
        """The project refuses a skill without one, and it refused this skill first."""
        assert "## Gotchas" in _SOURCE.read_text(encoding="utf-8")
