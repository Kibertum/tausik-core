"""The git projection tracks the DB after ANY mutation — property, not call sites.

`state-git-triggers` shipped with the export wired into three places by hand, and
the prose said "task done / decide / memory add". Eighteen of the ~20 mutating
service methods never exported: a decision recorded WITH a task_slug — the common
case — reached the DB and never `tausik/`. Nothing caught it because a periodic
full `tausik state export` rebuilt the tree, so `status` reported no divergence.

Asserting "method X calls auto_export" would repeat the original mistake at test
level: it can only check the call sites someone remembered to list. The property
below is indifferent to how the export happens —

    after any sequence of mutations, with NO manual command in between,
    the files on disk equal build_tree(db) byte for byte

— so a new mutator that forgets to project fails here, and a refactor that moves
the export somewhere else does not.
"""

from __future__ import annotations

import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import state_triggers  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from state_export import build_tree  # noqa: E402
from state_import import ENTITY_DIRS  # noqa: E402


def _mem_id(message: str) -> int:
    """`memory_add` returns a human message, not the row id — pull it back out."""
    m = re.search(r"#(\d+)", message)
    assert m, f"unexpected memory_add message: {message!r}"
    return int(m.group(1))


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "proj.db")))
    yield s
    s.be.close()


@pytest.fixture
def root(monkeypatch, tmp_path):
    """Auto-export on, tree root in a tmp dir (never the real project's)."""
    r = tmp_path / "tausik"
    monkeypatch.setattr(state_triggers, "_auto_export_enabled", lambda: True)
    monkeypatch.setattr(state_triggers, "_tree_root", lambda _svc: str(r))
    return str(r)


def _read_tree(root: str) -> dict[str, str]:
    """Every projection file on disk, keyed like build_tree's dict."""
    out: dict[str, str] = {}
    for kind in ENTITY_DIRS:
        d = os.path.join(root, kind)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.endswith(".md"):
                continue
            with open(os.path.join(d, name), encoding="utf-8", newline="") as fh:
                out[f"{kind}/{name}"] = fh.read()
    return out


def _assert_tracks(svc, root: str, note: str) -> None:
    expected, _ = build_tree(svc)
    actual = _read_tree(root)
    missing = sorted(set(expected) - set(actual))
    ghosts = sorted(set(actual) - set(expected))
    assert not missing, f"{note}: the DB has rows the tree lacks: {missing}"
    assert not ghosts, f"{note}: the tree has files the DB lacks: {ghosts}"
    differing = sorted(k for k in expected if expected[k] != actual[k])
    assert not differing, f"{note}: content diverged for {differing}"


# --- the mutation script, one function per projected kind --------------------
# Each returns the kind it covers, so the ratchet below can prove the set of
# kinds actually exercised equals the registry rather than trusting a comment.


def _mutate_epics(svc) -> str:
    svc.epic_add("rel", "Релиз")
    svc.epic_add("doomed", "Лишний эпик")
    svc.epic_done("rel")
    svc.epic_delete("doomed")
    return "epics"


def _mutate_stories(svc) -> str:
    svc.story_add("rel", "wave", "Волна")
    svc.story_add("rel", "scrap", "Лишняя стори")
    svc.story_done("wave")
    svc.story_delete("scrap")
    return "stories"


def _mutate_tasks(svc) -> str:
    svc.task_add("wave", "fix", "Починить", stack="python", goal="Цель", complexity="medium")
    svc.task_update(
        "fix",
        acceptance_criteria="AC1. Свойство держится. AC2. Ошибка при пустом дереве не роняет вызов.",
    )
    # QG-0 Rules 2 and 6 — a medium task must declare scope and a rollback plan
    # before it can start. Set here so the script exercises the real gate path.
    svc.task_update("fix", scope="scripts/", rollback_plan="git revert")
    svc.task_update("fix", call_budget=40)  # the budget-only early return
    svc.task_start("fix")
    svc.task_log("fix", "первый шаг")
    svc.task_plan("fix", ["шаг один", "шаг два"])
    svc.task_step("fix", 1)
    svc.task_block("fix", reason="ждём смежника")
    svc.task_unblock("fix")
    svc.task_review("fix")
    svc.task_move("fix", "wave")
    svc.task_add("wave", "gone", "Удаляемая", goal="Цель")
    svc.task_delete("gone")
    return "tasks"


