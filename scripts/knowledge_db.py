"""The shared knowledge database: one file in the user's home, many projects.

WHAT THIS IS NOT. It is not a second copy of the project schema. Tasks,
sessions, events and verification runs stay where they belong — in each
project's `.tausik/tausik.db` — and nothing here touches them. What crosses
project boundaries is KNOWLEDGE: a pattern learned once, a gotcha paid for
once, a decision worth carrying, a snippet worth reusing. That is the whole
schema, plus FTS over it.

WHERE IT LIVES. `~/.tausik/knowledge.db`, overridable with the `TAUSIK_HOME`
environment variable. Note the deliberate distinction from `TAUSIK_DIR`, which
selects a PROJECT's `.tausik/`: one names a project, the other names the user.
Confusing them is how a shared store would end up inside one repository, so
they are read by different functions and neither falls back to the other.

WHY WAL IS NOT AN OPTIMIZATION HERE. This database is multi-writer BY
CONSTRUCTION, not by accident: a person has several IDEs open on several
projects, and every one of them points at this one file. Writes are rare and
reads are many, which is exactly the profile WAL exists for. Long transactions
are forbidden for the same reason — a writer that holds the file makes every
other project's search hang, and the failure looks like "TAUSIK is slow" rather
than like a lock.

WHY CREATION IS LAZY. `sqlite3.connect()` CREATES the file it cannot find, so
"open it and see" would mean every `tausik status` in every project silently
brings an empty shared database into existence — including for people who never
opted in. Existence is therefore checked on the filesystem BEFORE connecting,
and only a write path is allowed to create. Reading a store that is not there
returns "nothing", which is the truth, rather than creating one to say it.

WHY EVERY ROW IS BORN WITH A UUID. A project row is identified by its rowid,
which is a fact about one machine's database. The moment two machines exchange
knowledge — the entire point of this file — rowids collide and there is no way
to tell "the same entry" from "a different entry that happened to land in the
same slot". Adding identity later means reconciling records that already
exist; adding it at creation costs one column. This is the cheapest it will
ever be, so it is done now even though nothing exchanges anything yet.

`origin_project` and `origin_slug` are free text ON PURPOSE — not foreign keys.
A shared record must outlive the project it came from, so it may name its
origin but must never depend on it.
"""

from __future__ import annotations

import os
import sqlite3

# Bumped whenever the DDL below changes shape. Read back via `PRAGMA
# user_version`, which is the one place SQLite gives us that costs no table and
# survives a file copied between machines. `kb-global-version-guard` compares it
# against what the running framework expects.
SCHEMA_VERSION = 1

_HOME_ENV = "TAUSIK_HOME"
_HOME_DIRNAME = ".tausik"
_DB_FILENAME = "knowledge.db"

KNOWLEDGE_SQL = """
CREATE TABLE IF NOT EXISTS memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_uuid TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL CHECK(type IN ('pattern', 'gotcha', 'convention', 'context', 'dead_end')),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT,
    origin_project TEXT,
    origin_slug TEXT,
    archived_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_uuid TEXT NOT NULL UNIQUE,
    decision TEXT NOT NULL,
    rationale TEXT,
    origin_project TEXT,
    origin_slug TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS snippets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_uuid TEXT NOT NULL UNIQUE,
    hash TEXT NOT NULL UNIQUE,
    language TEXT NOT NULL,
    code TEXT NOT NULL,
    source_file TEXT,
    source_lines TEXT,
    taxonomy_kind TEXT,
    origin_project TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_k_memory_type ON memory(type);
CREATE INDEX IF NOT EXISTS idx_k_memory_origin ON memory(origin_project);
CREATE INDEX IF NOT EXISTS idx_k_decisions_origin ON decisions(origin_project);
CREATE INDEX IF NOT EXISTS idx_k_snippets_language ON snippets(language);
"""

