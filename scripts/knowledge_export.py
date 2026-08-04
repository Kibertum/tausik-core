"""Backing up the shared store: logical, local, and loud when it cannot.

WHY THIS EXISTS AT ALL. The shared knowledge database lives in one directory on
one machine with no copy anywhere. Every project's memory is backed up as a
matter of course — `tausik.db.bak.*` — and this file, which accumulates what was
learned across all of them, has nothing. A dead disk takes years of it.

WHY THE BACKUP IS LOGICAL AND NOT A FILE COPY. Three reasons, and any one of
them settles it. A `.db` is not readable by a person, so a backup nobody can
inspect is a backup nobody can trust. It is not byte-stable either — freelist
movement, the header's change counter and WAL checkpoints all vary while the
content does not — so "unchanged means no diff" would be false. And a byte copy
carries the FTS5 shadow tables, which hold tokenised copies of every title,
body and snippet, plus pages of deleted rows that were never overwritten. One
file per record, deterministic field order: inspectable, diffable, and carrying
only what was asked for.

WHY DESTINATIONS ARE LOCAL ONLY (decision #219). Nothing on the write path
redacts CONTENT. `origin_project` no longer carries an absolute project root —
it is a label now, and snippet `source_file` is relative — so the structural
disclosure that used to be on every single row is gone. What that removed was
the part nobody chose to write; it does not touch what people typed. A memory
body can name a client outright, and the argument that made un-redacted storage
acceptable is still "it never leaves the machine", so a backup that leaves the
machine would silently withdraw the premise rather than the conclusion.
Redaction of content is a 1.9 task, and a real one: the existing scrubber
REFUSES rather than redacts and would reject every backup on the first absolute
path, so making this work means building a redactor, not moving a call.

WHY REFUSAL IS LOUD. A backup that quietly does not happen is discovered at the
one moment it was needed. Every failure here raises.
"""

from __future__ import annotations

import os
import re
import sqlite3
from typing import Any
from urllib.parse import urlparse

from knowledge_db import SCHEMA_VERSION, connect_knowledge_db, knowledge_db_path
from state_serialize import frontmatter
from tausik_utils import ServiceError

# One directory per table, mirroring how the project tree is laid out so a
# person who has seen one export can read the other without being told.
ENTITY_DIRS: dict[str, str] = {
    "memory": "memory",
    "decisions": "decisions",
    "snippets": "snippets",
}

# Field order is fixed HERE rather than taken from the cursor, because
# `SELECT *` order follows the schema and would silently reshuffle every file
# the day a column is added — turning a no-op migration into a full re-diff.
FIELDS: dict[str, tuple[str, ...]] = {
    "memory": (
        "entry_uuid",
        "type",
        "title",
        "content",
        "tags",
        "origin_project",
        "origin_slug",
        "archived_at",
        "created_at",
        "updated_at",
    ),
    "decisions": (
        "entry_uuid",
        "decision",
        "rationale",
        "origin_project",
        "origin_slug",
        "created_at",
    ),
    "snippets": (
        "entry_uuid",
        "hash",
        "language",
        "code",
        "source_file",
        "source_lines",
        "taxonomy_kind",
        "origin_project",
        "created_at",
    ),
}

_NETWORK_SCHEMES = frozenset(
    {
        "s3",
        "gs",
        "az",
        "azure",
        "http",
        "https",
        "ftp",
        "ftps",
        "sftp",
        "scp",
        "ssh",
        "smb",
        "webdav",
    }
)


def assert_local_destination(dest: str) -> str:
    """Return the absolute path, or refuse a destination that leaves this machine.

    Refusal is by SHAPE, not by reachability: a URL scheme, or a UNC path, means
    the bytes go somewhere this machine does not solely control. Testing whether
    a remote answers would be the wrong check — a remote that happens to be down
    today is still a remote.

    Deliberately permissive about ordinary paths, including ones on other drives
    or on a mounted volume: a mounted network share is indistinguishable from a
    local disk at this level, and refusing every mount would refuse the external
    drive that is the most likely backup target there is. The line drawn here is
    the one that can be drawn honestly; the rest is documented, not pretended.
    """
    if not dest or not dest.strip():
        raise ServiceError("Backup destination is empty. Give a local directory to write into.")

    raw = dest.strip()
    if raw.startswith("\\\\") or raw.startswith("//"):
        raise ServiceError(
            f"Refusing the UNC destination {raw!r}. The shared knowledge database is stored "
            "WITHOUT redaction — the memories, decisions and code snippets in it are free "
            "text and can name a client outright — so backups must stay on this machine. "
            "Give a local directory."
        )

    scheme = urlparse(raw).scheme.lower()
    # A single letter is a Windows drive, not a scheme: urlparse reads "D:/x"
    # as scheme "d". Length is the discriminator, and it is exact rather than
    # heuristic — URL schemes are at least two characters by definition.
    if len(scheme) > 1 and scheme in _NETWORK_SCHEMES:
        raise ServiceError(
            f"Refusing the remote destination {raw!r} (scheme {scheme!r}). The shared knowledge "
            "database is stored WITHOUT redaction — the memories, decisions and code snippets "
            "in it are free text and can name a client outright — so backups must stay on this "
            "machine. Redaction on export is planned separately; until then, give a local "
            "directory."
        )
    if len(scheme) > 1:
        raise ServiceError(
            f"Refusing the destination {raw!r}: {scheme!r} is not a local path. "
            "Give a local directory."
        )
    return os.path.abspath(os.path.expanduser(raw))


