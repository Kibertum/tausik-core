"""`scripts/project_cli*.py` are libraries. Running one must fail loudly.

Before this guard, `python .claude/scripts/project_cli.py skill sign <dir>`
defined the handlers, called none of them, printed nothing and exited 0. The
signature was never written and nothing said so.
"""

from __future__ import annotations

import glob
import os
import subprocess
import sys

import pytest

_SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "scripts")

# The real entry point. It must keep working.
_ENTRYPOINT = "project.py"


def _library_modules() -> list[str]:
    paths = sorted(glob.glob(os.path.join(_SCRIPTS, "project_cli*.py")))
    assert paths, "no project_cli*.py modules found — did the layout move?"
    return paths


def _run(path: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, path, *args],
        capture_output=True,
        text=True,
        timeout=60,
        stdin=subprocess.DEVNULL,
    )


@pytest.mark.parametrize("path", _library_modules(), ids=os.path.basename)
def test_direct_run_is_refused(path):
    """Every handler module, not just the one someone tripped over."""
    result = _run(path, "skill", "sign", "somewhere")
    assert result.returncode != 0, (
        f"{os.path.basename(path)} exits 0 when run directly — silence reads as success"
    )
    assert result.returncode == 2
    assert "not an entry point" in result.stderr
    assert ".tausik/tausik" in result.stderr
    assert result.stdout == ""


@pytest.mark.parametrize("path", _library_modules(), ids=os.path.basename)
def test_module_still_imports(path):
    """The guard must fire on __main__ only, never on import."""
    name = os.path.splitext(os.path.basename(path))[0]
    result = subprocess.run(
        [sys.executable, "-c", f"import sys; sys.path.insert(0, {_SCRIPTS!r}); import {name}"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr


def test_entrypoint_is_not_guarded():
    """project.py IS the entry point — it must not refuse to run."""
    result = _run(os.path.join(_SCRIPTS, _ENTRYPOINT), "--help")
    assert result.returncode == 0
    assert "not an entry point" not in result.stderr


def test_refusal_names_the_module():
    result = _run(os.path.join(_SCRIPTS, "project_cli_skill.py"))
    assert "project_cli_skill.py" in result.stderr
