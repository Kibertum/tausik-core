"""The run stops BETWEEN tasks, never inside one — and never early out of caution.

Both directions are failures and the second is the one that hides. Running into the context wall
mid-task leaves edits nobody can account for. Stopping early leaves the composition half-done
while the context was fine, which is the polite refusal of autonomy the /run skill exists to end.

The measurement behind the numbers, recorded because a threshold without one is a guess: tokens
per call across this project's own sessions run from 562 to 10,958 with a median near 2,200, and
48 of 231 sessions with call data recorded no token figure at all. That spread is why the driver
takes the runtime's own reading instead of inferring one, and that absence is why a missing
reading means GO.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

from run_capacity import (  # noqa: E402
    HANDOFF_RESERVE,
    TASK_RESERVE,
    advisory_line,
    room_to_finish,
)

_NEEDED = TASK_RESERVE + HANDOFF_RESERVE


@pytest.mark.parametrize(
    "remaining,expected,why",
    [
        (None, True, "AC-5: an absent reading is not a measurement of the limit"),
        (-1, True, "a nonsense reading is treated as absent, not as empty"),
        (_NEEDED, True, "exactly enough is enough — the threshold is not a superstition"),
        (_NEEDED + 1, True, "above the line the run continues"),
        (10_000_000, True, "AC-4: a live context must never produce a stop"),
        (_NEEDED - 1, False, "one token short of a full task plus its handoff"),
        (HANDOFF_RESERVE, False, "room for the handoff only"),
        (10, False, "not even the handoff fits — write it now"),
    ],
)
def test_the_verdict_matches_the_reading(remaining, expected, why):
    assert room_to_finish(remaining).go is expected, why


def test_every_verdict_carries_its_reason():
    """A driver that stopped without saying why reads exactly like one that gave up."""
    for reading in (None, 10, HANDOFF_RESERVE, _NEEDED, 10_000_000):
        reason = room_to_finish(reading).reason
        assert len(reason) > 30, f"{reading}: {reason!r} explains nothing"


def test_the_stop_says_to_finish_the_open_task_first():
    """AC-3: the instruction has to name the ORDER, or the driver stops where it stands."""
    reason = room_to_finish(_NEEDED - 1).reason
    assert "Close what is open" in reason and "BETWEEN tasks" in reason


def test_the_last_verdict_says_to_write_the_handoff_now():
    """Below the handoff's own cost the advice changes: there is nothing left to close with."""
    assert "handoff NOW" in room_to_finish(10).reason


def test_the_advisory_is_silent_while_there_is_room():
    """AC-4 in the driver's voice: between tasks it prints one line per close and nothing else,
    because prose is what ends a turn and ending the turn is the failure /run was built against.
    A capacity notice earns its line only when it changes what happens next."""
    assert advisory_line(10_000_000) == ""
    assert advisory_line(None) == ""
    assert advisory_line(10).startswith("/run STOPPING:")


def test_the_reserve_is_a_task_plus_a_tail_not_a_round_number():
    """The threshold is derived from the project's own figures, so it must stay derived.

    A hand-picked round number would drift from the work it describes; these two multiply out of
    the measured cost of a call and the measured length of a task.
    """
    from run_capacity import CALLS_PER_TASK, TOKENS_PER_CALL

    assert TASK_RESERVE == TOKENS_PER_CALL * CALLS_PER_TASK
    assert 0 < HANDOFF_RESERVE < TASK_RESERVE, "the tail is smaller than the task, not a copy of it"


@pytest.mark.parametrize(
    "argv,expected_exit",
    [
        (["--remaining", "10000000"], 0),
        ([], 0),
        (["--remaining", "1000"], 1),
        (["--remaining", str(_NEEDED)], 0),
        (["--remaining", str(_NEEDED - 1)], 1),
    ],
)
def test_the_command_exits_on_the_number(argv, expected_exit, capsys):
    """The skill names a COMMAND, so the command has to carry the decision.

    Autonomy asked for in prose got switched off the same week — the project measured that — and
    the capacity step was the last one still phrased as "judge whether there is room". An exit
    code is a judgement the driver cannot mistake for a suggestion.
    """
    from run_capacity import main

    assert main(argv) == expected_exit
    out = capsys.readouterr().out
    assert bool(out.strip()) is (expected_exit == 1), "it speaks only when it stops the run"
