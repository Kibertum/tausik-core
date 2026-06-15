"""Tests for v1.3 blind-review HIGH review findings 1-5."""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend
from project_service import ProjectService


HOOK_PATH = os.path.join(
    os.path.dirname(__file__), "..", "scripts", "hooks", "task_call_counter.py"
)
SETTINGS_PATH = os.path.join(
    os.path.dirname(__file__), "..", ".claude", "settings.json"
)


def _make_service(db_path: str) -> ProjectService:
    return ProjectService(SQLiteBackend(db_path))


# === HIGH-1: ALLOWED_GATE_EXECUTABLES extension ===


class TestIacExecutablesWhitelisted:
    @pytest.mark.parametrize(
        "exe", ["ansible-lint", "terraform", "helm", "kubeval", "hadolint"]
    )
    def test_iac_exe_in_whitelist(self, exe):
        from project_config import ALLOWED_GATE_EXECUTABLES

        assert exe in ALLOWED_GATE_EXECUTABLES

    def test_user_override_with_path_prefix_passes(self):
        """User pointing helm-lint at vendor/bin/helm should validate."""
        from project_config import _validate_custom_gate

        gate = {"command": "vendor/bin/ansible-lint playbook.yml"}
        assert _validate_custom_gate("custom-ansible", gate) is None


# === HIGH-2: shell chain blocked unconditionally, pipe only with {files} ===


class TestShellChainBlocked:
    @pytest.mark.parametrize(
        "cmd",
        [
            "pytest tests/ && echo done",
            "ruff check . || true",
            "pytest tests/ ; rm -rf /",
            "ruff $(cat secrets)",
            "ruff `id`",
        ],
    )
    def test_chain_rejected_without_files(self, cmd):
        """HIGH-2: chain operators must reject even without {files}."""
        from project_config import _validate_custom_gate

        gate = {"command": cmd}
        err = _validate_custom_gate("evil", gate)
        assert err is not None, f"Should reject: {cmd}"
        assert "shell operators" in err

    def test_pipe_without_files_still_allowed(self):
        """Stock pattern `2>&1 | head -N` must keep working."""
        from project_config import _validate_custom_gate

        gate = {"command": "npx tsc --noEmit 2>&1 | head -20"}
        assert _validate_custom_gate("custom-tsc", gate) is None


# === HIGH-3 + HIGH-4: hook handles multi-active and serialises with task_done ===


def _run_hook(cwd: str, payload: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, HOOK_PATH],
        input=json.dumps(payload or {}),
        capture_output=True,
        text=True,
        cwd=cwd,
        env={**os.environ, "CLAUDE_PROJECT_DIR": cwd},
        timeout=10,
    )


def _bootstrap_project(tmp_path):
    proj = tmp_path / "proj"
    os.makedirs(proj / ".tausik")
    db_path = str(proj / ".tausik" / "tausik.db")
    s = _make_service(db_path)
    s.epic_add("e", "Epic")
    s.story_add("e", "st", "Story")
    return proj, db_path, s


def _seed_active(svc, slug):
    svc.task_add("st", slug, slug, role="developer", goal="g")
    svc.be.task_update(slug, acceptance_criteria="Returns 400 on invalid input.")
    svc.task_start(slug)


class TestMultiActiveIncrement:
    def test_increments_all_active_tasks(self, tmp_path):
        """HIGH-4: hook must increment EACH active task, not no-op when >1."""
        proj, db_path, svc = _bootstrap_project(tmp_path)
        try:
            _seed_active(svc, "alpha")
            _seed_active(svc, "beta")
        finally:
            svc.be.close()

        result = _run_hook(str(proj))
        assert result.returncode == 0

        s2 = _make_service(db_path)
        try:
            assert s2.be.meta_get("tool_calls:alpha") == "1"
            assert s2.be.meta_get("tool_calls:beta") == "1"
        finally:
            s2.be.close()

    def test_repeat_call_bumps_each(self, tmp_path):
        proj, db_path, svc = _bootstrap_project(tmp_path)
        try:
            _seed_active(svc, "alpha")
            _seed_active(svc, "beta")
        finally:
            svc.be.close()

        for _ in range(3):
            _run_hook(str(proj))

        s2 = _make_service(db_path)
        try:
            assert s2.be.meta_get("tool_calls:alpha") == "3"
            assert s2.be.meta_get("tool_calls:beta") == "3"
        finally:
            s2.be.close()

    def test_no_active_remains_noop(self, tmp_path):
        proj, db_path, _svc = _bootstrap_project(tmp_path)
        # No tasks started
        result = _run_hook(str(proj))
        assert result.returncode == 0
        s2 = _make_service(db_path)
        try:
            assert s2.be.meta_get("tool_calls:nope") is None
        finally:
            s2.be.close()


class TestHookUsesImmediateLock:
    def test_hook_uses_begin_immediate_in_source(self):
        """HIGH-3: source must use BEGIN IMMEDIATE for serialisation."""
        with open(HOOK_PATH, encoding="utf-8") as f:
            src = f.read()
        assert "BEGIN IMMEDIATE" in src


# === HIGH-5: matcher restriction ===


class TestHookMatcher:
    def test_settings_matcher_excludes_read_only_tools(self):
        """HIGH-5: PostToolUse counter must be matched only for write tools."""
        with open(SETTINGS_PATH, encoding="utf-8") as f:
            settings = json.load(f)
        post = settings["hooks"]["PostToolUse"]
        # Find the entry that wires task_call_counter.py
        counter_entries = [
            entry
            for entry in post
            if any(
                "task_call_counter.py" in (h.get("command") or "")
                for h in entry.get("hooks", [])
            )
        ]
        assert len(counter_entries) == 1
        matcher = counter_entries[0]["matcher"]
        assert "Write" in matcher
        assert "Edit" in matcher
        assert "Bash" in matcher
        # Read/Grep/Glob explicitly NOT in matcher
        assert "Read" not in matcher
        assert "Grep" not in matcher
        assert "Glob" not in matcher
