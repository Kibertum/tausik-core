"""state-git-triggers: incremental single-entity export + fail-open lifecycle.

The load-bearing property is byte-identity: `export_one(kind, slug)` must produce
exactly the bytes `build_tree` would for that entity, so an incremental write on
task-done/decide/memory-add and a full export never diverge. Plus fail-open (a
serialization error must not break the underlying operation) and the disable flag.
"""

from __future__ import annotations

import os
import shutil
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from state_export import build_tree, export_one  # noqa: E402


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "trig.db")))
    yield s
    s.be.close()


def _seed(svc):
    svc.epic_add("team-state", "Состояние в git")
    svc.story_add("team-state", "mvp", "MVP в ветке")
    svc.task_add(
        "mvp", "exp", "Экспорт: сериализатор", stack="python", complexity="complex", goal="Цель"
    )
    svc.be.task_update(
        "exp",
        plan="план",
        scope_paths='["b.py", "a.py"]',
        call_budget=120,
        completed_at="2026-07-24T15:00:00Z",
    )
    svc.be._ex(
        "INSERT INTO task_logs(task_slug, message, phase, created_at) VALUES(?,?,?,?)",
        ("exp", "шаг", "implementation", "2026-07-24T15:10:00Z"),
    )
    a = svc.be.memory_add("pattern", "Память альфа", "тело A", ["git", "state"], "exp")
    b = svc.be.memory_add("gotcha", "Память бета", "тело B", None, "exp")
    d = svc.be.decision_add("Решение первое", "exp", "обоснование")
    svc.be.edge_add("memory", a, "memory", b, "relates_to")
    svc.be.edge_add("memory", a, "decision", d, "caused_by")


def test_export_one_is_byte_identical_to_build_tree(svc):
    _seed(svc)
    tree, _ = build_tree(svc)
    # every file in the full tree must be reproduced exactly by export_one
    for rel, content in tree.items():
        kind, name = rel.split("/", 1)
        slug = name[:-3]  # strip .md
        result = export_one(svc, kind, slug)
        assert result is not None, rel
        rel2, content2 = result
        assert rel2 == rel
        assert content2 == content, f"byte mismatch for {rel}"


def test_export_one_absent_entity_returns_none(svc):
    _seed(svc)
    assert export_one(svc, "tasks", "does-not-exist") is None
    assert export_one(svc, "memory", "nope") is None


def test_export_one_archived_memory_excluded(svc):
    _seed(svc)
    arch = svc.be.memory_add("pattern", "Dead mem", "y", None, "exp")
    slug = svc.be._q1("SELECT slug FROM memory WHERE id=?", (arch,))["slug"]
    svc.be.memory_archive_ids([arch])
    assert export_one(svc, "memory", slug) is None  # archived → not projected


# --- auto_export triggers (fail-open, config-gated, idempotent) ---------------

import state_triggers  # noqa: E402


@pytest.fixture
def enabled_root(monkeypatch, tmp_path):
    """Enable auto-export and point the tree root at a tmp dir (isolated config)."""
    root = tmp_path / "tausik"
    monkeypatch.setattr(state_triggers, "_auto_export_enabled", lambda _d: True)
    monkeypatch.setattr(state_triggers, "_tree_root", lambda _svc: str(root))
    return str(root)


def test_auto_export_disabled_writes_nothing(svc, monkeypatch, tmp_path):
    _seed(svc)
    root = tmp_path / "tausik"
    monkeypatch.setattr(state_triggers, "_auto_export_enabled", lambda _d: False)
    monkeypatch.setattr(state_triggers, "_tree_root", lambda _svc: str(root))
    assert state_triggers.auto_export_entity(svc, "tasks", "exp") is False
    assert not root.exists()  # disabled → no surprise files


def test_auto_export_writes_byte_identical_single_file(svc, enabled_root):
    _seed(svc)
    tree, _ = build_tree(svc)
    # Seeding now projects as it goes (every mutator exports, not just three), so
    # the tree is wiped here to isolate what THIS call writes. The claim under
    # test is incrementality — one entity in, one file out — and that claim used
    # to be read off a tree that was empty only because seeding did not export.
    shutil.rmtree(enabled_root, ignore_errors=True)
    assert state_triggers.auto_export_entity(svc, "tasks", "exp") is True
    p = os.path.join(enabled_root, "tasks", "exp.md")
    with open(p, encoding="utf-8", newline="") as fh:
        assert fh.read() == tree["tasks/exp.md"]  # identical to full export
    # exactly ONE file written, not the whole tree
    written = [f for _d, _s, fs in os.walk(enabled_root) for f in fs]
    assert written == ["exp.md"]


def test_auto_export_idempotent(svc, enabled_root):
    _seed(svc)
    assert state_triggers.auto_export_entity(svc, "tasks", "exp") is True
    assert state_triggers.auto_export_entity(svc, "tasks", "exp") is False  # unchanged


