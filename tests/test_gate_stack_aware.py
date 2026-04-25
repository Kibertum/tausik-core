"""Stack-aware gate dispatch — Epic 2 critical bug fix.

pytest gate must NOT silently false-pass on non-Python projects. With
the fix, gate.stacks is checked against file-extension inference: when
relevant_files contain no Python file, the gate is reported as SKIP
rather than run-an-empty-tests-dir.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from gate_runner import (
    gate_applies_to,
    infer_stacks_from_files,
    run_gates,
)


# === infer_stacks_from_files ===


class TestInferStacks:
    @pytest.mark.parametrize(
        "files,expected_member",
        [
            (["main.py"], "python"),
            (["app.ts"], "typescript"),
            (["index.tsx"], "react"),
            (["script.js"], "javascript"),
            (["main.go"], "go"),
            (["lib.rs"], "rust"),
            (["A.java"], "java"),
            (["B.kt"], "kotlin"),
            (["x.php"], "php"),
            (["x.blade.php"], "blade"),
            (["app.swift"], "swift"),
            (["main.dart"], "flutter"),
        ],
    )
    def test_ext_maps_to_expected_stack(self, files, expected_member):
        out = infer_stacks_from_files(files)
        assert expected_member in out

    def test_unknown_extension_yields_empty(self):
        assert infer_stacks_from_files(["README.md", "data.csv"]) == set()

    def test_empty_input(self):
        assert infer_stacks_from_files([]) == set()

    def test_mixed_files_unions(self):
        out = infer_stacks_from_files(["main.go", "ui.tsx", "x.py"])
        assert {"go", "react", "python"}.issubset(out)


# === gate_applies_to ===


class TestGateApplies:
    def test_universal_gate_always_applies(self):
        assert gate_applies_to({"stacks": []}, ["main.go"]) is True
        assert gate_applies_to({}, ["main.go"]) is True

    def test_empty_files_treated_as_universal(self):
        # Without relevant_files we cannot scope, so the gate runs.
        assert gate_applies_to({"stacks": ["python"]}, []) is True

    def test_python_gate_skipped_for_go_files(self):
        assert gate_applies_to({"stacks": ["python"]}, ["main.go", "lib.go"]) is False

    def test_python_gate_runs_for_python_files(self):
        assert gate_applies_to({"stacks": ["python"]}, ["main.py"]) is True

    def test_mixed_files_match_any(self):
        # If ANY file matches gate.stacks, the gate runs
        assert gate_applies_to({"stacks": ["python"]}, ["main.go", "x.py"]) is True


# === run_gates dispatch ===


class TestDispatchFiltering:
    """Test the stack-filter logic that run_gates uses, in isolation.

    The conftest auto-mocks gate_runner.run_gates so we cannot smoke-test the
    full pipeline here. Instead we replay the dispatch loop's filter step
    against the real default gate config — the integration test of run_gates
    itself lives in test_qg2_gates.py via service_verification.
    """

    def test_pytest_skipped_for_go_only_files(self):
        from project_config import get_gates_for_trigger
        from gate_runner import gate_applies_to

        gates = get_gates_for_trigger("task-done", {"gates": {}})
        pytest_gate = next((g for g in gates if g["name"] == "pytest"), None)
        assert pytest_gate is not None, "pytest gate must be in default config"
        assert gate_applies_to(pytest_gate, ["main.go"]) is False

    def test_pytest_runs_for_python_files(self):
        from project_config import get_gates_for_trigger
        from gate_runner import gate_applies_to

        gates = get_gates_for_trigger("task-done", {"gates": {}})
        pytest_gate = next((g for g in gates if g["name"] == "pytest"), None)
        assert gate_applies_to(pytest_gate, ["scripts/main.py"]) is True

    def test_filesize_gate_applies_universally(self):
        # filesize has no `stacks` — must apply to any file set, including
        # non-source files (markdown, JSON).
        from project_config import get_gates_for_trigger
        from gate_runner import gate_applies_to

        gates = get_gates_for_trigger("task-done", {"gates": {}})
        fs_gate = next((g for g in gates if g["name"] == "filesize"), None)
        assert fs_gate is not None
        assert gate_applies_to(fs_gate, ["README.md"]) is True
        assert gate_applies_to(fs_gate, ["main.go"]) is True

    def test_format_results_shows_skip_label(self):
        from gate_runner import format_results

        out = format_results(
            [
                {
                    "name": "pytest",
                    "severity": "block",
                    "passed": True,
                    "skipped": True,
                    "output": "Not applicable",
                }
            ]
        )
        assert "[SKIP]" in out
