"""An edge whose target left is invalidated where the departure happens, so the sweep ends.

MEASURED BEFORE, on 2000 memory rows with 40 orphans, three consecutive sweeps:
`returned=40/0/0` while each re-serialized 40 files and left 40 orphans. Forty
serializations that changed nothing, on every departure, growing with archived memory.

MEASURED AFTER, same shape: orphans reach 0 on the first departure and stay there, and all
edge rows remain with `valid_to` stamped — soft, because a link that existed and ended is a
different fact from one that never was.

The fix is three invalidation points and one helper, so this file is six tests: the
convergence claim, each departure path, and the two ways a "fix" could cheat — erasing the
graph, or ending the wrong kind of edge.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import state_triggers  # noqa: E402


@pytest.fixture
def linked(tmp_path):
    """20 edges whose targets are about to leave.

    Ids come from the DATABASE, not from `memory_add`'s return value — that is a
    confirmation message, and reading it as an id is what made the first run of this
    measurement insert nonsense into `memory_edges` while the code was fine.
    """
    from project_backend import SQLiteBackend
    from project_service import ProjectService

    root = tmp_path / "proj"
    (root / ".tausik").mkdir(parents=True)
    svc = ProjectService(SQLiteBackend(str(root / ".tausik" / "tausik.db")))
    for i in range(40):
        svc.memory_add("pattern", f"Row number {i} of the probe", f"Body of row {i}")
    ids = [int(r["id"]) for r in svc.be._q("SELECT id FROM memory ORDER BY id")]
    for i in range(0, 40, 2):
        svc.be.edge_add("memory", ids[i], "memory", ids[i + 1], "relates_to")
    yield svc, ids, [ids[i + 1] for i in range(0, 40, 2)]
    svc.be.close()


def _orphans(svc) -> int:
    return len(svc.be._q(state_triggers._ORPHANED_EDGE_SOURCES))


def _counts(svc) -> tuple[int, int]:
    live = svc.be._q1("SELECT COUNT(*) c FROM memory_edges WHERE valid_to IS NULL")["c"]
    dead = svc.be._q1("SELECT COUNT(*) c FROM memory_edges WHERE valid_to IS NOT NULL")["c"]
    return live, dead


def test_three_consecutive_sweeps_find_nothing(linked):
    """The measurement that filed the defect, run as a test.

    Before the fix this returned 40 then 0 then 0 with 40 orphans left each time. The claim
    is not that the sweep got faster but that there is nothing left for it to find.
    """
    svc, _ids, targets = linked
    assert _orphans(svc) == 0, "nothing has left yet"
    svc.be.memory_archive_ids(targets)
    for _ in range(3):
        assert state_triggers._reproject_orphaned_edge_sources(svc) == 0
        assert _orphans(svc) == 0


@pytest.mark.parametrize("departure", ["archive_ids", "archive_apply", "delete"])
def test_every_departure_path_ends_the_edges(linked, departure):
    """Three paths, not the one that was easiest to reach.

    `memory_archive_ids`, `memory_archive_apply` (a cutoff, so its ids must be read BEFORE
    the update) and `_delete_projected_by_id` are separate code; fixing one would leave the
    sweep re-serializing forever through the others.
    """
    svc, _ids, targets = linked
    if departure == "archive_ids":
        svc.be.memory_archive_ids(targets)
    elif departure == "archive_apply":
        assert svc.be.memory_archive_apply("2999-01-01T00:00:00Z") > 0
    else:
        for mid in targets:
            svc.be.memory_delete(mid)
    assert _orphans(svc) == 0


def test_invalidation_is_soft_so_the_graph_keeps_its_past(linked):
    """Deleting would converge too, and would make the graph lie about what was linked."""
    svc, _ids, targets = linked
    assert _counts(svc) == (20, 0)
    svc.be.memory_archive_ids(targets)
    assert _counts(svc) == (0, 20), "a row disappeared instead of being stamped"


def test_an_edge_to_a_living_row_stays_live(linked):
    """The first way a fix could cheat: invalidate everything and call it convergence."""
    svc, ids, targets = linked
    for i in range(0, 40, 2):
        svc.be.edge_add("memory", ids[i], "memory", ids[i], "relates_to")
    svc.be.memory_archive_ids(targets)
    live = svc.be._q("SELECT target_id FROM memory_edges WHERE valid_to IS NULL")
    assert live, "every edge was invalidated — the graph was erased, not converged"
    assert all(int(r["target_id"]) not in targets for r in live)


def test_only_the_named_kind_is_touched(linked):
    """The second way: `memory_edges` is polymorphic, so an id alone matches too much.

    A decision edge whose target id happens to equal a departed memory id must survive.
    """
    svc, ids, _targets = linked
    svc.be.edge_add("decision", 1, "decision", ids[0], "relates_to")
    svc.be._edges_invalidate_to("memory", [ids[0]])
    kept = svc.be._q1(
        "SELECT COUNT(*) c FROM memory_edges WHERE target_type='decision' AND valid_to IS NULL"
    )["c"]
    assert kept == 1, "a decision edge was ended by a memory departure"
