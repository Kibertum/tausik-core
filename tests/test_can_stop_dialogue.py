"""Codex dialogue regressions across the production prompt and Stop adapters."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from can_stop import classify_request
from tausik_utils import utcnow_iso
from test_can_stop import bound_service  # noqa: F401 -- shared pytest fixture


ROOT = Path(__file__).resolve().parents[1]
PROMPT_HOOK = ROOT / "scripts" / "hooks" / "user_prompt_submit.py"
STOP_HOOK = ROOT / "scripts" / "hooks" / "can_stop_gate.py"
OPEN_TASKS_RU = "\u041a\u0430\u043a\u0438\u0435 \u0437\u0430\u0434\u0430\u0447\u0438 \u043e\u0442\u043a\u0440\u044b\u0442\u044b?"


def _run_hook(project: Path, script: Path, payload: dict[str, str], *, host: str = "codex"):
    return subprocess.run(
        [sys.executable, str(script), "--trusted-host", host],
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(project), "PYTHONUTF8": "1"},
        check=False,
    )


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        (OPEN_TASKS_RU, "read_only"),
        (
            "\u041f\u043e\u043a\u0430\u0436\u0438 \u043e\u0442\u043a\u0440\u044b\u0442\u044b\u0435 \u0437\u0430\u0434\u0430\u0447\u0438",
            "read_only",
        ),
        (
            "\u041f\u0435\u0440\u0435\u0447\u0438\u0441\u043b\u0438 \u043e\u0442\u043a\u0440\u044b\u0442\u044b\u0435 \u0437\u0430\u0434\u0430\u0447\u0438.",
            "read_only",
        ),
        ("Which tasks are open?", "read_only"),
        ("Show me the open tasks", "read_only"),
        ("List open tasks.", "read_only"),
        (
            "\u041a\u0430\u043a\u0438\u0435 \u0437\u0430\u0434\u0430\u0447\u0438 \u043e\u0442\u043a\u0440\u044b\u0442\u044b \u0438 \u0437\u0430\u043a\u0440\u043e\u0439 \u0438\u0445",
            "work",
        ),
        (
            "\u041f\u043e\u043a\u0430\u0436\u0438 \u043e\u0442\u043a\u0440\u044b\u0442\u044b\u0435 \u0437\u0430\u0434\u0430\u0447\u0438, \u0437\u0430\u0442\u0435\u043c \u0438\u0441\u043f\u0440\u0430\u0432\u044c \u043f\u0435\u0440\u0432\u0443\u044e",
            "work",
        ),
        ("Which tasks are open and close them", "work"),
        ("List open tasks, then edit the first one", "work"),
        (
            "\u041a\u0430\u043a\u0438\u0435 \u0437\u0430\u0434\u0430\u0447\u0438 \u043f\u0430\u0445\u043d\u0443\u0442 \u0441\u0438\u043d\u0438\u043c?",
            "work",
        ),
    ],
)
def test_open_task_intent_is_bounded_and_mutation_suffixes_fail_closed(prompt, expected):
    assert classify_request(prompt, host_instance="codex") == expected


def test_open_task_intent_does_not_change_cursor_stop_contract(bound_service):  # noqa: F811
    service, project, lease = bound_service
    service.be._ex("UPDATE execution_leases SET host_instance='cursor' WHERE id=?", (lease["id"],))
    turn = {"session_id": "thread-a", "turn_id": "cursor-open-tasks", "prompt": OPEN_TASKS_RU}

    recorded = _run_hook(project, PROMPT_HOOK, turn, host="cursor")
    row = service.be._q1(
        "SELECT request_kind FROM can_stop_turns WHERE turn_id='cursor-open-tasks'"
    )
    stopped = _run_hook(project, STOP_HOOK, turn, host="cursor")

    assert recorded.returncode == 0, recorded.stderr
    assert row == {"request_kind": "work"}
    assert json.loads(stopped.stdout)["decision"] == "block"


def test_exact_open_tasks_dialogue_allows_repeated_stop_without_creating_task(
    bound_service,  # noqa: F811
):
    service, project, _lease = bound_service
    service.be._execution_lease_unbind_task("stop-work", utcnow_iso())
    service.be._ex("DELETE FROM tasks WHERE slug='stop-work'")
    prompt = OPEN_TASKS_RU
    turn = {"session_id": "thread-a", "turn_id": "open-tasks", "prompt": prompt}

    recorded = _run_hook(project, PROMPT_HOOK, turn)
    row = service.be._q1(
        "SELECT request_kind,decision FROM can_stop_turns WHERE turn_id='open-tasks'"
    )
    first_stop = _run_hook(project, STOP_HOOK, turn)
    repeated_stop = _run_hook(project, STOP_HOOK, turn)

    assert recorded.returncode == 0, recorded.stderr
    assert row == {"request_kind": "read_only", "decision": None}
    assert first_stop.returncode == repeated_stop.returncode == 0
    assert first_stop.stdout == repeated_stop.stdout == ""
    assert service.be._q1("SELECT id FROM tasks LIMIT 1") is None


def test_read_only_interruption_preserves_active_task_and_next_work_turn(
    bound_service,  # noqa: F811
):
    service, project, lease = bound_service
    read_turn = {
        "session_id": "thread-a",
        "turn_id": "read-during-work",
        "prompt": OPEN_TASKS_RU,
    }
    work_turn = {
        "session_id": "thread-a",
        "turn_id": "resume-work",
        "prompt": "fix the race",
    }

    _run_hook(project, PROMPT_HOOK, read_turn)
    allowed = _run_hook(project, STOP_HOOK, read_turn)
    task_after_read = service.be.task_get("stop-work")
    lease_after_read = service.be._q1(
        "SELECT task_slug FROM execution_leases WHERE id=?", (lease["id"],)
    )
    _run_hook(project, PROMPT_HOOK, work_turn)
    first_block = _run_hook(project, STOP_HOOK, work_turn)
    repeated_block = _run_hook(project, STOP_HOOK, work_turn)

    assert allowed.returncode == 0 and allowed.stdout == ""
    assert task_after_read["status"] == "active"
    assert lease_after_read["task_slug"] == "stop-work"
    assert first_block.returncode == repeated_block.returncode == 0
    assert json.loads(first_block.stdout) == json.loads(repeated_block.stdout)
    assert "complete plan step 1: run the negative matrix" in first_block.stdout
