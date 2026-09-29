"""The handoff states the slow lane's colour, because nothing else will.

`pytest -q` deselects `-m slow`, and CI does not run while push is forbidden, so two
slow tests stayed red through a whole session unseen (two-slow-lane-tests-are-red-and-unseen).
The test conftest records a whole-tree slow run in `.tausik/slow_lane.json`; the handoff
reads it. Silence is the failure mode, so every state but green is said in words.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from handoff_generate import SLOW_LANE_FILE, slow_lane  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402

_START = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)


def _write(tmp_path, **rec):
    (tmp_path / SLOW_LANE_FILE).write_text(json.dumps(rec), encoding="utf-8")


def test_a_project_that_records_no_lane_gets_nothing(tmp_path):
    assert slow_lane(str(tmp_path), _START) is None
    assert slow_lane(None, _START) is None


@pytest.mark.parametrize(
    ("minutes", "passed", "failed", "exit_status", "said"),
    [
        pytest.param(-180, 142, 0, 0, "NOT RUN this session", id="not_run_this_session"),
        pytest.param(5, 140, 2, 1, "RED: 2 failed, 140 passed", id="red_with_counts"),
        # An interrupted or errored run counts nothing as failed and is not green.
        pytest.param(5, 10, 0, 2, "RED", id="nonzero_exit_without_failures"),
        pytest.param(5, 142, 0, 0, "green: 142 passed", id="green_this_session"),
    ],
)
def test_the_lane_state_is_said_in_words(tmp_path, minutes, passed, failed, exit_status, said):
    ran_at = (_START + timedelta(minutes=minutes)).isoformat()
    _write(tmp_path, ran_at=ran_at, passed=passed, failed=failed, exit_status=exit_status)
    assert slow_lane(str(tmp_path), _START).startswith(said)


def test_an_unreadable_record_is_said_not_swallowed(tmp_path):
    (tmp_path / SLOW_LANE_FILE).write_text("{not json", encoding="utf-8")
    assert slow_lane(str(tmp_path), _START).startswith("UNREADABLE")


@pytest.fixture
def svc(tmp_path, monkeypatch):
    monkeypatch.setenv("TAUSIK_DISABLE_SESSION_METRICS", "1")
    s = ProjectService(SQLiteBackend(str(tmp_path / "tausik.db")))
    yield s
    s.be.close()


def test_the_saved_handoff_carries_the_lane_from_the_db_directory(svc, tmp_path):
    svc.session_start()
    _write(tmp_path, ran_at="2000-01-01T00:00:00+00:00", passed=1, failed=0)
    svc.session_handoff({})
    handoff = svc.session_last_handoff()
    assert handoff["slow_lane"].startswith("NOT RUN this session"), handoff
