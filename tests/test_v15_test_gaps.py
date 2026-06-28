"""Deferred v1.5 review test-gaps (memory #172) — regression guards."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from gate_qg0_renar import renar_qg0_advisory  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_cli_aidd_autogen import render_vision  # noqa: E402
from project_cli_aidd_validate import cmd_aidd_validate  # noqa: E402
from project_service import ProjectService  # noqa: E402


@pytest.fixture
def svc(tmp_path):
    be = SQLiteBackend(str(tmp_path / "t.db"))
    s = ProjectService(be)
    s.epic_add("v1", "V1")
    s.story_add("v1", "setup", "Setup")
    yield s
    be.close()


class TestDelegationEdgeCases:
    def test_non_dict_json_returns_none(self, svc):
        svc.task_add("setup", "x", "X", complexity="medium", role="developer")
        svc.be.meta_set("delegation:x", '"just-a-string"')  # valid JSON, not a dict
        assert svc.task_delegation("x") is None

    def test_list_json_returns_none(self, svc):
        svc.task_add("setup", "y", "Y", complexity="medium", role="developer")
        svc.be.meta_set("delegation:y", "[1, 2, 3]")
        assert svc.task_delegation("y") is None

    def test_delegate_after_blocked(self, svc):
        svc.task_add("setup", "z", "Z", complexity="medium", role="developer")
        svc.be.task_update("z", status="blocked")
        # blocked is delegable (only complex/done/unknown are refused).
        assert "delegated" in svc.task_delegate("z").lower()
        assert svc.task_delegation("z") is not None


class TestRenarAdvisoryEdge:
    def test_bare_task_dict_no_crash_no_advisory(self):
        # No tier / no complexity → not high-stakes → None, never raises.
        assert renar_qg0_advisory(object(), {}, "x") is None


class TestAiddValidateDriftExit:
    def test_lint_tool_drift_exits_1(self, tmp_path):
        (tmp_path / "conventions.md").write_text(
            "## Code\n\n- Lint / format tools: ruff\n", encoding="utf-8"
        )
        # No ruff configured anywhere → drift → exit 1 (non-filesize claim path).
        rc = cmd_aidd_validate(root=str(tmp_path), log=lambda _: None)
        assert rc == 1


class TestRenderVisionLeadingSection:
    def test_template_starting_with_section_heading(self):
        # Template whose first line is '## ' (no leading '# Title') must not crash.
        out = render_vision("## Target user\n\nWho.\n", {"name": "x"})
        assert "Project facts" in out and "Target user" in out
