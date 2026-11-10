"""Test SessionStart hook: auto-injection of TAUSIK state into new sessions.

The hook must: exit 0 always (graceful degradation), skip cleanly when DB absent,
respect TAUSIK_SKIP_HOOKS flag, and emit Claude Code hookSpecificOutput JSON when
it has context to share.
"""

from __future__ import annotations

import json
import hashlib
import importlib
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

_HOOK_PATH = os.path.join(os.path.dirname(__file__), "..", "scripts", "hooks", "session_start.py")
_SCRIPTS = str(Path(_HOOK_PATH).resolve().parents[1])
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from hooks.codex_capability import serialize_hook_argv  # noqa: E402


def test_context_uses_one_compact_state_call_and_stays_bounded(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(os.path.dirname(_HOOK_PATH)))
    hook = importlib.import_module("session_start")
    calls = []
    monkeypatch.setattr(hook, "_tausik_path", lambda project_dir: "tausik")
    monkeypatch.setattr(
        hook,
        "_run_tausik",
        lambda cmd, args, project_dir: calls.append(args) or '{"tasks_active":1}',
    )
    monkeypatch.setattr(hook, "_rag_summary", lambda project_dir: "RAG: ready")

    context = hook.build_context(str(tmp_path))

    assert calls == [["status", "--compact"]]
    assert len(context.encode()) <= hook.MAX_CONTEXT_BYTES
    assert "task show <slug> --package" in context


def _run_hook(project_dir: str, extra_env: dict | None = None) -> subprocess.CompletedProcess:
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project_dir), "PYTHONUTF8": "1"}
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, _HOOK_PATH],
        input="{}",
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
        env=env,
    )


def _install_valid_codex_profile(project_dir: Path) -> tuple[Path, Path]:
    codex = project_dir / ".codex"
    hooks = codex / "scripts" / "hooks"
    hooks.mkdir(parents=True)
    source_hooks = Path(_HOOK_PATH).resolve().parent
    pretool = hooks / "codex_write_gate.py"
    posttool = hooks / "memory_preflight_posttool.py"
    composite = hooks / "codex_composite_mcp.py"
    prompt = hooks / "user_prompt_submit.py"
    stop = hooks / "can_stop_gate.py"
    shutil.copy2(source_hooks / pretool.name, pretool)
    shutil.copy2(source_hooks / posttool.name, posttool)
    shutil.copy2(source_hooks / composite.name, composite)
    shutil.copy2(source_hooks / prompt.name, prompt)
    shutil.copy2(source_hooks / stop.name, stop)
    (codex / "hooks.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": serialize_hook_argv(
                                        [
                                            "python",
                                            "-X",
                                            "utf8",
                                            str(pretool),
                                            "--project",
                                            str(project_dir),
                                        ]
                                    ),
                                }
                            ],
                        }
                    ],
                    "PostToolUse": [
                        {
                            "matcher": "",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": serialize_hook_argv(
                                        [
                                            "python",
                                            "-X",
                                            "utf8",
                                            str(posttool),
                                            "--project",
                                            str(project_dir),
                                        ]
                                    ),
                                }
                            ],
                        }
                    ],
                    "UserPromptSubmit": [
                        {
                            "matcher": "",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": serialize_hook_argv(
                                        [
                                            "python",
                                            "-X",
                                            "utf8",
                                            str(prompt),
                                            "--trusted-host",
                                            "codex",
                                        ]
                                    ),
                                }
                            ],
                        }
                    ],
                    "Stop": [
                        {
                            "matcher": "",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": serialize_hook_argv(
                                        [
                                            "python",
                                            "-X",
                                            "utf8",
                                            str(stop),
                                            "--trusted-host",
                                            "codex",
                                        ]
                                    ),
                                }
                            ],
                        }
                    ],
                }
            }
        ),
        encoding="utf-8",
    )
    (codex / "tausik-capability.json").write_text(
        json.dumps(
            {
                "capability_version": 5,
                "mcp_transport_modes": ["direct", "functions.exec"],
                "python_executable": "python",
                "adapters": {
                    path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in (pretool, posttool, composite, prompt, stop)
                },
            }
        ),
        encoding="utf-8",
    )
    return pretool, posttool


