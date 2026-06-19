"""v14b-task-done-rename-drop-v2: matcher pins to single tausik_task_done.

The pre-rename matcher allowed both `tausik_task_done` and the interim
`tausik_task_done_v2` alias to keep the verify-fix-loop hook firing during
the transition. Post-rename only the single name exists. This test pins
the contract: `_TASK_DONE_TOOL_NAMES` must include the MCP-prefixed and
bare forms of `tausik_task_done` and MUST NOT include any `_v2` variant.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "hooks"))

from _common import _TASK_DONE_TOOL_NAMES, is_task_done_invocation


def test_mcp_prefixed_name_in_matcher():
    assert "mcp__tausik-project__tausik_task_done" in _TASK_DONE_TOOL_NAMES


def test_bare_name_in_matcher():
    assert "tausik_task_done" in _TASK_DONE_TOOL_NAMES


def test_v2_aliases_removed():
    """No _v2 variant should remain after the rename."""
    for name in _TASK_DONE_TOOL_NAMES:
        assert not name.endswith("_v2"), (
            f"_v2 alias {name!r} re-introduced — see v14b-task-done-rename-drop-v2."
        )


def test_is_task_done_invocation_for_canonical_name():
    assert is_task_done_invocation("mcp__tausik-project__tausik_task_done", {"slug": "x"})
    assert is_task_done_invocation("tausik_task_done", {"slug": "x"})


def test_unrelated_tool_is_not_task_done():
    assert not is_task_done_invocation("Read", {"path": "foo.py"})
    assert not is_task_done_invocation("Edit", {"slug": "x"})
