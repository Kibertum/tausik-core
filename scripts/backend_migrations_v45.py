"""v45 migration SQL — the trace a redaction leaves behind
(nothing-can-redact-the-memory-the-framework-publishes, decision #258).

Held in its own module to keep backend_migrations.py under the filesize gate.
``MIGRATION_V45`` is the ordered statement list referenced by
backend_migrations._CURRENT_MIGRATIONS[45]. Purely additive: one new table, no
column touched, no rebuild.

Why a table and not a column: the thing being recorded is an EVENT ("this field
was overwritten, for this reason, at this instant"), and one field can be
redacted more than once for different reasons over its life. A column would keep
only the last one and would silently overwrite the very history it exists to
preserve — the defect this feature was built to prevent, reproduced in its own
storage.

Rows are NEVER deleted and the table has no update path. It is the only reason
an append-only journal stays worth believing once rewriting it became possible:
the row changed, and here is who said so and why. A redaction whose trace can be
removed is indistinguishable from a silent rewrite.

`label` carries the CLASS of the removed thing and never its value. A trace
quoting the secret would put the leak straight back into the database it was
removed from, in a column nobody thinks to scan.
"""

from __future__ import annotations

MIGRATION_V45: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS redactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_type TEXT NOT NULL,
        entity_id INTEGER NOT NULL,
        field TEXT NOT NULL,
        label TEXT NOT NULL,
        reason TEXT NOT NULL,
        occurrences INTEGER NOT NULL,
        redacted_at TEXT NOT NULL
    )
    """,
    # The audit question this table makes answerable is "what has been struck
    # out of this project, and when" — a scan ordered by time, and a point
    # lookup for "was this row ever redacted?" when a reader meets a marker.
    "CREATE INDEX IF NOT EXISTS idx_redactions_at ON redactions(redacted_at)",
    "CREATE INDEX IF NOT EXISTS idx_redactions_entity ON redactions(entity_type, entity_id)",
]
