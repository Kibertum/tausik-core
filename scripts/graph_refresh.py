"""Re-index ONE file, in the process that already noticed it changed.

MEASURED BEFORE THIS EXISTED (session #235, on the live tree and live database):

    a hook process, start to finish   54 ms median (n=10) — almost all of it
                                      Python starting up
    re-indexing one file              0.47 ms median (n=100)
    parsing the largest file's AST    1.62 ms
    a full `graph build`              ~9,000 ms

The ratio is the whole design. The WORK is single-digit milliseconds; a separate
hook process to do it would cost thirty times the work in overhead, and would be
a second thing to deploy, keep in cross-host parity, and pay for on every write.
So this is a function called from a hook that already runs, never a hook of its
own.

FAIL-OPEN ON THE WORK, FAIL-LOUD ON THE TRUTH. The graph is secondary: if
re-indexing raises, the file is still written and the tool call still succeeds.
But the failure is not swallowed either — the artifact simply keeps its old
fingerprint, and `neighbours_of` recomputes fingerprints from disk on EVERY
query, so the next question about that file names it as stale. Silence about a
stale row is the one outcome the graph must never produce; silence about a
failed refresh is fine, because the query is what tells the truth.

WHAT THIS DOES NOT DO. It never ADDS an artifact. A file the graph has not been
told about stays unknown until `graph build` runs: letting a write quietly widen
the graph would make the stored row count stop matching what the build reported,
and a count nobody can reproduce is worse than a count that is behind.
"""

from __future__ import annotations

import os

#: Never re-index the framework's own state files. They change on almost every
#: command — a task journal entry, a roadmap regeneration — and re-indexing them
#: would make the write hook busiest exactly when the agent is doing bookkeeping
#: rather than work.
_SKIP_PREFIXES = (".tausik/", "docs/_generated/")


def _repo_relative(project_dir: str, file_path: str) -> str | None:
    """`file_path` as a repo-relative POSIX path, or None if it is outside."""
    try:
        rel = os.path.relpath(os.path.abspath(file_path), os.path.abspath(project_dir))
    except (OSError, ValueError):
        return None
    rel = rel.replace("\\", "/")
    if rel.startswith("../") or rel == "..":
        return None
    return rel


def refresh_one(project_dir: str, file_path: str) -> str | None:
    """Re-fingerprint one artifact the graph already knows. Returns its path.

    None means "nothing was done", and that covers every uninteresting case
    identically: the graph is empty, the file is not in it, the file is outside
    the project, the database is unreachable. None of those is an error — the
    query layer reports staleness regardless — so none of them is worth a
    message on a write.
    """
    rel = _repo_relative(project_dir, file_path)
    if not rel or rel.startswith(_SKIP_PREFIXES):
        return None
    if not os.path.isfile(file_path):
        return None

    try:
        from service_artifact_graph import classify, fingerprint
    except Exception:  # noqa: BLE001 — a refresh must never break a write
        return None

    # Built here rather than through a helper: there is no canonical one for
    # the database path (only `tausik_config_path` exists, and its guard test
    # covers the config file alone), and `hooks/_common` builds it the same
    # way. Inventing a second convention would be the drift, not the cure.
    db = os.path.join(project_dir, ".tausik", "tausik.db")
    if not os.path.isfile(db):
        return None

    # RAW sqlite3, NOT `SQLiteBackend`. Measured end to end on the real hook:
    # going through the backend put the write hook at 301 ms against 68 ms
    # before, because opening it runs `init_schema` and closing it runs
    # `wal_checkpoint(TRUNCATE)` over a 66 MB database — both sensible for a
    # long-lived process and both wasted on one UPDATE from a process that
    # exits immediately. `hooks/_common.current_active_task_slug` set this
    # precedent for the same reason and says so in its docstring.
    #
    # The SQL below is deliberately NOT the upsert `artifact_upsert` runs: this
    # only ever UPDATES a row that already exists (see the module docstring), so
    # it cannot insert an artifact the build never counted, and a test pins it
    # against the backend's own behaviour so the two cannot drift.
    import sqlite3
    from datetime import datetime, timezone

    try:
        with sqlite3.connect(db, timeout=2) as conn:
            row = conn.execute("SELECT id FROM artifacts WHERE path = ?", (rel,)).fetchone()
            if not row:
                # Not an error and not a gap to fill here — see the docstring.
                return None
            conn.execute(
                "UPDATE artifacts SET kind = ?, content_hash = ?, indexed_at = ? WHERE path = ?",
                (
                    classify(rel),
                    fingerprint(rel, project_dir),
                    datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    rel,
                ),
            )
        return rel
    except (sqlite3.Error, OSError):
        # Fail-open: the write already happened, and the query layer recomputes
        # fingerprints, so this artifact simply reads as stale next time.
        return None
