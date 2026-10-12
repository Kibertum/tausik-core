"""task next offers the release first (task-next-ignores-declared-wave-order).

Measured in session #272: `task next` suggested brainh-semantic-search, a task of
no release, while 1.10 had 27 offerable tasks — the ranking read the whole
backlog by score. The release composition declared in decisions now ranks first.
"""

from __future__ import annotations

import pytest

import service_task_order as order
from project_backend import SQLiteBackend
from project_service import ProjectService


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "next.db")))
    s.epic_add("e", "E")
    s.story_add("e", "rel", "Release story")
    s.story_add("e", "other", "Other story")
    s.task_add("rel", "in-release", "In release")
    s.task_add("other", "outside", "Outside")
    s.be.task_update("in-release", score=1)
    s.be.task_update("outside", score=99)
    yield s
    s.be.close()


def _release(monkeypatch, svc, slugs):
    ids = [svc.be.story_get(s)["id"] for s in slugs]
    monkeypatch.setattr(order, "release_story_ids", lambda _svc: (ids, "9.9"))


def test_a_release_task_beats_a_higher_score_outside(svc, monkeypatch):
    """NEGATIVE: score 99 outside the release loses to score 1 inside it."""
    _release(monkeypatch, svc, ["rel"])
    report = order.task_next_report(svc)
    assert report["task"]["slug"] == "in-release"
    assert report["basis"].startswith("release 9.9 first")


def test_without_a_declared_release_the_old_order_holds(svc):
    """NEGATIVE: no composition in decisions -> score decides, as before."""
    report = order.task_next_report(svc)
    assert report["task"]["slug"] == "outside"
    assert report["basis"] == order.ORDERING_BASIS


def test_outside_work_is_still_offered_when_the_release_has_none(svc, monkeypatch):
    svc.be.task_update("in-release", status="done")
    _release(monkeypatch, svc, ["rel"])
    assert order.task_next_report(svc)["task"]["slug"] == "outside"
