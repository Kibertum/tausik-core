"""Tests for CASCADE DELETE and FK integrity.

Verifies that deleting an epic cascades to stories and tasks,
deleting a story cascades to tasks, and FTS indexes stay in sync.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend
from project_service import ProjectService


@pytest.fixture
def svc(tmp_path):
    be = SQLiteBackend(str(tmp_path / "test.db"))
    s = ProjectService(be)
    yield s
    be.close()


def _build_tree(svc, n_stories=2, n_tasks_per_story=3):
    """Build epic → stories → tasks tree."""
    svc.epic_add("epic-1", "Epic One")
    for si in range(1, n_stories + 1):
        slug = f"story-{si}"
        svc.story_add("epic-1", slug, f"Story {si}")
        for ti in range(1, n_tasks_per_story + 1):
            svc.task_add(slug, f"task-{si}-{ti}", f"Task {si}.{ti}")


# === CASCADE DELETE: epic → stories → tasks ===

class TestCascadeDeleteEpic:
    def test_delete_epic_removes_stories(self, svc):
        _build_tree(svc, 2, 2)
        assert len(svc.story_list("epic-1")) == 2
        svc.epic_delete("epic-1")
        assert len(svc.story_list("epic-1")) == 0
        assert len(svc.story_list()) == 0

    def test_delete_epic_removes_tasks(self, svc):
        _build_tree(svc, 2, 3)
        assert len(svc.task_list()) == 6
        svc.epic_delete("epic-1")
        assert len(svc.task_list()) == 0

    def test_delete_epic_cleans_fts(self, svc):
        _build_tree(svc, 1, 2)
        # FTS should find tasks before delete
        results = svc.search("Task")
        assert len(results.get("tasks", [])) >= 1
        svc.epic_delete("epic-1")
        # FTS should return nothing after delete
        results = svc.search("Task")
        assert len(results.get("tasks", [])) == 0

    def test_delete_epic_preserves_other_epics(self, svc):
        _build_tree(svc, 1, 2)
        svc.epic_add("epic-2", "Epic Two")
        svc.story_add("epic-2", "story-other", "Other Story")
        svc.task_add("story-other", "task-other", "Other Task")
        svc.epic_delete("epic-1")
        assert len(svc.task_list()) == 1
        assert svc.task_list()[0]["slug"] == "task-other"


# === CASCADE DELETE: story → tasks ===

class TestCascadeDeleteStory:
    def test_delete_story_removes_tasks(self, svc):
        _build_tree(svc, 2, 3)
        assert len(svc.task_list(story="story-1")) == 3
        svc.story_delete("story-1")
        assert len(svc.task_list(story="story-1")) == 0
        # Other story tasks remain
        assert len(svc.task_list(story="story-2")) == 3

    def test_delete_story_cleans_fts(self, svc):
        svc.epic_add("e1", "E1")
        svc.story_add("e1", "s1", "S1")
        svc.task_add("s1", "unique-xyz", "Unique XYZ Task", goal="zqfindme")
        results = svc.search("zqfindme")
        assert len(results.get("tasks", [])) >= 1
        svc.story_delete("s1")
        results = svc.search("zqfindme")
        assert len(results.get("tasks", [])) == 0

    def test_delete_story_with_active_tasks(self, svc):
        svc.epic_add("e1", "E1")
        svc.story_add("e1", "s1", "S1")
        svc.task_add("s1", "t1", "T1")
        svc.task_start("t1", _internal_force=True)
        svc.story_delete("s1")
        assert svc.be.task_get("t1") is None


# === FK integrity ===

class TestForeignKeyIntegrity:
    def test_task_requires_valid_story(self, svc):
        with pytest.raises(Exception):
            svc.task_add("nonexistent", "t1", "T1")

    def test_story_requires_valid_epic(self, svc):
        with pytest.raises(Exception):
            svc.story_add("nonexistent", "s1", "S1")

    def test_fk_enforcement_on(self, svc):
        """Verify PRAGMA foreign_keys is ON."""
        row = svc.be._q1("PRAGMA foreign_keys")
        assert row["foreign_keys"] == 1

    def test_task_story_id_references_stories(self, svc):
        """Cannot insert task with invalid story_id directly."""
        with pytest.raises(Exception):
            svc.be._conn.execute(
                "INSERT INTO tasks(story_id, slug, title, status, created_at, updated_at) "
                "VALUES(99999, 'bad', 'Bad', 'planning', '2025-01-01', '2025-01-01')"
            )
            svc.be._conn.commit()

    def test_story_epic_id_references_epics(self, svc):
        """Cannot insert story with invalid epic_id directly."""
        with pytest.raises(Exception):
            svc.be._conn.execute(
                "INSERT INTO stories(epic_id, slug, title, status, created_at) "
                "VALUES(99999, 'bad', 'Bad', 'open', '2025-01-01')"
            )
            svc.be._conn.commit()


# === Edge cases ===

class TestCascadeEdgeCases:
    def test_delete_epic_with_no_stories(self, svc):
        svc.epic_add("empty-epic", "Empty Epic")
        svc.epic_delete("empty-epic")
        assert svc.be.epic_get("empty-epic") is None

    def test_delete_story_with_no_tasks(self, svc):
        svc.epic_add("e1", "E1")
        svc.story_add("e1", "empty-story", "Empty Story")
        svc.story_delete("empty-story")
        assert svc.be.story_get("empty-story") is None

    def test_deep_cascade_with_decisions(self, svc):
        """Decisions FK task_slug ON DELETE SET NULL — survive task deletion with null slug."""
        svc.epic_add("e1", "E1")
        svc.story_add("e1", "s1", "S1")
        svc.task_add("s1", "t1", "T1")
        svc.decide("Use REST", task_slug="t1")
        svc.epic_delete("e1")
        # Decisions survive but task_slug is SET NULL (FK cascade)
        decs = svc.decisions()
        assert len(decs) == 1
        assert decs[0]["task_slug"] is None

    def test_cascade_delete_many_tasks(self, svc):
        """Cascade works with many tasks (50+)."""
        svc.epic_add("big", "Big Epic")
        svc.story_add("big", "big-story", "Big Story")
        for i in range(50):
            svc.task_add("big-story", f"task-{i:03d}", f"Task {i}")
        assert len(svc.task_list()) == 50
        svc.epic_delete("big")
        assert len(svc.task_list()) == 0
