"""The shared knowledge database: one file in the user's home, many projects.

WHAT THIS IS NOT. It is not a second copy of the project schema. Tasks,
sessions, events and verification runs stay where they belong — in each
project's `.tausik/tausik.db` — and nothing here touches them. What crosses
project boundaries is KNOWLEDGE: a pattern learned once, a gotcha paid for
once, a decision worth carrying, a snippet worth reusing. That is the whole
schema, plus FTS over it.

WHERE IT LIVES. `~/.tausik-knowledge/knowledge.db`, overridable with the
`TAUSIK_HOME` environment variable — and spelled here by hand only because a
docstring cannot interpolate; every OTHER place that shows this path to a person
reads it from `default_store_display_path()` below. It said `~/.tausik/` until
the store moved (#222) and the sentence outlived the move, which is what that
helper exists to prevent next time.

Note the deliberate distinction from `TAUSIK_DIR`, which
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

`memory.tags` is a JSON ARRAY, the same spelling the project store uses. It was
comma-joined here for a while, and nothing broke only because no surface printed
tags at all — an unobservable divergence that would have detonated on the first
renderer written over a result set mixing both stores. The canonical form lives
in `knowledge_tags`; write through it rather than reaching for `",".join` or
`json.dumps` directly, or the two spellings come back.
"""

from __future__ import annotations

import os
import sqlite3

from knowledge_home_guard import assert_safe_knowledge_home, protect_home_in_git
from knowledge_migrations import apply_open_migrations

# Bumped whenever the DDL below changes shape. Read back via `PRAGMA
# user_version`, which is the one place SQLite gives us that costs no table and
# survives a file copied between machines. `kb-global-version-guard` compares it
# against what the running framework expects.
SCHEMA_VERSION = 1

_HOME_ENV = "TAUSIK_HOME"

# NOT ".tausik", and the difference is not cosmetic. `find_tausik_dir` locates a
# project by walking UP from the working directory looking for a directory named
# exactly `.tausik` — so a directory of that name in the user's HOME makes every
# path beneath it resolve to the home directory as its "project".
#
# This was not hypothetical. Creating `~/.tausik/knowledge.db` did it: from that
# moment any command run from a temp directory treated the home as the project,
# tests wrote a stray `tausik.db` and `config.json` there, six of them turned red
# by sharing one "project" database, and every project of the user's living under
# their home without its own `.tausik` would have resolved the same way.
#
# `brain` already uses `~/.tausik-brain` for exactly this reason; this follows the
# precedent instead of rediscovering it. The property is pinned by a test that
# compares the two constants rather than the literal string, because a literal
# survives a rename and stops guaranteeing anything.
_HOME_DIRNAME = ".tausik-knowledge"

# Where the store used to live. Kept ONLY so an existing one can be found and
# carried across — a silent "your knowledge base is empty" would be the worst
# possible way to deliver this fix.
_LEGACY_HOME_DIRNAME = ".tausik"

_DB_FILENAME = "knowledge.db"


def default_store_display_path() -> str:
    """The default location, written the way help text should show it.

    Help text is read as an INSTRUCTION: a person told `~/.tausik/knowledge.db`
    goes there, finds nothing, and concludes their entries were never saved.
    Four CLI help strings said exactly that after the store moved (#222) — the
    code went to the new directory and every hand-written copy of the old path
    stayed behind. Built from the constants so the next move carries the words
    with it instead of leaving them.

    Deliberately NOT `knowledge_db_path()`. That function answers "where is MY
    store right now", honouring `TAUSIK_HOME`; printing one machine's override
    into static help would describe that machine rather than the product. Forward
    slashes and a literal `~` for the same reason — this is documentation of a
    default, not a path to open.
    """
    return f"~/{_HOME_DIRNAME}/{_DB_FILENAME}"


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
    """The USER-level directory — `$TAUSIK_HOME` or `~/.tausik-knowledge`.

    Deliberately does NOT consult `TAUSIK_DIR` or search upward from the cwd.
    Those answer "which project am I in"; this answers "who am I", and a shared
    store that resolved through a project handle would be shared with nobody.

    The name matters as much as the location — see `_HOME_DIRNAME`.

    VALIDATED, and that is load-bearing rather than defensive. The write path
    does not scrub, and the reason recorded for it is that this file stays on
    this machine. `TAUSIK_HOME` is what decides whether that is true, so it is
    checked here rather than assumed: a network path or a cloud-sync directory
    is refused, and a git work tree is neutralised with a `.gitignore` instead
    of refused, because refusing would reject the default location for everyone
    who keeps their home in a dotfiles repository. See `knowledge_home_guard`.

    The returned path is RESOLVED — symlinks and junctions followed — so every
    caller sees the directory that will actually be written to, which is also
    the one the checks were run against.
    """
    override = os.environ.get(_HOME_ENV)
    if override is not None:
        return assert_safe_knowledge_home(override, _DB_FILENAME)
    default = os.path.join(os.path.expanduser("~"), _HOME_DIRNAME)
    return assert_safe_knowledge_home(default, _DB_FILENAME)


def legacy_knowledge_db_path() -> str:
    """Where the store lived before the rename. Only ever read, never created."""
    return os.path.join(os.path.expanduser("~"), _LEGACY_HOME_DIRNAME, _DB_FILENAME)


