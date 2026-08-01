"""Deleting a parent must not leave its children on disk.

`stories.epic_id` and `tasks.story_id` are `ON DELETE CASCADE`, and every
connection runs with `PRAGMA foreign_keys=ON`, so SQLite deletes the children
itself and Python never learns which rows went. Deleting an epic therefore
removed the epic's file and left its stories and tasks behind as GHOSTS — files
describing rows the DB no longer has. A full `state export` hid it (it rebuilds
the tree from scratch); only the incremental path accumulated them, and only
`state export --check` ever complained, in the vocabulary of "drift".

`ON DELETE SET NULL` is the quieter half of the same problem: `decisions.task_slug`
is blanked rather than removed, so the row survives with different content and its
file goes stale. Both are collected the same way, and both are handled by asking
`export_one` again — it answers `None` for a row that is gone and fresh bytes for
a row that changed.

Which children exist is read from the schema, not listed here. That is the whole
point: the previous two fixes in this area each shipped a list, and each list was
missing the case that broke next.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import state_triggers  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from state_export import build_tree  # noqa: E402
from state_import import ENTITY_DIRS  # noqa: E402


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "proj.db")))
    yield s
    s.be.close()


@pytest.fixture
def root(monkeypatch, tmp_path):
    r = tmp_path / "tausik"
    monkeypatch.setattr(state_triggers, "_auto_export_enabled", lambda _d: True)
    monkeypatch.setattr(state_triggers, "_tree_root", lambda _v: str(r))
    return str(r)


def _seed(svc):
    svc.epic_add("ep", "Epic")
    svc.story_add("ep", "st", "Story")
    svc.task_add("st", "t1", "Task one", goal="do it")


def _on_disk(root: str) -> set[str]:
    out: set[str] = set()
    for kind in ENTITY_DIRS:
        d = os.path.join(root, kind)
        if os.path.isdir(d):
            out.update(f"{kind}/{n}" for n in os.listdir(d) if n.endswith(".md"))
    return out


def _in_db(svc) -> set[str]:
    return set(build_tree(svc)[0])


class TestTheTreeShrinksWithTheDb:
    def test_deleting_an_epic_takes_its_stories_and_tasks_off_disk(self, svc, root):
        _seed(svc)
        # PREMISE: all three are on disk, so their absence later means removal and
        # not "never written" -- the failure mode a weaker test would confuse it with.
        assert {"epics/ep.md", "stories/st.md", "tasks/t1.md"} <= _on_disk(root)

        svc.epic_delete("ep")

        assert _in_db(svc) == set(), "sanity: the cascade emptied the DB"
        assert _on_disk(root) == set(), (
            "children of a deleted epic stayed on disk -- the tree now describes "
            "rows the DB has never heard of"
        )

    def test_deleting_a_story_takes_its_tasks_off_disk(self, svc, root):
        _seed(svc)
        svc.story_delete("st")
        assert _on_disk(root) == _in_db(svc) == {"epics/ep.md"}

    def test_a_set_null_child_is_re_rendered_not_removed(self, svc, root):
        """`decisions.task_slug` is blanked, not deleted: the row stays, changed."""
        _seed(svc)
        # Through the service: `decision_add` is a raw INSERT and does not project,
        # and this test is about what happens to a file that IS on disk.
        svc.decide("Решение", task_slug="t1", rationale="обоснование")
        dec = svc.be._q1("SELECT slug FROM decisions WHERE task_slug=?", ("t1",))
        rel = f"decisions/{dec['slug']}.md"
        assert rel in _on_disk(root)

        svc.be.task_delete("t1")

        assert rel in _on_disk(root), "the decision row survives, so must its file"
        assert _on_disk(root) == _in_db(svc)
        with open(os.path.join(root, rel), encoding="utf-8", newline="") as fh:
            assert "t1" not in fh.read(), (
                "the decision file still names a task that no longer exists -- "
                "the SET NULL never reached the projection"
            )


class TestVictimsComeFromTheSchema:
    def test_children_are_discovered_not_listed(self, svc):
        """The relation is read from `PRAGMA foreign_key_list`, so it cannot drift."""
        assert ("stories", "epic_id", "id") in svc.be._dependent_tables("epics")
        assert ("tasks", "story_id", "id") in svc.be._dependent_tables("stories")

    def test_collection_is_transitive_and_terminates(self, svc):
        """A grandchild must be collected; a self-referencing FK must not loop."""
        _seed(svc)
        svc.task_add("st", "t2", "Defect of t1", goal="g")
        svc.be.task_update("t2", defect_of="t1")
        victims = svc.be._projection_victims("epics", "ep")
        assert ("stories", "st") in victims
        assert ("tasks", "t1") in victims and ("tasks", "t2") in victims
        assert len(victims) == len(set(victims)), "a row was collected twice"

    def test_an_unprojected_or_missing_parent_collects_nothing(self, svc):
        assert svc.be._projection_victims("sessions", "x") == []
        assert svc.be._projection_victims("epics", "does-not-exist") == []


class TestItStaysBestEffort:
    def test_a_delete_that_matched_nothing_touches_no_files(self, svc, root):
        _seed(svc)
        before = _on_disk(root)
        assert svc.be.epic_delete("no-such-epic") == 0
        assert _on_disk(root) == before

    def test_a_failing_export_does_not_break_the_delete(self, svc, root, monkeypatch):
        import state_export

        _seed(svc)
        monkeypatch.setattr(state_export, "export_one", lambda *_a, **_k: 1 / 0)
        assert svc.be.epic_delete("ep") == 1
        assert svc.be.epic_get("ep") is None
