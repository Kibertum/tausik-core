"""The root of the project a gate is verifying — found from its `.tausik/`, not from `__file__`.

Gates used to walk up from their own file to the nearest `.git`. From the deployed copy
(`<project>/<ide profile>/scripts/`) that lands on the project, which is why it looked right.
Run from the framework's own tree — a submodule CLI, a sandbox, a global install — it
lands on the FRAMEWORK: `test_dedupe` measured the framework's tests inside a consumer's
close, and `ruff_format` refused a sandbox on another drive with "path is on mount 'C:',
start on mount 'D:'" (found by `tausik demo`).

The project is where its `.tausik/` is. The walk to `.git` starts there; a project with
no git is its own root. Only when no `.tausik/` exists at all does the old walk apply.
"""

from __future__ import annotations

import os


def _git_root_from(start: str) -> str | None:
    d = start
    for _ in range(12):
        if os.path.exists(os.path.join(d, ".git")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent
    return None


def project_root() -> str | None:
    """The verified project's root, or None when no `.tausik/` can be found."""
    try:
        from project_config import find_tausik_dir

        tausik_dir = find_tausik_dir()
    except Exception:  # noqa: BLE001 — no resolvable project: the caller keeps its old walk
        return None
    if not os.path.isdir(tausik_dir):
        return None
    start = os.path.dirname(os.path.abspath(tausik_dir))
    return _git_root_from(start) or start