class TestSessionStartHook:
    def test_exits_zero_when_no_db(self, tmp_path):
        """No .tausik/tausik.db → graceful skip, exit 0, no output."""
        result = _run_hook(tmp_path)
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert result.stdout.strip() == ""

    def test_skip_flag_bypasses(self, tmp_path):
        """TAUSIK_SKIP_HOOKS=1 short-circuits before any work."""
        (tmp_path / ".tausik").mkdir()
        (tmp_path / ".tausik" / "tausik.db").write_text("")
        result = _run_hook(tmp_path, {"TAUSIK_SKIP_HOOKS": "1"})
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_db_present_but_no_cli(self, tmp_path):
        """DB exists but CLI wrapper missing → exit 0, no output (graceful)."""
        (tmp_path / ".tausik").mkdir()
        (tmp_path / ".tausik" / "tausik.db").write_text("")
        result = _run_hook(tmp_path)
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_empty_stdin(self, tmp_path):
        """Hook must not crash on malformed/empty stdin (Claude Code sometimes sends nothing)."""
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path), "PYTHONUTF8": "1"}
        result = subprocess.run(
            [sys.executable, _HOOK_PATH],
            input="",
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=15,
            env=env,
        )
        assert result.returncode == 0

    def test_output_is_valid_json_when_present(self, tmp_path):
        """When the hook produces context, output must be parseable hookSpecificOutput JSON."""
        tausik_dir = tmp_path / ".tausik"
        tausik_dir.mkdir()
        (tausik_dir / "tausik.db").write_text("")
        # Mock tausik CLI that always succeeds with dummy status
        wrapper = "tausik.cmd" if sys.platform == "win32" else "tausik"
        wrapper_path = tausik_dir / wrapper
        if sys.platform == "win32":
            wrapper_path.write_text("@echo off\r\necho Mock status: Tasks 1/1, Session #99\r\n")
        else:
            wrapper_path.write_text("#!/bin/sh\necho 'Mock status: Tasks 1/1, Session #99'\n")
            os.chmod(wrapper_path, 0o755)

        result = _run_hook(tmp_path)
        assert result.returncode == 0
        if result.stdout.strip():
            parsed = json.loads(result.stdout)
            assert parsed["hookSpecificOutput"]["hookEventName"] == "SessionStart"
            assert "additionalContext" in parsed["hookSpecificOutput"]
            ctx = parsed["hookSpecificOutput"]["additionalContext"]
            assert "TAUSIK" in ctx
            assert "SENAR Rule 9.1" in ctx

    def test_invalid_project_dir_env(self, tmp_path, monkeypatch):
        """Unset CLAUDE_PROJECT_DIR → falls back to cwd, still exits cleanly."""
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
        env["PYTHONUTF8"] = "1"
        result = subprocess.run(
            [sys.executable, _HOOK_PATH],
            input="{}",
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=15,
            env=env,
            cwd=str(tmp_path),
        )
        assert result.returncode == 0


class TestMemoryPolicyReminder:
    """SessionStart injection must carry the auto-memory policy reminder."""

    def _setup_mock_tausik(self, tmp_path):
        tausik_dir = tmp_path / ".tausik"
        tausik_dir.mkdir()
        (tausik_dir / "tausik.db").write_text("")
        wrapper = "tausik.cmd" if sys.platform == "win32" else "tausik"
        wrapper_path = tausik_dir / wrapper
        if sys.platform == "win32":
            wrapper_path.write_text("@echo off\r\necho Mock status line\r\n")
        else:
            wrapper_path.write_text("#!/bin/sh\necho 'Mock status line'\n")
            os.chmod(wrapper_path, 0o755)

    def test_reminder_includes_auto_memory_policy(self, tmp_path):
        self._setup_mock_tausik(tmp_path)
        result = _run_hook(tmp_path)
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip(), "hook produced no output"
        parsed = json.loads(result.stdout)
        ctx = parsed["hookSpecificOutput"]["additionalContext"]
        assert "Project knowledge" in ctx
        assert "tausik memory add" in ctx
        assert "~/.claude/*/memory/" in ctx
        assert "confirm: cross-project" in ctx

    def test_policy_reminder_sits_with_other_reminders(self, tmp_path):
        """NEGATIVE: the bullet must live under the Reminders section, not wander elsewhere."""
        self._setup_mock_tausik(tmp_path)
        result = _run_hook(tmp_path)
        parsed = json.loads(result.stdout)
        ctx = parsed["hookSpecificOutput"]["additionalContext"]
        reminders_idx = ctx.find("**Reminders:**")
        policy_idx = ctx.find("Project knowledge")
        assert reminders_idx != -1
        assert policy_idx != -1
        assert reminders_idx < policy_idx


