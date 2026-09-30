"""Capacity describes THIS session's work, not a window inherited from a task
(capacity-counts-the-task-window-not-the-session-work, github#24, GitLab #8).

Two layers, as the ticket names them:
* the counter of calls — fixed in 1.9.0 (9eab6893): `used` counts the
  session's own usage events, not a closed task's whole life;
* the reservation of active tasks — `planned` added each active task's FULL
  budget, so a task that spent 140 of its 150 calls in an earlier session still
  reserved 150 in every new one. It now reserves what is LEFT of the budget.
Calibration (actual/budget per task over the last 10 closes) is per task by
design and stays descriptive — see the status wording test below.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend
from project_service import ProjectService


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "w.db")))
    s.epic_add("e", "Epic")
    s.story_add("e", "s", "Story")
    yield s
    s.be.close()


def _calls(svc, n, slug=None):
    sid = svc.be.session_current()["id"]
    for _ in range(n):
        svc.be.usage_event_append(sid, slug, 0, 0, 0, 0.0, 1, None, "posttool")


def _task(svc, slug, budget):
    svc.task_add("s", slug, "T", role="developer", goal="g", call_budget=budget)
    svc.be.task_update(slug, acceptance_criteria="Returns 400 on invalid input.")
    svc.task_start(slug)


def _new_session(svc):
    svc.session_end("shift over")
    svc.session_start()


def test_a_fresh_session_does_not_inherit_a_task_s_spent_budget(svc):
    svc.session_start()
    _task(svc, "long", 150)
    _calls(svc, 140, "long")
    _new_session(svc)
    out = svc.be.session_capacity_summary(200)
    assert out["used"] == 0
    assert out["planned_active"] == 10  # what is left of 150, not 150
    assert out["remaining"] == 190


def test_a_fresh_session_allows_a_start(svc):
    svc.session_start()
    _task(svc, "long", 150)
    _calls(svc, 400, "long")
    _new_session(svc)
    _task(svc, "next", 50)  # never refused (decision #376); nothing inherited
    out = svc.be.session_capacity_summary(200)
    assert out["used"] == 0 and out["planned_active"] == 50


def test_work_done_in_a_long_session_is_not_lost(svc):
    svc.session_start()
    _task(svc, "a", 60)
    _calls(svc, 40, "a")
    _task(svc, "b", 60)
    _calls(svc, 70, "b")  # b overspent: it reserves nothing more, it does not go negative
    _calls(svc, 5)  # calls outside any task still count
    out = svc.be.session_capacity_summary(200)
    assert out["used"] == 115
    assert out["planned_active"] == 20  # 60-40 for a, 0 for b
    assert out["remaining"] == 65


def test_calibration_is_printed_as_descriptive():
    from status_view import status_primary_lines

    view = {
        "data": {"task_counts": {}, "tasks": {}},
        "risk_line": None,
        "renar_line": None,
        "session_metrics": None,
        "max_min": 180,
        "epics_count": 0,
        "calibration": {"label": "calibrated", "avg_ratio": 0.74, "samples": 10},
        "capacity": None,
    }
    line = [ln for ln in status_primary_lines(view) if ln.startswith("Calibration")][0]
    assert "descriptive, not a forecast" in line
