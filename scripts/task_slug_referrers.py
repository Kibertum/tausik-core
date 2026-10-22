"""Discover columns that store a tasks.slug — derived from the live schema."""

from __future__ import annotations

from typing import Any


def task_slug_referrers(conn: Any) -> list[tuple[str, str]]:
    """Return (table, column) pairs that hold a task slug.

    Built from PRAGMA foreign_key_list (references tasks.slug) plus any
    `task_slug` column that has no FK (verification_runs, gate_runs, …).
    FTS shadow tables are excluded — they are rebuilt after the rename.
    """
    tables = [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    ]
    found: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for table in tables:
        if table.startswith("fts_"):
            continue
        for row in conn.execute(f"PRAGMA foreign_key_list({table})"):
            # row: id, seq, table, from, to, on_update, on_delete, match
            if row[2] == "tasks" and row[4] == "slug":
                pair = (table, row[3])
                if pair not in seen:
                    seen.add(pair)
                    found.append(pair)
        cols = {c[1] for c in conn.execute(f"PRAGMA table_info({table})")}
        if "task_slug" in cols:
            pair = (table, "task_slug")
            if pair not in seen:
                seen.add(pair)
                found.append(pair)
    return found