MANIFEST = "manifest.md"

# A managed backup file is named for the record's identity and nothing else.
# Anything not matching this was not written by an export, and pruning must not
# touch it.
_MANAGED_NAME = re.compile(r"^[0-9A-Za-z_-]+\.md$")


def _assert_uuid_is_a_safe_filename(entry_uuid: str) -> str:
    """A record's identity becomes a path component, so it has to be one.

    `entry_uuid` is TEXT with no CHECK behind it. Everything that writes it today
    generates a UUID, but "today" is not a guarantee: one stray value containing
    a separator would make os.path.join write OUTSIDE the backup directory. The
    column's shape is asserted here rather than assumed.
    """
    if not entry_uuid or not _MANAGED_NAME.match(f"{entry_uuid}.md"):
        raise ServiceError(
            f"Refusing to back up a record whose entry_uuid is not a safe filename: "
            f"{entry_uuid!r}. Nothing was written."
        )
    return entry_uuid


def assert_backup_directory(out: str) -> None:
    """Refuse a destination holding files this export did not write.

    The export reconciles deletions, and reconciliation over someone else's
    directory is a delete-your-files bug rather than a backup. The check is cheap
    and fail-closed: an empty or absent directory is fine, a directory carrying
    our manifest is fine, and anything else is refused before a single byte moves.

    This is not hypothetical caution. `state_export` writes `decisions/` and
    `memory/` under a project's `tausik/` tree — the SAME directory names this
    module uses — so pointing --to at that tree without this guard would delete
    the project's own records on the first run.
    """
    if not os.path.isdir(out):
        return
    if os.path.isfile(os.path.join(out, MANIFEST)):
        return
    if any(os.scandir(out)):
        raise ServiceError(
            f"{out} already contains files and is not a knowledge backup (no {MANIFEST}). "
            "Refusing to write here: the backup reconciles deletions and would remove "
            "files it did not create. Choose an empty or dedicated directory."
        )


def _rows(conn: sqlite3.Connection, table: str) -> list[sqlite3.Row]:
    # Ordered by the stable identity, not by rowid: rowids differ between two
    # databases holding the same knowledge, and a backup that reorders itself
    # per machine is not diffable.
    return conn.execute(f"SELECT * FROM {table} ORDER BY entry_uuid").fetchall()


def _render(table: str, row: sqlite3.Row) -> str:
    pairs: list[tuple[str, Any]] = [(f, row[f]) for f in FIELDS[table]]
    return "---\n" + frontmatter(pairs) + "---\n"


def export_shared_knowledge(dest: str) -> dict[str, int]:
    """Write every shared record as one file. Returns per-table counts.

    Idempotent by construction: the content of each file is a pure function of
    the row, so an unchanged store rewrites byte-identical files and a diff shows
    nothing. Files whose record has gone are removed, or a deleted entry would
    live on in the backup forever and a restore would resurrect it.
    """
    out = assert_local_destination(dest)
    assert_backup_directory(out)
    conn = connect_knowledge_db(create=False)
    if conn is None:
        raise ServiceError(
            f"There is no shared knowledge database at {knowledge_db_path()} to back up. "
            "Nothing was written."
        )

    counts: dict[str, int] = {}
    try:
        os.makedirs(out, exist_ok=True)
        _write_manifest(out, conn)
        for table, dirname in ENTITY_DIRS.items():
            target = os.path.join(out, dirname)
            os.makedirs(target, exist_ok=True)
            rows = _rows(conn, table)
            wanted = set()
            for row in rows:
                name = f"{_assert_uuid_is_a_safe_filename(row['entry_uuid'])}.md"
                wanted.add(name)
                _write_if_changed(os.path.join(target, name), _render(table, row))
            _prune(target, wanted)
            counts[table] = len(rows)
    except (OSError, sqlite3.Error) as e:
        # sqlite3.Error belongs here too: a locked or damaged store failing midway
        # leaves some tables fresh and others stale, and the dispatcher does not
        # catch that class — the user would get a traceback instead of the one
        # sentence that matters, which is that this backup is not trustworthy.
        raise ServiceError(f"Backup to {out} failed: {e}. The backup is INCOMPLETE.") from e
    finally:
        conn.close()
    return counts


