"""v15-scope-rule2-hardgate: SENAR Rule 2 scope warning -> hard gate.

QG-0 blocks starting explicitly medium/complex tasks with NO scope
declaration (neither structured scope_paths nor legacy free-text scope).
Opt-out via config qg0.scope_hard_gate=false; simple/unset complexity
keeps warning-only behavior.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import gate_qg0_check  # noqa: E402
from gate_qg0_check import check_qg0_start  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402


def _task(complexity="medium", scope=None, scope_paths=None):
    return {
        "slug": "t1",
        "title": "T",
        "goal": "do something",
        "acceptance_criteria": "1. works. 2. returns error on invalid input",
        "scope": scope,
        "scope_paths": scope_paths,
        "scope_exclude": "y.py",
        "complexity": complexity,
        "rollback_plan": "git revert",
    }


class TestHardGate:
    def test_medium_without_any_scope_blocked(self):
        with pytest.raises(ServiceError, match="Rule 2") as exc:
            check_qg0_start("t1", _task("medium"))
        msg = str(exc.value)
        assert "--scope-paths" in msg and "--scope" in msg
        assert "scope_hard_gate" in msg  # opt-out is discoverable

    def test_complex_without_any_scope_blocked(self):
        with pytest.raises(ServiceError, match="declares no scope"):
            check_qg0_start("t1", _task("complex"))

    def test_whitespace_legacy_scope_blocked(self):
        with pytest.raises(ServiceError, match="Rule 2"):
            check_qg0_start("t1", _task("medium", scope="   "))


class TestDeclarationSatisfies:
    def test_scope_paths_passes(self):
        check_qg0_start("t1", _task("medium", scope_paths='["src/*"]'))

    def test_explicit_empty_scope_paths_passes(self):
        # "[]" is a declaration (deny-all ACL) — the gate wants intent, not breadth
        check_qg0_start("t1", _task("complex", scope_paths="[]"))

    def test_legacy_free_text_scope_passes(self):
        check_qg0_start("t1", _task("medium", scope="x.py only"))


class TestSoftPaths:
    def test_simple_without_scope_warns_not_blocks(self):
        warnings = check_qg0_start("t1", _task("simple"))
        assert any("no scope defined" in w for w in warnings)

    def test_unset_complexity_warns_not_blocks(self):
        warnings = check_qg0_start("t1", _task(None))
        assert any("no scope defined" in w for w in warnings)

    def test_opt_out_config_downgrades_to_warning(self, monkeypatch):
        monkeypatch.setattr(gate_qg0_check, "_scope_hard_gate_enabled", lambda: False)
        warnings = check_qg0_start("t1", _task("medium"))
        assert any("no scope defined" in w for w in warnings)


class TestConfigResolution:
    def test_default_enabled(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)  # no .tausik/config.json anywhere near
        assert gate_qg0_check._scope_hard_gate_enabled() is True

    def test_explicit_false_disables(self, monkeypatch):
        import project_config

        monkeypatch.setattr(
            project_config, "load_config", lambda: {"qg0": {"scope_hard_gate": False}}
        )
        assert gate_qg0_check._scope_hard_gate_enabled() is False

    def test_broken_config_stays_enabled(self, monkeypatch):
        import project_config

        def _boom():
            raise RuntimeError("config unreadable")

        monkeypatch.setattr(project_config, "load_config", _boom)
        assert gate_qg0_check._scope_hard_gate_enabled() is True
