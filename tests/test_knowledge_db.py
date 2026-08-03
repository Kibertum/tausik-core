"""The shared knowledge store: where it lives, what it holds, and when it appears.

Four properties, one per acceptance criterion, each written so it fails for the
reason it names rather than for a neighbouring one.

The laziness test is the load-bearing one. `sqlite3.connect()` creates the file
it is handed, so "open and see" would spawn an empty shared database on every
`status` call in every project, for people who never opted in. That is a defect
you cannot see — the store exists, it is simply empty — which is why it is
pinned mechanically here rather than left to whoever reads the module.
"""

from __future__ import annotations

import os
import sqlite3
import sys
import threading

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import knowledge_db  # noqa: E402

# The basename heuristic already maps knowledge_db.py here, but the shared store
# is also reachable from home/project path resolution, which shares no basename
# with this file — so the guarded tree is declared rather than assumed.
CROSSCUTTING_SCOPE = ["scripts/knowledge_db.py"]

_TS = "2026-08-01T00:00:00Z"
_INS_MEMORY = (
    "INSERT INTO memory (entry_uuid, type, title, content, created_at, updated_at) "
    "VALUES (?, 'context', ?, 'c', '" + _TS + "', '" + _TS + "')"
)


@pytest.fixture(autouse=True)
def home(monkeypatch, tmp_path):
    """Point TAUSIK_HOME at a temp dir — never the developer's real ~/.tausik."""
    h = tmp_path / "home"
    monkeypatch.setenv("TAUSIK_HOME", str(h))
    return h


class TestWhereItLives:
    """AC1: `~/.tausik/knowledge.db`, overridable by TAUSIK_HOME."""

    def test_override_wins(self, home):
        assert knowledge_db.knowledge_db_path() == str(home / "knowledge.db")

    def test_default_is_under_the_user_home(self, monkeypatch):
        """Built from the CONSTANT, not from a literal.

        This asserted `~/.tausik/knowledge.db` and passed while that very name
        was capturing project discovery for everything under the home. A literal
        pins the spelling of the bug, not the property; the property lives in
        `test_shared_home_does_not_capture_project_discovery.py`.
        """
        monkeypatch.delenv("TAUSIK_HOME", raising=False)
        expected = os.path.join(os.path.expanduser("~"), knowledge_db._HOME_DIRNAME, "knowledge.db")
        assert knowledge_db.knowledge_db_path() == expected

    def test_the_project_handle_does_not_answer_for_the_user(self, monkeypatch, tmp_path):
        """TAUSIK_DIR selects a PROJECT. It must not move the shared store.

        Both variables end in `.tausik` and each is a plausible typo for the
        other; a fallback between them would put everyone's shared knowledge
        inside whichever repository happened to be open.
        """
        monkeypatch.delenv("TAUSIK_HOME", raising=False)
        monkeypatch.setenv("TAUSIK_DIR", str(tmp_path / "some-project" / ".tausik"))
        assert str(tmp_path) not in knowledge_db.knowledge_db_path()


class TestWhatItHolds:
    """AC2: knowledge only — and the project schema explicitly absent."""

    def test_only_knowledge_tables_exist(self):
        conn = knowledge_db.connect_knowledge_db(create=True)
        assert conn is not None
        try:
            names = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )
            }
        finally:
            conn.close()

        assert {"memory", "decisions", "snippets"} <= names
        forbidden = {
            "tasks",
            "sessions",
            "events",
            "verification_runs",
            "epics",
            "stories",
            "task_logs",
        }
        assert not (forbidden & names), (
            f"the project schema leaked into the shared store: {sorted(forbidden & names)}"
        )

    def test_fts_is_wired_to_each_table(self):
        conn = knowledge_db.connect_knowledge_db(create=True)
        assert conn is not None
        try:
            conn.execute(
                "INSERT INTO memory (entry_uuid, type, title, content, created_at, updated_at) "
                f"VALUES ('u1', 'pattern', 'Кэш инвалидируется по ключу', 'подробности', "
                f"'{_TS}', '{_TS}')"
            )
            conn.commit()
            hits = conn.execute("SELECT rowid FROM fts_memory WHERE fts_memory MATCH ?", ("кэш",))
            assert hits.fetchone() is not None, "an inserted row was not indexed by FTS"
        finally:
            conn.close()

    def test_a_shared_row_does_not_depend_on_a_project_row(self):
        """`origin_slug` NAMES a project's task; it must not be a foreign key.

        A shared record has to outlive the project it came from. If the origin
        were enforced, importing knowledge would require importing tasks too.
        """
        conn = knowledge_db.connect_knowledge_db(create=True)
        assert conn is not None
        try:
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute(
                "INSERT INTO decisions (entry_uuid, decision, origin_project, origin_slug, "
                f"created_at) VALUES ('u2', 'Решение', 'some-repo', 'task-elsewhere', '{_TS}')"
            )
            conn.commit()
            assert conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == 1
        finally:
            conn.close()

    def test_identity_is_unique_and_required(self):
        conn = knowledge_db.connect_knowledge_db(create=True)
        assert conn is not None
        try:
            conn.execute(_INS_MEMORY, ("dup", "первая"))
            conn.commit()
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(_INS_MEMORY, ("dup", "вторая"))
        finally:
            conn.close()


