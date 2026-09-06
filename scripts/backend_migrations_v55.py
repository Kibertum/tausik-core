"""v55 migration SQL -- at_results (at-red-with-tc-green-routes-to-interpretation-not-code).

Held in its own module to keep backend_migrations.py under the filesize gate.
Purely additive -- a brand-new table plus its index, no ALTER on any existing
table. Unlike v53 (actz_points.tz_ref), this needs NO guarded postseed step:
a new table's CREATE+INDEX pair is safe within the unconditional fresh-DDL
block on every path (fresh, upgrade, or table-does-not-exist-yet) precisely
because nothing existing could already be shaped without it.
"""

from __future__ import annotations

MIGRATION_V55: list[str] = [
    """CREATE TABLE IF NOT EXISTS at_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        at_slug TEXT NOT NULL REFERENCES ats(slug) ON DELETE CASCADE,
        outcome TEXT NOT NULL CHECK(outcome IN ('red', 'green')),
        note TEXT,
        recorded_at TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_at_results_slug ON at_results(at_slug, recorded_at)",
]
