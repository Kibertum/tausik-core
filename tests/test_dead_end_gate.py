"""A task that saw a failure closes with a dead end or a stated reason; a dead end
names its task (negative-knowledge-is-voluntary-and-therefore-absent)."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import dead_end_gate as g  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "d.db")))
    s.epic_add("e", "Epic")
    s.story_add("e", "s", "Story")
    s.task_add("s", "t", "T", role="developer", goal="g")
    s.be.task_update("t", acceptance_criteria="Returns 400 on invalid input.")
    s.task_start("t")
    yield s
    s.be.close()


def _red_run(svc, slug="t"):
    svc.be._conn.execute(
        "INSERT INTO verification_runs(task_slug, scope, command, exit_code, files_hash, ran_at) "
        "VALUES (?, 'manual', 'pytest', 1, 'h', '2026-09-23T10:00:00Z')",
        (slug,),
    )
    svc.be._conn.commit()


def _task(svc):
    return svc.be.task_get("t")


def test_no_observed_failure_means_no_question(svc):
    assert g.check(svc.be, _task(svc)) is None


@pytest.mark.parametrize("trigger", ["red", "blocked", "attempts"])
def test_each_trigger_asks_for_a_dead_end_or_a_reason(svc, trigger):
    if trigger == "red":
        _red_run(svc)
    elif trigger == "blocked":
        svc.task_block("t", "waiting for the fixture")
    else:
        svc.be.task_update("t", attempts=2)
    msg = g.check(svc.be, _task(svc))
    assert msg and "dead-end" in msg and "NO-DEAD-END:" in msg and "--task t" in msg


def test_a_dead_end_linked_to_the_task_satisfies_it(svc):
    _red_run(svc)
    svc.dead_end("Patched the fixture", "It masked the real ordering bug")
    assert g.check(svc.be, _task(svc)) is None


def test_a_stated_reason_satisfies_it_and_a_short_one_does_not(svc):
    _red_run(svc)
    svc.task_log("t", "NO-DEAD-END: ok")
    assert g.check(svc.be, _task(svc)) is not None
    svc.task_log("t", "NO-DEAD-END: the red run was a typo in the test name")
    assert g.check(svc.be, _task(svc)) is None


def test_a_dead_end_without_a_task_binds_to_the_single_active_one(svc):
    svc.dead_end("Tried a cache", "Stale after rename")
    rows = svc.be._q("SELECT task_slug FROM memory WHERE type='dead_end'")
    assert [r["task_slug"] for r in rows] == ["t"]


def test_a_dead_end_with_no_active_task_is_refused(svc):
    svc.task_block("t", "parked")
    with pytest.raises(ServiceError, match="must name its task"):
        svc.dead_end("Tried a cache", "Stale after rename")


def test_a_dead_end_with_two_active_tasks_is_refused(svc):
    svc.task_add("s", "u", "U", role="developer", goal="g")
    svc.be.task_update("u", acceptance_criteria="Returns 400 on invalid input.")
    svc.task_start("u")
    with pytest.raises(ServiceError, match="2 tasks are active"):
        svc.dead_end("Tried a cache", "Stale after rename")
    assert svc.dead_end("Tried a cache", "Stale", task_slug="u").startswith("Dead end #")


def test_task_done_refuses_the_silent_close_and_accepts_the_stated_one(svc):
    _red_run(svc)
    svc.task_log("t", "AC verified: 1. ✓ Returns 400 on invalid input — checked by hand")
    with pytest.raises(ServiceError, match="saw a failure"):
        svc.task_done("t", ac_verified=True, no_knowledge=True)
    svc.task_log("t", "NO-DEAD-END: the red run was a typo in the test name")
    assert "completed" in svc.task_done("t", ac_verified=True, no_knowledge=True)
