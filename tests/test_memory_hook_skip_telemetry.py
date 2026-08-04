"""memory-pretool-block-skip-toggle-and-docstring: the memory guard's skip
paths must be honest and instrumented.

Two defects were fixed here (Decision #159):
  1. The docstring claimed `TAUSIK_SKIP_HOOKS` skipped the hook, but only
     `TAUSIK_SKIP_MEMORY_HOOK` was honored (narrative != code).
  2. `TAUSIK_SKIP_MEMORY_HOOK` — a way to bypass cross-project memory
     protection — left no supervision-bypass trace.

Fix: honor BOTH flags (parity with the rest of the hook suite) and emit a
distinct `bypass_*` event per skip path, symmetric to l26-bypass-telemetry.
These tests pin the parity so it cannot silently rot again.
"""

from __future__ import annotations

import inspect
import json
import os
import re
import sqlite3
import subprocess
import sys

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
_HOOKS = os.path.join(_SCRIPTS, "hooks")
for _p in (_SCRIPTS, _HOOKS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from project_backend import SQLiteBackend  # noqa: E402

_HOOK_PATH = os.path.join(_HOOKS, "memory_pretool_block.py")
_HOME = os.path.expanduser("~").replace("\\", "/")
_MEMORY_TARGET = f"{_HOME}/.claude/projects/test-proj/memory/foo.md"


def _make_project(tmp_path) -> str:
    """A throwaway project with a REAL schema so `events` can be written."""
    tdir = tmp_path / ".tausik"
    tdir.mkdir()
    be = SQLiteBackend(str(tdir / "tausik.db"))  # constructs schema
    be.close()  # release the connection so the subprocess hook can write
    return str(tmp_path)


def _run(project_dir, extra_env: dict | None = None) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "CLAUDE_PROJECT_DIR": str(project_dir),
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    env.pop("TAUSIK_SKIP_HOOKS", None)
    env.pop("TAUSIK_SKIP_MEMORY_HOOK", None)
    if extra_env:
        env.update(extra_env)
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": _MEMORY_TARGET},
        "transcript_path": "",
    }
    return subprocess.run(
        [sys.executable, _HOOK_PATH],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
        env=env,
    )


def _supervision_rows(project_dir) -> list[tuple[str, str]]:
    db = os.path.join(project_dir, ".tausik", "tausik.db")
    conn = sqlite3.connect(db)
    try:
        return conn.execute(
            "SELECT entity_id, action FROM events WHERE entity_type='supervision' ORDER BY id"
        ).fetchall()
    finally:
        conn.close()


class TestSkipEmitsTelemetry:
    def test_umbrella_skip_hooks_passes_and_emits(self, tmp_path):
        project_dir = _make_project(tmp_path)
        result = _run(project_dir, {"TAUSIK_SKIP_HOOKS": "1"})
        assert result.returncode == 0, result.stderr
        assert _supervision_rows(project_dir) == [("memory_pretool_block", "bypass_skip_hooks")]

    def test_specific_skip_memory_hook_passes_and_emits(self, tmp_path):
        project_dir = _make_project(tmp_path)
        result = _run(project_dir, {"TAUSIK_SKIP_MEMORY_HOOK": "1"})
        assert result.returncode == 0, result.stderr
        assert _supervision_rows(project_dir) == [
            ("memory_pretool_block", "bypass_skip_memory_hook")
        ]

    def test_umbrella_wins_over_specific_and_emits_once(self, tmp_path):
        """Both flags set: the umbrella is checked first, so exactly one row
        (skip_hooks) is recorded — never a double-count."""
        project_dir = _make_project(tmp_path)
        result = _run(project_dir, {"TAUSIK_SKIP_HOOKS": "1", "TAUSIK_SKIP_MEMORY_HOOK": "1"})
        assert result.returncode == 0, result.stderr
        assert _supervision_rows(project_dir) == [("memory_pretool_block", "bypass_skip_hooks")]

    def test_no_flag_blocks_and_emits_nothing(self, tmp_path):
        """The guard doing its job is not a bypass — no supervision row."""
        project_dir = _make_project(tmp_path)
        result = _run(project_dir)
        assert result.returncode == 2, result.stderr
        assert "BLOCKED" in result.stderr
        assert _supervision_rows(project_dir) == []

    def test_arbitrary_truthy_value_honored(self, tmp_path):
        """Parity with the suite: any non-empty value skips, not only '1'."""
        project_dir = _make_project(tmp_path)
        result = _run(project_dir, {"TAUSIK_SKIP_HOOKS": "true"})
        assert result.returncode == 0, result.stderr
        assert _supervision_rows(project_dir) == [("memory_pretool_block", "bypass_skip_hooks")]

    def test_telemetry_failure_never_blocks(self, tmp_path):
        """Corrupt db → emit_supervision_bypass swallows the error; a skip must
        still be a skip (exit 0), never flipped into a block."""
        tdir = tmp_path / ".tausik"
        tdir.mkdir()
        (tdir / "tausik.db").write_bytes(b"not a sqlite database")
        result = _run(str(tmp_path), {"TAUSIK_SKIP_MEMORY_HOOK": "1"})
        assert result.returncode == 0, result.stderr


class TestDocstringCodeParity:
    """Anti-drift: the exact defect this task fixed was a docstring naming a
    flag the code did not honor. Pin the two in lockstep so it cannot recur."""

    _SKIP_FLAG_RE = re.compile(r"TAUSIK_SKIP_[A-Z_]+")

    def _module(self):
        import memory_pretool_block

        return memory_pretool_block

    def test_docstring_flags_equal_honored_flags(self):
        mod = self._module()
        doc_flags = set(self._SKIP_FLAG_RE.findall(mod.__doc__ or ""))
        # Flags actually consulted in main() via os.environ.get(...)
        main_src = inspect.getsource(mod.main)
        honored = set(re.findall(r"os\.environ\.get\(\"(TAUSIK_SKIP_[A-Z_]+)\"\)", main_src))
        assert doc_flags, "docstring names no skip flags"
        assert honored, "main() honors no skip flags"
        assert doc_flags == honored, (
            f"docstring/code skip-flag drift: docstring={doc_flags} honored={honored}"
        )

    def test_both_flags_present(self):
        mod = self._module()
        honored = set(
            re.findall(
                r"os\.environ\.get\(\"(TAUSIK_SKIP_[A-Z_]+)\"\)",
                inspect.getsource(mod.main),
            )
        )
        assert honored == {"TAUSIK_SKIP_HOOKS", "TAUSIK_SKIP_MEMORY_HOOK"}
