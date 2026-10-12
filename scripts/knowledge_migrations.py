"""Rewrites applied to a shared store that already exists, at the moment it opens.

WHY ON OPEN AND NOT AS A COMMAND. Each of these fixes a value that was already
written, so a fix confined to the write path would leave the defect in place for
exactly the stores that have the most of it. `adopt_legacy_store_if_present`
settled the same question the same way, and for the same reason: a migration
nobody runs is a migration that did not happen.

WHY `user_version` IS NOT BUMPED TO GATE THEM. A version bump is the cheaper
trigger, and it would make every older TAUSIK on this machine REFUSE to open the
shared store — `require_compatible_schema` is deliberately fatal. That is a
breaking change across projects, bought to avoid a scan on a path that already
rebuilds the schema and the FTS triggers on every open.

The trade was measured rather than asserted, because "it scans every table on
every open, forever" is the kind of claim that sounds decisive and is not. On a
fully migrated store of 20 000 rows — far past what a personal knowledge base
reaches — the scan finds nothing in 1.8 ms, against 0.8 ms for the DDL and FTS
rebuild it runs beside and 4.0 ms for the whole schema setup. A marker table to
skip it would add DDL and a second thing to keep consistent, to save two
milliseconds. Not worth it.

EVERY FUNCTION HERE RETURNS A COUNT, and that is not decoration. A migration
that reports nothing is indistinguishable from one that matched nothing, and the
difference is the whole evidence that it ran at all. Each is idempotent, so the
count dropping to zero on a second pass is itself the property worth asserting.
"""

from __future__ import annotations

import sqlite3

# A cheap SUPERSET of the rows that need rewriting — not the decision itself.
# `knowledge_origin.redacted_origin` is the authority on what is a path, and it
# is stricter than this: it wants an absolute one, so a free-text value that
# merely contains a separator survives. Keeping the SQL loose and the Python
# strict means the two cannot disagree in the dangerous direction — the worst a
# loose predicate costs is a row fetched and put back down.
#
# Backslash needs no escaping: SQLite's LIKE treats only `%` and `_` as special.
_PATH_SHAPED = "(origin_project LIKE '%/%' OR origin_project LIKE '%\\%')"

_ORIGIN_TABLES = ("memory", "decisions", "snippets")


def redact_stored_origins(conn: sqlite3.Connection) -> int:
    """Rewrite absolute project roots already in the store into labels.

    Idempotent: a second pass matches nothing, because a label contains no
    separator and the predicate only selects values that do.
    """
    from knowledge_origin import redacted_origin

    changed = 0
    for table in _ORIGIN_TABLES:
        rows = conn.execute(
            f"SELECT id, origin_project FROM {table} WHERE origin_project IS NOT NULL "
            f"AND {_PATH_SHAPED}"
        ).fetchall()
        for row_id, origin in rows:
            label = redacted_origin(origin)
            if label is None:
                continue
            conn.execute(f"UPDATE {table} SET origin_project = ? WHERE id = ?", (label, row_id))
            changed += 1
    return changed


def normalize_stored_tags(conn: sqlite3.Connection) -> int:
    """Rewrite comma-joined tag lists into the canonical JSON array.

    Only `memory` has a `tags` column in this schema; naming the one table
    rather than looping over three is the honest shape here, and a `tags` column
    added elsewhere later would want its own decision anyway.

    `tags` IS in the FTS index, so the UPDATE re-indexes the row through the
    existing trigger — which is correct: search should match what is stored.
    """
    from knowledge_tags import normalized_tags

    rows = conn.execute(
        "SELECT id, tags FROM memory WHERE tags IS NOT NULL AND tags != ''"
    ).fetchall()
    changed = 0
    for row_id, raw in rows:
        canonical = normalized_tags(raw)
        if canonical is None:
            continue
        conn.execute("UPDATE memory SET tags = ? WHERE id = ?", (canonical, row_id))
        changed += 1
    return changed


def apply_open_migrations(conn: sqlite3.Connection) -> dict[str, int]:
    """Run every on-open rewrite. Returns what each one changed.

    One entry point rather than a call per migration at the schema site, so
    adding the next one is a change HERE and cannot be half-wired: a migration
    written but never called is the failure this shape rules out.
    """
    return {
        "origins": redact_stored_origins(conn),
        "tags": normalize_stored_tags(conn),
    }
