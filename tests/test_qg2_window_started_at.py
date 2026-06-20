"""p0-defect: QG-2 git-diff cross-check window must start at started_at.

Backlog tasks are created sessions before work begins. Using created_at as
the `git log --since` lower bound sweeps every intervening (unrelated) commit
into the `actual` change-set, so the declared relevant_files can never cover
it -> permanent cache_status=git-mismatch and task_done is unclosable
(reproduced on v15p-fix-rag-reindex-hang, foreign commit 831f03e).

The window must be started_at (when work actually began), falling back to
created_at only when the task was never started.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


class _StubBackend:
    """Minimal backend: one task with distinct created_at / started_at."""

    _conn = None  # run_gates_with_cache is monkeypatched away

    def __init__(self, task: dict):
        self._task = task

    def task_get(self, slug):
        return dict(self._task)

    def task_append_notes(self, slug, msg):
        pass


def _make_service(task: dict):
    from service_gates import GatesMixin

    class _Svc(GatesMixin):
        def __init__(self, be):
            self.be = be

    return _Svc(_StubBackend(task))


def _capture_window(monkeypatch, task: dict) -> str | None:
    """Run run_verify_for_task, capture task_created_at passed downstream."""
    captured: dict = {}

    def fake_run_gates_with_cache(conn, slug, files, **kwargs):
        captured.update(kwargs)
        return True, [], "miss"

    monkeypatch.setattr("service_verification.run_gates_with_cache", fake_run_gates_with_cache)
    svc = _make_service(task)
    svc.run_verify_for_task("some-task", relevant_files=["a.py"])
    return captured.get("task_created_at")


def test_verify_window_prefers_started_at(monkeypatch):
    window = _capture_window(
        monkeypatch,
        {
            "slug": "some-task",
            "created_at": "2026-06-01T00:00:00Z",
            "started_at": "2026-06-11T23:19:05Z",
            "relevant_files": '["a.py"]',
        },
    )
    assert window == "2026-06-11T23:19:05Z"


def test_verify_window_falls_back_to_created_at(monkeypatch):
    window = _capture_window(
        monkeypatch,
        {
            "slug": "some-task",
            "created_at": "2026-06-01T00:00:00Z",
            "started_at": None,
            "relevant_files": '["a.py"]',
        },
    )
    assert window == "2026-06-01T00:00:00Z"


def test_no_caller_uses_bare_created_at():
    """Source invariant: every cross-check caller prefers started_at."""
    for fname in ("project_cli_verify.py", "service_gates.py"):
        src = (SCRIPTS / fname).read_text(encoding="utf-8")
        for line in src.splitlines():
            if "task_created_at" in line and 'task.get("created_at")' in line:
                assert 'task.get("started_at")' in line, (
                    f"{fname}: cross-check window uses bare created_at: {line.strip()}"
                )
