"""Journal freshness is a signal per task (1.10, story E)."""

from __future__ import annotations

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from journal_freshness import calls_since_last_log, freshness_advice  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "jf.db")))
    s.epic_add("e", "E")
    s.story_add("e", "s", "S")
    s.task_add("s", "t", "T", role="developer", goal="g")
    s.be.task_update("t", acceptance_criteria="Returns 400 on invalid input.")
    s.task_start("t")
    yield s
    s.be.close()


def _calls(svc, n: int, slug: str = "t", at: str | None = None) -> None:
    for _ in range(n):
        svc.be.usage_event_append(None, slug, 0, 0, 0, 0.0, 1, "", "posttool", recorded_at=at)


def test_calls_after_the_last_log_are_counted(svc):
    _calls(svc, 3, at="2000-01-01T00:00:00Z")
    svc.task_log("t", "step one done")
    _calls(svc, 7, at="2999-01-01T00:00:00Z")
    assert calls_since_last_log(svc.be, "t") == 7


def test_the_advice_fires_past_the_threshold_once_per_bucket(svc):
    svc.task_log("t", "start")
    _calls(svc, 41)
    assert "41 tool calls since its last log entry" in freshness_advice(svc.be)
    assert freshness_advice(svc.be) == ""


def test_it_works_without_any_session(svc):
    """NEGATIVE: per task, not per session — no open session, still a signal."""
    assert svc.be.session_current() is None
    _calls(svc, 45)
    assert "tool calls since its last log entry" in freshness_advice(svc.be)


def test_it_never_refuses_a_closure(svc):
    """NEGATIVE: a stale journal is advice; task done does not consult it."""
    import inspect

    import service_task

    assert "journal_freshness" not in inspect.getsource(service_task)