def adopt_legacy_store_if_present() -> str | None:
    """Carry a store from the old location to the new one. Returns the source, or None.

    Runs on the read/write paths rather than as a migration command, because a
    migration nobody runs is a knowledge base nobody has. Copies rather than
    moves: the old directory may hold other things (it did — stray files written
    by tests while it was masquerading as a project), and deleting inside a
    user's home is theirs to decide, not ours.

    Only ever adopts when the new location is absent, so it cannot overwrite a
    store that already exists here.
    """
    if os.environ.get(_HOME_ENV):
        # An explicit home was named. Adopting into it would be reaching for
        # data the caller did not point at.
        return None
    target = os.path.join(knowledge_home(), _DB_FILENAME)
    if os.path.isfile(target):
        return None
    legacy = legacy_knowledge_db_path()
    if not os.path.isfile(legacy):
        return None
    import shutil

    os.makedirs(os.path.dirname(target), exist_ok=True)
    shutil.copy2(legacy, target)
    return legacy


def knowledge_db_path() -> str:
    """Absolute path of the shared knowledge database. Says nothing about existence."""
    return os.path.join(knowledge_home(), _DB_FILENAME)


def knowledge_db_exists() -> bool:
    """True iff the shared store is on disk — at the current OR the old address.

    Adopts first, so `exists()` and a subsequent read agree. Two functions that
    disagree about whether something exists is how a caller ends up reporting
    "nothing to back up" over a database full of records.
    """
    adopt_legacy_store_if_present()
    return os.path.isfile(knowledge_db_path())


def _configure(conn: sqlite3.Connection) -> sqlite3.Connection:
    conn.row_factory = sqlite3.Row
    # WAL: readers never block the writer and vice versa — mandatory for a file
    # several projects hold open at once. busy_timeout: when two DO collide,
    # wait rather than raise "database is locked" into a user's search.
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def stored_schema_version(conn: sqlite3.Connection) -> int:
    """`PRAGMA user_version` of an OPEN store. 0 means a store nobody stamped yet."""
    row = conn.execute("PRAGMA user_version").fetchone()
    return int(row[0]) if row else 0


def require_compatible_schema(conn: sqlite3.Connection) -> None:
    """Refuse to touch a store written by a NEWER framework than this one.

    One machine, several projects, and each may sit on a different TAUSIK
    version — but they all share this one file. When a newer project has already
    written it, an older one has three options and only one of them is honest.

    It could read anyway, and get a schema it does not understand. It could fall
    back to project-only knowledge, which is the tempting one and the worst: the
    person keeps working, notices nothing, and discovers a week later that shared
    hints quietly stopped arriving — with no event to trace it back to. Or it can
    refuse and say why. This does the third.

    The refusal is fatal rather than a warning line, deliberately. A warning in
    the middle of search output is exactly what a busy reader skips, and the
    whole failure mode being prevented here is one that hides. The cost is real
    and worth naming: until the framework is updated, commands touching shared
    knowledge stop working in that project. The reverse skew — a store OLDER
    than this code — is not an error at all; it migrates on open.

    This also has to run BEFORE the schema is stamped. `init_knowledge_schema`
    writes `user_version` unconditionally, so an older framework opening a newer
    store would rewrite the marker DOWNWARD and destroy the evidence that any
    skew existed — for every other project on the machine, not just its own.
    """
    from tausik_utils import ServiceError

    found = stored_schema_version(conn)
    if found > SCHEMA_VERSION:
        raise ServiceError(
            f"The shared knowledge database at {knowledge_db_path()} was written by a "
            f"NEWER TAUSIK (schema v{found}); this project understands up to v{SCHEMA_VERSION}. "
            "Update TAUSIK in this project to use shared knowledge again. "
            "Nothing was read or written, and the store was left untouched."
        )


def init_knowledge_schema(conn: sqlite3.Connection) -> None:
    """Create the knowledge objects if absent. Idempotent — safe to run always.

    Stamps the version LAST, and only for a store this code is allowed to own:
    `connect_knowledge_db` runs the compatibility check first, so by the time
    this writes `user_version` the value can only move up (a migration) or stay.
    """
    conn.executescript(KNOWLEDGE_SQL)
    conn.executescript(KNOWLEDGE_FTS_SQL)
    apply_open_migrations(conn)
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
    # Before deciding the store is absent: it may simply be at the old address.
    # Checked on the READ path too, so a person who never writes again still
    # finds what they had — the alternative is a silent "you have no shared
    # knowledge" for someone holding thousands of records.
    adopt_legacy_store_if_present()

    path = knowledge_db_path()
    if not create and not os.path.isfile(path):
        return None
    home = os.path.dirname(path)
    os.makedirs(home, exist_ok=True)
    # After the directory exists, and only here — never from `knowledge_home()`,
    # which read paths reach. Inside a git work tree the store needs an ignore
    # rule of its own, or the first `git add -A` commits everything this person
    # has learned anywhere. Re-decided on every open rather than cached: a
    # directory can become a repository while a long-lived process is running,
    # and a remembered "it was not one" would be the guard switching itself off.
    protect_home_in_git(home, _DB_FILENAME)
    fresh = not os.path.isfile(path)
    conn = _configure(sqlite3.connect(path, timeout=10, check_same_thread=False))
    try:
        # Close before propagating: the caller never receives this handle, so
        # nothing else can close it, and a leaked one holds the WAL open for
        # every other project pointing at this file. This covers the schema
        # setup too, not only the version check. It used to guard the check
        # alone, on the reading that the setup was CREATE-IF-NOT-EXISTS and
        # could not realistically fail; `redact_stored_origins` made that
        # reading false — it does per-row work, so a lock contended by another
        # project is now a way for this to raise with a live handle in hand.
        require_compatible_schema(conn)
        init_knowledge_schema(conn)
    except Exception:
        conn.close()
        raise
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