class TestConcurrency:
    """AC3: WAL and a non-zero busy timeout, because this file is multi-writer."""

    def test_wal_and_busy_timeout_are_set(self):
        conn = knowledge_db.connect_knowledge_db(create=True)
        assert conn is not None
        try:
            assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
            assert conn.execute("PRAGMA busy_timeout").fetchone()[0] > 0
        finally:
            conn.close()

    def test_two_connections_writing_at_once_do_not_raise_database_is_locked(self):
        """The scenario is ordinary, not exotic: two IDEs, two projects, one file."""
        opened = knowledge_db.connect_knowledge_db(create=True)
        assert opened is not None
        opened.close()
        errors: list[Exception] = []
        barrier = threading.Barrier(2)

        def writer(tag: str) -> None:
            conn = knowledge_db.connect_knowledge_db(create=True)
            if conn is None:
                errors.append(RuntimeError("store vanished"))
                return
            try:
                barrier.wait(timeout=10)
                for i in range(25):
                    conn.execute(_INS_MEMORY, (f"{tag}-{i}", f"{tag} {i}"))
                    conn.commit()
            except Exception as e:  # noqa: BLE001 — seeing it IS the assertion
                errors.append(e)
            finally:
                conn.close()

        threads = [threading.Thread(target=writer, args=(t,)) for t in ("a", "b")]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert not errors, f"concurrent writers failed: {errors!r}"
        conn = knowledge_db.connect_knowledge_db(create=False)
        assert conn is not None
        try:
            assert conn.execute("SELECT COUNT(*) FROM memory").fetchone()[0] == 50
        finally:
            conn.close()


class TestLazyAndIdempotent:
    """AC4: nothing exists until something writes, and opening twice makes one file."""

    def test_reading_a_missing_store_creates_nothing(self, home):
        assert knowledge_db.knowledge_db_exists() is False
        assert knowledge_db.connect_knowledge_db(create=False) is None
        assert knowledge_db.knowledge_schema_version() is None
        assert not home.exists(), (
            "a read path brought the shared store into existence — this is the "
            "defect the create flag exists to prevent"
        )

    def test_the_write_path_creates_it_once(self):
        conn = knowledge_db.connect_knowledge_db(create=True)
        assert conn is not None
        conn.close()
        assert knowledge_db.knowledge_db_exists() is True
        first = os.stat(knowledge_db.knowledge_db_path()).st_ino

        again = knowledge_db.connect_knowledge_db(create=True)
        assert again is not None
        again.close()
        assert os.stat(knowledge_db.knowledge_db_path()).st_ino == first, (
            "a second open replaced the file instead of reusing it"
        )

    def test_schema_init_is_idempotent(self):
        conn = knowledge_db.connect_knowledge_db(create=True)
        assert conn is not None
        try:
            knowledge_db.init_knowledge_schema(conn)
            knowledge_db.init_knowledge_schema(conn)
            assert conn.execute("PRAGMA user_version").fetchone()[0] == knowledge_db.SCHEMA_VERSION
        finally:
            conn.close()

    def test_version_is_stamped_for_the_guard_that_will_read_it(self):
        conn = knowledge_db.connect_knowledge_db(create=True)
        assert conn is not None
        conn.close()
        assert knowledge_db.knowledge_schema_version() == knowledge_db.SCHEMA_VERSION
