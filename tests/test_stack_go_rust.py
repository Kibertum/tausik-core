"""Go + Rust verticals — test runners exposed as stack-scoped gates."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend
from project_service import ProjectService


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "go-rust.db")))
    yield s
    s.be.close()


# === Default gate registration ===


class TestGateRegistration:
    def test_go_test_in_defaults(self):
        from project_config import DEFAULT_GATES

        assert "go-test" in DEFAULT_GATES
        gate = DEFAULT_GATES["go-test"]
        assert gate["stacks"] == ["go"]
        assert "task-done" in gate["trigger"]
        assert gate["severity"] == "block"
        assert "go test" in gate["command"]

    def test_cargo_test_in_defaults(self):
        from project_config import DEFAULT_GATES

        assert "cargo-test" in DEFAULT_GATES
        gate = DEFAULT_GATES["cargo-test"]
        assert gate["stacks"] == ["rust"]
        assert "task-done" in gate["trigger"]
        assert "cargo test" in gate["command"]

    def test_in_stack_gate_map(self):
        from project_config import STACK_GATE_MAP

        assert "go-test" in STACK_GATE_MAP.get("go", [])
        assert "cargo-test" in STACK_GATE_MAP.get("rust", [])


# === Stack info exposure ===


class TestStackInfo:
    def test_go_info_lists_test_runner(self, svc):
        info = svc.stack_info("go")
        names = [g["name"] for g in info["gates"]]
        assert "go-test" in names
        assert "go-vet" in names

    def test_rust_info_lists_test_runner(self, svc):
        info = svc.stack_info("rust")
        names = [g["name"] for g in info["gates"]]
        assert "cargo-test" in names
        assert "cargo-check" in names
        assert "clippy" in names


# === Stack-aware dispatch (regression / negative scenarios) ===


class TestStackFiltering:
    def test_go_test_skipped_for_python_files(self):
        from gate_runner import gate_applies_to
        from project_config import DEFAULT_GATES

        gate = {**DEFAULT_GATES["go-test"], "name": "go-test"}
        assert gate_applies_to(gate, ["scripts/main.py"]) is False

    def test_go_test_runs_for_go_files(self):
        from gate_runner import gate_applies_to
        from project_config import DEFAULT_GATES

        gate = {**DEFAULT_GATES["go-test"], "name": "go-test"}
        assert gate_applies_to(gate, ["main.go", "lib_test.go"]) is True

    def test_cargo_test_skipped_for_python_files(self):
        from gate_runner import gate_applies_to
        from project_config import DEFAULT_GATES

        gate = {**DEFAULT_GATES["cargo-test"], "name": "cargo-test"}
        assert gate_applies_to(gate, ["scripts/main.py"]) is False

    def test_cargo_test_runs_for_rust_files(self):
        from gate_runner import gate_applies_to
        from project_config import DEFAULT_GATES

        gate = {**DEFAULT_GATES["cargo-test"], "name": "cargo-test"}
        assert gate_applies_to(gate, ["src/lib.rs"]) is True

    def test_pytest_unaffected_by_new_gates(self):
        from gate_runner import gate_applies_to
        from project_config import DEFAULT_GATES

        gate = {**DEFAULT_GATES["pytest"], "name": "pytest"}
        assert gate_applies_to(gate, ["scripts/main.py"]) is True
        assert gate_applies_to(gate, ["main.go"]) is False
