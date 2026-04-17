"""Test `tausik hud` CLI sub-command."""

from __future__ import annotations

import contextlib
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))


def _fresh_svc(tmp_path):
    os.environ["TAUSIK_DIR"] = str(tmp_path / ".tausik")
    (tmp_path / ".tausik").mkdir()
    from project_backend import SQLiteBackend
    from project_service import ProjectService

    return ProjectService(SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db")))


def _run_hud(svc):
    from project_cli_ops import cmd_hud

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        cmd_hud(svc, object())
    return buf.getvalue()


class TestHudCli:
    def test_empty_project_does_not_crash(self, tmp_path):
        svc = _fresh_svc(tmp_path)
        out = _run_hud(svc)
        assert "TAUSIK HUD" in out
        assert "no active task" in out.lower()

    def test_with_active_task(self, tmp_path):
        svc = _fresh_svc(tmp_path)
        svc.task_add(None, "demo", "Demo task")
        svc.task_update("demo", status="active")
        out = _run_hud(svc)
        assert "demo" in out
        assert "Demo task" in out

    def test_with_session_and_logs(self, tmp_path):
        svc = _fresh_svc(tmp_path)
        svc.task_add(None, "demo", "Demo task")
        svc.task_update("demo", status="active")
        svc.be.task_log_add("demo", "First log", phase="implementation")
        svc.be.task_log_add("demo", "Second log", phase="testing")
        out = _run_hud(svc)
        assert "Recent logs" in out
        assert "First log" in out or "Second log" in out

    def test_long_title_truncated(self, tmp_path):
        svc = _fresh_svc(tmp_path)
        long_title = "X" * 200
        svc.task_add(None, "big", long_title)
        svc.task_update("big", status="active")
        out = _run_hud(svc)
        # Title should be truncated to 80 chars in the header line
        header = [line for line in out.splitlines() if line.startswith("Active:")]
        assert header
        assert len(header[0]) < 200

    def test_output_has_borders(self, tmp_path):
        svc = _fresh_svc(tmp_path)
        out = _run_hud(svc)
        assert out.startswith("═══ TAUSIK HUD ═══")
        assert out.rstrip().endswith("═══════════════════")