class TestRagFirstReminder:
    """The v1.4 RAG-first reminder is GONE (decision #390): a paired replay
    measured 0 search_code calls with it and 0 without. The Reminders block
    must not steer the agent's search tool any more."""

    def _setup_mock_tausik(self, tmp_path):
        tausik_dir = tmp_path / ".tausik"
        tausik_dir.mkdir()
        (tausik_dir / "tausik.db").write_text("")
        wrapper = "tausik.cmd" if sys.platform == "win32" else "tausik"
        wrapper_path = tausik_dir / wrapper
        if sys.platform == "win32":
            wrapper_path.write_text("@echo off\r\necho Mock status line\r\n")
        else:
            wrapper_path.write_text("#!/bin/sh\necho 'Mock status line'\n")
            os.chmod(wrapper_path, 0o755)

    def test_reminders_block_no_longer_advises_search_code(self, tmp_path):
        self._setup_mock_tausik(tmp_path)
        result = _run_hook(tmp_path)
        assert result.returncode == 0, result.stderr
        parsed = json.loads(result.stdout)
        ctx = parsed["hookSpecificOutput"]["additionalContext"]
        reminders_idx = ctx.find("**Reminders:**")
        assert reminders_idx != -1
        reminders_section = ctx[reminders_idx:]
        assert "search_code" not in reminders_section
        assert "task start" in reminders_section  # the block itself survives


class TestSettingsGeneration:
    """Generated settings.json must include SessionStart hook referencing session_start.py."""

    def test_claude_settings_has_sessionstart(self, tmp_path):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bootstrap"))
        from bootstrap_generate import generate_settings_claude

        target = tmp_path / ".claude"
        target.mkdir()
        generate_settings_claude(str(target), str(tmp_path))
        cfg = json.loads((target / "settings.json").read_text(encoding="utf-8"))
        hooks = cfg.get("hooks", {})
        assert "SessionStart" in hooks, "SessionStart hook not registered"
        cmds = [h["command"] for entry in hooks["SessionStart"] for h in entry["hooks"]]
        assert any("session_start.py" in c for c in cmds)

    def test_qwen_settings_has_sessionstart(self, tmp_path):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bootstrap"))
        from bootstrap_qwen import generate_settings_qwen

        target = tmp_path / ".qwen"
        target.mkdir()
        generate_settings_qwen(str(target), str(tmp_path), venv_python=sys.executable)
        cfg = json.loads((target / "settings.json").read_text(encoding="utf-8"))
        hooks = cfg.get("hooks", {})
        assert "SessionStart" in hooks, "SessionStart hook not registered for Qwen"
        cmds = [h["command"] for entry in hooks["SessionStart"] for h in entry["hooks"]]
        assert any("session_start.py" in c for c in cmds)


def _load_session_start():
    import importlib.util

    spec = importlib.util.spec_from_file_location("_ss_mod", _HOOK_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestRagSummary:
    """Regression for issue #2 / PR #3: wrong table name + swallowed schema error."""

    def _make_rag_db(self, tmp_path, table: str, rows: int):
        import sqlite3

        rag_dir = tmp_path / ".tausik" / "rag"
        rag_dir.mkdir(parents=True)
        con = sqlite3.connect(str(rag_dir / "rag.db"))
        con.execute(f"CREATE TABLE {table}(id INTEGER)")
        con.executemany(f"INSERT INTO {table} VALUES(?)", [(i,) for i in range(rows)])
        con.commit()
        con.close()

    def test_healthy_index_reports_count(self, tmp_path):
        ss = _load_session_start()
        self._make_rag_db(tmp_path, "rag_chunks", 42)
        out = ss._rag_summary(str(tmp_path))
        assert "42 chunks indexed" in out

    def test_schema_error_is_surfaced_not_hidden(self, tmp_path):
        # Wrong/missing table → real OperationalError, must NOT be the generic swallow.
        ss = _load_session_start()
        self._make_rag_db(tmp_path, "other_table", 1)
        out = ss._rag_summary(str(tmp_path))
        assert "schema error" in out
        assert "no such table: rag_chunks" in out
        assert "db unreadable" not in out


def test_native_codex_session_start_command_issues_durable_lease(tmp_path):
    from project_backend import SQLiteBackend

    backend = SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db"))
    backend.close()
    _install_valid_codex_profile(tmp_path)
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"TAUSIK_SKIP_HOOKS", "TAUSIK_HOOK_FAIL_OPEN"}
    }
    env.update({"CLAUDE_PROJECT_DIR": str(tmp_path), "PYTHONUTF8": "1"})
    result = subprocess.run(
        [sys.executable, _HOOK_PATH, "--trusted-host", "codex"],
        input=json.dumps({"hook_event_name": "SessionStart", "session_id": "native-thread"}),
        text=True,
        capture_output=True,
        encoding="utf-8",
        env=env,
        timeout=15,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert "EXECUTION LEASE ISSUED" in payload["hookSpecificOutput"]["additionalContext"]
    check = SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db"))
    try:
        assert check.session_current("native-thread") is not None
        assert check._q1("SELECT COUNT(*) AS count FROM execution_leases")["count"] == 1
    finally:
        check.close()


def test_native_codex_session_start_refuses_a_profile_without_security_adapters(tmp_path):
    from project_backend import SQLiteBackend

    backend = SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db"))
    backend.close()
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"TAUSIK_SKIP_HOOKS", "TAUSIK_HOOK_FAIL_OPEN"}
    }
    env.update({"CLAUDE_PROJECT_DIR": str(tmp_path), "PYTHONUTF8": "1"})
    result = subprocess.run(
        [sys.executable, _HOOK_PATH, "--trusted-host", "codex"],
        input=json.dumps({"hook_event_name": "SessionStart", "session_id": "native-thread"}),
        text=True,
        capture_output=True,
        encoding="utf-8",
        env=env,
        timeout=15,
    )
    payload = json.loads(result.stdout)
    context = payload["hookSpecificOutput"]["additionalContext"]
    assert "CAPABILITY_MISMATCH" in context
    assert "Do not begin project work" in context


