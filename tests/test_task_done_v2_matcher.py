"""r14-task-done-verify-v2: PostToolUse hook matcher must cover task_done_v2.

Pre-1.4 the matcher only knew about `mcp__tausik-project__tausik_task_done`
and the bare `tausik_task_done`. After 1.3.7 introduced
`tausik_task_done_v2` as a structured-response variant, promoting it to
the default skill path would silently disable the verify-fix-loop hook.
This test pins the matcher at the source.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "hooks"))

from _common import _TASK_DONE_TOOL_NAMES, is_task_done_invocation


def test_v1_mcp_name_in_matcher():
    assert "mcp__tausik-project__tausik_task_done" in _TASK_DONE_TOOL_NAMES


def test_v2_mcp_name_in_matcher():
    assert "mcp__tausik-project__tausik_task_done_v2" in _TASK_DONE_TOOL_NAMES


def test_v2_bare_name_in_matcher():
    assert "tausik_task_done_v2" in _TASK_DONE_TOOL_NAMES


def test_is_task_done_invocation_v2():
    assert is_task_done_invocation(
        "mcp__tausik-project__tausik_task_done_v2", {"slug": "x"}
    )
    assert is_task_done_invocation("tausik_task_done_v2", {"slug": "x"})


def test_unrelated_tool_is_not_task_done():
    assert not is_task_done_invocation("Read", {"path": "foo.py"})
    assert not is_task_done_invocation("Edit", {"slug": "x"})
