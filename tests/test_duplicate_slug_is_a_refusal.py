"""A duplicate slug is a one-line refusal, not a traceback
(story-add-duplicate-slug-is-a-traceback-not-a-refusal)."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend
from project_service import ProjectService
from tausik_utils import ServiceError


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "h.db")))
    s.epic_add("e", "Epic")
    s.story_add("e", "s", "Story")
    s.task_add("s", "t", "Task", role="developer", goal="g")
    yield s
    s.be.close()


def _counts(svc):
    return tuple(
        svc.be._q1(f"SELECT COUNT(*) AS n FROM {t}")["n"] for t in ("epics", "stories", "tasks")
    )


@pytest.mark.parametrize(
    "call,kind",
    [
        (lambda s: s.epic_add("e", "Again"), "Epic 'e' already exists"),
        (lambda s: s.story_add("e", "s", "Again"), "Story 's' already exists"),
        (
            lambda s: s.task_add("s", "t", "Again", role="developer", goal="g"),
            "Task 't' already exists",
        ),
    ],
    ids=["epic", "story", "task"],
)
def test_a_duplicate_is_refused_in_one_line_and_changes_nothing(svc, call, kind):
    before = _counts(svc)
    with pytest.raises(ServiceError) as exc:
        call(svc)
    assert kind in str(exc.value) and "\n" not in str(exc.value)
    assert _counts(svc) == before


def test_a_missing_epic_is_still_its_own_refusal(svc):
    with pytest.raises(ServiceError) as exc:
        svc.story_add("no-such-epic", "s2", "Story")
    assert "already exists" not in str(exc.value)
    assert "no-such-epic" in str(exc.value)
