"""Writing into the shared store: explicit, attributed, and never a silent fallback.

ONE RULE ABOVE THE REST. A write asked to go global goes global or it FAILS. It
never quietly lands in the project database instead. The reason is the shape of
the mistake: a person who typed `--global` believes the knowledge is now
available everywhere, and a fallback would leave it in one repository while
telling them otherwise. That defect is invisible at the moment it is committed
and is discovered months later, in another project, as an absence. So the
failure is loud and it names the path it could not write to.

WHY THERE IS NO PROMPT. The route is decided by the flag and by nothing else —
no heuristic, no classifier, no "this looks cross-project, shall I?". A
classifier already exists in this repository for the Notion brain, and it has
misfiled seven decisions to date. Routing a person can predict is worth more
than routing that is occasionally cleverer.

WHY THE UNIVERSALITY HINT DOES NOT FIRE HERE. `memory_add` normally emits a
nudge asking whether the entry belongs in a shared store. On this path the
person has already answered that question by typing the flag; asking again is
noise, and worse, it is noise pointing at a DIFFERENT shared store.

WHY NO SCRUBBER, AND WHAT THAT ARGUMENT DOES NOT COVER. Redaction belongs at
the boundary where knowledge leaves the machine — publishing to Notion — not on
a write into a file in the user's own home. Scrubbing here would corrupt entries
(a redacted identifier is a wrong identifier) to buy privacy against oneself.

That much holds. What it does NOT establish is that this store sits inside one
confidentiality boundary, and an earlier version of this docstring claimed it
did by treating "same OS account" as "same trust domain". One person routinely
works for several clients out of one home directory — the path of this very
repository names a client — so a shared store IS read across those boundaries,
by construction, with no export required. Two consequences are tracked rather
than hand-waved: `origin-project-stores-client-names-readable-from-every-project`
and `export-of-the-shared-store-must-scrub-or-stay-local`, the latter because
the planned backup target for this unredacted file includes S3-compatible
remotes, which would carry it off the machine the argument above relies on.

`origin_project` holds a LABEL — `basename@fingerprint` — and no longer the
project's absolute root. It used to hold the root, on the argument that
basenames collide (`core`, `server`, `api`) and a collision would attribute one
project's knowledge to another. That argument was right about collisions and
wrong about the remedy: the label keeps them distinguishable through the
fingerprint while dropping the directory names, so the second consequence named
above — a client's name readable from any other project, by reading the file —
is gone rather than merely tracked. See `knowledge_origin` for why the
fingerprint needs no mapping table to be useful.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import uuid
from datetime import datetime, timezone

from knowledge_db import connect_knowledge_db, knowledge_db_path
from knowledge_origin import origin_label_for, relative_source_file
from knowledge_tags import dump_tags
from tausik_utils import ServiceError


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def origin_project_root() -> str:
    """Absolute root of the project this write comes from. Never stored as-is.

    Derived from the resolved `.tausik/` handle rather than from the cwd, so a
    command run from a subdirectory still attributes to the project rather than
    to wherever the shell happened to be.

    Raises when the resolved handle does not exist. `find_tausik_dir` falls back
    to `cwd/.tausik` when its search finds nothing, which is the right default
    for a project-local command — it names where the project WOULD be. Here it
    is the wrong one: the write would succeed and attribute a row to whatever
    directory the shell stood in, in a store read from every other project. A
    fabricated origin is worse than no write, because nothing later can tell it
    from a real one. So this checks the handle instead of trusting the fallback.
    """
    from project_config import find_tausik_dir

    handle = find_tausik_dir()
    if not handle or not os.path.isdir(handle):
        raise ServiceError(
            "Cannot attribute this shared write: no TAUSIK project was found from "
            f"the current directory (looked for {handle}). Nothing was written — "
            "attributing it to the current directory would have invented an origin. "
            "Run from inside a TAUSIK project, or set TAUSIK_DIR."
        )
    return os.path.dirname(os.path.abspath(handle))


def origin_label() -> str:
    """What a shared row stores in `origin_project`: `basename@fingerprint`."""
    return origin_label_for(origin_project_root())


def _open_or_fail() -> sqlite3.Connection:
    """Open the shared store for writing, or raise naming the path.

    Every failure mode collapses to one outcome on purpose: the caller must not
    be able to continue as if the write had happened. Callers therefore never
    receive None and cannot mistake "no store" for "wrote nothing".
    """
    path = knowledge_db_path()
    try:
        conn = connect_knowledge_db(create=True)
    except (OSError, sqlite3.Error) as e:
        raise ServiceError(
            f"Cannot open the shared knowledge database at {path}: {e}. "
            "Nothing was written — the project database was NOT used as a fallback. "
            "Check TAUSIK_HOME or the permissions on that directory."
        ) from e
    if conn is None:  # pragma: no cover — create=True never returns None
        raise ServiceError(f"Cannot open the shared knowledge database at {path}.")
    return conn


def write_memory(
    mem_type: str,
    title: str,
    content: str,
    tags: list[str] | None = None,
    task_slug: str | None = None,
) -> str:
    """Write one memory entry into the shared store. Raises rather than falling back."""
    conn = _open_or_fail()
    path = knowledge_db_path()
    try:
        now = _now()
        cur = conn.execute(
            "INSERT INTO memory (entry_uuid, type, title, content, tags, origin_project, "
            "origin_slug, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                mem_type,
                title,
                content,
                dump_tags(tags),
                origin_label(),
                task_slug,
                now,
                now,
            ),
        )
        conn.commit()
        return f"Memory #{cur.lastrowid} ({mem_type}) saved to the SHARED store ({path})."
    except sqlite3.Error as e:
        raise ServiceError(f"Shared write failed at {path}: {e}") from e
    finally:
        conn.close()


def write_decision(
    text: str,
    rationale: str | None = None,
    task_slug: str | None = None,
) -> str:
    """Write one decision into the shared store. Raises rather than falling back."""
    conn = _open_or_fail()
    path = knowledge_db_path()
    try:
        cur = conn.execute(
            "INSERT INTO decisions (entry_uuid, decision, rationale, origin_project, "
            "origin_slug, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                text,
                rationale,
                origin_label(),
                task_slug,
                _now(),
            ),
        )
        conn.commit()
        return f"Decision #{cur.lastrowid} recorded in the SHARED store ({path})."
    except sqlite3.Error as e:
        raise ServiceError(f"Shared write failed at {path}: {e}") from e
    finally:
        conn.close()


def write_snippet(
    code: str,
    language: str,
    source_file: str | None = None,
    source_lines: str | None = None,
    taxonomy_kind: str | None = None,
) -> str:
    """Write one snippet into the shared store, deduplicating on content hash.

    `hash` is UNIQUE in the schema, so re-ingesting identical code is a no-op
    rather than an error — matching how the project store already behaves.

    `source_file` is normalised against the project root for the same reason
    `origin_project` is a label: an absolute path here names the same directories
    the label was introduced to stop storing, and it names them once per snippet.
    """
    digest = hashlib.sha256(code.encode("utf-8")).hexdigest()
    root = origin_project_root()
    source_file = relative_source_file(source_file, root)
    conn = _open_or_fail()
    path = knowledge_db_path()
    try:
        existing = conn.execute("SELECT id FROM snippets WHERE hash = ?", (digest,)).fetchone()
        if existing is not None:
            return f"Snippet #{existing[0]} already in the SHARED store (identical content)."
        cur = conn.execute(
            "INSERT INTO snippets (entry_uuid, hash, language, code, source_file, source_lines, "
            "taxonomy_kind, origin_project, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                digest,
                language,
                code,
                source_file,
                source_lines,
                taxonomy_kind,
                origin_label_for(root),
                _now(),
            ),
        )
        conn.commit()
        return f"Snippet #{cur.lastrowid} saved to the SHARED store ({path})."
    except sqlite3.Error as e:
        raise ServiceError(f"Shared write failed at {path}: {e}") from e
    finally:
        conn.close()
