"""The autonomy promise is a number, and the number refuses to punish conversation.

WHAT IS BEING MADE CHECKABLE. "The agent works autonomously through your plan" is words until it
is closures per owner message. Measured on this project's own session #277: 68 owner messages
against 5644 tool results and 43 harness notifications, 3 of those messages asking only to carry
on, and 44 task closures — 0.65 closures per message and 0.07 stops per closure, against the
0.32 the task recorded as its starting point.

THE TWO REFUSALS THAT MAKE IT HONEST, both pinned below:

* A message carrying a NEW instruction is not a stop, however it is worded. Otherwise the metric
  scores a conversation about plans as a failure and the first real discussion ruins it. The
  owner is allowed to talk; the agent is not allowed to freeze.
* The verdict says out loud that it is descriptive. It reports one transcript that exists; it
  forecasts nothing, exactly like risk and calibration in this project.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

from autonomy_metric import Counts, count, is_stop, owner_text, render  # noqa: E402


@pytest.mark.parametrize(
    "text,expected,why",
    [
        ("продолжай", True, "a bare request to carry on is the owner undoing a freeze"),
        ("Продолжай.", True, "punctuation and case do not change what it asks for"),
        ("continue", True, "same in English"),
        ("keep going", True, "same"),
        ("не останавливайся", True, "the plainest form of the same request"),
        (
            "продолжай, но сначала почини гейт",
            False,
            "AC-4: it carries an instruction, so counting it would punish the conversation",
        ),
        (
            "continue with the site task",
            False,
            "AC-4 in English: an instruction, not a nudge",
        ),
        ("что у нас со статусом?", False, "a question is not a stop"),
        ("", False, "nothing is not a stop"),
    ],
)
def test_only_a_bare_nudge_counts_as_a_stop(text, expected, why):
    assert is_stop(text) is expected, why


@pytest.mark.parametrize(
    "record,expected",
    [
        ({"type": "assistant", "message": {"content": "hi"}}, None),
        ({"type": "user", "message": {"content": [{"type": "tool_result"}]}}, None),
        ({"type": "user", "message": {"content": "<system-reminder>x</system-reminder>"}}, None),
        ({"type": "user", "message": {"content": "[SYSTEM NOTIFICATION] done"}}, None),
        ({"type": "user", "message": {"content": "Base directory for this skill: d:\\x"}}, None),
        ({"type": "user", "message": {"content": "   "}}, None),
        ({"type": "user", "message": {"content": "работай автономно"}}, "работай автономно"),
        (
            {"type": "user", "message": {"content": [{"type": "text", "text": "go on"}]}},
            "go on",
        ),
    ],
)
def test_the_owners_words_are_separated_from_everything_else(record, expected):
    """AC-2: most `user` records are not from the user.

    Tool results, reminders, notifications and injected skill bodies all arrive in that role. On
    the measured transcript they outnumbered real messages 5687 to 68, so a count that skipped
    this separation would be wrong by two orders of magnitude rather than slightly.
    """
    assert owner_text(record) == expected


def test_the_verdict_says_it_is_descriptive():
    """AC-5: the sentence is part of the output, not of the documentation around it."""
    text = render(Counts(owner_messages=10, stops=1, closures=5))
    assert "DESCRIPTIVE, NOT PREDICTIVE" in text
    assert "not a promise" in text
    assert "new instruction is NOT counted" in text


def test_the_rates_are_arithmetic_and_survive_zero():
    """A session with no closures must not divide by zero and must not read as perfect."""
    assert Counts(10, 2, 5).closures_per_message == 0.5
    assert Counts(10, 2, 5).stops_per_closure == 0.4
    assert Counts(0, 0, 0).closures_per_message == 0.0
    assert Counts(3, 3, 0).stops_per_closure == 0.0


def test_it_counts_a_real_transcript(tmp_path):
    """End to end over a file, including the tail line a live transcript often has half-written."""
    p = tmp_path / "t.jsonl"
    rows = [
        {"type": "user", "message": {"content": "работай автономно"}},
        {"type": "user", "message": {"content": [{"type": "tool_result"}]}},
        {"type": "assistant", "message": {"content": "ok"}},
        {"type": "user", "message": {"content": "продолжай"}},
        {"type": "user", "message": {"content": "<system-reminder>noise</system-reminder>"}},
        {"type": "user", "message": {"content": "продолжай, но сперва почини гейт"}},
    ]
    with io.open(p, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        fh.write('{"type": "user", "message": {"content": "hal')  # truncated tail
    counts = count(p, closures=6)
    assert counts.owner_messages == 3, "three real messages, the rest is machinery"
    assert counts.stops == 1, "only the bare nudge; the one with an instruction is not a stop"
    assert counts.closures_per_message == 2.0
