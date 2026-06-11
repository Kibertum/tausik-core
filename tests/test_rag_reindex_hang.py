"""v15p-fix-rag-reindex-hang: reindex must never hang.

Root cause (reproduced on win32): subprocess.run(git diff, capture_output=True,
timeout=3) blocks FOREVER when git spawns a long-lived grandchild that
inherits the stdout pipe (fsmonitor--daemon, credential helper, git.exe shim).
On TimeoutExpired CPython kills the direct child, then calls communicate()
a second time WITHOUT a timeout — the pipe never EOFs, so the call never
returns. Fix: rag_indexer._run_git manages Popen manually and never issues
the second blocking read; index_full gets a bounded default budget; the MCP
server wraps every tool call in a hard asyncio.wait_for envelope.
"""

from __future__ import annotations

import inspect
import os
import sys
import textwrap
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RAG_DIR = ROOT / "harness" / "claude" / "mcp" / "codebase-rag"
if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))


# --- _run_git: the communicate-after-kill hang -----------------------------


def _write_fake_git(tmp_path: Path) -> Path:
    """Fake git: exits immediately but leaves a grandchild holding stdout.

    Mirrors git fsmonitor--daemon behavior — the direct child is gone, yet
    the stdout pipe never reaches EOF until the grandchild dies.
    """
    script = tmp_path / "fake_git.py"
    script.write_text(
        textwrap.dedent(
            """
            import subprocess, sys
            subprocess.Popen(
                [sys.executable, "-c", "import time; time.sleep(8)"],
                stdout=sys.stdout,
                stderr=subprocess.DEVNULL,
            )
            # parent exits immediately, grandchild keeps the pipe open
            """
        ),
        encoding="utf-8",
    )
    return script


def test_run_git_survives_pipe_holding_grandchild(tmp_path):
    """_run_git must return None within ~timeout, not hang forever."""
    from rag_indexer import _run_git

    script = _write_fake_git(tmp_path)
    t0 = time.monotonic()
    out = _run_git([sys.executable, str(script)], cwd=str(tmp_path), timeout_sec=2)
    elapsed = time.monotonic() - t0
    assert out is None
    assert elapsed < 7, f"_run_git took {elapsed:.1f}s — hang not fixed"


def test_run_git_returns_stdout_on_success(tmp_path):
    from rag_indexer import _run_git

    out = _run_git([sys.executable, "-c", "print('M\\tfoo.py')"], cwd=str(tmp_path))
    assert out is not None
    assert "foo.py" in out


def test_run_git_returns_none_on_nonzero_exit(tmp_path):
    from rag_indexer import _run_git

    out = _run_git([sys.executable, "-c", "import sys; sys.exit(1)"], cwd=str(tmp_path))
    assert out is None


def test_run_git_returns_none_on_missing_binary(tmp_path):
    from rag_indexer import _run_git

    out = _run_git(["definitely-not-a-real-binary-xyz"], cwd=str(tmp_path))
    assert out is None


def test_get_changed_files_no_subprocess_run():
    """The unsafe subprocess.run(timeout=) pattern must not come back."""
    import rag_indexer

    src = inspect.getsource(rag_indexer._get_changed_files)
    assert "subprocess.run" not in src
    assert "_run_git" in src


def test_get_changed_files_parses_diff_output(monkeypatch, tmp_path):
    import rag_indexer

    monkeypatch.setattr(
        rag_indexer,
        "_run_git",
        lambda argv, cwd, timeout_sec=5: "M\ta.py\nD\tb.py\nA\tc.py\n",
    )
    modified, deleted = rag_indexer._get_changed_files(str(tmp_path), "abc")
    assert modified == ["a.py", "c.py"]
    assert deleted == ["b.py"]


def test_get_changed_files_timeout_degrades_to_empty(monkeypatch, tmp_path):
    import rag_indexer

    monkeypatch.setattr(rag_indexer, "_run_git", lambda argv, cwd, timeout_sec=5: None)
    assert rag_indexer._get_changed_files(str(tmp_path), "abc") == ([], [])


# --- index_full: bounded by default ----------------------------------------


def test_index_full_default_budget_is_bounded():
    from rag_indexer import DEFAULT_MAX_SECONDS, index_full

    sig = inspect.signature(index_full)
    assert sig.parameters["max_seconds"].default == DEFAULT_MAX_SECONDS
    assert DEFAULT_MAX_SECONDS is not None
    assert 0 < DEFAULT_MAX_SECONDS <= 600


# --- get_file_list: deadline + cycle protection -----------------------------


def test_get_file_list_respects_deadline(tmp_path):
    from rag_detect import get_file_list

    for i in range(20):
        (tmp_path / f"f{i}.py").write_text("x = 1\n")
    t0 = time.monotonic()
    files = get_file_list(str(tmp_path), max_seconds=0)
    assert time.monotonic() - t0 < 5
    assert files == []  # deadline already expired before the walk


def test_get_file_list_unbounded_by_default(tmp_path):
    from rag_detect import get_file_list

    (tmp_path / "a.py").write_text("x = 1\n")
    files = get_file_list(str(tmp_path))
    assert [f["rel_path"] for f in files] == ["a.py"]


@pytest.mark.skipif(os.name != "nt", reason="junctions are Windows-only")
def test_get_file_list_skips_junction_cycle(tmp_path):
    """A junction cycle must not multiply indexed files (was 64x)."""
    import _winapi

    from rag_detect import get_file_list

    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text("def f():\n    return 1\n")
    _winapi.CreateJunction(str(tmp_path), str(src / "loop"))

    files = get_file_list(str(tmp_path))
    assert [f["rel_path"] for f in files] == ["src/a.py"]


# --- server: hard timeout envelope ------------------------------------------


def test_tool_timeout_envelope_exceeds_soft_budget():
    import server
    from rag_indexer import DEFAULT_MAX_SECONDS

    assert server._REINDEX_SOFT_DEFAULT_SEC == DEFAULT_MAX_SECONDS
    assert server._tool_timeout_sec("reindex", {}) > DEFAULT_MAX_SECONDS
    assert server._tool_timeout_sec("reindex", {"max_seconds": 30}) == 90.0
    assert server._tool_timeout_sec("search_code", {}) == server.TOOL_TIMEOUT_DEFAULT_SEC


def test_call_tool_wrapped_in_wait_for():
    """server.call_tool must keep the asyncio.wait_for hard envelope."""
    import server

    src = inspect.getsource(server.main)
    assert "asyncio.wait_for" in src
    assert "_tool_timeout_sec" in src
