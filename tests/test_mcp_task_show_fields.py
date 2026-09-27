"""tausik_task_show shows the fields the agent is judged by, like the CLI does.

mcp-task-show-hides-the-fields-the-agent-is-judged-by: the MCP handler listed six
fields (role, stack, complexity, goal, notes, acceptance_criteria), the CLI
twenty-six. scope_paths is the ACL scope_write_gate refuses writes by and
rollback_plan is SENAR Rule 6, so an agent following MCP-first met a limit it
had never been shown. The list now lives once, in scripts/task_detail_fields.py.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project")
)

import handlers
from project_backend import SQLiteBackend
from project_service import ProjectService


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "show.db")))
    s.epic_add("e", "E")
    s.story_add("e", "s", "S")
    s.task_add("s", "t-show", "Show me")
    yield s
    s.be.close()


def _show(svc) -> str:
    return handlers.handle_tool(svc, "tausik_task_show", {"slug": "t-show"})


def test_the_scope_acl_and_the_rollback_plan_are_shown(svc):
    """NEGATIVE — red on the six-field handler."""
    svc.task_update("t-show", scope_paths=["scripts/x.py"], rollback_plan="git revert")
    out = _show(svc)
    assert "scope_paths:" in out and "scripts/x.py" in out
    assert "rollback_plan: git revert" in out


def test_empty_fields_print_nothing(svc):
    """NEGATIVE — a task without them reads as before: no empty headers."""
    out = _show(svc)
    assert "scope_paths" not in out
    assert "rollback_plan" not in out
    assert not [ln for ln in out.splitlines() if ln.rstrip().endswith(":")]


def test_cli_and_mcp_read_one_list():
    import project_cli_task
    import task_detail_fields

    src_cli = open(project_cli_task.__file__, encoding="utf-8").read()
    src_mcp = open(
        handlers.__file__.replace("handlers.py", "handlers_task.py"), encoding="utf-8"
    ).read()
    assert "detail_lines" in src_cli and "detail_lines" in src_mcp
    assert '"rollback_plan",' not in src_mcp  # no second copy of the list
    assert {"scope_paths", "rollback_plan"} <= set(task_detail_fields.TASK_DETAIL_FIELDS)