def test_auto_export_fail_open_on_serialization_error(svc, enabled_root, monkeypatch):
    _seed(svc)

    def _boom(*a, **k):
        raise RuntimeError("serialization blew up")

    monkeypatch.setattr("state_export.export_one", _boom)
    # must NOT raise — fail-open swallows and returns False
    assert state_triggers.auto_export_entity(svc, "tasks", "exp") is False


def test_auto_export_slugless_skips_without_crash(svc, enabled_root):
    _seed(svc)
    # a non-existent slug (export_one → None) is skipped, never crashes
    assert state_triggers.auto_export_entity(svc, "tasks", "ghost") is False


def test_memory_add_service_triggers_export(svc, enabled_root):
    _seed(svc)
    svc.memory_add("pattern", "Свежая память", "тело", ["x"], "exp")
    slug = svc.be._q1("SELECT slug FROM memory WHERE title='Свежая память'")["slug"]
    assert os.path.isfile(os.path.join(enabled_root, "memory", f"{slug}.md"))


def test_import_suggested_none_when_tree_matches_db(svc, enabled_root):
    from state_serialize import write_tree
    from state_export import ENTITY_DIRS

    _seed(svc)
    tree, _ = build_tree(svc)
    write_tree(enabled_root, tree, managed_dirs=set(ENTITY_DIRS))
    # a fresh DB imported from this tree == matches → but here svc IS the source,
    # so a dry-run import finds the same entities already present → no changes
    assert state_triggers.import_suggested(svc) is None


def test_import_suggested_flags_divergence(monkeypatch, tmp_path):
    """A tree carrying an entity the DB lacks → suggestion with counts."""
    from state_serialize import write_tree
    from state_export import ENTITY_DIRS

    src = ProjectService(SQLiteBackend(str(tmp_path / "src.db")))
    root = str(tmp_path / "tausik")
    try:
        _seed(src)
        tree, _ = build_tree(src)
    finally:
        src.be.close()
    write_tree(root, tree, managed_dirs=set(ENTITY_DIRS))
    fresh = ProjectService(SQLiteBackend(str(tmp_path / "fresh.db")))
    monkeypatch.setattr(state_triggers, "_tree_root", lambda _svc: root)
    try:
        sug = state_triggers.import_suggested(fresh)  # empty DB, populated tree
        assert sug is not None and sug["added"] > 0
        # the tree genuinely holds rows the DB has none of — the ONE direction the
        # counts do establish
        assert sug["direction"] == "tree-has-rows-db-lacks"
    finally:
        fresh.be.close()


def test_stale_tree_is_not_reported_as_carrying_new_state(svc, enabled_root, monkeypatch):
    """AC-10: the tree being BEHIND must not read as the tree being AHEAD.

    Divergence proves the two sides differ, never which is newer. Here the DB is
    newer (the projection predates a status change), so calling this "files carry
    state the DB does not" — and suggesting `tausik sync` on it — would revert a
    closed task back to planning.

    HOW THE TREE IS MADE STALE MATTERS. This used to rely on `be.task_update`
    not projecting at all, which was the cascade-projection defect, not a
    scenario: once the write layer started projecting, the premise evaporated and
    there was nothing left to diverge. The staleness is now produced the way it
    actually occurs — `state.auto_export` is opt-in and OFF by default, so a
    project that never enabled it accumulates exactly this drift.
    """
    from state_export import ENTITY_DIRS
    from state_serialize import write_tree

    _seed(svc)
    tree, _ = build_tree(svc)
    write_tree(enabled_root, tree, managed_dirs=set(ENTITY_DIRS))
    monkeypatch.setattr(state_triggers, "_auto_export_enabled", lambda _d: False)
    svc.be.task_update("exp", status="done")  # DB moves on; projection does not
    monkeypatch.setattr(state_triggers, "_auto_export_enabled", lambda _d: True)

    sug = state_triggers.import_suggested(svc)
    assert sug is not None, "a real divergence must still be reported"
    assert sug["updated"] > 0
    assert sug["added"] == 0 and sug["journal"] == 0 and sug["edges"] == 0
    assert sug["direction"] == "field-divergence-only"
    # and the guidance must not name sync as the unconditional resolution
    assert "tausik state export" in sug["resolve"]


def test_prewarm_is_safe_without_a_tree(svc, monkeypatch):
    """A warm-up must never matter: no tree → False, no raise."""
    monkeypatch.setattr(state_triggers, "_tree_root", lambda _svc: None)
    assert state_triggers.prewarm(svc) is False


def test_prewarm_reads_the_tree_when_present(svc, enabled_root):
    from state_export import ENTITY_DIRS
    from state_serialize import write_tree

    _seed(svc)
    tree, _ = build_tree(svc)
    write_tree(enabled_root, tree, managed_dirs=set(ENTITY_DIRS))
    assert state_triggers.prewarm(svc) is True
