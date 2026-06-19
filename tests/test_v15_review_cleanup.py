"""Tests for v1.5 review-cleanup fixes (v15p-review-low-cleanup)."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "hooks"))

from gate_command_runner import run_command_gate  # noqa: E402
from project_cli_aidd_validate import _files_over, _verify_max_filesize  # noqa: E402
from scope_write_gate import delegated_missing_scope  # noqa: E402
from service_knowledge_aggregates import build_memory_compact  # noqa: E402


class TestFilesOverTruncation:
    def test_truncation_flagged(self, tmp_path):
        for i in range(5):
            (tmp_path / f"f{i}.py").write_text("x\n", encoding="utf-8")
        _offenders, truncated = _files_over(str(tmp_path), 400, max_files=2)
        assert truncated is True

    def test_no_truncation_when_under_cap(self, tmp_path):
        (tmp_path / "a.py").write_text("x\n", encoding="utf-8")
        offenders, truncated = _files_over(str(tmp_path), 400, max_files=100)
        assert truncated is False and offenders == []

    def test_verify_unverifiable_on_truncation(self, tmp_path, monkeypatch):
        import project_cli_aidd_validate as v

        monkeypatch.setattr(v, "_files_over", lambda root, limit: ([], True))
        assert _verify_max_filesize(str(tmp_path), "400 lines")[0] == "unverifiable"


class TestDelegatedEmptyScope:
    def test_empty_list_scope_counts_as_missing(self):
        assert delegated_missing_scope([("w", "[]")], {"w"}) == "w"

    def test_none_scope_counts_as_missing(self):
        assert delegated_missing_scope([("w", None)], {"w"}) == "w"

    def test_real_scope_ok(self):
        assert delegated_missing_scope([("w", '["scripts/*"]')], {"w"}) is None


class TestMemoryCompactGuard:
    def test_backend_error_returns_empty(self):
        class _Boom:
            def task_log_recent(self, n):
                raise RuntimeError("db down")

        assert build_memory_compact(_Boom()) == ""


class TestGateSpawnError:
    def test_missing_binary_reports_not_runnable(self):
        gate = {"command": "this_binary_does_not_exist_xyz --flag"}
        passed, out = run_command_gate(gate, [])
        assert passed is False
        assert "not runnable" in out.lower() or "error" in out.lower()
