"""Integration tests for scripts/hooks/memory_posttool_audit.py.

The audit hook is a warning-only safety-net: it always exits 0, and only
speaks (stderr) when a just-written auto-memory file contains project-
specific markers. Silence on clean writes is as important as noise on
dirty ones — this suite guards both.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

_HOOK_PATH = os.path.join(
    os.path.dirname(__file__), "..", "scripts", "hooks", "memory_posttool_audit.py"
)

_HOME = os.path.expanduser("~").replace("\\", "/")


def _run(
    project_dir,
    payload: dict,
    extra_env: dict | None = None,
    home_override: str | None = None,
) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "CLAUDE_PROJECT_DIR": str(project_dir),
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    if home_override is not None:
        env["HOME"] = home_override
        env["USERPROFILE"] = home_override
    env.pop("TAUSIK_SKIP_HOOKS", None)
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, _HOOK_PATH],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )


def _setup_tausik(tmp_path):
    tausik = tmp_path / ".tausik"
    tausik.mkdir()
    (tausik / "tausik.db").write_text("")
    return tausik


def _make_home_memory_file(home_dir, content: str, name: str = "fake.md") -> str:
    """Create a file under a fake HOME/.claude/projects/test-proj/memory/.

    Returns the posix-style path the hook should see in tool_input.file_path.
    Tests pass the same `home_dir` to _run via home_override so the hook's
    os.path.expanduser matches this location instead of the real user home.
    """
    base = os.path.join(home_dir, ".claude", "projects", "test-proj", "memory")
    os.makedirs(base, exist_ok=True)
    abs_path = os.path.join(base, name)
    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(content)
    return abs_path.replace("\\", "/")


@pytest.fixture
def fake_home(tmp_path):
    """Isolated HOME directory for this test; no touching the real user home."""
    home = tmp_path / "fake_home"
    home.mkdir()
    return str(home)


class TestDetectionEmitsWarning:
    def test_markers_trigger_audit_stderr(self, tmp_path, fake_home):
        _setup_tausik(tmp_path)
        path = _make_home_memory_file(
            fake_home,
            "closed mem-pretool-hook. edited scripts/hooks/session_start.py. "
            "run .tausik/tausik status afterwards.",
        )
        result = _run(
            tmp_path,
            {"tool_name": "Write", "tool_input": {"file_path": path}},
            home_override=fake_home,
        )
        assert result.returncode == 0
        assert "AUDIT" in result.stderr
        assert "project marker" in result.stderr
        assert "tausik memory add" in result.stderr
        assert "[slug]" in result.stderr or "[src_file]" in result.stderr

    @pytest.mark.parametrize("tool", ["Write", "Edit", "MultiEdit"])
    def test_all_tools_audited(self, tmp_path, fake_home, tool):
        _setup_tausik(tmp_path)
        path = _make_home_memory_file(fake_home, "task some-slug-with-parts done")
        result = _run(
            tmp_path,
            {"tool_name": tool, "tool_input": {"file_path": path}},
            home_override=fake_home,
        )
        assert result.returncode == 0
        assert "AUDIT" in result.stderr, tool

    def test_truncates_when_more_than_5_markers(self, tmp_path, fake_home):
        _setup_tausik(tmp_path)
        # 7 distinct slugs — exceeds _MAX_REPORTED=5
        content = " ".join(f"task slug-number-{i}-more done" for i in range(1, 8))
        path = _make_home_memory_file(fake_home, content)
        result = _run(
            tmp_path,
            {"tool_name": "Write", "tool_input": {"file_path": path}},
            home_override=fake_home,
        )
        assert result.returncode == 0
        assert "AUDIT" in result.stderr
        assert "...and" in result.stderr, result.stderr
        assert "more" in result.stderr

    def test_binary_content_does_not_crash(self, tmp_path, fake_home):
        """Non-UTF8 bytes must be tolerated (errors='replace')."""
        _setup_tausik(tmp_path)
        base = os.path.join(fake_home, ".claude", "projects", "test-proj", "memory")
        os.makedirs(base, exist_ok=True)
        raw_path = os.path.join(base, "bin.md")
        with open(raw_path, "wb") as f:
            f.write(b"\xff\xfe\x00 task mem-pretool-hook done \x80\x81")
        file_path = raw_path.replace("\\", "/")
        result = _run(
            tmp_path,
            {"tool_name": "Write", "tool_input": {"file_path": file_path}},
            home_override=fake_home,
        )
        assert result.returncode == 0
        assert "AUDIT" in result.stderr
        assert "mem-pretool-hook" in result.stderr


class TestSilentOnCleanWrites:
    def test_cross_project_preference_is_quiet(self, tmp_path, fake_home):
        _setup_tausik(tmp_path)
        path = _make_home_memory_file(
            fake_home,
            "User prefers Russian responses and concise commit messages.\n"
            "Likes pytest over unittest. Uses Docker for local dev.",
        )
        result = _run(
            tmp_path,
            {"tool_name": "Write", "tool_input": {"file_path": path}},
            home_override=fake_home,
        )
        assert result.returncode == 0
        assert result.stderr == "", result.stderr


class TestNonAuditedPaths:
    def test_outside_memory_is_quiet(self, tmp_path, fake_home):
        _setup_tausik(tmp_path)
        outside = tmp_path / "outside.md"
        outside.write_text(
            "task mem-pretool-hook done, scripts/foo.py", encoding="utf-8"
        )
        result = _run(
            tmp_path,
            {
                "tool_name": "Write",
                "tool_input": {"file_path": str(outside).replace("\\", "/")},
            },
            home_override=fake_home,
        )
        assert result.returncode == 0
        assert result.stderr == ""

    @pytest.mark.parametrize("tool", ["Bash", "Read", "Grep", "Glob"])
    def test_non_write_tools_skipped(self, tmp_path, fake_home, tool):
        _setup_tausik(tmp_path)
        path = f"{fake_home}/.claude/projects/x/memory/y.md".replace("\\", "/")
        result = _run(
            tmp_path,
            {"tool_name": tool, "tool_input": {"file_path": path}},
            home_override=fake_home,
        )
        assert result.returncode == 0
        assert result.stderr == ""


class TestGraceful:
    def test_missing_file_is_quiet(self, tmp_path, fake_home):
        _setup_tausik(tmp_path)
        path = f"{fake_home}/.claude/projects/x/memory/does_not_exist.md".replace(
            "\\", "/"
        )
        result = _run(
            tmp_path,
            {"tool_name": "Write", "tool_input": {"file_path": path}},
            home_override=fake_home,
        )
        assert result.returncode == 0
        assert result.stderr == ""

    def test_non_tausik_project(self, tmp_path, fake_home):
        # No _setup_tausik: tmp_path lacks .tausik/tausik.db
        path = _make_home_memory_file(fake_home, "task mem-pretool-hook done")
        result = _run(
            tmp_path,
            {"tool_name": "Write", "tool_input": {"file_path": path}},
            home_override=fake_home,
        )
        assert result.returncode == 0
        assert result.stderr == ""

    def test_skip_hooks_env(self, tmp_path, fake_home):
        _setup_tausik(tmp_path)
        path = _make_home_memory_file(fake_home, "task mem-pretool-hook done")
        result = _run(
            tmp_path,
            {"tool_name": "Write", "tool_input": {"file_path": path}},
            extra_env={"TAUSIK_SKIP_HOOKS": "1"},
            home_override=fake_home,
        )
        assert result.returncode == 0
        assert result.stderr == ""

    def test_malformed_stdin(self, tmp_path):
        _setup_tausik(tmp_path)
        env = {
            **os.environ,
            "CLAUDE_PROJECT_DIR": str(tmp_path),
            "PYTHONUTF8": "1",
        }
        env.pop("TAUSIK_SKIP_HOOKS", None)
        result = subprocess.run(
            [sys.executable, _HOOK_PATH],
            input="not json {{{",
            capture_output=True,
            text=True,
            timeout=15,
            env=env,
        )
        assert result.returncode == 0
        assert result.stderr == ""

    def test_file_path_not_string(self, tmp_path):
        _setup_tausik(tmp_path)
        result = _run(
            tmp_path,
            {"tool_name": "Write", "tool_input": {"file_path": 42}},
        )
        assert result.returncode == 0

    def test_tool_input_missing_entirely(self, tmp_path):
        _setup_tausik(tmp_path)
        result = _run(tmp_path, {"tool_name": "Write"})
        assert result.returncode == 0
        assert result.stderr == ""

    def test_tool_input_is_null(self, tmp_path):
        _setup_tausik(tmp_path)
        result = _run(tmp_path, {"tool_name": "Write", "tool_input": None})
        assert result.returncode == 0
        assert result.stderr == ""

    def test_tool_input_is_string(self, tmp_path):
        _setup_tausik(tmp_path)
        result = _run(tmp_path, {"tool_name": "Write", "tool_input": "nonsense"})
        assert result.returncode == 0
        assert result.stderr == ""


class TestSettingsGeneration:
    def test_claude_settings_registers_audit(self, tmp_path):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bootstrap"))
        from bootstrap_generate import generate_settings_claude

        target = tmp_path / ".claude"
        target.mkdir()
        generate_settings_claude(str(target), str(tmp_path))
        cfg = json.loads((target / "settings.json").read_text(encoding="utf-8"))
        hooks = cfg.get("hooks", {})
        assert "PostToolUse" in hooks
        matched = False
        for entry in hooks["PostToolUse"]:
            if not any(
                "memory_posttool_audit.py" in h["command"] for h in entry["hooks"]
            ):
                continue
            assert entry["matcher"] == "Write|Edit|MultiEdit", entry
            matched = True
        assert matched, "memory_posttool_audit.py not registered in Claude PostToolUse"

    def test_qwen_settings_registers_audit(self, tmp_path):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bootstrap"))
        from bootstrap_qwen import generate_settings_qwen

        target = tmp_path / ".qwen"
        target.mkdir()
        generate_settings_qwen(str(target), str(tmp_path), venv_python=sys.executable)
        cfg = json.loads((target / "settings.json").read_text(encoding="utf-8"))
        hooks = cfg.get("hooks", {})
        assert "PostToolUse" in hooks
        matched = False
        for entry in hooks["PostToolUse"]:
            if not any(
                "memory_posttool_audit.py" in h["command"] for h in entry["hooks"]
            ):
                continue
            assert entry["matcher"] == "Write|Edit|MultiEdit", entry
            matched = True
        assert matched, "memory_posttool_audit.py not registered in Qwen PostToolUse"
