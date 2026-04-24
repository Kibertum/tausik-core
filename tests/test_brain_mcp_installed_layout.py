"""Regression tests for tausik-brain MCP path resolution in installed layout.

Background
----------
Commit b5f6281 shipped agents/{claude,cursor}/mcp/brain/server.py and
handlers.py with 4-segment `..` path arithmetic that only resolves
scripts/ correctly in the source-tree layout (agents/claude/mcp/brain/ →
repo root). In the installed layout (.claude/mcp/brain/) four `..` jumps
to the parent of the project — scripts/ is not found and handlers.py
fails at `import brain_config` with ModuleNotFoundError. The MCP server
then refuses to start. The existing test suite passed because it exec'd
handlers.py from the source tree, where the wrong arithmetic happens to
coincide with reality.

The fix copies the convention used by agents/claude/mcp/project/server.py:17
which is 2-segment `..` (.claude/mcp/project/ → .claude/scripts/).

These tests exercise a simulated installed layout in tmp_path and import
handlers.py in a clean subprocess (PYTHONPATH wiped) so the source-tree
scripts/ cannot mask the bug.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BRAIN_SRCS = {
    "claude": REPO_ROOT / "agents" / "claude" / "mcp" / "brain",
    "cursor": REPO_ROOT / "agents" / "cursor" / "mcp" / "brain",
}

# Minimal stubs that satisfy handlers.py's module-level imports.
_STUBS: dict[str, str] = {
    "brain_config.py": (
        "def load_brain():\n"
        "    return {'enabled': False}\n"
        "def get_brain_mirror_path():\n"
        "    return ''\n"
    ),
    "brain_mcp_read.py": (
        "def search_with_fallback(*a, **k):\n"
        "    return {'results': [], 'warnings': []}\n"
        "def format_search_results(*a, **k):\n"
        "    return ''\n"
        "def get_with_fallback(*a, **k):\n"
        "    return None, []\n"
        "def format_record(*a, **k):\n"
        "    return ''\n"
    ),
    "brain_mcp_write.py": (
        "def store_record(*a, **k):\n"
        "    return {}\n"
        "def format_store_result(*a, **k):\n"
        "    return ''\n"
    ),
    "brain_notion_client.py": (
        "class NotionClient:\n    def __init__(self, *a, **k):\n        pass\n"
    ),
    "brain_sync.py": (
        "import sqlite3\n"
        "def open_brain_db(*a, **k):\n"
        "    return sqlite3.connect(':memory:')\n"
    ),
    "brain_runtime.py": (
        "def open_brain_deps():\n    return None, None, {'enabled': False}\n"
    ),
}


def _make_installed_layout(
    root: Path, brain_src: Path, with_scripts: bool = True
) -> Path:
    """Build root/.claude/mcp/brain/ (+ optional root/.claude/scripts/). Return handlers.py path."""
    mcp_brain = root / ".claude" / "mcp" / "brain"
    mcp_brain.mkdir(parents=True)
    for fname in ("handlers.py", "server.py", "tools.py"):
        shutil.copy(brain_src / fname, mcp_brain / fname)
    if with_scripts:
        scripts = root / ".claude" / "scripts"
        scripts.mkdir(parents=True)
        for fname, content in _STUBS.items():
            (scripts / fname).write_text(content, encoding="utf-8")
    return mcp_brain / "handlers.py"


def _run_import(handlers_path: Path, tail: str = "") -> subprocess.CompletedProcess:
    """Import handlers.py under a unique module name in a clean subprocess."""
    script = (
        textwrap.dedent(
            f"""
            import importlib.util, sys
            spec = importlib.util.spec_from_file_location(
                'brain_handlers_under_test', r'{handlers_path}'
            )
            mod = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(mod)
            except ModuleNotFoundError as e:
                sys.stderr.write('IMPORT_FAILED: ' + str(e) + '\\n')
                sys.exit(42)
            """
        ).strip()
        + "\n"
        + tail
    )
    env = {**os.environ, "PYTHONPATH": ""}
    return subprocess.run(
        [sys.executable, "-c", script],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


@pytest.mark.parametrize("variant", ["claude", "cursor"])
def test_handlers_resolves_scripts_dir_in_installed_layout(tmp_path, variant):
    """handlers.py._SCRIPTS_DIR must resolve to <root>/.claude/scripts/ when it
    lives at <root>/.claude/mcp/brain/handlers.py."""
    handlers_path = _make_installed_layout(tmp_path, BRAIN_SRCS[variant])
    r = _run_import(handlers_path, tail="print('SCRIPTS=' + mod._SCRIPTS_DIR)")
    assert r.returncode == 0, (
        f"handlers.py import failed in installed layout ({variant}).\n"
        f"STDOUT: {r.stdout}\nSTDERR: {r.stderr}"
    )
    marker = "SCRIPTS="
    assert marker in r.stdout, r.stdout
    resolved = r.stdout.split(marker, 1)[1].strip().splitlines()[0]
    expected = tmp_path / ".claude" / "scripts"
    assert os.path.normpath(resolved) == os.path.normpath(str(expected)), (
        f"Expected _SCRIPTS_DIR={expected}, got {resolved}"
    )


@pytest.mark.parametrize("variant", ["claude", "cursor"])
def test_handlers_emits_stderr_diag_when_scripts_missing(tmp_path, variant):
    """When .claude/scripts/ does not exist, handlers.py must emit a stderr
    diagnostic ('[tausik-brain] scripts dir missing: ...') instead of silently
    inserting a bad path into sys.path."""
    handlers_path = _make_installed_layout(
        tmp_path, BRAIN_SRCS[variant], with_scripts=False
    )
    r = _run_import(handlers_path)
    # Import will fail (no stubs, brain_config missing), but BEFORE the import
    # attempt, handlers.py must print a diagnostic.
    assert "tausik-brain" in r.stderr and "scripts dir missing" in r.stderr, (
        f"Expected '[tausik-brain] scripts dir missing' diagnostic in stderr.\n"
        f"STDERR: {r.stderr}"
    )


@pytest.mark.parametrize("variant", ["claude", "cursor"])
def test_server_call_tool_logs_traceback(variant):
    """server.py call_tool exception branch must log the full traceback to
    stderr before returning the error TextContent. Currently only the repr of
    the exception leaks through, making MCP-side debugging blind."""
    src = (BRAIN_SRCS[variant] / "server.py").read_text(encoding="utf-8")
    assert "traceback" in src, (
        f"{variant}/server.py should import/reference traceback for call_tool diagnostics"
    )
    assert "format_exc()" in src or "logging.exception" in src, (
        f"{variant}/server.py call_tool exception branch must emit a full traceback "
        "via traceback.format_exc() or logging.exception"
    )
