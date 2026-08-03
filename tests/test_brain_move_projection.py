"""`brain move` keeps the git projection in step — the module the ratchet cannot reach.

`tests/test_state_projection_tracks_db.py` proves the projection property over
generated SERVICE sequences. `brain_move` sits outside that: it is a migration
command driving `svc.be` directly, so its write paths were invisible to the tap
and its `("decisions", "DELETE")` exclusion cited this very defect as the reason.

All three of its writes went around the projection. Two raw
`DELETE ... WHERE id = ?` statements removed rows and left their files behind as
GHOSTS — files describing entries the database no longer had — and one raw
`decision_add` created a row with no file at all. `brain move` works in BATCHES,
so a single run left as many ghosts as it moved rows, and a later full
`state export` hid every one of them by rebuilding the tree from scratch. That
is the ugly part: `status` stayed clean while the incremental tree rotted.

Adding these operations to the generated sequence was tried and reverted; the
reason is recorded in that file's `_UNREACHABLE` entry. This file covers the
paths where they actually live.
"""

from __future__ import annotations

import os
import sys
from typing import Any

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import brain_move  # noqa: E402
import brain_mcp_write  # noqa: E402
import brain_runtime  # noqa: E402
import project_config  # noqa: E402
import state_triggers  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from state_export import build_tree  # noqa: E402
from state_import import ENTITY_DIRS  # noqa: E402

CROSSCUTTING_SCOPE = [
    "scripts/brain_move.py",
    "scripts/project_backend.py",
    "scripts/backend_crud_knowledge.py",
]


@pytest.fixture
def svc(tmp_path, monkeypatch):
    monkeypatch.setattr(project_config, "find_tausik_dir", lambda *_a, **_kw: str(tmp_path))
    s = ProjectService(SQLiteBackend(str(tmp_path / "proj.db")))
    yield s
    s.be.close()


def _tree_of(handle: Any) -> str:
    return os.path.join(os.path.dirname(os.path.abspath(str(handle.be.db_path))), "tausik")


@pytest.fixture
def root(monkeypatch, svc):
    monkeypatch.setattr(state_triggers, "_auto_export_enabled", lambda _d: True)
    monkeypatch.setattr(state_triggers, "_tree_root", _tree_of)
    return _tree_of(svc)


