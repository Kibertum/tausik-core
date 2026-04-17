"""Test QG-0 9-dimension intent completeness scoring (prompt-master)."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from service_gates import qg0_dimensions_score


class TestDimensionsScore:
    def test_empty_task_all_false(self):
        dims = qg0_dimensions_score({})
        assert all(v is False for v in dims.values())
        assert sum(dims.values()) == 0

    def test_all_nine_filled(self):
        task = {
            "goal": "Ship feature X",
            "acceptance_criteria": "scripts/foo.py updates; memory #5 consulted",
            "scope": "scripts/",
            "scope_exclude": "tests/",
            "role": "developer",
            "stack": "python",
            "complexity": "medium",
            "story_slug": "s-1",
        }
        dims = qg0_dimensions_score(task)
        assert all(dims.values()), f"Some dims not filled: {dims}"
        assert sum(dims.values()) == 9

    def test_epic_also_counts_as_story_link(self):
        task = {"epic_slug": "e-1"}
        dims = qg0_dimensions_score(task)
        assert dims["story_link"] is True

    def test_evidence_plan_via_file_reference(self):
        task = {"acceptance_criteria": "Update scripts/service_gates.py function"}
        dims = qg0_dimensions_score(task)
        assert dims["evidence_plan"] is True

    def test_evidence_plan_via_memory_reference(self):
        task = {"acceptance_criteria": "Apply convention from memory #32"}
        dims = qg0_dimensions_score(task)
        assert dims["evidence_plan"] is True

    def test_evidence_plan_vague_ac(self):
        task = {"acceptance_criteria": "Make it good and fast"}
        dims = qg0_dimensions_score(task)
        assert dims["evidence_plan"] is False

    def test_whitespace_only_fields_count_as_unfilled(self):
        task = {"goal": "   ", "scope": "\n\t"}
        dims = qg0_dimensions_score(task)
        assert dims["goal"] is False
        assert dims["scope"] is False

    def test_keys_are_stable(self):
        dims = qg0_dimensions_score({})
        expected = {
            "goal",
            "acceptance_criteria",
            "scope",
            "scope_exclude",
            "role",
            "stack",
            "complexity",
            "story_link",
            "evidence_plan",
        }
        assert set(dims.keys()) == expected


class TestIntegrationWithQg0Start:
    """The warning is emitted by _check_qg0_start when <5 dims are filled."""

    def _fresh_svc(self, tmp_path):
        os.environ["TAUSIK_DIR"] = str(tmp_path / ".tausik")
        (tmp_path / ".tausik").mkdir()
        from project_backend import SQLiteBackend
        from project_service import ProjectService

        be = SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db"))
        return ProjectService(be)

    def test_minimal_task_emits_context_warning(self, tmp_path):
        svc = self._fresh_svc(tmp_path)
        svc.task_add(None, "t1", "minimal")
        svc.task_update(
            "t1", goal="do thing", acceptance_criteria="Error on empty input"
        )
        warnings = svc._check_qg0_start("t1", svc.task_show("t1"))
        context_warnings = [w for w in warnings if w.startswith("CONTEXT:")]
        assert context_warnings, f"Expected CONTEXT warning, got: {warnings}"
        assert "/9 intent dimensions" in context_warnings[0]

    def test_rich_task_no_context_warning(self, tmp_path):
        svc = self._fresh_svc(tmp_path)
        svc.task_add(
            None,
            "t2",
            "rich",
            stack="python",
            complexity="medium",
            goal="Ship feature",
            role="developer",
        )
        svc.task_update(
            "t2",
            acceptance_criteria="Update scripts/foo.py; error on empty input.",
            scope="scripts/",
            scope_exclude="tests/",
        )
        warnings = svc._check_qg0_start("t2", svc.task_show("t2"))
        context_warnings = [w for w in warnings if w.startswith("CONTEXT:")]
        assert not context_warnings, f"Unexpected CONTEXT warning: {context_warnings}"
