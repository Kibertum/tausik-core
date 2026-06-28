"""v15s-rule6-rollback-plan: SENAR Rule 6 — rollback_plan field + enforcement.

QG-0 blocks starting explicitly medium/complex tasks without rollback_plan
(with templates in the error); simple/unset complexity is exempt (warning
only for unset); task_done only WARNS so pre-v28 tasks remain closable.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from gate_qg0_check import check_qg0_start  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402


@pytest.fixture
def svc(tmp_path):
    be = SQLiteBackend(str(tmp_path / "test.db"))
    s = ProjectService(be)
    yield s
    be.close()


def _task(complexity="medium", rollback_plan=None):
    return {
        "slug": "t1",
        "title": "T",
        "goal": "do something",
        "acceptance_criteria": "1. works. 2. returns error on invalid input",
        "scope": "x.py",
        "scope_exclude": "y.py",
        "complexity": complexity,
        "rollback_plan": rollback_plan,
    }


class TestQg0RollbackGate:
    def test_medium_without_plan_blocked_with_templates(self):
        with pytest.raises(ServiceError, match="Rule 6") as exc:
            check_qg0_start("t1", _task("medium"))
        msg = str(exc.value)
        assert "git revert" in msg
        assert "migration down" in msg
        assert "feature flag off" in msg
        assert "--rollback-plan" in msg

    def test_complex_without_plan_blocked(self):
        with pytest.raises(ServiceError, match="rollback_plan"):
            check_qg0_start("t1", _task("complex"))

    def test_medium_with_plan_passes(self):
        check_qg0_start("t1", _task("medium", rollback_plan="git revert"))

    def test_simple_without_plan_passes(self):
        check_qg0_start("t1", _task("simple"))

    def test_unset_complexity_warns_not_blocks(self):
        warnings = check_qg0_start("t1", _task(None))
        assert any("rollback_plan" in w for w in warnings)

    def test_whitespace_plan_blocked(self):
        with pytest.raises(ServiceError, match="rollback_plan"):
            check_qg0_start("t1", _task("medium", rollback_plan="   "))


class TestSchemaAndPersistence:
    def test_fresh_db_has_column_and_update_persists(self, svc):
        svc.epic_add("e", "E")
        svc.story_add("e", "s", "S")
        svc.task_add("s", "t1", "Task")
        svc.task_update("t1", rollback_plan="git revert <commit>")
        task = svc.task_show("t1")
        assert task["rollback_plan"] == "git revert <commit>"

    def test_task_start_enforces_rule6_end_to_end(self, svc):
        svc.epic_add("e", "E")
        svc.story_add("e", "s", "S")
        svc.task_add("s", "t1", "Task", None, "medium")
        svc.task_update(
            "t1",
            goal="g",
            acceptance_criteria="1. ok. 2. fails with error on bad input",
            # scope declared so the Rule 2 hard gate (v15-scope-rule2-hardgate)
            # doesn't fire first — this test pins the Rule 6 failure.
            scope="x.py",
        )
        with pytest.raises(ServiceError, match="Rule 6"):
            svc.task_start("t1")
        svc.task_update("t1", rollback_plan="git revert")
        assert "started" in svc.task_start("t1")


class TestTaskDoneWarns:
    def _seed(self, svc):
        svc.epic_add("e", "E")
        svc.story_add("e", "s", "S")
        svc.task_add("s", "t1", "Task", None, "medium")
        svc.task_update(
            "t1",
            goal="g",
            acceptance_criteria="1. ok. 2. fails with error on bad input",
            rollback_plan="git revert",
            scope="x.py",  # satisfy the Rule 2 hard gate (v15-scope-rule2-hardgate)
        )
        svc.task_start("t1")

    def test_done_warns_without_plan_but_completes(self, svc, monkeypatch):
        monkeypatch.setenv("TAUSIK_QUIET", "1")
        self._seed(svc)
        # wipe the plan post-start to simulate a pre-v28 task at close time
        svc.task_update("t1", rollback_plan="")
        result = svc.task_done("t1", None, True, True, evidence="AC verified: 1. OK 2. OK")
        assert "completed" in result
        assert "Rule 6" in result

    def test_done_quiet_with_plan(self, svc, monkeypatch):
        monkeypatch.setenv("TAUSIK_QUIET", "1")
        self._seed(svc)
        result = svc.task_done("t1", None, True, True, evidence="AC verified: 1. OK 2. OK")
        assert "completed" in result
        assert "Rule 6" not in result