def _mutate_decisions(svc) -> str:
    # Task-linked: the branch that used to skip the projection entirely.
    svc.decide("Свойство проверяется прогоном, а не перечнем вызовов", task_slug="fix")
    svc.decide("Решение без привязки к задаче")
    return "decisions"


def _mutate_memory(svc) -> str:
    svc.memory_add("convention", "Проекция обязана уметь сжиматься", "Удаление снимает файл.")
    svc.dead_end("Ратчет по AST", "Бэкенд пишет через хелпер — литерального DML в теле нет")
    svc.memory_delete(_mem_id(svc.memory_add("context", "Временная", "Будет удалена")))
    a = _mem_id(svc.memory_add("pattern", "Источник ребра", "У записи есть исходящее ребро"))
    b = _mem_id(svc.memory_add("pattern", "Цель ребра", "Сюда указывает ребро"))
    svc.memory_link("memory", a, "memory", b, "relates_to")
    return "memory"


_MUTATORS = (_mutate_epics, _mutate_stories, _mutate_tasks, _mutate_decisions, _mutate_memory)


def test_projection_tracks_db_after_every_mutation(svc, root):
    """The load-bearing test: no manual export anywhere in this function."""
    covered = set()
    for mutate in _MUTATORS:
        kind = mutate(svc)
        covered.add(kind)
        _assert_tracks(svc, root, f"after {kind}")
    assert covered == set(ENTITY_DIRS)


def test_every_projected_kind_is_exercised():
    """Coverage ratchet: a sixth projected kind must extend the script above.

    Derived from `state_import.ENTITY_DIRS` — the same registry the importer
    walks — so the two cannot drift apart silently.
    """
    covered = {fn.__name__.removeprefix("_mutate_") for fn in _MUTATORS}
    assert covered == set(ENTITY_DIRS)


def test_registry_has_not_collapsed():
    """Guard against a degenerate pass: an empty registry would make both green."""
    assert len(ENTITY_DIRS) >= 5
    assert "decisions" in ENTITY_DIRS and "tasks" in ENTITY_DIRS


# --- the two behaviours the property depends on ------------------------------


def test_delete_removes_the_projection_file(svc, root):
    svc.epic_add("e", "Эпик")
    svc.story_add("e", "s", "Стори")
    svc.task_add("s", "temp", "Временная", goal="Цель")
    path = os.path.join(root, "tasks", "temp.md")
    assert os.path.isfile(path)
    svc.task_delete("temp")
    assert not os.path.exists(path), "a deleted task left a ghost file behind"


def test_archived_memory_leaves_the_projection(svc, root):
    mid = _mem_id(svc.memory_add("context", "Старая запись", "Уедет в архив"))
    slug = svc.be.memory_get(mid)["slug"]
    path = os.path.join(root, "memory", f"{slug}.md")
    assert os.path.isfile(path)
    svc.be._ex("UPDATE memory SET created_at='2020-01-01T00:00:00Z' WHERE id=?", (mid,))
    svc.memory_archive("30d", confirm=True)
    assert not os.path.exists(path), "archived memory is excluded from the projection"


def test_export_failure_does_not_roll_back_the_write(svc, root, monkeypatch):
    """Fail-open (gotcha #271): the DB write is the truth, the file is best-effort."""

    def _boom(*_a, **_kw):
        raise RuntimeError("serializer exploded")

    monkeypatch.setattr("state_export.export_one", _boom)
    svc.epic_add("survivor", "Эпик переживает падение экспорта")
    assert svc.be.epic_get("survivor") is not None
    assert not os.path.exists(os.path.join(root, "epics", "survivor.md"))
