"""Tests for the SENAR Rule 5 checklist hard gate (v15s-rule5-checklist-hardgate).

Pure checklist_hard_block decisions by planning tier + the task_done integration
(hard block for substantial/deep, escalating nudge for lower tiers, config
opt-out downgrades to a warning).
"""

from __future__ import annotations

import os
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from gate_ac_check import checklist_hard_block, checklist_missing  # noqa: E402


_AC = "1. does the thing\n2. errors on bad input"


def _task(tier=None, notes="", ac=_AC):
    return {"tier": tier, "notes": notes, "relevant_files": "[]", "acceptance_criteria": ac}


class TestChecklistHardBlock:
    """rule5-checklist-keyword-theater: the gate reads evidence, not vocabulary.

    It used to count words — `scope`, `secret`, `phantom` — anywhere in the
    notes, so one occurrence cleared it. Measured over the 851 closed tasks that
    carry AC, that verdict disagreed with the structured evidence on 380 of them
    (44.7%): 320 passed on vocabulary alone with no real evidence behind any
    criterion. The tests below used to assert that behaviour was correct.
    """

    def test_substantial_without_checklist_blocks(self):
        block, msg = checklist_hard_block(_task("substantial", notes="just did stuff"))
        assert block is True
        assert "Rule 5" in msg and "substantial" in msg
        assert "checklist_hard=false" in msg  # opt-out documented

    def test_deep_without_checklist_blocks(self):
        block, _ = checklist_hard_block(_task("deep", notes=""))
        assert block is True

    def test_keyword_vocabulary_alone_no_longer_clears_the_gate(self):
        """The exact notes this test used to accept as a passing checklist."""
        block, _ = checklist_hard_block(_task("substantial", notes="scope clean, no secret leak"))
        assert block is True, "vocabulary still clears the hard gate"

    def test_bare_checkmarks_do_not_clear_the_gate(self):
        block, _ = checklist_hard_block(
            _task("substantial", notes="1. ✓\n2. ✓\nall criteria verified")
        )
        assert block is True, "a check mark is a claim, not evidence"

    def test_real_test_reference_clears_the_gate(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_real.py").write_text("def test_a(): pass\n", encoding="utf-8")

        block, msg = checklist_hard_block(
            _task("substantial", notes="1. ✓ tests/test_real.py::test_a\n2. ✓ manual run")
        )
        assert block is False and msg == ""

    def test_unresolvable_test_reference_is_treated_as_no_evidence(self, tmp_path, monkeypatch):
        """Fail-closed: a path that does not exist could equally be invented."""
        monkeypatch.chdir(tmp_path)

        block, _ = checklist_hard_block(
            _task("substantial", notes="1. ✓ tests/test_does_not_exist.py::test_a")
        )
        assert block is True

    def test_lower_tier_never_hard_blocks(self):
        for tier in ("trivial", "light", "moderate", None):
            block, msg = checklist_hard_block(_task(tier, notes=""))
            assert block is False and msg == ""

    def test_checklist_missing_reads_evidence_not_vocabulary(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_real.py").write_text("def test_a(): pass\n", encoding="utf-8")

        assert checklist_missing(_task(notes="nothing relevant here")) is True
        assert checklist_missing(_task(notes="verified scope and secret scan")) is True
        assert checklist_missing(_task(notes="1. ✓ tests/test_real.py::test_a")) is False

    def test_invented_test_name_on_a_real_file_does_not_clear_the_gate(self, tmp_path, monkeypatch):
        """The `::name` was split off and never looked at."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_real.py").write_text("def test_a(): pass\n", encoding="utf-8")

        block, _ = checklist_hard_block(
            _task("substantial", notes="1. ✓ tests/test_real.py::test_totally_made_up_9876")
        )
        assert block is True
        # …and the honest citation on the same file still passes.
        ok, _ = checklist_hard_block(_task("substantial", notes="1. ✓ tests/test_real.py::test_a"))
        assert ok is False

    def test_pytest_class_qualified_node_id_is_accepted(self, tmp_path, monkeypatch):
        """`file::Class::method` is the id pytest itself prints."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_real.py").write_text(
            "class TestThing:\n    def test_a(self): pass\n", encoding="utf-8"
        )

        for ref in (
            "tests/test_real.py::TestThing::test_a",
            "tests/test_real.py::test_a[case-3]",
        ):
            block, _ = checklist_hard_block(_task("substantial", notes=f"1. ✓ {ref}"))
            assert block is False, f"rejected a real pytest node id: {ref}"

    def test_traversal_out_of_the_test_tree_does_not_clear_the_gate(self, tmp_path, monkeypatch):
        """`tests/../scripts/x.py` let a production source file count as a test."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
        (tmp_path / "tests").mkdir()
        (tmp_path / "scripts").mkdir()
        (tmp_path / "scripts" / "prod.py").write_text("def helper(): pass\n", encoding="utf-8")

        block, _ = checklist_hard_block(_task("substantial", notes="1. ✓ tests/../scripts/prod.py"))
        assert block is True

    def test_verdict_does_not_depend_on_the_directory_the_command_ran_from(
        self, tmp_path, monkeypatch
    ):
        """Same task, same evidence, different cwd — the answer must not move."""
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_real.py").write_text("def test_a(): pass\n", encoding="utf-8")
        (tmp_path / "scripts").mkdir()
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
        task = _task("substantial", notes="1. ✓ tests/test_real.py::test_a")

        monkeypatch.chdir(tmp_path)
        from_root = checklist_hard_block(task)[0]
        monkeypatch.chdir(tmp_path / "scripts")
        from_subdir = checklist_hard_block(task)[0]

        assert from_root == from_subdir is False, (
            "the gate blocks genuine evidence depending on where it was invoked"
        )

    def test_manual_run_counts_for_the_warning_but_not_the_hard_gate(self):
        """A manual run is a real activity; it is just not a citation."""
        task = _task("substantial", notes="1. ✓ verified by manual run against staging")
        assert checklist_missing(task) is False
        assert checklist_hard_block(task)[0] is True


class TestTaskDoneIntegration:
    def _make(self, tmp_path, monkeypatch, tier):
        from project_backend import SQLiteBackend
        from project_service import ProjectService

        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TAUSIK_QUIET", "1")
        svc = ProjectService(SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db")))
        svc.task_add(None, "t-cl", "Checklist task")
        svc.task_update(
            "t-cl",
            goal="g",
            acceptance_criteria="1. ok\n2. errors on bad input",
            scope="x.py",
            tier=tier,
        )
        svc.task_start("t-cl")
        return svc

    def test_substantial_blocked_without_checklist(self, tmp_path, monkeypatch):
        from tausik_utils import ServiceError

        svc = self._make(tmp_path, monkeypatch, "substantial")
        try:
            with pytest.raises(ServiceError, match="Rule 5"):
                svc.task_done("t-cl", None, True, True, evidence="AC verified: 1. OK 2. OK")
            assert svc.be.task_get("t-cl")["status"] == "active"  # not closed
        finally:
            svc.be.close()

    def test_substantial_passes_with_a_resolvable_test_reference(self, tmp_path, monkeypatch):
        svc = self._make(tmp_path, monkeypatch, "substantial")
        (tmp_path / "tests").mkdir(exist_ok=True)
        (tmp_path / "tests" / "test_real.py").write_text("def test_a(): pass\n", encoding="utf-8")
        try:
            result = svc.task_done(
                "t-cl",
                None,
                True,
                True,
                evidence="1. ✓ tests/test_real.py::test_a 2. ✓ tests/test_real.py::test_a",
            )
            assert "completed" in result
            assert svc.be.task_get("t-cl")["status"] == "done"
        finally:
            svc.be.close()

    def test_substantial_still_blocked_by_checklist_vocabulary(self, tmp_path, monkeypatch):
        """The old passing evidence, unchanged — now it must not close."""
        from tausik_utils import ServiceError

        svc = self._make(tmp_path, monkeypatch, "substantial")
        try:
            with pytest.raises(ServiceError, match="Rule 5"):
                svc.task_done(
                    "t-cl",
                    None,
                    True,
                    True,
                    evidence=(
                        "AC verified: 1. OK 2. OK. Checklist: scope clean, no secret, tests pass."
                    ),
                )
            assert svc.be.task_get("t-cl")["status"] == "active"
        finally:
            svc.be.close()

    def test_lower_tier_not_blocked(self, tmp_path, monkeypatch):
        svc = self._make(tmp_path, monkeypatch, "light")
        try:
            # No checklist, but light tier -> nudge, not a block.
            result = svc.task_done("t-cl", None, True, True, evidence="AC verified: 1. OK 2. OK")
            assert "completed" in result
            assert svc.be.task_get("t-cl")["status"] == "done"
        finally:
            svc.be.close()

    def test_opt_out_downgrades_to_warning(self, tmp_path, monkeypatch):
        import service_task_done

        monkeypatch.setattr(service_task_done, "_checklist_hard_enabled", lambda: False)
        svc = self._make(tmp_path, monkeypatch, "deep")
        try:
            result = svc.task_done("t-cl", None, True, True, evidence="AC verified: 1. OK 2. OK")
            assert "completed" in result  # not blocked
            assert "checklist_hard=false" in result
        finally:
            svc.be.close()
