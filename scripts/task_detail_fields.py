"""The task fields a detail view shows — one list for the CLI and the MCP server.

mcp-task-show-hides-the-fields-the-agent-is-judged-by: `task show` printed
twenty-six fields and `tausik_task_show` six, so an agent working MCP-first was
never shown scope_paths (the ACL scope_write_gate refuses writes by) or
rollback_plan (SENAR Rule 6). Two copies of a field list drift; this is the one.
"""

from __future__ import annotations

from typing import Any

TASK_DETAIL_FIELDS: tuple[str, ...] = (
    "story_slug",
    "epic_slug",
    "role",
    "stack",
    "complexity",
    "goal",
    "acceptance_criteria",
    "scope",
    "scope_exclude",
    "scope_paths",
    "scope_tools",
    "rollback_plan",
    "notes",
    "started_at",
    "completed_at",
    "blocked_at",
    "relevant_files",
    "tracker_refs",
    "defect_of",
    "claimed_by",
    "attempts",
    "started_model_id",
    "started_model_version",
    "done_model_id",
    "done_model_version",
    "model_mismatch",
)


def detail_lines(task: dict[str, Any]) -> list[str]:
    """`field: value` for every listed field that is set; an empty one prints nothing."""
    return [f"{field}: {task[field]}" for field in TASK_DETAIL_FIELDS if task.get(field)]
