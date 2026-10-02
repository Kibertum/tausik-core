"""Disposable Codex cold-start drill: journal state must survive a replacement."""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from tausik_utils import utcnow_iso  # noqa: E402
from verify_files_hash import compute_files_hash  # noqa: E402


def _git(root, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


@pytest.fixture
def drill(tmp_path, monkeypatch):
    monkeypatch.setenv("TAUSIK_DISABLE_SESSION_METRICS", "1")
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "drill@example.test")
    _git(tmp_path, "config", "user.name", "Cold start drill")
    source = tmp_path / "src.py"
    source.write_text("value = 1\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text(".tausik/\n", encoding="utf-8")
    _git(tmp_path, "add", "src.py", ".gitignore")
    _git(tmp_path, "commit", "-m", "baseline")
    svc = ProjectService(SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db")))
    svc.epic_add("e", "E")
    svc.story_add("e", "s", "S")
    svc.task_add("s", "resume-me", "Resume me", role="developer", goal="Preserve the goal")
    svc.task_update(
        "resume-me",
        acceptance_criteria=(
            "Restore facts without a handwritten rescue prompt. "
            "Negative: missing evidence is reported as unknown."
        ),
        relevant_files=json.dumps(["src.py"]),
        risk_score=4,
    )
    svc.task_plan("resume-me", ["record before state", "continue after restart"])
    svc.session_start("isolated-codex-before")
    svc.task_start("resume-me")
    svc.task_step("resume-me", 1)
    svc.task_log("resume-me", "before interruption: source is ready")
    svc.decide("The drill uses an isolated workspace.", task_slug="resume-me")
    svc.decide("An unrelated older project decision.")
    # Keep this fixture independent of scheduler timing: the retained decision
    # is strictly before the replacement session and the unrelated record is
    # equally old.  The old window-only projection therefore fails reliably.
    svc.be._ex(
        "UPDATE decisions SET created_at=?",
        ("2026-01-01T00:00:00+00:00",),
    )
    yield svc, source
    svc.be.close()


def _green_receipt(svc, source) -> None:
    svc.be._ex(
        "INSERT INTO verification_runs(task_slug,scope,command,exit_code,summary,files_hash,ran_at) "
        "VALUES(?,?,?,?,?,?,?)",
        (
            "resume-me",
            "standard",
            "trigger=verify|sig=drill|files=src.py",
            0,
            "green before interruption",
            compute_files_hash(["src.py"], root=str(source.parent)),
            utcnow_iso(),
        ),
    )


def _continue_in_fresh_process(db_path) -> dict:
    """The replacement process receives no Python objects from the interrupted one."""
    code = (
        "import json, sys; "
        "sys.path.insert(0, sys.argv[1] + '/scripts'); "
        "from project_backend import SQLiteBackend; "
        "from project_service import ProjectService; "
        "svc = ProjectService(SQLiteBackend(sys.argv[2])); "
        "print(json.dumps(svc.session_last_handoff(), sort_keys=True)); "
        "svc.be.close()"
    )
    out = subprocess.run(
        [sys.executable, "-c", code, _ROOT, str(db_path)],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(out.stdout)


def test_isolated_drill_restores_state_then_invalidates_stale_green(drill):
    """A replacement sees recorded facts; a later edit cannot inherit a green."""
    svc, source = drill
    _green_receipt(svc, source)
    svc.session_end(host_session_id="isolated-codex-before")
    svc.session_start("isolated-codex-after")
    svc.be._ex(
        "UPDATE sessions SET started_at=? WHERE host_session_id=?",
        ("2026-01-02T00:00:00+00:00", "isolated-codex-after"),
    )
    svc.session_handoff()
    before = _continue_in_fresh_process(svc.be.db_path)

    restored = before["in_progress"][0]
    assert restored["goal"] == "Preserve the goal"
    assert "Restore facts" in restored["acceptance_criteria"]
    assert restored["plan"]["completed"] == [1]
    assert restored["plan"]["remaining"] == [{"number": 2, "step": "continue after restart"}]
    assert restored["unresolved_risk"]["risk_score"] == 4
    assert before["decisions"] == ["#1 The drill uses an isolated workspace."]
    assert before["verify"] == [{"task": "resume-me", "run": 1, "passed": True, "state": "current"}]
    assert before["working_tree"] == {"state": "recorded", "modified_uncommitted": []}

    source.write_text("value = 2\n", encoding="utf-8")
    svc.session_handoff()
    after = _continue_in_fresh_process(svc.be.db_path)

    assert after["verify"][0]["state"] == "stale"
    assert after["working_tree"]["modified_uncommitted"] == ["src.py"]


def test_missing_or_conflicting_records_are_visible_not_completed(drill):
    """Negative drill: absent proof and malformed plan remain unknown/unreadable."""
    svc, _source = drill
    svc.be.task_update("resume-me", plan='["not a plan step"]')
    svc.session_handoff()
    handoff = svc.session_last_handoff()

    restored = handoff["in_progress"][0]
    assert restored["plan"] == {"state": "unreadable"}
    assert handoff["verify"] == []
    assert handoff["completed"] == []
