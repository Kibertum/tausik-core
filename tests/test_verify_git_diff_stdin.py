"""Regression test for v14b-defect-mcp-task-done-stdin-hang.

Asserts that scripts/verify_git_diff.py invokes git with stdin=subprocess.DEVNULL.

Why: when the verify_git_diff probe runs inside the MCP project server's
asyncio.to_thread worker, the subprocess.run children inherit stdin from the
parent — which is the JSON-RPC pipe to the IDE. On Windows, git can block
reading that stdin (paginator probe / credential prompt detection / generic
stdin handling) until the subprocess.run timeout fires (10s). Without
stdin=DEVNULL the previous behavior was: every MCP `task_done` invocation
spent ~10s in the cache lookup path, then defensively returned cache=hit via
the except branch, masking the hang as a successful-but-slow result.

Empirical measurement during root-cause investigation: 10031ms → 63ms (159×).
"""

from __future__ import annotations

import os
import subprocess
import sys
from unittest.mock import MagicMock

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)


def test_changed_files_since_passes_stdin_devnull(tmp_path):
    """Both git log and git diff calls must include stdin=subprocess.DEVNULL."""
    from verify_git_diff import changed_files_since

    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    runner = MagicMock(
        return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    )
    changed_files_since("2026-01-01T00:00:00Z", root=str(tmp_path), runner=runner)

    assert runner.call_count == 2
    for call in runner.call_args_list:
        kwargs = call.kwargs
        assert kwargs.get("stdin") is subprocess.DEVNULL, (
            f"git subprocess called without stdin=DEVNULL — "
            f"kwargs={kwargs!r}. Re-introduces v14b-defect-mcp-task-done-stdin-hang."
        )
