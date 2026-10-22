"""Canon B: memory-only keeps a light backlog and skips the SENAR default path."""

from __future__ import annotations

import io
import json
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project"),
)

from handlers import handle_tool
from memory_only_backlog import deferred_reply
from project_backend import SQLiteBackend
from project_parser import build_parser
from project_service import ProjectService
from tausik_utils import ServiceError


def _service(tmp_path: Path, profile: str | None) -> ProjectService:
    if profile is not None:
        (tmp_path / "config.json").write_text(
            json.dumps({"governance_profile": profile}),
            encoding="utf-8",
        )
    return ProjectService(SQLiteBackend(str(tmp_path / "tausik.db")))


def test_light_close_skips_gates_and_full_path_does_not(tmp_path: Path):
    svc = _service(tmp_path, "memory-only")
    svc.task_add(None, "light", "Light task")

    def _boom(*_a, **_k):
        raise AssertionError("gates ran")

    svc._run_quality_gates_report = _boom  # type: ignore[method-assign]
    message = svc.task_done("light")
    assert "without gates" in message
    assert svc.be.task_get("light")["status"] == "done"

    svc.task_add(None, "gated", "Gated task")
    with pytest.raises(ServiceError, match="never started"):
        svc.task_done("gated", full_path=True)
    assert svc.be.task_get("gated")["status"] == "planning"


def test_full_profile_still_refuses_an_unstarted_close(tmp_path: Path):
    svc = _service(tmp_path, None)
    svc.task_add(None, "plain", "Plain task")
    with pytest.raises(ServiceError, match="never started"):
        svc.task_done("plain")
    assert svc.be.task_get("plain")["status"] == "planning"


def test_session_start_and_verify_are_marked_disabled(tmp_path: Path):
    svc = _service(tmp_path, "memory-only")
    for tool in ("tausik_session_start", "tausik_verify"):
        payload = json.loads(handle_tool(svc, tool, {}))
        assert payload["ok"] is False
        assert payload["annotation"] == "profile=disabled"
        assert payload["profile"] == "memory-only"
        assert tool in payload["reason"]
    assert deferred_reply(svc, "tausik_verify", {"full_path": True}) is None
    added = handle_tool(svc, "tausik_task_add", {"slug": "kept", "title": "Kept"})
    assert "kept" in added
    closed = json.loads(handle_tool(svc, "tausik_task_done", {"slug": "kept"}))
    assert closed["ok"] is True
    assert closed["gates_skipped"] is True


def test_memory_only_status_omits_senar_walls(tmp_path: Path):
    svc = _service(tmp_path, "memory-only")
    svc.task_add(None, "one", "One")
    compact = json.loads(handle_tool(svc, "tausik_status", {"compact": True}))
    assert compact["governance_profile"] == "memory-only"
    assert compact["backlog_policy"] == "B"
    assert compact["tasks_total"] == 1
    assert "audit_overdue_closures" not in compact
    assert "session_max_minutes" not in compact
    assert "session_id" not in compact
    text = handle_tool(svc, "tausik_status", {})
    assert "light backlog" in text
    assert "SENAR" not in text
    assert "RENAR" not in text
    assert "bootstrap" not in text.lower()


def test_full_profile_status_keeps_the_session_field(tmp_path: Path):
    svc = _service(tmp_path, "full")
    svc.task_add(None, "one", "One")
    compact = json.loads(handle_tool(svc, "tausik_status", {"compact": True}))
    assert "governance_profile" not in compact
    assert "session_id" in compact
    text = handle_tool(svc, "tausik_status", {})
    assert "canon B" not in text
    assert "Session:" in text


def test_cli_full_path_flag_defaults_off():
    parser = build_parser()
    assert parser.parse_args(["task", "done", "t"]).full_path is False
    assert parser.parse_args(["task", "done", "t", "--full-path"]).full_path is True


def test_doctor_does_not_ask_memory_only_for_a_full_skill_bootstrap(tmp_path, monkeypatch):
    tausik = tmp_path / ".tausik"
    tausik.mkdir()
    (tausik / "config.json").write_text(
        json.dumps({"governance_profile": "memory-only"}),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    from unittest.mock import patch

    from project_cli_doctor import cmd_doctor

    class _Svc:
        def session_active_minutes(self):
            return 0

        def session_wall_minutes(self):
            return 0

    buf = io.StringIO()
    with (
        patch("project_cli_doctor.run_optional_checks", return_value=(0, 0)),
        redirect_stdout(buf),
    ):
        try:
            cmd_doctor(_Svc(), type("A", (), {})())
        except SystemExit:
            pass
    skills = next(line for line in buf.getvalue().splitlines() if "Core skills" in line)
    assert "full skill bootstrap is not required" in skills
    assert "re-run bootstrap" not in skills.lower()
    assert "run bootstrap" not in skills.lower()
