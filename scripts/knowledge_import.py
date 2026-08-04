"""Bringing what accumulated in the wiki into the store that belongs to you.

WHY THIS RUNS ONCE. Years of decisions were mirrored to Notion by a classifier
that decided on their behalf; that mirroring is gone (decision #221), and what
it left behind is a local copy — `~/.tausik-brain/brain.db` — holding records
that exist nowhere else the framework can read. This walks that mirror into
`~/.tausik-knowledge/knowledge.db`, so the knowledge outlives the account it was
published under.

NO NETWORK. The mirror is already a local SQLite file, so the import neither
needs Notion nor is affected by it being unreachable, rate-limited or cancelled.
That is the whole reason it can be done now rather than "when we get around to
re-syncing".

IDEMPOTENT, BY IDENTITY. Each imported row gets an `entry_uuid` derived from the
Notion page id, so running the import twice imports nothing the second time. A
derived id rather than a fresh one, because a fresh one would make every rerun
look like new knowledge and quietly triple the store.

ORIGIN IS PRESERVED, NOT INVENTED. The mirror records which project a decision
came from as a hash — the wiki never held the name. A hash is not a path, so it
is written as `brain:<hash>` rather than dressed up as a directory that never
existed. Someone reading the shared store later can tell an imported record from
a locally written one, which is exactly what they need to know.
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from knowledge_db import connect_knowledge_db
from knowledge_tags import dump_tags, load_tags
from tausik_utils import ServiceError

# The mirror's tables, mapped to where their content belongs locally. Only
# these two carry knowledge a person wrote: `web_cache` is fetched material with
# no author, and importing it would pass someone else's article off as a note.
SOURCES: dict[str, str] = {
    "brain_decisions": "decisions",
    "brain_patterns": "memory",
    "brain_gotchas": "memory",
}

# Deterministic namespace, so the uuid for a given Notion page is the same on
# every machine and every rerun. Ad-hoc uuid4 would make re-import look new.
_NS = uuid.UUID("6f1c8d2e-9a4b-4f77-9c31-0f1a2b3c4d5e")


def _mirror_path() -> str:
    from brain_config import get_brain_mirror_path

    return get_brain_mirror_path()


def _entry_uuid(page_id: str) -> str:
    return str(uuid.uuid5(_NS, page_id))


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _origin(row: sqlite3.Row) -> str:
    """`brain:<hash>` — honest about what the wiki actually recorded.

    The mirror keeps a project HASH, never a name or a path. Bare, it would sit
    in `origin_project` next to values shaped `basename@fingerprint` and read as
    one of them — a project that never existed under a name nobody can check.
    The prefix says where it came from and that it is a mirror, not a directory
    on this machine.
    """
    keys = row.keys()
    h = (row["source_project_hash"] if "source_project_hash" in keys else "") or "unknown"
    return f"brain:{h}"


def _text(row: sqlite3.Row, *names: str) -> str:
    for name in names:
        if name in row.keys() and row[name]:
            return str(row[name])
    return ""


def import_from_brain_mirror(*, dry_run: bool = False) -> dict[str, int]:
    """Copy the local Notion mirror into the shared store. Returns per-kind counts.

    `dry_run` reports what WOULD be imported without writing, because a person
    about to fold thousands of rows into their knowledge base is entitled to
    look first.
    """
    mirror = _mirror_path()
    if not os.path.isfile(mirror):
        raise ServiceError(
            f"No brain mirror at {mirror} — there is nothing to import. Nothing was written."
        )

    src = sqlite3.connect(f"file:{mirror}?mode=ro", uri=True)
    src.row_factory = sqlite3.Row
    dest = None if dry_run else connect_knowledge_db(create=True)
    counts: dict[str, int] = {}
    try:
        for table, target in SOURCES.items():
            rows = _read(src, table)
            counts[table] = 0
            for row in rows:
                page_id = _text(row, "notion_page_id")
                if not page_id:
                    # No page id means no stable identity, and a random one would
                    # duplicate on the next run. Skipped and counted separately
                    # rather than silently dropped.
                    counts["skipped_no_page_id"] = counts.get("skipped_no_page_id", 0) + 1
                    continue
                if dry_run or dest is None:
                    counts[table] += 1
                    continue
                if _insert(dest, target, table, row, page_id):
                    counts[table] += 1
        if dest is not None:
            dest.commit()
    except sqlite3.Error as e:
        raise ServiceError(f"Import from {mirror} failed: {e}. Nothing was committed.") from e
    finally:
        src.close()
        if dest is not None:
            dest.close()
    return counts


def _read(src: sqlite3.Connection, table: str) -> list[sqlite3.Row]:
    try:
        return src.execute(f"SELECT * FROM {table}").fetchall()  # noqa: S608 — fixed names
    except sqlite3.Error:
        # A mirror written by an older brain may not have every table. Absent is
        # not an error: there is simply nothing of that kind to bring over.
        return []


def _insert(
    dest: sqlite3.Connection, target: str, table: str, row: sqlite3.Row, page_id: str
) -> bool:
    """Insert one record; return True only if a row was actually added."""
    created = _text(row, "created_at", "last_pull_at") or _now()
    if target == "decisions":
        cur = dest.execute(
            "INSERT INTO decisions (entry_uuid, decision, rationale, origin_project, "
            "origin_slug, created_at) VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(entry_uuid) DO NOTHING",
            (
                _entry_uuid(page_id),
                _text(row, "decision", "name") or "(no text)",
                _text(row, "rationale", "context"),
                _origin(row),
                None,
                created,
            ),
        )
    else:
        kind = "pattern" if table == "brain_patterns" else "gotcha"
        cur = dest.execute(
            "INSERT INTO memory (entry_uuid, type, title, content, tags, origin_project, "
            "origin_slug, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(entry_uuid) DO NOTHING",
            (
                _entry_uuid(page_id),
                kind,
                _text(row, "name", "title") or "(untitled)",
                _text(row, "description", "content", "example"),
                # Through the canonical form, not straight from the mirror. The
                # mirror spells tags however Notion did, and an import is a
                # write like any other — a second producer of the legacy shape
                # would leave the migration cleaning up after itself forever.
                dump_tags(load_tags(_text(row, "tags"))),
                _origin(row),
                None,
                created,
                created,
            ),
        )
    return bool(cur.rowcount and cur.rowcount > 0)


def format_counts(counts: dict[str, Any]) -> str:
    parts = [f"{v} {k}" for k, v in sorted(counts.items()) if v]
    return ", ".join(parts) if parts else "nothing"
