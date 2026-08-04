"""Repo-wide mypy ZERO check (mypy-ten-preexisting-errors-nobody-owns).

The framework teaches proving a fact over a form, yet closure evidence had for
two releases carried the formula "mypy N errors — all pre-existing, count did not
grow". A "did not grow" threshold is not a threshold: it passes the first time a
new error happens to cancel a fixed one, and it lets a pre-existing error sit in a
file no task touches (the mypy gate scopes to the task's files). Those ten errors
are now fixed — `mypy scripts/` is clean — and this pins that state as a NUMBER
(zero), enforced, rather than a dynamic nobody re-measures.

Deliberately NOT marked slow: a zero-check that only runs in an opt-in slow lane
is a dynamic nobody re-measures — the exact failure mode this task closes. It is
a ~3-4s subprocess (negligible in the default full run) and it must run there so
a re-introduced type error is caught immediately, not at some later full pass.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]


def _mypy_available() -> bool:
    if shutil.which("mypy"):
        return True
    try:
        import mypy  # noqa: F401

        return True
    except ImportError:
        return False


@pytest.mark.skipif(not _mypy_available(), reason="mypy not installed in this environment")
def test_declared_tree_is_mypy_clean():
    """The declared tree must type-check with ZERO errors — not "no new errors".

    A pre-existing error in an untouched module is invisible to the per-task
    mypy gate (it only checks the task's files); this repo-wide run is what
    makes the zero real.

    Invoked with NO path argument on purpose, so the scope is whatever
    `[tool.mypy] files` declares and there is exactly one place to widen it.
    This test used to pass `scripts/` explicitly, which made the config's scope
    and the test's scope two separate lists — so adding the MCP package to the
    config would have left it unenforced here, silently.
    """
    proc = subprocess.run(
        [sys.executable, "-m", "mypy"],
        cwd=str(_REPO),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, (
        "mypy found type errors in the declared tree — it is no longer clean.\n"
        "Fix the error at the type level (a per-module ignore is for a STRUCTURAL\n"
        "reason that carries a written justification, not for silencing a bug):\n"
        f"{proc.stdout}\n{proc.stderr}"
    )


def test_declared_scope_covers_the_agent_facing_mcp_package():
    """The MCP package must stay in scope — it is the surface the agent uses.

    `scripts/` was the whole scope for two releases while `harness/` — which
    CLAUDE.md tells the agent to prefer over the CLI — was never type-checked at
    all. Narrowing the scope back would be a silent regression, so it is pinned.
    """
    config = (_REPO / "pyproject.toml").read_text(encoding="utf-8")
    assert '"harness/claude/mcp/project"' in config, (
        "the MCP project package dropped out of [tool.mypy] files — the code the "
        "agent talks to would stop being type-checked"
    )