def _write_manifest(out: str, conn: sqlite3.Connection) -> None:
    """Record the schema version the backup was taken at.

    A restore into a framework that predates the schema would otherwise fail in
    whatever way the data happened to break. The version makes the mismatch a
    statement rather than a symptom.
    """
    from knowledge_db import stored_schema_version

    body = "---\n" + frontmatter([("schema_version", stored_schema_version(conn))]) + "---\n"
    _write_if_changed(os.path.join(out, MANIFEST), body)


def _write_if_changed(path: str, content: str) -> None:
    """Write only on a real difference, so mtimes do not churn on a no-op backup."""
    if os.path.isfile(path):
        with open(path, encoding="utf-8", newline="") as fh:
            if fh.read() == content:
                return
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)


def _prune(target: str, wanted: set[str]) -> None:
    """Remove backup files whose record no longer exists.

    Scoped to `.md` files in a directory this function created, and only those
    not in `wanted` — the reconciliation cannot reach anything the export did not
    put there.
    """
    for name in os.listdir(target):
        if name in wanted or not name.endswith(".md"):
            continue
        if not _MANAGED_NAME.match(name):
            # Belt to assert_backup_directory's braces: a file that does not
            # carry a record's identity was not written here, and deleting it
            # would be destroying a stranger's work to tidy our own.
            continue
        os.remove(os.path.join(target, name))


def restore_shared_knowledge(src: str) -> dict[str, int]:
    """Rebuild the shared store from a backup. Returns per-table INSERT counts.

    Restores BY IDENTITY, and by that identity ONLY: `entry_uuid` is what a
    record is, which is why every row was born with one. A row already present
    under the same uuid is left alone, so restoring twice — or restoring over a
    store that partly survived — converges instead of doubling.

    The conflict target is named explicitly rather than left to `OR IGNORE`, and
    the difference is data. `OR IGNORE` suppresses EVERY constraint: snippets
    also carry a UNIQUE hash and memory a CHECK on its type, so a record with a
    fresh uuid whose code already exists under another one would have been
    dropped in silence — an identity the backup holds and the store would not,
    reported as success. Anything that is not an identity collision now raises
    and names the file.

    ALL OR NOTHING. The commit happens once, at the end; a failure part-way
    leaves the store exactly as it was rather than half-restored. A half-restored
    store is the worst outcome available here, because it looks like a working
    one.

    Counts are actual inserts (`rowcount`), not files read. Counting files would
    report a confident number while rows were being skipped, which is precisely
    how a lossy restore passes for a good one.

    A record already present is REPORTED, under `<table>:already-present`, not
    folded into the total. It matters because "left alone" and "restored" are
    different outcomes and only one of them means the backup was applied: a row
    that survived an incident in a DAMAGED state keeps its damage, and a reader
    told only "restored N" would believe otherwise. The backup is not treated as
    the source of truth for existing rows — overwriting a row that is NEWER than
    the backup would lose data just as surely — so the divergence is surfaced
    rather than resolved by guessing.
    """
    root = assert_local_destination(src)
    if not os.path.isdir(root):
        raise ServiceError(f"No backup directory at {root}. Nothing was restored.")

    _check_manifest(root)

    conn = connect_knowledge_db(create=True)
    if conn is None:  # pragma: no cover — create=True never returns None
        raise ServiceError("Could not open the shared knowledge database.")
    counts: dict[str, int] = {}
    try:
        for table, dirname in ENTITY_DIRS.items():
            target = os.path.join(root, dirname)
            inserted = 0
            already = 0
            for name in sorted(os.listdir(target)) if os.path.isdir(target) else []:
                if not name.endswith(".md"):
                    continue
                path = os.path.join(target, name)
                with open(path, encoding="utf-8") as fh:
                    record = _parse(fh.read())
                if "entry_uuid" not in record:
                    raise ServiceError(
                        f"{path} has no entry_uuid — it is not a knowledge record. "
                        "Nothing was restored."
                    )
                fields = [f for f in FIELDS[table] if f in record]
                placeholders = ", ".join("?" for _ in fields)
                try:
                    cur = conn.execute(
                        f"INSERT INTO {table} ({', '.join(fields)}) VALUES ({placeholders}) "
                        "ON CONFLICT(entry_uuid) DO NOTHING",
                        tuple(record[f] for f in fields),
                    )
                except sqlite3.IntegrityError as e:
                    raise ServiceError(
                        f"{path} could not be restored: {e}. This is NOT a duplicate identity — "
                        f"the record's entry_uuid is new, so the backup holds something this "
                        f"store cannot accept. Nothing was restored; the store is unchanged."
                    ) from e
                if cur.rowcount > 0:
                    inserted += 1
                else:
                    already += 1
            counts[table] = inserted
            if already:
                counts[f"{table}:already-present"] = already
        conn.commit()
    except (OSError, sqlite3.Error) as e:
        raise ServiceError(f"Restore from {root} failed: {e}. Nothing was committed.") from e
    finally:
        conn.close()
    return counts


