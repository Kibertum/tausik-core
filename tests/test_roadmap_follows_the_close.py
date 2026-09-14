"""closing-a-task-reddens-the-next-verify-silently: the map follows the close.

Measured in session #241 — four times in one session — and again in #263, three
times: closing a task moves the counters ROADMAP.md prints, the map on disk is
now stale, and the next `verify` is red on `test_release_roadmap` until a human
types `tausik doc roadmap`. A generated file was being left for a test to
catch when the act that moved its source could have rewritten it.

One chain is held here, at the service level: seed a project whose root holds a
GENERATED map, change a task's status through the service, and the map on disk
equals a fresh render — the exact comparison `doc roadmap --check` and the test
behind it make — with no generator call in between. Two boundaries beside it:
a hand-written ROADMAP.md (no generator marker) is never touched, and the
rewrite of a versioned file is announced, not silent (AC-3).
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
)

import release_roadmap  # noqa: E402
import state_triggers  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402


@pytest.fixture
def project(monkeypatch, tmp_path):
    """A project root with a live service, auto-export on, and a generated map."""
    root = tmp_path / "proj"
    tree = root / "tausik"
    tree.mkdir(parents=True)
    svc = ProjectService(SQLiteBackend(str(root / "trig.db")))
    monkeypatch.setattr(state_triggers, "_auto_export_enabled", lambda _d: True)
    monkeypatch.setattr(state_triggers, "_tree_root", lambda _svc: str(tree))
    svc.epic_add("e", "Эпик 1.9")
    svc.story_add("e", "s", "История")
    svc.story_add("e", "s2", "Вторая история")
    svc.task_add("s", "t", "Задача", stack="python", complexity="simple", goal="Цель")
    # The renderer refuses a release with no declared composition (#367).
    svc.be.decision_add("Версия 1.9. Состав: s, s2", None, "тест")
    path = root / "ROADMAP.md"
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(release_roadmap.render(svc.be._conn))
    yield svc, str(path)
    svc.be.close()


def _stale(svc, path: str) -> bool:
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read() != release_roadmap.render(svc.be._conn)


def test_a_status_change_leaves_the_map_current_without_a_generator_call(project, capsys):
    svc, path = project
    assert not _stale(svc, path), "premise: the seeded map is current"
    svc.be.task_update("t", status="done")  # the counters move here …
    state_triggers.auto_export_entity(svc, "tasks", "t")  # … and the projection follows
    assert not _stale(svc, path), "the map did not follow the close"
    assert "ROADMAP.md reissued" in capsys.readouterr().err  # AC-3: announced, on stderr


def test_a_hand_written_map_is_never_touched(project):
    svc, path = project
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write("# My own roadmap\n")
    svc.be.task_update("t", status="done")
    state_triggers.auto_export_entity(svc, "tasks", "t")
    with open(path, encoding="utf-8", newline="") as fh:
        assert fh.read() == "# My own roadmap\n"
