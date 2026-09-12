"""Where the retired Notion mirror sits on disk.

The Notion transport left the framework with decision #358, but the local
SQLite mirror it maintained — `~/.tausik-brain/brain.db` — may still hold
records that exist nowhere else. `tausik knowledge import-brain` walks that file
into the shared store, and this is the only question it still needs answered:
where the file is. The old `brain.local_mirror_path` config key is honoured so
an operator who relocated the mirror does not lose it to the migration.
"""

from __future__ import annotations

import os
from typing import Any

DEFAULT_MIRROR_PATH = "~/.tausik-brain/brain.db"


def get_brain_mirror_path(cfg: dict[str, Any] | None = None) -> str:
    """Absolute path to the local mirror, from `brain.local_mirror_path` or the default."""
    if cfg is None:
        from project_config import load_config

        cfg = load_config()
    brain = cfg.get("brain") if isinstance(cfg, dict) else None
    raw = (brain or {}).get("local_mirror_path") if isinstance(brain, dict) else None
    if not isinstance(raw, str) or not raw.strip():
        raw = DEFAULT_MIRROR_PATH
    return os.path.abspath(os.path.expandvars(os.path.expanduser(raw)))
