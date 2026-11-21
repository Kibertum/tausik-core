"""Honesty for configured ``testing.roots`` vs pytest in ``.tausik/venv``.

TB-005: when a project declares test roots, the TAUSIK venv must be able to
import pytest, or doctor/verify must report the roots unrunnable. Falling back
to a system pytest without naming the gap treats configured roots as executed
under a runner the project never provisioned.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable, Sequence
from typing import Any

from tausik_utils import tausik_config_path

Runner = Callable[..., Any]


def declared_testing_roots(base: str) -> list[str] | None:
    """Return ``testing.roots`` when the key is present as a list; else None."""
    path = tausik_config_path(base)
    try:
        with open(path, encoding="utf-8") as fh:
            cfg = json.load(fh)
    except (OSError, ValueError):
        return None
    testing = cfg.get("testing")
    if not isinstance(testing, dict) or "roots" not in testing:
        return None
    roots = testing["roots"]
    if not isinstance(roots, list):
        return None
    return [str(r) for r in roots if isinstance(r, (str, os.PathLike)) and str(r).strip()]


def tausik_venv_python(base: str) -> str | None:
    """Absolute path to ``.tausik/venv`` python, or None when missing."""
    tausik_dir = os.path.join(base, ".tausik")
    if sys.platform == "win32":
        candidates: Sequence[str] = (os.path.join(tausik_dir, "venv", "Scripts", "python.exe"),)
    else:
        candidates = (
            os.path.join(tausik_dir, "venv", "bin", "python3"),
            os.path.join(tausik_dir, "venv", "bin", "python"),
        )
    return next((path for path in candidates if os.path.isfile(path)), None)


def venv_can_import_pytest(python: str, *, runner: Runner = subprocess.run) -> bool:
    """True when *python* imports pytest without error."""
    try:
        proc = runner(
            [python, "-c", "import pytest"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return int(getattr(proc, "returncode", 1) or 0) == 0


def missing_venv_pytest_refusal(
    base: str | None = None, *, runner: Runner = subprocess.run
) -> str | None:
    """Refusal when configured roots exist but ``.tausik/venv`` lacks pytest.

    Returns None when roots are not configured, when no configured path exists
    on disk (NoTestRoots / uncertainty owns that), or when the venv has pytest.
    """
    root = base or os.getcwd()
    roots = declared_testing_roots(root)
    if not roots:
        return None
    existing = [rel for rel in roots if os.path.isdir(os.path.join(root, rel))]
    if not existing:
        return None
    python = tausik_venv_python(root)
    if python is None:
        return (
            "Configured testing.roots are unrunnable: .tausik/venv Python is missing. "
            "Run bootstrap, then install pytest into the TAUSIK venv. "
            "Configured roots must not be treated as executed without that runner."
        )
    if venv_can_import_pytest(python, runner=runner):
        return None
    return (
        f"Configured testing.roots are unrunnable: {python} cannot import pytest. "
        f"Install with: {python} -m pip install pytest. "
        "Never treat configured roots as executed while the TAUSIK venv runner is absent."
    )


def doctor_venv_pytest_check(
    project_dir: str, *, runner: Runner = subprocess.run
) -> tuple[str, str, str] | None:
    """Doctor row for venv pytest when roots are configured.

    Returns ``(level, label, detail)`` with level in ``ok|fail``, or None when
    the check does not apply (no configured roots / no existing root dirs).
    """
    refusal = missing_venv_pytest_refusal(project_dir, runner=runner)
    if refusal is None:
        roots = declared_testing_roots(project_dir)
        if not roots:
            return None
        existing = [rel for rel in roots if os.path.isdir(os.path.join(project_dir, rel))]
        if not existing:
            return None
        return ("ok", "Venv pytest", "importable in .tausik/venv for configured testing.roots")
    return ("fail", "Venv pytest", refusal)
