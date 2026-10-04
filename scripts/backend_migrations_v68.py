"""Migration v68: task assurance declarations."""

from __future__ import annotations

MIGRATION_V68: list[str] = [
    "ALTER TABLE tasks ADD COLUMN assurance_profiles TEXT",
    "ALTER TABLE tasks ADD COLUMN assurance_impact TEXT",
]
