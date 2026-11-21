"""Default task-start text stays compact without dropping contract fields."""

from __future__ import annotations

from task_start_compact import append_start_context, compact_start_contract_lines


def test_compact_lines_keep_goal_ac_scope_and_fingerprint_pointer():
    package = {
        "fingerprint": "abc123",
        "required": {
            "goal": "stay compact",
            "acceptance_criteria": "AC remains",
            "scope": "service_task only",
            "scope_exclude": "release cut",
        },
    }
    lines = compact_start_contract_lines(package)
    assert lines == [
        "Goal: stay compact",
        "Acceptance criteria: AC remains",
        "Scope: service_task only",
        "Scope exclude: release cut",
        "Package bound (fingerprint=abc123); full: task show --package / task start --package",
    ]
    assert "Task package:" not in "\n".join(lines)


def test_append_start_context_skips_when_memory_disabled():
    messages: list[str] = ["started"]
    append_start_context(
        messages,
        be=object(),
        slug="work",
        package={"fingerprint": "x", "required": {"goal": "g"}},
        include_memory=False,
    )
    assert messages == ["started"]
