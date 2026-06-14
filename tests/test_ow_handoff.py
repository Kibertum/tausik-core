"""Tests for the orchestrator-worker handoff contract (v15-ow-subagent-profile)."""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from ow_handoff import (  # noqa: E402
    WORKER_SKILLS,
    build_handoff_contract,
    serialize_contract,
)
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService, ServiceError  # noqa: E402


_TASK = {
    "slug": "feat-x",
    "goal": "do x",
    "acceptance_criteria": "AC1: works. Negative: errors on bad input.",
    "scope": "scripts/x.py",
    "scope_exclude": "tests/",
}


class TestBuildContract:
    def test_carries_task_fields_and_model_and_skills(self):
        c = build_handoff_contract(_TASK, {"model": "claude-sonnet-4-6"})
        assert c["slug"] == "feat-x"
        assert c["goal"] == "do x"
        assert c["scope"] == "scripts/x.py"
        assert c["model"] == "claude-sonnet-4-6"
        assert c["skills"] == list(WORKER_SKILLS)

    def test_missing_optional_fields_degrade_to_empty(self):
        c = build_handoff_contract({"slug": "bare"}, None)
        assert c["goal"] == "" and c["scope_exclude"] == "" and c["model"] == ""
        assert c["skills"] == list(WORKER_SKILLS)  # profile always present

    def test_worker_profile_excludes_orchestrator_skills(self):
        assert "plan" not in WORKER_SKILLS and "explore" not in WORKER_SKILLS
        assert "task" in WORKER_SKILLS and "test" in WORKER_SKILLS


class TestRoundTrip:
    def test_serialize_parse_is_identity(self):
        c = build_handoff_contract(_TASK, {"model": "m"})
        assert json.loads(serialize_contract(c)) == c

    def test_serialize_is_deterministic(self):
        c = build_handoff_contract(_TASK, {"model": "m"})
        assert serialize_contract(c) == serialize_contract(dict(reversed(list(c.items()))))


class TestServiceHandoff:
    def test_task_handoff_builds_from_db(self, tmp_path):
        be = SQLiteBackend(str(tmp_path / "t.db"))
        svc = ProjectService(be)
        svc.epic_add("v1", "V1")
        svc.story_add("v1", "setup", "Setup")
        svc.task_add("setup", "feat-x", "X", complexity="medium", role="developer")
        svc.task_update("feat-x", goal="do x", scope="scripts/x.py")
        svc.task_delegate("feat-x")
        c = svc.task_handoff("feat-x")
        assert c["slug"] == "feat-x" and c["goal"] == "do x"
        assert c["model"]  # delegation model present
        be.close()

    def test_unknown_task_raises(self, tmp_path):
        be = SQLiteBackend(str(tmp_path / "t.db"))
        svc = ProjectService(be)
        with pytest.raises(ServiceError, match="not found"):
            svc.task_handoff("nope")
        be.close()