@pytest.mark.parametrize(
    "manifest",
    [
        [],
        {
            "capability_version": 5,
            "mcp_transport_modes": [{}],
            "python_executable": "python",
            "adapters": {},
        },
    ],
)
def test_native_codex_session_start_types_malformed_manifest_as_capability_mismatch(
    tmp_path, manifest
):
    from project_backend import SQLiteBackend

    backend = SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db"))
    backend.close()
    _install_valid_codex_profile(tmp_path)
    (tmp_path / ".codex" / "tausik-capability.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"TAUSIK_SKIP_HOOKS", "TAUSIK_HOOK_FAIL_OPEN"}
    }
    env.update({"CLAUDE_PROJECT_DIR": str(tmp_path), "PYTHONUTF8": "1"})

    result = subprocess.run(
        [sys.executable, _HOOK_PATH, "--trusted-host", "codex"],
        input=json.dumps({"hook_event_name": "SessionStart", "session_id": "native-thread"}),
        text=True,
        capture_output=True,
        encoding="utf-8",
        env=env,
        timeout=15,
    )

    assert result.returncode == 0, result.stderr
    context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "CAPABILITY_MISMATCH" in context
    assert "LEASE_INTERNAL" not in context


@pytest.mark.parametrize(
    "mutation",
    [
        "swap_events",
        "nonempty_matcher",
        "wrong_path",
        "missing_file",
        "wrong_project",
        "inert_argument",
        "non_command_type",
        "missing_composite",
        "duplicate_project",
        "trailing_argument",
        "wrong_python",
    ],
)
def test_codex_capability_attestation_rejects_stale_hook_profiles(tmp_path, mutation):
    ss = _load_session_start()
    pretool, posttool = _install_valid_codex_profile(tmp_path)
    event_pre, event_post = "PreToolUse", "PostToolUse"
    matcher = ""
    pretool_command = f'python -X utf8 "{pretool}" --project "{tmp_path}"'
    posttool_command = f'python -X utf8 "{posttool}" --project "{tmp_path}"'
    if mutation == "swap_events":
        event_pre, event_post = event_post, event_pre
    elif mutation == "nonempty_matcher":
        matcher = "Bash"
    elif mutation == "wrong_path":
        pretool_command = pretool_command.replace("codex_write_gate.py", "other.py")
    elif mutation == "missing_file":
        posttool.unlink()
    elif mutation == "wrong_project":
        posttool_command = posttool_command.replace(str(tmp_path), str(tmp_path / "other"))
    elif mutation == "inert_argument":
        pretool_command = f'echo "{pretool}" --project "{tmp_path}"'
    elif mutation == "missing_composite":
        (pretool.parent / "codex_composite_mcp.py").unlink()
    elif mutation == "duplicate_project":
        pretool_command += f' --project "{tmp_path / "other"}"'
    elif mutation == "trailing_argument":
        pretool_command += " --unknown"
    elif mutation == "wrong_python":
        pretool_command = pretool_command.replace("python -X", "python-evil.exe -X", 1)
    hook_type = "prompt" if mutation == "non_command_type" else "command"
    payload = {
        "hooks": {
            event_pre: [
                {"matcher": matcher, "hooks": [{"type": hook_type, "command": pretool_command}]}
            ],
            event_post: [
                {"matcher": matcher, "hooks": [{"type": hook_type, "command": posttool_command}]}
            ],
        }
    }
    (tmp_path / ".codex" / "hooks.json").write_text(json.dumps(payload), encoding="utf-8")

    assert ss._codex_preflight_hooks_ready(str(tmp_path)) is False


def test_codex_capability_attestation_rejects_adapter_content_drift(tmp_path):
    ss = _load_session_start()
    pretool, _posttool = _install_valid_codex_profile(tmp_path)
    pretool.write_text("# no-op replacement\n", encoding="utf-8")

    assert ss._codex_preflight_hooks_ready(str(tmp_path)) is False
