"""Behavioral contract for the transport-independent atomic task creator."""

from __future__ import annotations

import os

import pytest

from project_backend import SQLiteBackend
from project_service import ProjectService
from service_task_create import task_add_complete


@pytest.fixture
def svc(tmp_path):
    return ProjectService(SQLiteBackend(os.path.join(str(tmp_path), "tausik.db")))


def test_complete_task_creation_commits_all_parts_or_none(svc):
    svc.task_add(None, "ready", "Ready")
    result = task_add_complete(
        svc,
        story_slug=None,
        slug="complete",
        title="Complete",
        goal="Create one complete contract",
        acceptance_criteria="Everything persists. Negative: missing predecessor rolls back.",
        scope="scripts/ tests/",
        rollback_plan="git revert",
        plan_steps=["Implement", "Verify"],
        rationale="One atomic service operation.",
        depends_on=["ready"],
    )

    task = svc.task_show("complete")
    assert result == "Task 'complete' created."
    assert task["acceptance_criteria"].startswith("Everything persists")
    assert (
        task["plan"] == '[{"step": "Implement", "done": false}, {"step": "Verify", "done": false}]'
    )
    assert svc.be._task_deps_of("complete") == ["ready"]
    assert svc.task_logs("complete")[0]["message"] == "One atomic service operation."

    with pytest.raises(Exception, match="not found"):
        task_add_complete(
            svc,
            story_slug=None,
            slug="rolled-back",
            title="Rolled back",
            goal="Leave no partial task",
            acceptance_criteria="Nothing persists when the edge is invalid.",
            plan_steps=["Must disappear"],
            rationale="Must disappear.",
            depends_on=["missing"],
        )
    assert svc.be.task_get("rolled-back") is None
    assert svc.be._task_deps_of("rolled-back") == []
    assert svc.task_logs("rolled-back") == []


def test_complete_task_creation_persists_relevant_files(svc):
    task_add_complete(
        svc,
        story_slug=None,
        slug="with-files",
        title="With files",
        goal="Store relevant_files on create",
        acceptance_criteria="Files persist. Negative: omitted field stays empty.",
        relevant_files=["scripts/a.py", "tests/test_a.py"],
    )
    task = svc.task_show("with-files")
    raw = task.get("relevant_files")
    if isinstance(raw, str):
        import json

        files = json.loads(raw)
    else:
        files = raw
    assert files == ["scripts/a.py", "tests/test_a.py"]