def _check_manifest(root: str) -> None:
    path = os.path.join(root, MANIFEST)
    if not os.path.isfile(path):
        raise ServiceError(
            f"{root} has no manifest.md — this does not look like a knowledge backup. "
            "Nothing was restored."
        )
    with open(path, encoding="utf-8") as fh:
        found = _parse(fh.read()).get("schema_version")
    try:
        version = int(found) if found is not None else 0
    except (TypeError, ValueError) as e:
        # This check runs OUTSIDE the module's general error wrapper, so an
        # unguarded int() here would surface a raw traceback while every other
        # refusal in this file explains itself. A damaged manifest is exactly
        # when a person needs the sentence, not the stack.
        raise ServiceError(
            f"manifest.md at {root} has a non-numeric schema_version ({found!r}) — "
            "this is not a valid knowledge backup. Nothing was restored."
        ) from e
    if version > SCHEMA_VERSION:
        raise ServiceError(
            f"The backup at {root} was taken at schema v{version}; this TAUSIK understands up "
            f"to v{SCHEMA_VERSION}. Update TAUSIK before restoring. Nothing was restored."
        )


def _parse(text: str) -> dict[str, Any]:
    """Read back one rendered record. Mirrors `frontmatter`, and nothing more.

    Deliberately not a YAML parser: what this reads is what this module wrote,
    and a general parser would accept shapes the writer never produces — which
    is how a restore starts succeeding on files it should have refused.
    """
    out: dict[str, Any] = {}
    inside = False
    for line in text.splitlines():
        if line.strip() == "---":
            if inside:
                break
            inside = True
            continue
        if inside and line.lstrip().startswith("- "):
            # The shared writer, `frontmatter`, CAN emit block lists, and every
            # such line lacks a colon — so the skip below would drop them one by
            # one without a word. No field is a list today; the guard is here so
            # that the day one becomes one, the restore stops instead of quietly
            # returning a record with an empty collection.
            raise ServiceError(
                "A backup record contains a list value, which this reader does not "
                "support. Restoring it would silently drop the list. Nothing was restored."
            )
        if not inside or ":" not in line:
            continue
        key, _, raw = line.partition(":")
        value = raw.strip()
        if value == "null":
            out[key.strip()] = None
        elif len(value) >= 2 and value.startswith('"') and value.endswith('"'):
            out[key.strip()] = _unescape(value[1:-1])
        else:
            out[key.strip()] = value
    return out


_UNESCAPE = {"\\": "\\", '"': '"', "n": "\n", "t": "\t", "r": "\r"}


def _unescape(s: str) -> str:
    """Exact inverse of `state_serialize._dq`, scanned left to right.

    Not a chain of `.replace()` calls, and the difference is not cosmetic. `_dq`
    escapes the backslash FIRST, so a chain that turned `\\n` into a newline
    before restoring `\\\\` would read a literal backslash followed by `n` as a
    line break. Any Windows path in a snippet body or a memory content field is
    full of backslashes, so that mistake would corrupt a field on restored rows
    while the restore reported success. It was `origin_project` that made this
    certain rather than likely, on every row, before it became a label.

    Scanning consumes the escape and its target together, which cannot confuse
    the two no matter what the text contains.
    """
    out: list[str] = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == "\\" and i + 1 < len(s):
            out.append(_UNESCAPE.get(s[i + 1], s[i + 1]))
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)
