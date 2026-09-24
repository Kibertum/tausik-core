"""A multi-line argument through tausik.cmd is refused out loud, never truncated
(cmd-wrapper-silently-truncates-multiline-arguments).

cmd.exe ends a command line at a newline, so the second line of an argument can
never reach the CLI through the wrapper. Measured in session #267: the guard
refused `task update --acceptance-criteria "<two lines>"` and named what was lost.
This pins that the refusal covers a newline, for every free-text field alike —
the guard compares the whole line, not a list of options.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from cmdline_fidelity import describe_mismatch  # noqa: E402

_PREFIX = "C:\\Windows\\system32\\cmd.exe /c D:\\p\\.tausik\\tausik.cmd"


@pytest.mark.parametrize(
    "flag",
    ["--acceptance-criteria", "--goal", "--notes", "--rationale"],
)
def test_the_lost_second_line_is_reported(flag):
    raw = f'{_PREFIX} task update t {flag} "1. first line\n2. second line"'
    arrived = ["task", "update", "t", flag, "1. first line"]
    message = describe_mismatch(arrived, raw)
    assert message is not None
    assert "2. second line" in message


def test_a_single_line_value_passes():
    raw = f'{_PREFIX} task update t --goal "one line"'
    assert describe_mismatch(["task", "update", "t", "--goal", "one line"], raw) is None
