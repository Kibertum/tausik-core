"""Resolve the project ROOT from a service handle — never from the cwd.

Convention (memory #265, defect `mcp-config-read-paths`): a component that
already holds a project handle must read that project's state through the
handle. Resolving from `os.getcwd()` instead makes the answer depend on which
directory the process happens to stand in — which is how `tausik verify` run
from a subdirectory signed against a directory with no key, and how a gate
would inspect whatever repo the MCP server was launched in.

The rule was spelled privately in four places (`gate_changelog`,
`project_cli_verify`, `project_cli_receipt`, `verify_run_record`), each with
its own fallback. One spelling, one fallback: a service exposing no project
directory yields `None`, and the caller decides — a gate fails closed, a
presentation path may degrade to the cwd. The choice belongs to the caller,
so this module never picks silently.
"""

from __future__ import annotations

import os
from typing import Any


def root_from_service(svc: Any) -> str | None:
    """Project root for *svc*, or None when it exposes no project directory.

    `ProjectService.tausik_dir()` returns `<root>/.tausik`; one `dirname` is
    the root. Returns None (rather than the cwd) when the attribute is absent,
    not callable, or raises — "unknown" is a distinct answer from "here", and
    conflating them is the defect this module exists to prevent.
    """
    td = getattr(svc, "tausik_dir", None)
    if not callable(td):
        return None
    try:
        resolved = td()
    except Exception:  # noqa: BLE001 — an unresolvable project is "unknown", not "here"
        return None
    if not resolved:
        return None
    return os.path.dirname(os.path.abspath(str(resolved)))