KNOWLEDGE_FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS fts_memory USING fts5(
    title, content, tags,
    content='memory', content_rowid='id'
);
CREATE VIRTUAL TABLE IF NOT EXISTS fts_decisions USING fts5(
    decision, rationale,
    content='decisions', content_rowid='id'
);
CREATE VIRTUAL TABLE IF NOT EXISTS fts_snippets USING fts5(
    code, source_file, taxonomy_kind,
    content='snippets', content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS k_memory_ai AFTER INSERT ON memory BEGIN
    INSERT INTO fts_memory(rowid, title, content, tags)
    VALUES (new.id, new.title, new.content, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS k_memory_ad AFTER DELETE ON memory BEGIN
    INSERT INTO fts_memory(fts_memory, rowid, title, content, tags)
    VALUES ('delete', old.id, old.title, old.content, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS k_memory_au AFTER UPDATE ON memory BEGIN
    INSERT INTO fts_memory(fts_memory, rowid, title, content, tags)
    VALUES ('delete', old.id, old.title, old.content, old.tags);
    INSERT INTO fts_memory(rowid, title, content, tags)
    VALUES (new.id, new.title, new.content, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS k_decisions_ai AFTER INSERT ON decisions BEGIN
    INSERT INTO fts_decisions(rowid, decision, rationale)
    VALUES (new.id, new.decision, new.rationale);
END;
CREATE TRIGGER IF NOT EXISTS k_decisions_ad AFTER DELETE ON decisions BEGIN
    INSERT INTO fts_decisions(fts_decisions, rowid, decision, rationale)
    VALUES ('delete', old.id, old.decision, old.rationale);
END;
CREATE TRIGGER IF NOT EXISTS k_decisions_au AFTER UPDATE ON decisions BEGIN
    INSERT INTO fts_decisions(fts_decisions, rowid, decision, rationale)
    VALUES ('delete', old.id, old.decision, old.rationale);
    INSERT INTO fts_decisions(rowid, decision, rationale)
    VALUES (new.id, new.decision, new.rationale);
END;

CREATE TRIGGER IF NOT EXISTS k_snippets_ai AFTER INSERT ON snippets BEGIN
    INSERT INTO fts_snippets(rowid, code, source_file, taxonomy_kind)
    VALUES (new.id, new.code, new.source_file, new.taxonomy_kind);
END;
CREATE TRIGGER IF NOT EXISTS k_snippets_ad AFTER DELETE ON snippets BEGIN
    INSERT INTO fts_snippets(fts_snippets, rowid, code, source_file, taxonomy_kind)
    VALUES ('delete', old.id, old.code, old.source_file, old.taxonomy_kind);
END;
CREATE TRIGGER IF NOT EXISTS k_snippets_au AFTER UPDATE ON snippets BEGIN
    INSERT INTO fts_snippets(fts_snippets, rowid, code, source_file, taxonomy_kind)
    VALUES ('delete', old.id, old.code, old.source_file, old.taxonomy_kind);
    INSERT INTO fts_snippets(rowid, code, source_file, taxonomy_kind)
    VALUES (new.id, new.code, new.source_file, new.taxonomy_kind);
END;
"""


def knowledge_home() -> str:
    """The USER-level TAUSIK directory — `$TAUSIK_HOME` or `~/.tausik`.

    Deliberately does NOT consult `TAUSIK_DIR` or search upward from the cwd.
    Those answer "which project am I in"; this answers "who am I", and a shared
    store that resolved through a project handle would be shared with nobody.
    """
    override = os.environ.get(_HOME_ENV)
    if override:
        return os.path.abspath(os.path.expanduser(override))
    return os.path.join(os.path.expanduser("~"), _HOME_DIRNAME)


def knowledge_db_path() -> str:
    """Absolute path of the shared knowledge database. Says nothing about existence."""
    return os.path.join(knowledge_home(), _DB_FILENAME)


def knowledge_db_exists() -> bool:
    """True iff the shared store is already on disk. Never creates it."""
    return os.path.isfile(knowledge_db_path())


def _configure(conn: sqlite3.Connection) -> sqlite3.Connection:
    conn.row_factory = sqlite3.Row
    # WAL: readers never block the writer and vice versa — mandatory for a file
    # several projects hold open at once. busy_timeout: when two DO collide,
    # wait rather than raise "database is locked" into a user's search.
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_knowledge_schema(conn: sqlite3.Connection) -> None:
    """Create the knowledge objects if absent. Idempotent — safe to run always."""
    conn.executescript(KNOWLEDGE_SQL)
    conn.executescript(KNOWLEDGE_FTS_SQL)
    conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
    conn.commit()


def connect_knowledge_db(*, create: bool = False) -> sqlite3.Connection | None:
    """Open the shared store. Returns None when it does not exist and create=False.

    `create` is not a convenience flag, it is the whole laziness contract.
    `sqlite3.connect()` creates whatever file it is given, so a read path that
    simply connected would bring an empty shared database into being on every
    `status` call in every project — for people who never asked for one. Hence
    existence is settled on the filesystem first, and only a caller that is
    about to WRITE passes create=True.
    """
    path = knowledge_db_path()
    if not create and not os.path.isfile(path):
        return None
    home = os.path.dirname(path)
    os.makedirs(home, exist_ok=True)
    fresh = not os.path.isfile(path)
    conn = _configure(sqlite3.connect(path, timeout=10, check_same_thread=False))
    init_knowledge_schema(conn)
    if fresh:
        _restrict_permissions(home, path)
    return conn


def _restrict_permissions(home: str, path: str) -> None:
    """Owner-only on the directory and the file, mirroring how keys are treated.

    Not defence against the person who owns the file — it is defence against
    everyone ELSE on a shared machine or in a container. This store accumulates
    whatever its owner considered worth keeping across projects, and nothing on
    the write path redacts it, so "readable by default umask" is a wider
    audience than anyone chose. `crypto_keys` already does exactly this for the
    signing seed; the reasoning is the same and so is the mode.

    Best-effort by design: on Windows the POSIX bits are largely advisory, and
    a store that exists with loose permissions beats a command that refuses to
    write. The narrowing is attempted once, at creation, so an owner who
    deliberately widened it later is not overruled on every open.
    """
    import contextlib
    import stat

    with contextlib.suppress(OSError):
        os.chmod(home, stat.S_IRWXU)
    with contextlib.suppress(OSError):
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def knowledge_schema_version() -> int | None:
    """`PRAGMA user_version` of the store on disk, or None if there is no store."""
    conn = connect_knowledge_db(create=False)
    if conn is None:
        return None
    try:
        row = conn.execute("PRAGMA user_version").fetchone()
        return int(row[0]) if row else None
    finally:
        conn.close()