def _read_tree(root: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for kind in ENTITY_DIRS:
        d = os.path.join(root, kind)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if name.endswith(".md"):
                with open(os.path.join(d, name), encoding="utf-8", newline="") as fh:
                    out[f"{kind}/{name}"] = fh.read()
    return out


def _assert_tracks(svc, root: str, note: str) -> None:
    """The same property as the generated suite, asserted after a brain move."""
    expected, _ = build_tree(svc)
    actual = _read_tree(root)
    missing = sorted(set(expected) - set(actual))
    ghosts = sorted(set(actual) - set(expected))
    assert not missing, f"{note}: the DB has rows the tree lacks: {missing}"
    assert not ghosts, f"{note}: the tree has files the DB lacks: {ghosts}"
    differing = sorted(k for k in expected if expected[k] != actual[k])
    assert not differing, f"{note}: content diverged for {differing}"


@pytest.fixture
def brain_ok(monkeypatch):
    """A brain that accepts everything, with no Notion and no network.

    The publish itself is not what is under test — the LOCAL consequence is. A
    real store call would make this a network test and it would stop running.
    """
    monkeypatch.setattr(
        brain_runtime, "open_brain_deps", lambda *a, **kw: (object(), object(), {"enabled": True})
    )
    monkeypatch.setattr(
        brain_mcp_write,
        "store_record",
        lambda *a, **kw: {"status": "ok", "notion_page_id": "page-1"},
    )


def _mem_id(msg: str) -> int:
    """Service messages carry the new row's id; the digits are the id."""
    digits = "".join(ch for ch in msg if ch.isdigit())
    assert digits, f"no id in service reply: {msg!r}"
    return int(digits)


class TestHandingARowOverLeavesNoGhost:
    def test_moving_a_decision_out_removes_its_file(self, svc, root, brain_ok):
        did = _mem_id(svc.decide("Решение, которое уезжает", rationale="Основание"))
        svc.decide("Решение, которое остаётся")
        _assert_tracks(svc, root, "before the move")

        result = brain_move.move_to_brain(svc, "decision", did, keep_source=False)
        assert result["status"] == "ok", result

        _assert_tracks(svc, root, "after moving a decision out")

    def test_moving_a_memory_out_removes_its_file(self, svc, root, brain_ok):
        mid = _mem_id(svc.memory_add("pattern", "Уезжающий паттерн", "тело"))
        svc.memory_add("pattern", "Остающийся паттерн", "тело")
        _assert_tracks(svc, root, "before the move")

        result = brain_move.move_to_brain(svc, "pattern", mid, keep_source=False)
        assert result["status"] == "ok", result

        _assert_tracks(svc, root, "after moving a memory out")

    def test_a_departing_memory_leaves_no_edge_pointing_at_nothing(self, svc, root, brain_ok):
        """AC4(a): the referring row is re-rendered, not just the departing one.

        `memory_edges` is polymorphic, so a row that pointed at the one being
        moved keeps an `edges:` block naming it. `build_tree` drops such an edge
        with a warning while the incremental path never re-renders the source —
        the two disagree, and the disagreement is the defect.
        """
        keeper = _mem_id(svc.memory_add("pattern", "Остаётся и ссылается", "тело"))
        leaver = _mem_id(svc.memory_add("gotcha", "Уезжает", "тело"))
        svc.memory_link("memory", keeper, "memory", leaver, "relates_to")
        _assert_tracks(svc, root, "before the move")

        assert brain_move.move_to_brain(svc, "gotcha", leaver, keep_source=False)["status"] == "ok"

        _assert_tracks(svc, root, "after a linked memory departed")

    def test_publishing_without_keep_source_false_changes_nothing_locally(
        self, svc, root, brain_ok
    ):
        """The default is a MIRROR. Its whole point is that the local copy stays."""
        did = _mem_id(svc.decide("Решение, которое публикуется и остаётся"))
        before = _read_tree(root)

        assert brain_move.move_to_brain(svc, "decision", did)["status"] == "ok"

        assert _read_tree(root) == before
        _assert_tracks(svc, root, "after a publish that keeps the source")


class TestBringingARowBackCreatesItsFile:
    def test_a_decision_pulled_from_the_brain_is_projected(self, svc, root, monkeypatch):
        """The fourth call site of `decision_add` — the one nobody counted.

        `write_local`'s docstring counted three of four sites that reached past
        it and skipped the projection. This was the fourth, missed because the
        count was taken inside the service layer and this caller is not in it.
        """
        row = {
            "decision": "Решение, вернувшееся из brain",
            "rationale": "Основание",
            "source_project_hash": brain_move._current_project_hash(),
        }
        monkeypatch.setattr(
            brain_runtime,
            "open_brain_deps",
            lambda *a, **kw: (object(), object(), {"enabled": True}),
        )
        monkeypatch.setattr(brain_move, "_read_brain_row", lambda *a, **kw: row)

        # `keep_source=True`: what is under test is the LOCAL row appearing in the
        # tree. Letting the brain side be deleted too would drag a second, fake
        # database into a test about this one.
        result = brain_move.move_to_local(svc, "page-1", "decisions", keep_source=True)
        assert result["status"] == "ok", result

        _assert_tracks(svc, root, "after pulling a decision back")


class TestFailOpen:
    """AC4(b): the projection is best-effort; the migration is not its hostage."""

    def test_a_broken_projection_does_not_roll_back_or_kill_the_move(
        self, svc, root, brain_ok, monkeypatch
    ):
        did = _mem_id(svc.decide("Решение, чья проекция сломается"))

        def boom(*_a, **_kw):
            raise OSError("disk went away mid-projection")

        monkeypatch.setattr(state_triggers, "auto_export_entity", boom)

        result = brain_move.move_to_brain(svc, "decision", did, keep_source=False)

        assert result["status"] == "ok", "a projection failure aborted the migration itself"
        assert svc.be.decision_get(did) is None, "the DB write was rolled back by a failed export"
