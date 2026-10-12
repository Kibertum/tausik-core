"""`metrics calls`: what a closed task spends its tool calls on."""

from __future__ import annotations

import json
import os
import sys

import pytest

CROSSCUTTING_SCOPE = ["scripts/call_mix.py"]

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import call_mix  # noqa: E402


@pytest.mark.parametrize(
    "command,expected",
    [
        ("PYTHONUTF8=1 grep -n foo scripts/x.py", "read"),
        ('PYTHONIOENCODING=utf-8 FOO="a b" sed -n 1,20p x.py', "read"),
        ("cd /repo && sed -i 's/a/b/' x.py", "edit"),
        ("cd /repo; .tausik/tausik task log s 'm'", "ceremony"),
        ("python scripts/project.py task show s", "ceremony"),
        ("python -m pytest -q tests/", "run"),
        ("python - <<'EOF'", "script"),
        ("git log --oneline", "read"),
        ("git commit -m x", "other"),
    ],
)
def test_the_real_command_is_judged_not_its_prefix(command, expected):
    """AC-4: env assignments and cd hops hid the command (PYTHONUTF8=1 ranked third)."""
    assert call_mix.shell_category(command) == expected


def _transcript(tmp_path, calls):
    lines = [
        json.dumps(
            {
                "type": "assistant",
                "message": {"content": [{"type": "tool_use", "name": n, "input": i}]},
            }
        )
        for n, i in calls
    ]
    p = tmp_path / "t.jsonl"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(p)


def test_calls_between_start_and_done_belong_to_the_task(tmp_path):
    path = _transcript(
        tmp_path,
        [
            ("Read", {"file_path": "a"}),  # before any task: unattributed
            ("Bash", {"command": ".tausik/tausik task start fix-a"}),
            ("Grep", {"pattern": "x"}),
            ("Edit", {"file_path": "a"}),
            ("Bash", {"command": ".tausik/tausik task done fix-a --ac-verified"}),
            ("Bash", {"command": ".tausik/tausik task start never-closed"}),
            ("Read", {"file_path": "b"}),
        ],
    )
    per, unattributed = call_mix.attribute([path])
    assert set(per) == {"fix-a"}  # a task with no done in view is not a closed task
    assert per["fix-a"]["read"] == 1 and per["fix-a"]["edit"] == 1 and per["fix-a"]["ceremony"] == 2
    assert per["fix-a"]["responses"] == 4
    assert unattributed == 1


def test_parallel_reads_are_one_model_response_but_keep_every_tool_call(tmp_path):
    path = tmp_path / "parallel.jsonl"
    messages = [
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "input": {"command": ".tausik/tausik task start fan-out"},
                    }
                ]
            },
        },
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "tool_use", "name": "Read", "input": {"file_path": "a"}},
                    {"type": "tool_use", "name": "Grep", "input": {"pattern": "x"}},
                ]
            },
        },
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "input": {"command": ".tausik/tausik task done fan-out"},
                    }
                ]
            },
        },
    ]
    path.write_text("\n".join(json.dumps(row) for row in messages), encoding="utf-8")
    per, _ = call_mix.attribute([str(path)])
    assert per["fan-out"]["read"] == 2
    assert per["fan-out"]["responses"] == 3


def test_one_compound_read_replaces_separate_read_tool_calls(tmp_path):
    separate = _transcript(
        tmp_path,
        [
            ("Bash", {"command": ".tausik/tausik task start separate"}),
            ("Read", {"file_path": "a"}),
            ("Read", {"file_path": "b"}),
            ("Bash", {"command": ".tausik/tausik task done separate"}),
        ],
    )
    per, _ = call_mix.attribute([separate])
    compound = _transcript(
        tmp_path,
        [
            ("Bash", {"command": ".tausik/tausik task start compound"}),
            ("PowerShell", {"command": "Get-Content a; Get-Content b"}),
            ("Bash", {"command": ".tausik/tausik task done compound"}),
        ],
    )
    batched, _ = call_mix.attribute([compound])
    assert per["separate"]["read"] == 2
    assert batched["compound"]["read"] == 1


def test_native_codex_calls_keep_task_boundaries_and_response_rounds(tmp_path):
    records = []

    def turn(source):
        records.extend(
            [
                {"type": "event_msg", "payload": {"type": "task_started"}},
                {
                    "type": "response_item",
                    "payload": {"type": "custom_tool_call", "name": "exec", "input": source},
                },
                {"type": "event_msg", "payload": {"type": "task_complete"}},
            ]
        )

    turn('tools.exec_command({cmd:".tausik/tausik task start codex-task"})')
    turn('tools.exec_command({cmd:"rg -n one a; rg -n two b"})')
    turn('tools.exec_command({cmd:".tausik/tausik task done codex-task"})')
    path = tmp_path / "codex.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in records), encoding="utf-8")
    per, unattributed = call_mix.attribute([str(path)])
    assert per["codex-task"]["read"] == 1
    assert per["codex-task"]["ceremony"] == 2
    assert per["codex-task"]["responses"] == 3
    assert unattributed == 0


def test_failed_done_attempt_is_not_reported_as_an_accepted_task(tmp_path):
    path = _transcript(
        tmp_path,
        [
            ("Bash", {"command": ".tausik/tausik task start gate-blocked"}),
            ("Read", {"file_path": "a"}),
            ("Bash", {"command": ".tausik/tausik task done gate-blocked"}),
        ],
    )
    per, _ = call_mix.attribute([path])
    tasks = [{"slug": "gate-blocked", "status": "active"}]
    assert call_mix.completed_only(per, tasks) == {}


def test_project_state_admits_only_successfully_completed_windows():
    per = {
        "accepted": dict.fromkeys(call_mix.CATEGORIES, 1),
        "blocked": dict.fromkeys(call_mix.CATEGORIES, 2),
    }
    tasks = [
        {"slug": "accepted", "status": "done"},
        {"slug": "blocked", "status": "active"},
    ]
    assert set(call_mix.completed_only(per, tasks)) == {"accepted"}


def test_codex_discovery_requires_matching_session_metadata(tmp_path, monkeypatch):
    home = tmp_path / "codex"
    sessions = home / "sessions/2026/10/01"
    sessions.mkdir(parents=True)
    project = tmp_path / "project"
    project.mkdir()
    matching = sessions / "matching.jsonl"
    matching.write_text(
        json.dumps({"type": "session_meta", "payload": {"cwd": str(project)}}) + "\n",
        encoding="utf-8",
    )
    (sessions / "other.jsonl").write_text(
        json.dumps({"type": "session_meta", "payload": {"cwd": str(tmp_path / "other")}}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CODEX_HOME", str(home))
    assert call_mix.codex_transcripts(str(project), 10) == [str(matching)]


def test_the_report_is_split_by_complexity_never_blended_alone():
    """AC-3 NEGATIVE: a blended median hides a changing task mix."""
    per = {"a": dict.fromkeys(call_mix.CATEGORIES, 1), "b": dict.fromkeys(call_mix.CATEGORIES, 9)}
    text = call_mix.report(per, {"a": "simple", "b": "complex"}, 0)
    assert "simple" in text and "complex" in text and "responses" in text
