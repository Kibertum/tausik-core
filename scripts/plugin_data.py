"""Plugin-data directory resolution for skills that need persistent storage.

Honours Claude Code's `CLAUDE_PLUGIN_DATA` convention so a plugin's state lives
outside its installation directory (survives reinstall, plugin-root reshuffles,
and respects the host's data-layout).

If the env var is unset or empty, falls back to `<project>/.tausik/plugin_data/`
so skills still work on projects bootstrapped with TAUSIK.
"""

from __future__ import annotations

import os


_FALLBACK_SUBDIR = os.path.join(".tausik", "plugin_data")


def get_plugin_data_dir(project_dir: str | None = None, *, create: bool = True) -> str:
    """Return an absolute path to the plugin-data directory.

    Resolution order:
    1. `CLAUDE_PLUGIN_DATA` env var (if set and non-empty)
    2. `<project_dir>/.tausik/plugin_data/`
    3. `<cwd>/.tausik/plugin_data/` when project_dir is None

    Args:
        project_dir: Optional project root; used only for the fallback.
        create: If True (default), ensures the directory exists before returning.
    """
    env_path = os.environ.get("CLAUDE_PLUGIN_DATA")
    if env_path and env_path.strip():
        path = os.path.abspath(env_path.strip())
    else:
        base = project_dir or os.getcwd()
        path = os.path.abspath(os.path.join(base, _FALLBACK_SUBDIR))

    if create:
        os.makedirs(path, exist_ok=True)
    return path
