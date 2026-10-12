"""Behavior tests for observed Codex payloads; these are not live-host evidence."""

import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from conftest import canonical_ddl

_GATE = Path(__file__).resolve().parents[1] / "scripts/hooks/codex_write_gate.py"


def run_gate(root, event, state="no_task"):
    directory = root / ".tausik"
    directory.mkdir(exist_ok=True)
    with sqlite3.connect(directory / "tausik.db") as db:
        db.execute(canonical_ddl("tasks"))
        db.execute("CREATE TABLE meta (key TEXT, value TEXT)")
        if state != "no_task":
            db.execute(
                """INSERT INTO tasks(
                    slug, title, status, scope_paths, created_at, updated_at
                ) VALUES ('probe', 'Probe', 'active', ?, '2026-10-01', '2026-10-01')""",
                (json.dumps(["allowed.py"]),),
            )
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("TAUSIK_SKIP_HOOKS", "TAUSIK_HOOK_FAIL_OPEN")
    }
    return subprocess.run(
        [sys.executable, "-X", "utf8", str(_GATE), "--project", str(root)],
        input=json.dumps(event),
        text=True,
        capture_output=True,
        encoding="utf-8",
        cwd=root.parent,  # host launch cwd is NOT project jurisdiction
        env=env,
        timeout=10,
    )


@pytest.mark.parametrize("route", ["patch", "powershell_as_bash"])
@pytest.mark.parametrize("state", ["no_task", "out_of_scope", "allowed"])
def test_observed_payloads_use_real_task_and_scope_gates(tmp_path, route, state):
    target = "outside.py" if state == "out_of_scope" else "allowed.py"
    if route == "patch":
        tool, command = (
            "apply_patch",
            f"*** Begin Patch\n*** Add File: {target}\n+VALUE = 1\n*** End Patch",
        )
    else:
        tool, command = "Bash", f"Set-Content -LiteralPath {target} -Value VALUE"
    result = run_gate(
        tmp_path,
        {"tool_name": tool, "tool_input": {"command": command}, "cwd": str(tmp_path)},
        state,
    )
    assert result.returncode == 0, result.stderr
    if state == "allowed":
        assert not result.stdout
    else:
        assert_denied(result)


def assert_denied(result):
    assert result.returncode == 0, result.stderr
    decision = json.loads(result.stdout)["hookSpecificOutput"]
    assert decision["hookEventName"] == "PreToolUse"
    assert decision["permissionDecision"] == "deny"
    assert decision["permissionDecisionReason"]
    return decision["permissionDecisionReason"]


@pytest.mark.parametrize(
    "patch",
    [
        "*** Add File: allowed.py\n+ok\n*** Add File: outside.py\n+bad",
        "*** Update File: allowed.py\n*** Move to: outside.py\n@@\n-old\n+new",
        "*** Delete File: outside.py",
    ],
)
def test_every_patch_target_including_move_and_delete_is_checked(tmp_path, patch):
    result = run_gate(
        tmp_path,
        {
            "tool_name": "apply_patch",
            "cwd": str(tmp_path),
            "tool_input": {"command": f"*** Begin Patch\n{patch}\n*** End Patch"},
        },
        "active",
    )
    assert "outside.py" in assert_denied(result)


@pytest.mark.parametrize(
    "event",
    [
        [],
        {"tool_name": "apply_patch", "tool_input": {"command": "unrecognized patch"}},
        {"tool_name": "apply_patch", "tool_input": {"command": "*** Begin Patch\n*** End Patch"}},
        {"tool_name": "apply_patch", "tool_input": {}},
        {"tool_name": "Bash", "tool_input": {"command": "Set-Content"}},
    ],
)
def test_uncheckable_payloads_refuse_instead_of_appearing_protected(tmp_path, event):
    assert_denied(run_gate(tmp_path, event, "active"))


def test_payload_cwd_resolves_relative_patch_targets(tmp_path):
    child = tmp_path / "subdir"
    child.mkdir()
    event = {
        "tool_name": "apply_patch",
        "cwd": str(child),
        "tool_input": {
            "command": "*** Begin Patch\n*** Add File: allowed.py\n+content\n*** End Patch"
        },
    }
    result = run_gate(tmp_path, event, "active")
    assert_denied(result)  # subdir/allowed.py is not allowed.py


@pytest.mark.parametrize(
    "command", ["Get-Content allowed.py", "Write-Output 'Set-Content outside.py'"]
)
def test_read_or_quoted_write_text_is_not_promoted_to_a_write(tmp_path, command):
    event = {"tool_name": "Bash", "tool_input": {"command": command}}
    result = run_gate(tmp_path, event)
    assert result.returncode == 0
    assert not result.stdout
