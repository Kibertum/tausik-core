"""Both write gates answer "is this file ours?" with the SAME answer.

Jurisdiction itself -- outside allowed, inside gated, prefix sibling, `..`
escape, unclassifiable input -- is already held by
`test_hooks.py::TestTaskGateJurisdiction` against the real hook process. This
file does not restate any of that. It covers the two things that class cannot
see, because both are about the answer being SHARED:

  1. a target on a different DRIVE, where containment is impossible by
     construction and both `commonpath` and `relpath` raise;
  2. the two gates agreeing, since the rule used to be implemented twice.

`task_gate` read a path-arithmetic failure as "not proven outside" and blocked;
`scope_write_gate` read it as "outside" and allowed. On Windows a cross-drive
target makes both raise, so one and the same file was refused via Write and
written via a Bash heredoc a call later -- `bash_write_gate` reuses
`scope_write_gate`. The strongest available evidence of being outside was
handled as the weakest, and the gate became cheaper to bypass than to satisfy.
`hook_policy.classify_target` is now the single answer both call.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "hooks"))

from hook_policy import classify_target  # noqa: E402
from scope_write_gate import _relative_to_project  # noqa: E402
from task_gate import target_is_outside_project  # noqa: E402

_OTHER_DRIVE_ONLY = pytest.mark.skipif(
    os.name != "nt", reason="drive letters are a Windows concept"
)


def _stdin_for(path: str) -> str:
    return json.dumps({"tool_name": "Write", "tool_input": {"file_path": path}})


def _cross_drive_path(root: str) -> str:
    """A path that CANNOT be inside `root`, because it is on another drive."""
    other = "C:" if not os.path.realpath(root).upper().startswith("C:") else "D:"
    return other + os.sep + os.path.join("tmp", "scratch", "draft.py")


@_OTHER_DRIVE_ONLY
def test_a_path_on_another_drive_is_proven_outside_not_merely_unknown(tmp_path):
    """THE DEFECT, at the level that decides it.

    Containment across drives is impossible by construction, so this is the
    strongest evidence a target can carry. `commonpath` and `relpath` both
    answer it by raising, and the old code read that raise as "could not
    tell" -- the one case where doubt was never warranted.
    """
    verdict, rel = classify_target(_cross_drive_path(str(tmp_path)), str(tmp_path))

    assert verdict == "outside"
    assert rel is None


@_OTHER_DRIVE_ONLY
def test_both_channels_stand_down_on_the_same_cross_drive_target(tmp_path):
    """The asymmetry itself, held so it cannot come back.

    Measured live in session #221: a scratch file under `C:\\...\\Temp`, with
    the project on `D:\\`, refused by the Write gate and accepted by the Bash
    one. Two implementations, opposite verdicts, same path.
    """
    root = str(tmp_path)
    target = _cross_drive_path(root)

    write_channel = target_is_outside_project(_stdin_for(target), root)
    bash_channel = _relative_to_project(target, root)

    assert (write_channel, bash_channel) == (True, None), (
        "the Write gate and the gate the Bash channel reuses disagreed on one path"
    )


def test_both_channels_still_claim_a_target_inside_the_tree(tmp_path):
    """The direction that must NOT loosen, asserted on both channels at once.

    The fix widens what counts as PROVEN outside. Nothing about a file in the
    tree may move with it, and one assertion covering both callers is what
    keeps a future edit from loosening only one of them.
    """
    root = tmp_path / "proj"
    (root / "scripts").mkdir(parents=True)
    target = root / "scripts" / "mod.py"
    target.write_text("x = 1", encoding="utf-8")

    write_channel = target_is_outside_project(_stdin_for(str(target)), str(root))
    bash_channel = _relative_to_project(str(target), str(root))

    assert write_channel is False, "an in-project target must stay gated"
    assert bash_channel == os.path.join("scripts", "mod.py")


def test_a_prefix_sibling_is_out_of_jurisdiction_on_both_channels(tmp_path):
    """`…/core-old` beside `…/core`, checked for AGREEMENT rather than for the
    verdict itself -- which `test_hooks.py` already pins on the real process."""
    root = tmp_path / "core"
    sibling = tmp_path / "core-old"
    root.mkdir()
    sibling.mkdir()
    target = sibling / "f.py"
    target.write_text("x = 1", encoding="utf-8")

    write_channel = target_is_outside_project(_stdin_for(str(target)), str(root))
    bash_channel = _relative_to_project(str(target), str(root))

    assert (write_channel, bash_channel) == (True, None)
