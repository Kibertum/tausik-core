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
def test_scripts_tree_is_mypy_clean():
    """`scripts/` must type-check with ZERO errors — not "no new errors".

    A pre-existing error in an untouched module is invisible to the per-task
    mypy gate (it only checks the task's files); this repo-wide run is what
    makes the zero real.
    """
    proc = subprocess.run(
        [sys.executable, "-m", "mypy", "scripts/"],
        cwd=str(_REPO),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, (
        "mypy found type errors in scripts/ — the tree is no longer clean.\n"
        "Fix the error (do NOT add a per-module ignore; the bar is zero):\n"
        f"{proc.stdout}\n{proc.stderr}"
    )
