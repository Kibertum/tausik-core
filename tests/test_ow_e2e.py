"""End-to-end orchestrator-worker flow (v15-ow-docs-tests).

Drives one task through delegate -> task_start recognition -> scope-gate
decision -> summary-back, plus the unhappy paths (complex refused, delegated
without scope flagged).
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "hooks"))

from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService, ServiceError  # noqa: E402
from scope_acl import match_path  # noqa: E402
from scope_write_gate import delegated_missing_scope  # noqa: E402


@pytest.fixture
def svc(tmp_path):
    be = SQLiteBackend(str(tmp_path / "t.db"))
    s = ProjectService(be)
    s.epic_add("v1", "V1")
    s.story_add("v1", "setup", "Setup")
    yield s
    be.close()


def _ready(svc, slug, complexity="medium"):
    svc.task_add("setup", slug, slug, complexity=complexity, role="developer")
    svc.task_update(
        slug,
        goal="do it",
        acceptance_criteria="AC1: works. Negative: errors on bad input.",
        scope="scripts/x.py",
        scope_exclude="tests/",
        rollback_plan="git revert",
    )


class TestHappyPath:
    def test_full_loop(self, svc):
        _ready(svc, "feat-x")
        svc.be.task_update("feat-x", scope_paths='["scripts/*"]')

        # 1. delegate
        assert "delegated" in svc.task_delegate("feat-x").lower()
        deleg = svc.task_delegation("feat-x")
        assert deleg and deleg["model"]

        # 2. handoff contract carries the scope + model
        contract = svc.task_handoff("feat-x")
        assert contract["scope"] == "scripts/x.py" and contract["model"]

        # 3. task_start recognizes worker mode (banner suppressed)
        start = svc.task_start("feat-x")
        assert "Worker mode" in start and "Model recommendation:" not in start

        # 4. scope gate: in-scope allowed, out-of-scope denied; not missing-scope
        acls = [("feat-x", '["scripts/*"]')]
        assert delegated_missing_scope(acls, {"feat-x"}) is None
        assert match_path("scripts/x.py", ["scripts/*"]) is True
        assert match_path("secrets/y.py", ["scripts/*"]) is False

        # 5. summary-back returns the result to the orchestrator
        svc.task_summary_back("feat-x", "implemented", gates="green")
        rec = svc.task_worker_summary("feat-x")
        assert rec and rec["summary"] == "implemented" and rec["gates"] == "green"


class TestUnhappyPaths:
    def test_complex_refused_delegation(self, svc):
        _ready(svc, "feat-c", complexity="complex")
        with pytest.raises(ServiceError, match="complex"):
            svc.task_delegate("feat-c")

    def test_delegated_without_scope_is_flagged(self, svc):
        _ready(svc, "feat-n")  # no scope_paths set
        svc.task_delegate("feat-n")
        acls = [("feat-n", None)]
        assert delegated_missing_scope(acls, {"feat-n"}) == "feat-n"
