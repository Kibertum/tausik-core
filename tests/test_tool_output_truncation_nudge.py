"""Tests for the tool_output_truncation_nudge PostToolUse hook
(v14b-start-lite-tool-truncation, AC #2 + #4).

The hook:
- Watches Read / Grep / Bash / Glob outputs (other tools ignored)
- Counts lines in `tool_response`
- Emits stderr nudge when n_lines > threshold (default 250, configurable)
- NEVER modifies tool output, NEVER raises (silent best-effort)
- Threshold lookup: .tausik/config.json → env → hard default
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

REPO = os.path.join(os.path.dirname(__file__), "..")
HOOK_PATH = os.path.join(REPO, "scripts", "hooks", "tool_output_truncation_nudge.py")


# --- Pure-function unit tests ----------------------------------------------


def _import_hook():
    """Import the hook module with `scripts/hooks/` on sys.path."""
    hooks_dir = os.path.join(REPO, "scripts", "hooks")
    if hooks_dir not in sys.path:
        sys.path.insert(0, hooks_dir)
    import importlib

    mod = importlib.import_module("tool_output_truncation_nudge")
    return mod


def test_count_lines_handles_empty():
    mod = _import_hook()
    assert mod.count_lines("") == 0


def test_count_lines_no_trailing_newline():
    mod = _import_hook()
    assert mod.count_lines("a\nb\nc") == 3


def test_count_lines_trailing_newline():
    mod = _import_hook()
    assert mod.count_lines("a\nb\nc\n") == 3


def test_resolve_threshold_default(tmp_path, monkeypatch):
    mod = _import_hook()
    monkeypatch.delenv("TAUSIK_OUTPUT_TRUNCATION_THRESHOLD", raising=False)
    assert mod._resolve_threshold(str(tmp_path)) == mod.DEFAULT_THRESHOLD


def test_resolve_threshold_from_config_json(tmp_path, monkeypatch):
    mod = _import_hook()
    cfg_dir = tmp_path / ".tausik"
    cfg_dir.mkdir()
    (cfg_dir / "config.json").write_text(
        json.dumps({"tool_output_truncation_threshold": 42}),
        encoding="utf-8",
    )
    monkeypatch.delenv("TAUSIK_OUTPUT_TRUNCATION_THRESHOLD", raising=False)
    assert mod._resolve_threshold(str(tmp_path)) == 42


def test_resolve_threshold_from_env(tmp_path, monkeypatch):
    mod = _import_hook()
    monkeypatch.setenv("TAUSIK_OUTPUT_TRUNCATION_THRESHOLD", "77")
    assert mod._resolve_threshold(str(tmp_path)) == 77


def test_resolve_threshold_config_wins_over_env(tmp_path, monkeypatch):
    mod = _import_hook()
    cfg_dir = tmp_path / ".tausik"
    cfg_dir.mkdir()
    (cfg_dir / "config.json").write_text(
        json.dumps({"tool_output_truncation_threshold": 100}),
        encoding="utf-8",
    )
    monkeypatch.setenv("TAUSIK_OUTPUT_TRUNCATION_THRESHOLD", "200")
    assert mod._resolve_threshold(str(tmp_path)) == 100


def test_resolve_threshold_rejects_zero_and_negative(tmp_path, monkeypatch):
    mod = _import_hook()
    cfg_dir = tmp_path / ".tausik"
    cfg_dir.mkdir()
    (cfg_dir / "config.json").write_text(
        json.dumps({"tool_output_truncation_threshold": 0}),
        encoding="utf-8",
    )
    monkeypatch.delenv("TAUSIK_OUTPUT_TRUNCATION_THRESHOLD", raising=False)
    assert mod._resolve_threshold(str(tmp_path)) == mod.DEFAULT_THRESHOLD


def test_extract_output_text_string_response():
    mod = _import_hook()
    payload = {"tool_response": "line1\nline2"}
    assert mod._extract_output_text(payload) == "line1\nline2"


def test_extract_output_text_dict_with_output():
    mod = _import_hook()
    payload = {"tool_response": {"output": "hello\nworld"}}
    assert mod._extract_output_text(payload) == "hello\nworld"


def test_extract_output_text_content_parts():
    mod = _import_hook()
    payload = {
        "tool_response": {
            "content": [
                {"type": "text", "text": "alpha"},
                {"type": "text", "text": "beta"},
            ]
        }
    }
    assert mod._extract_output_text(payload) == "alpha\nbeta"


def test_extract_output_text_missing_returns_empty():
    mod = _import_hook()
    assert mod._extract_output_text({}) == ""
    assert mod._extract_output_text({"tool_response": None}) == ""
    assert mod._extract_output_text({"tool_response": {"unrelated": 1}}) == ""


# --- Subprocess integration tests (real stdin / stdout / stderr) -----------


def _run_hook(payload: dict, env: dict[str, str] | None = None, cwd: str | None = None):
    """Invoke the hook as a subprocess (matches harness behavior)."""
    full_env = os.environ.copy()
    full_env.pop("TAUSIK_OUTPUT_TRUNCATION_THRESHOLD", None)
    full_env.pop("TAUSIK_SKIP_HOOKS", None)
    if env:
        full_env.update(env)
    return subprocess.run(
        [sys.executable, HOOK_PATH],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=full_env,
        cwd=cwd,
        timeout=10,
    )


def test_hook_silent_under_threshold(tmp_path):
    payload = {
        "tool_name": "Read",
        "tool_response": "x\n" * 50,
    }
    res = _run_hook(payload, cwd=str(tmp_path))
    assert res.returncode == 0
    assert res.stderr.strip() == "", f"unexpected stderr: {res.stderr!r}"


def test_hook_emits_nudge_over_threshold(tmp_path):
    payload = {
        "tool_name": "Grep",
        "tool_response": "x\n" * 500,  # 500 lines, default threshold 250
    }
    res = _run_hook(payload, cwd=str(tmp_path))
    assert res.returncode == 0
    assert "TAUSIK truncation nudge" in res.stderr
    assert "Grep" in res.stderr
    assert "500" in res.stderr


def test_hook_ignores_unwatched_tool(tmp_path):
    payload = {
        "tool_name": "Edit",
        "tool_response": "x\n" * 1000,
    }
    res = _run_hook(payload, cwd=str(tmp_path))
    assert res.returncode == 0
    assert res.stderr.strip() == ""


def test_hook_silent_on_empty_stdin(tmp_path):
    res = subprocess.run(
        [sys.executable, HOOK_PATH],
        input="",
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        timeout=10,
    )
    assert res.returncode == 0
    assert res.stderr.strip() == ""


def test_hook_silent_on_malformed_json(tmp_path):
    res = subprocess.run(
        [sys.executable, HOOK_PATH],
        input="{not json",
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        timeout=10,
    )
    assert res.returncode == 0
    assert res.stderr.strip() == ""


def test_hook_skipped_via_env_flag(tmp_path):
    payload = {
        "tool_name": "Bash",
        "tool_response": "x\n" * 1000,
    }
    res = _run_hook(payload, env={"TAUSIK_SKIP_HOOKS": "1"}, cwd=str(tmp_path))
    assert res.returncode == 0
    assert res.stderr.strip() == ""


def test_hook_respects_config_threshold(tmp_path):
    cfg_dir = tmp_path / ".tausik"
    cfg_dir.mkdir()
    (cfg_dir / "config.json").write_text(
        json.dumps({"tool_output_truncation_threshold": 10}),
        encoding="utf-8",
    )
    # 50 lines exceeds custom threshold 10 even though default 250 wouldn't trip.
    payload = {
        "tool_name": "Read",
        "tool_response": "x\n" * 50,
    }
    res = _run_hook(payload, env={"CLAUDE_PROJECT_DIR": str(tmp_path)}, cwd=str(tmp_path))
    assert res.returncode == 0
    assert "TAUSIK truncation nudge" in res.stderr
    assert "threshold 10" in res.stderr
