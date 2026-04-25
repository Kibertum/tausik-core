"""tausik stack info / stack list — Epic 2 visibility command."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend
from project_service import ProjectService
from tausik_utils import ServiceError


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "stack.db")))
    yield s
    s.be.close()


# === stack_info ===


class TestStackInfo:
    def test_python_lists_pytest(self, svc):
        info = svc.stack_info("python")
        names = [g["name"] for g in info["gates"]]
        assert "pytest" in names
        assert "filesize" in names  # universal gate
        assert info["gap_notice"] == ""

    def test_go_lists_go_specific_gates(self, svc):
        info = svc.stack_info("go")
        names = [g["name"] for g in info["gates"]]
        assert "go-vet" in names
        assert "filesize" in names
        # pytest should NOT appear — it's stack-gated to python
        assert "pytest" not in names

    def test_unknown_stack_raises_with_suggestion(self, svc):
        with pytest.raises(ServiceError, match="Unknown stack"):
            svc.stack_info("phyton")

    def test_blade_lists_php_gates(self, svc):
        info = svc.stack_info("blade")
        names = [g["name"] for g in info["gates"]]
        # blade is rendered alongside laravel/php in default config
        assert "filesize" in names


# === stack_list ===


class TestStackList:
    def test_lists_all_valid_stacks(self, svc):
        from project_types import VALID_STACKS

        rows = svc.stack_list()
        listed = {r["stack"] for r in rows}
        assert listed == VALID_STACKS

    def test_each_stack_has_at_least_one_gate(self, svc):
        # filesize is universal, so every stack should report >= 1.
        for r in svc.stack_list():
            assert r["applicable_gates"] >= 1


# === CLI smoke ===


class TestCliStack:
    def test_info_output_smoke(self, svc, capsys):
        from argparse import Namespace
        from project_cli_extra import cmd_stack

        cmd_stack(svc, Namespace(stack_cmd="info", stack="python"))
        out = capsys.readouterr().out
        assert "Stack: python" in out
        assert "pytest" in out

    def test_list_output_smoke(self, svc, capsys):
        from argparse import Namespace
        from project_cli_extra import cmd_stack

        cmd_stack(svc, Namespace(stack_cmd="list"))
        out = capsys.readouterr().out
        for stack in ("python", "go", "rust", "java", "php"):
            assert stack in out
