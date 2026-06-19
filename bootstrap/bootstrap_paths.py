"""Rename-proof path helper for bootstrap generators.

Generated IDE configs (MCP server paths, ``--project`` args, hook commands)
historically embedded ABSOLUTE paths, so renaming the project folder broke
them. ``portable_path`` rewrites a path that lives *inside* the project as a
workspace-variable-relative path the IDE expands at launch:

- Claude Code ``.mcp.json``: ``${CLAUDE_PROJECT_DIR:-.}`` (var is absent at
  config-parse time, so the ``:-.`` fallback is required).
- Claude Code hooks (``settings.json``): ``${CLAUDE_PROJECT_DIR}`` (always set
  in the hook environment).
- Cursor / Kilo (VS Code family): ``${workspaceFolder}``.

Paths *outside* the project (an external lib, a system venv) are kept absolute —
a project rename does not move them.
"""

from __future__ import annotations

import os


def _fwd(path: str) -> str:
    """Forward-slash a path for JSON portability (Windows-safe)."""
    return path.replace("\\", "/")


def portable_path(abs_path: str, project_dir: str, workspace_var: str) -> str:
    """Return ``workspace_var/<relpath>`` if abs_path is inside project_dir.

    Otherwise return the absolute, forward-slashed path unchanged. Never raises:
    a cross-drive path (relpath ValueError on Windows) falls back to absolute.
    """
    abs_norm = os.path.normpath(abs_path)
    proj_norm = os.path.normpath(project_dir)
    try:
        rel = os.path.relpath(abs_norm, proj_norm)
    except ValueError:
        # Different drive (Windows) → not inside the project.
        return _fwd(abs_norm)
    if rel == os.pardir or rel.startswith(os.pardir + os.sep) or os.path.isabs(rel):
        return _fwd(abs_norm)  # outside the project tree
    return workspace_var + "/" + _fwd(rel)
