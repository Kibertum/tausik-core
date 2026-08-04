"""The projection follows the WRITE, not the caller's memory.

`state-git-triggers` hung the export off each mutating service method by hand.
That list grew from two to eight to fourteen, and `service_cascade` still wrote
story/epic status straight through `self.be` with nothing projecting: starting a
task flipped its story to `active` in the DB while `tausik/stories/*.md` kept
saying `open`, and closing the last task of an epic closed the epic in the DB and
left it `active` in git — on a tree the team is meant to read.

`SQLiteBackend._update` is where all three of those writes already met, so the
hook lives there, and the cases below are the ones it genuinely closes: an UPDATE
by slug and a delete on epics/stories/tasks.

That is ALL it closes. This docstring used to add "a mutator nobody remembers to
wire is covered on the commit that introduces it", which was not true and is not
what these tests check — every INSERT, both knowledge kinds, the budget setters
and the bulk archive go around the hook, and the service layer's hand-written
calls are what keep them projected. `auto_export_write` now lists the gaps by
name, and `test_the_hook_alone_does_not_carry_the_projection` holds the line by
measuring it. Coverage as a whole is guaranteed by the property in
`test_state_projection_tracks_db.py`, not by either mechanism on its own.

The transaction cases are here for a reason of their own. `task_done` runs its
status change and the cascade inside one transaction, so an eager write would put
a file on disk describing state a rollback then discards — the same divergence
with the sign flipped.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import state_triggers  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from state_import import ENTITY_DIRS  # noqa: E402

_AC = "1. Делает своё дело.\n2. Ошибка при пустом поле."


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "proj.db")))
    yield s
    s.be.close()


@pytest.fixture
def root(monkeypatch, tmp_path):
    """Auto-export on, tree root in a tmp dir -- never the real project's."""
    r = tmp_path / "tausik"
    monkeypatch.setattr(state_triggers, "_auto_export_enabled", lambda _d: True)
    monkeypatch.setattr(state_triggers, "_tree_root", lambda _v: str(r))
    return str(r)


def _seed(svc):
    svc.epic_add("ep", "Epic")
    svc.story_add("ep", "st", "Story")
    svc.task_add("st", "t1", "Task one", goal="do it")
    svc.task_update("t1", acceptance_criteria=_AC)


def _projected(root: str, kind: str, slug: str) -> str:
    with open(os.path.join(root, kind, f"{slug}.md"), encoding="utf-8", newline="") as fh:
        return fh.read()


class TestCascadeReachesTheTree:
    def test_starting_a_task_projects_its_story_status(self, svc, root):
        """The headline defect, end to end through the real `task_start`."""
        _seed(svc)
        # PREMISE: without an `open` story the cascade's guard never fires and a
        # green result would say nothing about whether the projection followed.
        assert svc.be.story_get("st")["status"] == "open"
        assert "status: open" in _projected(root, "stories", "st")

        svc.task_start("t1")

        assert svc.be.story_get("st")["status"] == "active"
        assert "status: active" in _projected(root, "stories", "st"), (
            "story status changed in the DB but not in the tree -- the cascade "
            "wrote through the backend and nothing projected"
        )

    def test_closing_the_last_task_projects_story_and_epic(self, svc, root):
        _seed(svc)
        svc.task_start("t1")
        assert "status: active" in _projected(root, "epics", "ep")

        svc.be.task_update("t1", status="done")
        svc._cascade_done("t1")

        assert svc.be.story_get("st")["status"] == "done"
        assert svc.be.epic_get("ep")["status"] == "done"
        assert "status: done" in _projected(root, "stories", "st")
        assert "status: done" in _projected(root, "epics", "ep"), (
            "an epic auto-closed in the DB stayed active in git -- the tree the "
            "team clones would show work that is finished as still running"
        )


class TestTransactionSemantics:
    """`task_done` cascades inside a transaction; the projection must wait for it."""

    def test_projection_waits_for_the_commit_then_lands(self, svc, root):
        _seed(svc)
        svc.be.begin_tx()
        svc.be.story_update("st", status="active")
        assert "status: open" in _projected(root, "stories", "st"), (
            "a file was written mid-transaction -- a rollback would now leave the "
            "tree describing state the DB never kept"
        )
        svc.be.commit_tx()
        assert "status: active" in _projected(root, "stories", "st")

    def test_rollback_discards_the_pending_projection(self, svc, root):
        _seed(svc)
        svc.be.begin_tx()
        svc.be.story_update("st", status="active")
        svc.be.rollback_tx()
        assert svc.be.story_get("st")["status"] == "open"
        assert "status: open" in _projected(root, "stories", "st")
        # And the discarded pair must not resurface on the NEXT commit.
        svc.be.begin_tx()
        svc.be.epic_update("ep", status="active")
        svc.be.commit_tx()
        assert "status: open" in _projected(root, "stories", "st")


class TestTheHookKeysOnTheRegistry:
    def test_every_projected_kind_is_a_real_table(self, svc):
        """The table->kind mapping is identity; that is asserted, not assumed.

        `auto_export_write` looks a written table up in `ENTITY_DIRS` directly.
        If a projected kind ever stops naming a table, the hook silently covers
        nothing -- so the correspondence is checked rather than trusted.
        """
        names = {r["name"] for r in svc.be._q("SELECT name FROM sqlite_master WHERE type='table'")}
        missing = [k for k in ENTITY_DIRS if k not in names]
        assert not missing, f"projected kinds with no matching table: {missing}"

    def test_a_write_to_an_unprojected_table_is_ignored(self, svc, root):
        """Boundary: the hook must not try to render rows the tree has no room for."""
        assert state_triggers.auto_export_write(svc.be, "sessions", "whatever") is False
        assert state_triggers.auto_export_write(svc.be, "../etc", "x") is False


class TestItStaysBestEffort:
    def test_an_unchanged_write_does_not_rewrite_the_file(self, svc, root):
        """Idempotence: no mtime churn, or every `git status` fills with noise."""
        _seed(svc)
        path = os.path.join(root, "stories", "st.md")
        before = os.stat(path).st_mtime_ns
        svc.be.story_update("st", status="open")  # same value
        assert os.stat(path).st_mtime_ns == before

    def test_a_failing_export_does_not_break_the_db_write(self, svc, root, monkeypatch):
        """FAIL-OPEN: the DB is the source of truth; the projection is a courtesy."""

        def boom(*_a, **_k):
            raise OSError("disk gone")

        import state_export

        # Patched INSIDE the export, not at `auto_export_entity`: that function is
        # where the fail-open lives, so replacing it would test the test.
        monkeypatch.setattr(state_export, "export_one", boom)
        svc.be.story_update("st2", status="active")  # missing row: rowcount 0, no hook
        svc.epic_add("ep2", "Epic two")
        assert svc.be.epic_update("ep2", status="active") == 1
        assert svc.be.epic_get("ep2")["status"] == "active"
