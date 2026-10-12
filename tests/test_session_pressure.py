"""Context pressure is a measured signal with a basis (1.10, story E)."""

from __future__ import annotations

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from service_session_metrics import session_overrun_warning  # noqa: E402
from session_pressure import CROSSED, summary  # noqa: E402


def test_summary_gives_the_basis_figures():
    rows = [{"active_minutes": m} for m in (10, 60, 73, 146, 246)]
    s = summary(rows, 180)
    assert s == {
        "sessions": 5,
        "median_active": 73,
        "p90_active": 246,
        "max_active": 246,
        "threshold": 180,
        "over_threshold": 1,
    }


def test_summary_of_nothing_is_nothing():
    assert summary([], 180) == {"sessions": 0}


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "p.db")))
    s.session_start()
    sid = s.be.session_current()["id"]
    s.be._ex("UPDATE sessions SET started_at='2020-01-01T00:00:00Z' WHERE id=?", (sid,))
    for n in range(13):
        s.be._ex(
            "INSERT INTO events(entity_type, entity_id, action, created_at) VALUES ('t','x','tick',?)",
            (f"2020-01-01T00:{n * 5:02d}:00Z",),
        )
    yield s, sid
    s.be.close()


def test_a_crossing_is_recorded_once(svc):
    s, sid = svc
    assert session_overrun_warning(s.be, 30) is not None
    assert session_overrun_warning(s.be, 30) is not None
    crossed = [
        e
        for e in s.be.events_list(entity_type="session", entity_id=str(sid))
        if e["action"] == CROSSED
    ]
    assert len(crossed) == 1


def test_a_zero_threshold_switches_the_signal_off(svc):
    """NEGATIVE: 0 means off — no advice and no event."""
    s, sid = svc
    assert session_overrun_warning(s.be, None, effective_limit=0) is None
    assert not [
        e
        for e in s.be.events_list(entity_type="session", entity_id=str(sid))
        if e["action"] == CROSSED
    ]


def test_no_signal_ever_refuses_a_start(svc):
    """NEGATIVE: over every threshold, the task still starts (decision #376)."""
    s, _ = svc
    s.epic_add("e", "E")
    s.story_add("e", "st", "S")
    s.task_add("st", "t", "T", role="developer", goal="g", call_budget=9999)
    s.be.task_update("t", acceptance_criteria="Returns 400 on invalid input.")
    s.task_start("t")
    assert s.be.task_get("t")["status"] == "active"
