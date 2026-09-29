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
    assert unattributed == 1


def test_the_report_is_split_by_complexity_never_blended_alone():
    """AC-3 NEGATIVE: a blended median hides a changing task mix."""
    per = {"a": dict.fromkeys(call_mix.CATEGORIES, 1), "b": dict.fromkeys(call_mix.CATEGORIES, 9)}
    text = call_mix.report(per, {"a": "simple", "b": "complex"}, 0)
    assert "simple" in text and "complex" in text
