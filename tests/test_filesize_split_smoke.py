"""Backwards-compat smoke test for v14b-filesize-debt-paydown splits.

Each of these imports must continue to work from its ORIGINAL module after
the split — even though the implementation now lives elsewhere. If any line
fails, an external caller will break the same way.

Splits in this round:
- security_pattern.py        ← from service_verification (is_security_sensitive +
                               _SECURITY_PATH_TOKENS / _SEC_BASE / _SECURITY_BASENAMES /
                               _SECURITY_EXTENSIONS)
- verify_cache.py            ← from service_verification (resolve_gate_signature,
                               _build_cache_command, has_fresh_verify_run, is_cache_allowed)
- gate_command_runner.py     ← from gate_runner (run_command_gate, _SCOPED_SKIP_SENTINEL)
- backend_queries_usage.py   ← from backend_queries (4 usage methods on
                               BackendQueriesUsageMixin → BackendQueriesMixin)
- bootstrap_hooks.py         ← from bootstrap_generate (build_hooks_dict)
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bootstrap"))


class TestServiceVerificationReexports:
    def test_security_helpers_still_importable(self):
        from service_verification import (
            _SEC_BASE,
            _SEC_EXT,
            _SECURITY_BASENAMES,
            _SECURITY_EXTENSIONS,
            _SECURITY_PATH_TOKENS,
            is_security_sensitive,
        )

        assert callable(is_security_sensitive)
        assert isinstance(_SECURITY_PATH_TOKENS, tuple) and "/auth/" in _SECURITY_PATH_TOKENS
        assert isinstance(_SECURITY_BASENAMES, frozenset) and "auth.py" in _SECURITY_BASENAMES
        assert isinstance(_SECURITY_EXTENSIONS, frozenset) and ".env" in _SECURITY_EXTENSIONS
        assert isinstance(_SEC_BASE, list) and isinstance(_SEC_EXT, tuple)

    def test_cache_helpers_still_importable(self):
        from service_verification import (
            _build_cache_command,
            has_fresh_verify_run,
            is_cache_allowed,
            resolve_gate_signature,
        )

        assert callable(is_cache_allowed)
        assert callable(resolve_gate_signature)
        assert callable(_build_cache_command)
        assert callable(has_fresh_verify_run)
        # smoke: cache key includes trigger + sig + files
        cmd = _build_cache_command("verify", ["a.py", "b.py"])
        assert cmd.startswith("trigger=verify|sig=") and "files=a.py,b.py" in cmd

    def test_security_pattern_module_is_authoritative(self):
        """security_pattern is the source-of-truth; service_verification re-exports it."""
        from security_pattern import is_security_sensitive as canonical
        from service_verification import is_security_sensitive as reexport

        assert canonical is reexport


class TestGateRunnerReexports:
    def test_run_command_gate_still_importable(self):
        from gate_runner import _SCOPED_SKIP_SENTINEL, run_command_gate

        assert callable(run_command_gate)
        assert isinstance(_SCOPED_SKIP_SENTINEL, str) and _SCOPED_SKIP_SENTINEL

    def test_gate_command_runner_module_is_authoritative(self):
        from gate_command_runner import run_command_gate as canonical
        from gate_runner import run_command_gate as reexport

        assert canonical is reexport


class TestBackendQueriesUsage:
    def test_usage_methods_inherited(self):
        from backend_queries import BackendQueriesMixin
        from backend_queries_usage import BackendQueriesUsageMixin

        assert issubclass(BackendQueriesMixin, BackendQueriesUsageMixin)
        for m in (
            "usage_event_append",
            "session_usage_record",
            "usage_events_cost_rollup_by_task",
            "session_usage_summary",
        ):
            assert hasattr(BackendQueriesMixin, m), f"{m} missing from BackendQueriesMixin"


class TestBootstrapHooksExtraction:
    def test_build_hooks_dict_importable(self):
        from bootstrap_hooks import build_hooks_dict

        assert callable(build_hooks_dict)

    def test_settings_json_unchanged_in_shape(self, tmp_path):
        """generate_settings_claude must produce the same hook structure post-split."""
        from bootstrap_generate import generate_settings_claude

        target = tmp_path / ".claude"
        target.mkdir()
        generate_settings_claude(str(target), str(tmp_path))
        import json

        cfg = json.loads((target / "settings.json").read_text(encoding="utf-8"))
        hooks = cfg["hooks"]
        # contract: every event class still present, hook list non-empty
        for event in (
            "PreToolUse",
            "PostToolUse",
            "SessionStart",
            "UserPromptSubmit",
            "Stop",
            "SessionEnd",
        ):
            assert event in hooks, f"missing hook event: {event}"
            assert hooks[event], f"empty hook list: {event}"
        # specific hook coverage from previous tests still passes
        pretool_cmds = [h["command"] for entry in hooks["PreToolUse"] for h in entry["hooks"]]
        assert any("task_gate.py" in c for c in pretool_cmds)
        assert any("memory_pretool_block.py" in c for c in pretool_cmds)
        assert any("secret_scan.py" in c for c in pretool_cmds)
        posttool_cmds = [h["command"] for entry in hooks["PostToolUse"] for h in entry["hooks"]]
        assert any("posttool_usage.py" in c for c in posttool_cmds)
        assert any("activity_event.py" in c for c in posttool_cmds)
        stop_cmds = [h["command"] for entry in hooks["Stop"] for h in entry["hooks"]]
        assert any("keyword_detector.py" in c for c in stop_cmds)
