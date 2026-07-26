"""ProjectService factory — the ONE edge from config to the DB layer.

Extracted from ``project_config`` (project-config-god-module-split) so importing
the config loader no longer drags ``project_backend`` + ``project_service`` (the
whole SQLite + service layer) at import time. That import-time edge was the blocker
for a standalone config loader (v2-engine-standalone-package): code that only reads
``.tausik/config.json`` must not require the database layer to import. ``get_service``
and the two DB imports live HERE now, not in ``project_config``; ``project_config``
imports nothing from the DB layer.
"""

from __future__ import annotations

from project_backend import SQLiteBackend
from project_config import get_db_path
from project_service import ProjectService


def get_service() -> ProjectService:
    """Create ProjectService with SQLite backend."""
    db_path = get_db_path()
    be = SQLiteBackend(db_path)
    return ProjectService(be)
