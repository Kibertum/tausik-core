"""A plan's ORDER must be expressible in the system that carries the plan.

`task next` sorted by complexity score and called the winner "suggested", which
a reader takes for priority. The project states order in decisions and in the
release plan -- "this one FIRST", "that one ONLY after it" -- and none of that
reached the query. An agent trusting the command started in the middle of a
sequence whose every step depends on the previous one.

The shape of the fix follows the shape of the statement it has to carry: the
plan says "after", so the mechanism is an EDGE, not a priority number. A number
would need the whole queue renumbered on every insertion and would never say
*why* the order is what it is.

These tests are written before the mechanism exists and fail without it.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from service_task_order import (  # noqa: E402
    task_depends,
    task_deps,
    task_next_report,
    task_undepends,
)
from tausik_utils import ServiceError  # noqa: E402


@pytest.fixture
def svc(tmp_path):
    be = SQLiteBackend(str(tmp_path / "test.db"))
    service = ProjectService(be)
    service.epic_add("v1", "Version 1")
    service.story_add("v1", "setup", "Setup")
    yield service
    be.close()


def _tasks(svc, *specs):
    for slug, complexity in specs:
        svc.task_add("setup", slug, slug.upper(), complexity=complexity)


# ---- The edge exists and is declarable -------------------------------


class TestDeclaringOrder:
    def test_a_task_can_be_declared_to_come_after_another(self, svc):
        _tasks(svc, ("first", "simple"), ("second", "simple"))
        msg = task_depends(svc, "second", "first")
        assert "second" in msg and "first" in msg

    def test_the_declaration_is_readable_back(self, svc):
        _tasks(svc, ("first", "simple"), ("second", "simple"))
        task_depends(svc, "second", "first")
        assert task_deps(svc, "second") == ["first"]

    def test_a_task_may_wait_on_several_predecessors(self, svc):
        _tasks(svc, ("a", "simple"), ("b", "simple"), ("c", "simple"))
        task_depends(svc, "c", "a")
        task_depends(svc, "c", "b")
        assert sorted(task_deps(svc, "c")) == ["a", "b"]

    def test_declaring_the_same_edge_twice_is_not_an_error_and_not_a_duplicate(self, svc):
        """Re-running a plan script must converge, not accumulate."""
        _tasks(svc, ("a", "simple"), ("b", "simple"))
        task_depends(svc, "b", "a")
        task_depends(svc, "b", "a")
        assert task_deps(svc, "b") == ["a"]

    def test_an_edge_can_be_withdrawn(self, svc):
        _tasks(svc, ("a", "simple"), ("b", "simple"))
        task_depends(svc, "b", "a")
        task_undepends(svc, "b", "a")
        assert task_deps(svc, "b") == []


# ---- Refusals must name what is wrong --------------------------------


class TestRefusalsAreNamed:
    def test_an_unknown_predecessor_is_refused_by_name(self, svc):
        _tasks(svc, ("b", "simple"))
        with pytest.raises(ServiceError, match="nope"):
            task_depends(svc, "b", "nope")

    def test_an_unknown_dependent_is_refused_by_name(self, svc):
        _tasks(svc, ("a", "simple"))
        with pytest.raises(ServiceError, match="ghost"):
            task_depends(svc, "ghost", "a")

    def test_a_task_cannot_depend_on_itself(self, svc):
        _tasks(svc, ("a", "simple"))
        with pytest.raises(ServiceError, match="itself"):
            task_depends(svc, "a", "a")

    def test_a_cycle_is_refused_at_declaration_and_names_the_path(self, svc):
        """Refused when DECLARED, not discovered later during a traversal.

        A cycle accepted into the table makes every later reader responsible for
        surviving it. Refusing at the edge keeps the graph acyclic by
        construction, and the message names the path so the author can see which
        of their own statements contradicts the new one.
        """
        _tasks(svc, ("a", "simple"), ("b", "simple"), ("c", "simple"))
        task_depends(svc, "b", "a")
        task_depends(svc, "c", "b")
        with pytest.raises(ServiceError) as excinfo:
            task_depends(svc, "a", "c")

        message = str(excinfo.value)
        assert "cycle" in message
        # The PATH, not just the word. Asserting only on "cycle" let a version
        # ship that printed `a -> a -> c`: technically a refusal, but it named
        # the wrong loop and repeated the first node.
        assert "a -> c -> b -> a" in message
        assert task_deps(svc, "a") == []


# ---- What `task next` may offer --------------------------------------


class TestNextRespectsOrder:
    def test_a_task_with_an_unfinished_predecessor_is_not_offered(self, svc):
        """The mandatory negative: the heaviest task waits its turn."""
        _tasks(svc, ("light-first", "simple"), ("heavy-second", "complex"))
        task_depends(svc, "heavy-second", "light-first")

        picked = svc.task_next()
        assert picked is not None
        assert picked["slug"] == "light-first"

    def test_the_successor_becomes_available_once_the_predecessor_is_done(self, svc):
        _tasks(svc, ("light-first", "simple"), ("heavy-second", "complex"))
        task_depends(svc, "heavy-second", "light-first")
        svc.be.task_update("light-first", status="done")

        picked = svc.task_next()
        assert picked is not None
        assert picked["slug"] == "heavy-second"

    def test_without_edges_the_old_order_is_unchanged(self, svc):
        """Complexity remains the tie-break among ready tasks.

        The task was about ORDER being inexpressible, not about the score being
        the wrong tie-break. Changing both at once would leave neither measured.
        """
        _tasks(svc, ("low", "simple"), ("high", "complex"), ("mid", "medium"))
        picked = svc.task_next()
        assert picked is not None
        assert picked["slug"] == "high"

    def test_a_predecessor_that_is_merely_active_still_blocks(self, svc):
        """`after` means after it is DONE, not after somebody started it."""
        _tasks(svc, ("first", "simple"), ("second", "complex"))
        task_depends(svc, "second", "first")
        svc.be.task_update("first", status="active")

        picked = svc.task_next()
        assert picked is None or picked["slug"] != "second"


# ---- Empty must not be conflated with blocked ------------------------


class TestNothingToOfferIsTwoDifferentStates:
    def test_an_empty_backlog_and_a_blocked_backlog_differ(self, svc):
        """`None` for both would report a stalled plan as a finished one.

        Same class as `check-result-conflates-could-not-run-with-passed`: the
        caller cannot act on an answer that merges "there is no work" with
        "all remaining work is waiting on something".
        """
        assert task_next_report(svc)["state"] == "empty"

        _tasks(svc, ("first", "simple"), ("second", "simple"))
        task_depends(svc, "second", "first")
        svc.be.task_update("first", status="active")

        report = task_next_report(svc)
        assert report["state"] == "all-blocked"
        assert "second" in report["blocked"]

    def test_a_saturated_team_is_not_an_empty_backlog(self, svc):
        """The conflation the FIRST version of this fix left behind.

        `task next` used to return `None` for three situations; splitting off
        "everything waits on a predecessor" and then folding "everything is
        claimed" back into `empty` reproduces the same defect one size smaller.
        A fresh agent reading "no available tasks" concludes the work is done;
        reading "all claimed" concludes the team is saturated. Opposite actions.
        """
        _tasks(svc, ("taken", "simple"))
        svc.task_claim("taken", "agent-7")

        report = task_next_report(svc)
        assert report["state"] == "all-claimed"
        assert report["claimed"] == ["taken"]

    def test_a_genuinely_empty_backlog_still_says_empty(self, svc):
        """The green branch that keeps the case above from being vacuous."""
        report = task_next_report(svc)
        assert report["state"] == "empty"
        assert report["claimed"] == []
        assert report["blocked"] == []

    def test_a_ready_backlog_reports_its_basis(self, svc):
        """AC4: the command says WHAT it ordered by, so nobody reads priority
        into a complexity sort."""
        _tasks(svc, ("low", "simple"), ("high", "complex"))
        report = task_next_report(svc)
        assert report["state"] == "ready"
        assert report["task"]["slug"] == "high"
        assert "complexity" in report["basis"]

    def test_the_report_counts_what_it_withheld(self, svc):
        _tasks(svc, ("first", "simple"), ("second", "complex"), ("third", "complex"))
        task_depends(svc, "second", "first")
        task_depends(svc, "third", "first")

        report = task_next_report(svc)
        assert report["state"] == "ready"
        assert report["task"]["slug"] == "first"
        assert sorted(report["blocked"]) == ["second", "third"]


# ---- The plan must survive a clone -----------------------------------


class TestOrderTravelsWithTheProjection:
    def test_the_edge_is_serialized_into_the_task_file(self, svc):
        from state_export import build_tree

        _tasks(svc, ("first", "simple"), ("second", "simple"))
        task_depends(svc, "second", "first")

        tree, _ = build_tree(svc)
        assert "first" in tree["tasks/second.md"]

    def test_the_edge_survives_a_round_trip(self, tmp_path, svc):
        """A plan that evaporates on clone is the defect, not the fix.

        Exported to disk and imported into a SEPARATE database, because that is
        the journey the projection actually makes: a clone reads files, not a
        dict a test handed it.
        """
        from state_export import build_tree
        from state_import import import_tree
        from state_serialize import write_tree

        _tasks(svc, ("first", "simple"), ("second", "simple"))
        task_depends(svc, "second", "first")

        out = tmp_path / "tree"
        tree, _ = build_tree(svc)
        write_tree(str(out), tree)

        be2 = SQLiteBackend(str(tmp_path / "clone.db"))
        clone = ProjectService(be2)
        try:
            import_tree(clone, str(out))
            assert task_deps(clone, "second") == ["first"]
        finally:
            be2.close()


class TestTheTriggerWritesTheEdgeToDisk:
    """What `_UNREACHABLE` in the ratchet points at for its evidence.

    The tests above compare `build_tree` output, which proves the SERIALIZER
    carries the edge. This one proves the auto-export TRIGGER fires on
    `task_depends` / `task_undepends`, so the file on disk moves with the row --
    the property the ratchet would otherwise have had to observe itself.
    """

    @pytest.fixture
    def projected(self, tmp_path, monkeypatch):
        import project_config
        import state_triggers

        monkeypatch.setattr(project_config, "find_tausik_dir", lambda *a, **k: str(tmp_path))
        monkeypatch.setattr(state_triggers, "_auto_export_enabled", lambda _d: True)
        monkeypatch.setattr(
            state_triggers,
            "_tree_root",
            lambda handle: os.path.join(str(tmp_path), "tausik"),
        )
        be = SQLiteBackend(str(tmp_path / "proj.db"))
        service = ProjectService(be)
        service.epic_add("v1", "Version 1")
        service.story_add("v1", "setup", "Setup")
        try:
            yield service, os.path.join(str(tmp_path), "tausik")
        finally:
            be.close()

    def _read(self, root, slug):
        path = os.path.join(root, "tasks", f"{slug}.md")
        with open(path, encoding="utf-8", newline="") as handle:
            return handle.read()

    def test_declaring_an_edge_rewrites_the_task_file(self, projected):
        service, root = projected
        _tasks(service, ("first", "simple"), ("second", "simple"))
        task_depends(service, "second", "first")

        assert "first" in self._read(root, "second")

    def test_withdrawing_an_edge_rewrites_the_task_file(self, projected):
        """A withdrawal that does not reach the tree leaves a ghost constraint --
        a file saying the task waits for something the database no longer holds."""
        service, root = projected
        _tasks(service, ("first", "simple"), ("second", "simple"))
        task_depends(service, "second", "first")
        assert "depends_on" in self._read(root, "second")

        task_undepends(service, "second", "first")
        doc = self._read(root, "second")
        assert "- first" not in doc
