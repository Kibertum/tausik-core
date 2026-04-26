"""Test memory_pretool_block PreToolUse hook.

The hook must block Write/Edit/MultiEdit under ~/.claude/projects/*/memory/
from a TAUSIK project, with a bypass marker escape hatch. Non-memory paths,
non-TAUSIK projects, other tools, and malformed stdin must all pass through
(exit 0) without blocking.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

_HOOK_PATH = os.path.join(
    os.path.dirname(__file__), "..", "scripts", "hooks", "memory_pretool_block.py"
)

_HOME = os.path.expanduser("~").replace("\\", "/")
_MEMORY_ROOT = f"{_HOME}/.claude/projects/test-proj/memory"


def _run(
    project_dir, payload: dict, extra_env: dict | None = None
) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "CLAUDE_PROJECT_DIR": str(project_dir),
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    # Do not inherit TAUSIK_SKIP_HOOKS from the agent that runs these tests.
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
    """Create a minimal .tausik/tausik.db so the hook recognizes a TAUSIK project."""
    tausik = tmp_path / ".tausik"
    tausik.mkdir()
    (tausik / "tausik.db").write_text("")
    return tausik


def _write_transcript(tmp_path, events: list[dict]) -> str:
    path = tmp_path / "transcript.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")
    return str(path)


class TestBlocksMemoryWrites:
    @pytest.mark.parametrize("tool", ["Write", "Edit", "MultiEdit"])
    def test_blocks_tool_at_memory_root(self, tmp_path, tool):
        _setup_tausik(tmp_path)
        result = _run(
            tmp_path,
            {
                "tool_name": tool,
                "tool_input": {"file_path": f"{_MEMORY_ROOT}/foo.md"},
                "transcript_path": "",
            },
        )
        assert result.returncode == 2, result.stderr
        assert "BLOCKED" in result.stderr
        assert "tausik memory add" in result.stderr
        assert "confirm: cross-project" in result.stderr

    def test_blocks_nested_subdir(self, tmp_path):
        _setup_tausik(tmp_path)
        result = _run(
            tmp_path,
            {
                "tool_name": "Write",
                "tool_input": {"file_path": f"{_MEMORY_ROOT}/sub/deep/nested.md"},
                "transcript_path": "",
            },
        )
        assert result.returncode == 2

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific path form")
    def test_blocks_raw_windows_backslash_path(self, tmp_path):
        """Guards _normalize's backslash→forward-slash conversion.

        Without that conversion the path wouldn't match the forward-slash prefix
        and the hook would silently pass a write it should block.
        """
        _setup_tausik(tmp_path)
        raw = os.path.expanduser("~") + "\\.claude\\projects\\test-proj\\memory\\foo.md"
        result = _run(
            tmp_path,
            {
                "tool_name": "Write",
                "tool_input": {"file_path": raw},
                "transcript_path": "",
            },
        )
        assert result.returncode == 2, result.stderr

    def test_blocks_tilde_expanded_path(self, tmp_path):
        _setup_tausik(tmp_path)
        result = _run(
            tmp_path,
            {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": "~/.claude/projects/test-proj/memory/foo.md"
                },
                "transcript_path": "",
            },
        )
        assert result.returncode == 2, result.stderr

    def test_blocks_bare_claude_memory(self, tmp_path):
        """Broadened guard: .claude/memory/ directly under home (no projects/)."""
        _setup_tausik(tmp_path)
        result = _run(
            tmp_path,
            {
                "tool_name": "Write",
                "tool_input": {"file_path": f"{_HOME}/.claude/memory/note.md"},
                "transcript_path": "",
            },
        )
        assert result.returncode == 2, result.stderr
        assert "BLOCKED" in result.stderr

    def test_blocks_agents_memory(self, tmp_path):
        """Broadened guard: .claude/agents/<name>/memory/."""
        _setup_tausik(tmp_path)
        result = _run(
            tmp_path,
            {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": f"{_HOME}/.claude/agents/my-agent/memory/notes.md"
                },
                "transcript_path": "",
            },
        )
        assert result.returncode == 2, result.stderr

    def test_blocks_deeply_nested_memory(self, tmp_path):
        """Broadened guard: memory segment can appear at any depth."""
        _setup_tausik(tmp_path)
        result = _run(
            tmp_path,
            {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": f"{_HOME}/.claude/plugins/foo/memory/sub/f.md"
                },
                "transcript_path": "",
            },
        )
        assert result.returncode == 2, result.stderr

    def test_blocks_memory_dir_basename_no_file(self, tmp_path):
        """C1 regression fix: path ending in 'memory' (no file inside) blocks.

        Before: `[:-1]` slice excluded the basename → directory-form path
        sneaked past. Old guard `rest[1] == 'memory'` caught it.
        """
        _setup_tausik(tmp_path)
        for path in (
            f"{_HOME}/.claude/projects/test-proj/memory",
            f"{_HOME}/.claude/memory",
            f"{_HOME}/.claude/agents/x/memory",
        ):
            result = _run(
                tmp_path,
                {
                    "tool_name": "Write",
                    "tool_input": {"file_path": path},
                    "transcript_path": "",
                },
            )
            assert result.returncode == 2, (path, result.stderr)


class TestAllowsNonMemoryPaths:
    @pytest.mark.parametrize(
        "file_path",
        [
            lambda home: (
                "d:/some/project/README.md"
                if sys.platform == "win32"
                else "/some/project/README.md"
            ),
            lambda home: f"{home}/.claude/projects/test-proj/settings.json",
            lambda home: f"{home}/.claude/projects/test-proj/plans/plan.md",
            lambda home: f"{home}/Documents/note.md",
            # Boundary: file literally named memory.md (not under a memory/ dir)
            lambda home: f"{home}/.claude/projects/test-proj/memory.md",
            # Boundary: substring `memory` in segment name but not exact
            lambda home: f"{home}/.claude/projects/test-proj/somememory/note.md",
            lambda home: f"{home}/.claude/projects/test-proj/memoryold/note.md",
        ],
    )
    def test_allows_path_outside_memory(self, tmp_path, file_path):
        _setup_tausik(tmp_path)
        result = _run(
            tmp_path,
            {
                "tool_name": "Write",
                "tool_input": {"file_path": file_path(_HOME)},
                "transcript_path": "",
            },
        )
        assert result.returncode == 0, result.stderr

    def test_allows_other_tool_names(self, tmp_path):
        _setup_tausik(tmp_path)
        for tool in ("Bash", "Read", "Grep", "Glob", "WebFetch"):
            result = _run(
                tmp_path,
                {
                    "tool_name": tool,
                    "tool_input": {"file_path": f"{_MEMORY_ROOT}/foo.md"},
                    "transcript_path": "",
                },
            )
            assert result.returncode == 0, (tool, result.stderr)


class TestAllowsOutsideTausik:
    def test_allows_without_tausik_db(self, tmp_path):
        # tmp_path has no .tausik/ — not a TAUSIK project
        result = _run(
            tmp_path,
            {
                "tool_name": "Write",
                "tool_input": {"file_path": f"{_MEMORY_ROOT}/foo.md"},
                "transcript_path": "",
            },
        )
        assert result.returncode == 0, result.stderr

    def test_skip_hooks_env_var(self, tmp_path):
        _setup_tausik(tmp_path)
        result = _run(
            tmp_path,
            {
                "tool_name": "Write",
                "tool_input": {"file_path": f"{_MEMORY_ROOT}/foo.md"},
                "transcript_path": "",
            },
            extra_env={"TAUSIK_SKIP_MEMORY_HOOK": "1"},
        )
        assert result.returncode == 0, result.stderr


class TestGracefulMalformed:
    def test_malformed_json(self, tmp_path):
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
        assert result.returncode == 0, result.stderr

    def test_empty_stdin(self, tmp_path):
        _setup_tausik(tmp_path)
        env = {
            **os.environ,
            "CLAUDE_PROJECT_DIR": str(tmp_path),
            "PYTHONUTF8": "1",
        }
        env.pop("TAUSIK_SKIP_HOOKS", None)
        result = subprocess.run(
            [sys.executable, _HOOK_PATH],
            input="",
            capture_output=True,
            text=True,
            timeout=15,
            env=env,
        )
        assert result.returncode == 0, result.stderr

    def test_array_instead_of_object(self, tmp_path):
        _setup_tausik(tmp_path)
        env = {
            **os.environ,
            "CLAUDE_PROJECT_DIR": str(tmp_path),
            "PYTHONUTF8": "1",
        }
        env.pop("TAUSIK_SKIP_HOOKS", None)
        result = subprocess.run(
            [sys.executable, _HOOK_PATH],
            input="[1,2,3]",
            capture_output=True,
            text=True,
            timeout=15,
            env=env,
        )
        assert result.returncode == 0

    def test_missing_tool_input(self, tmp_path):
        _setup_tausik(tmp_path)
        result = _run(tmp_path, {"tool_name": "Write"})
        assert result.returncode == 0

    def test_file_path_not_string(self, tmp_path):
        _setup_tausik(tmp_path)
        result = _run(
            tmp_path,
            {
                "tool_name": "Write",
                "tool_input": {"file_path": ["list", "of", "parts"]},
                "transcript_path": "",
            },
        )
        assert result.returncode == 0


class TestBypassMarker:
    def test_substring_marker_does_NOT_bypass(self, tmp_path):
        """Regression: quoting the hook's own error text must not trigger
        bypass — only a marker on a line by itself counts."""
        _setup_tausik(tmp_path)
        transcript = _write_transcript(
            tmp_path,
            [
                {
                    "type": "user",
                    "message": {
                        "role": "user",
                        "content": (
                            "The hook said reply with `confirm: cross-project` "
                            "in the next message. What does that mean?"
                        ),
                    },
                }
            ],
        )
        result = _run(
            tmp_path,
            {
                "tool_name": "Write",
                "tool_input": {"file_path": f"{_MEMORY_ROOT}/new.md"},
                "transcript_path": transcript,
            },
        )
        assert result.returncode == 2, result.stderr
        assert "BLOCKED" in result.stderr

    def test_marker_inside_fenced_code_block_does_NOT_bypass(self, tmp_path):
        """Regression: quoting the hook's error text inside fenced code must
        not trigger bypass."""
        _setup_tausik(tmp_path)
        transcript = _write_transcript(
            tmp_path,
            [
                {
                    "type": "user",
                    "message": {
                        "role": "user",
                        "content": (
                            "The hook said:\n```text\n"
                            "reply with `confirm: cross-project` to override\n"
                            "```\n"
                            "Can you explain?"
                        ),
                    },
                }
            ],
        )
        result = _run(
            tmp_path,
            {
                "tool_name": "Write",
                "tool_input": {"file_path": f"{_MEMORY_ROOT}/new.md"},
                "transcript_path": transcript,
            },
        )
        assert result.returncode == 2, result.stderr

    def test_marker_in_last_user_turn_as_string(self, tmp_path):
        _setup_tausik(tmp_path)
        transcript = _write_transcript(
            tmp_path,
            [
                {
                    "type": "user",
                    "message": {
                        "role": "user",
                        "content": "save this\nconfirm: cross-project",
                    },
                }
            ],
        )
        result = _run(
            tmp_path,
            {
                "tool_name": "Write",
                "tool_input": {"file_path": f"{_MEMORY_ROOT}/new.md"},
                "transcript_path": transcript,
            },
        )
        assert result.returncode == 0, result.stderr

    def test_marker_in_last_user_turn_as_list(self, tmp_path):
        _setup_tausik(tmp_path)
        transcript = _write_transcript(
            tmp_path,
            [
                {
                    "type": "user",
                    "message": {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "please save\nconfirm: cross-project\nnow",
                            }
                        ],
                    },
                }
            ],
        )
        result = _run(
            tmp_path,
            {
                "tool_name": "Write",
                "tool_input": {"file_path": f"{_MEMORY_ROOT}/new.md"},
                "transcript_path": transcript,
            },
        )
        assert result.returncode == 0, result.stderr

    def test_marker_case_insensitive(self, tmp_path):
        _setup_tausik(tmp_path)
        transcript = _write_transcript(
            tmp_path,
            [
                {
                    "type": "user",
                    "message": {
                        "role": "user",
                        "content": "CONFIRM: Cross-Project",
                    },
                }
            ],
        )
        result = _run(
            tmp_path,
            {
                "tool_name": "Write",
                "tool_input": {"file_path": f"{_MEMORY_ROOT}/new.md"},
                "transcript_path": transcript,
            },
        )
        assert result.returncode == 0, result.stderr

    def test_marker_only_in_earlier_turn_blocks(self, tmp_path):
        """NEGATIVE: marker in an older turn, a newer user turn has no marker → block."""
        _setup_tausik(tmp_path)
        transcript = _write_transcript(
            tmp_path,
            [
                {
                    "type": "user",
                    "message": {
                        "role": "user",
                        "content": "confirm: cross-project",
                    },
                },
                {
                    "type": "assistant",
                    "message": {"role": "assistant", "content": "ok"},
                },
                {
                    "type": "user",
                    "message": {
                        "role": "user",
                        "content": "actually save this project note",
                    },
                },
            ],
        )
        result = _run(
            tmp_path,
            {
                "tool_name": "Write",
                "tool_input": {"file_path": f"{_MEMORY_ROOT}/new.md"},
                "transcript_path": transcript,
            },
        )
        assert result.returncode == 2, result.stderr

    def test_missing_transcript_file(self, tmp_path):
        """Transcript path points nowhere → treated as no bypass → block."""
        _setup_tausik(tmp_path)
        result = _run(
            tmp_path,
            {
                "tool_name": "Write",
                "tool_input": {"file_path": f"{_MEMORY_ROOT}/new.md"},
                "transcript_path": str(tmp_path / "does_not_exist.jsonl"),
            },
        )
        assert result.returncode == 2


class TestSkipsToolResultTurns:
    def test_tool_result_turn_is_not_the_bypass_source(self, tmp_path):
        """Real Claude Code format: tool_result events have type=user.

        Parser must skip them and find the previous turn with actual text.
        """
        _setup_tausik(tmp_path)
        transcript = _write_transcript(
            tmp_path,
            [
                {
                    "type": "user",
                    "message": {
                        "role": "user",
                        "content": [{"type": "text", "text": "confirm: cross-project"}],
                    },
                },
                {
                    "type": "assistant",
                    "message": {"role": "assistant", "content": "ran a tool"},
                },
                {
                    "type": "user",
                    "message": {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": "toolu_01",
                                "content": "some output",
                            }
                        ],
                    },
                },
            ],
        )
        result = _run(
            tmp_path,
            {
                "tool_name": "Write",
                "tool_input": {"file_path": f"{_MEMORY_ROOT}/new.md"},
                "transcript_path": transcript,
            },
        )
        assert result.returncode == 0, result.stderr

    def test_no_real_user_turns_only_tool_results(self, tmp_path):
        _setup_tausik(tmp_path)
        transcript = _write_transcript(
            tmp_path,
            [
                {
                    "type": "user",
                    "message": {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": "x",
                                "content": "r",
                            }
                        ],
                    },
                }
            ],
        )
        result = _run(
            tmp_path,
            {
                "tool_name": "Write",
                "tool_input": {"file_path": f"{_MEMORY_ROOT}/new.md"},
                "transcript_path": transcript,
            },
        )
        assert result.returncode == 2


class TestSettingsGeneration:
    def test_claude_settings_registers_hook(self, tmp_path):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bootstrap"))
        from bootstrap_generate import generate_settings_claude

        target = tmp_path / ".claude"
        target.mkdir()
        generate_settings_claude(str(target), str(tmp_path))
        cfg = json.loads((target / "settings.json").read_text(encoding="utf-8"))
        hooks = cfg.get("hooks", {})
        assert "PreToolUse" in hooks
        matched = False
        for entry in hooks["PreToolUse"]:
            if not any(
                "memory_pretool_block.py" in h["command"] for h in entry["hooks"]
            ):
                continue
            assert entry["matcher"] == "Write|Edit|MultiEdit", entry
            matched = True
        assert matched, "memory_pretool_block.py not registered in Claude PreToolUse"

    def test_qwen_settings_registers_hook(self, tmp_path):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bootstrap"))
        from bootstrap_qwen import generate_settings_qwen

        target = tmp_path / ".qwen"
        target.mkdir()
        generate_settings_qwen(str(target), str(tmp_path), venv_python=sys.executable)
        cfg = json.loads((target / "settings.json").read_text(encoding="utf-8"))
        hooks = cfg.get("hooks", {})
        assert "PreToolUse" in hooks
        matched = False
        for entry in hooks["PreToolUse"]:
            if not any(
                "memory_pretool_block.py" in h["command"] for h in entry["hooks"]
            ):
                continue
            assert entry["matcher"] == "Write|Edit|MultiEdit", entry
            matched = True
        assert matched, "memory_pretool_block.py not registered in Qwen PreToolUse"


class TestEdgeCases:
    def test_marker_in_mixed_list_with_bare_strings_and_non_text(self, tmp_path):
        """Content list can mix dict-with-text, bare strings, and other types.

        Parser should join all text chunks; marker in any of them still counts.
        """
        _setup_tausik(tmp_path)
        transcript = _write_transcript(
            tmp_path,
            [
                {
                    "type": "user",
                    "message": {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "first chunk"},
                            {"type": "image", "source": {"type": "base64"}},
                            "bare string preceding marker\nconfirm: cross-project",
                        ],
                    },
                }
            ],
        )
        result = _run(
            tmp_path,
            {
                "tool_name": "Write",
                "tool_input": {"file_path": f"{_MEMORY_ROOT}/new.md"},
                "transcript_path": transcript,
            },
        )
        assert result.returncode == 0, result.stderr

    def test_marker_in_assistant_turn_is_ignored(self, tmp_path):
        """Only user-type events count; assistant echoing the marker must not bypass."""
        _setup_tausik(tmp_path)
        transcript = _write_transcript(
            tmp_path,
            [
                {
                    "type": "assistant",
                    "message": {
                        "role": "assistant",
                        "content": "I will use the confirm: cross-project marker",
                    },
                },
                {
                    "type": "user",
                    "message": {"role": "user", "content": "save it"},
                },
            ],
        )
        result = _run(
            tmp_path,
            {
                "tool_name": "Write",
                "tool_input": {"file_path": f"{_MEMORY_ROOT}/new.md"},
                "transcript_path": transcript,
            },
        )
        assert result.returncode == 2, result.stderr

    def test_corrupt_jsonl_line_does_not_kill_parser(self, tmp_path):
        """One broken line among valid ones must not crash _last_user_prompt."""
        _setup_tausik(tmp_path)
        path = tmp_path / "transcript.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "type": "user",
                        "message": {
                            "role": "user",
                            "content": "confirm: cross-project",
                        },
                    }
                )
                + "\n"
            )
            f.write("this is not valid json at all {{{\n")
            f.write(
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {"role": "assistant", "content": "ok"},
                    }
                )
                + "\n"
            )
        result = _run(
            tmp_path,
            {
                "tool_name": "Write",
                "tool_input": {"file_path": f"{_MEMORY_ROOT}/new.md"},
                "transcript_path": str(path),
            },
        )
        assert result.returncode == 0, result.stderr
