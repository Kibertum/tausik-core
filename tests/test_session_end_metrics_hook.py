from __future__ import annotations

from pathlib import Path

from project_backend import SQLiteBackend
from project_service import ProjectService


def _make_service(tmp_path: Path) -> ProjectService:
    be = SQLiteBackend(str(tmp_path / "tausik.db"))
    return ProjectService(be)


def test_session_end_triggers_metrics_hook(monkeypatch, tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    calls: list[list[str]] = []

    def _fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(list(cmd))

        class _R:
            returncode = 0
            stdout = "ok"
            stderr = ""

        return _R()

    import subprocess

    monkeypatch.setattr(subprocess, "run", _fake_run)
    try:
        svc.session_start()
        msg = svc.session_end("done")
        assert "ended" in msg
        assert calls, "session_end should attempt to run session_metrics hook"
        assert "--auto" in calls[0]
        assert "--record" in calls[0]
    finally:
        svc.be.close()

