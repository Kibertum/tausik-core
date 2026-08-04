"""An older framework refuses a newer shared store — loudly, and without touching it.

The failure this prevents is the quiet one. Several projects on one machine sit
on different TAUSIK versions and share a single knowledge file; when an older
project meets a newer store, falling back to project-only knowledge would let
the person keep working and notice nothing, then discover a week later that
shared hints stopped arriving with no event to trace it to.

Two halves matter equally: the refusal must happen, and the store must come
through it unchanged. An older framework that stamped the version down would
erase the evidence of skew for every OTHER project too.
"""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import knowledge_db  # noqa: E402
import knowledge_read  # noqa: E402
import knowledge_write  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/knowledge_db.py"]


@pytest.fixture(autouse=True)
def home(monkeypatch, tmp_path):
    monkeypatch.setenv("TAUSIK_HOME", str(tmp_path / "home"))
    return tmp_path / "home"


def _make_store_at_version(version: int) -> None:
    """Create a real store, then stamp it as some other framework's version."""
    conn = knowledge_db.connect_knowledge_db(create=True)
    assert conn is not None
    try:
        conn.execute(
            "INSERT INTO memory (entry_uuid, type, title, content, created_at, updated_at) "
            "VALUES ('u1', 'pattern', 'существующая запись', 'тело', '2026-08-02T00:00:00Z', "
            "'2026-08-02T00:00:00Z')"
        )
        conn.execute(f"PRAGMA user_version={version}")
        conn.commit()
    finally:
        conn.close()


def _raw_version() -> int:
    """Read the stamp without going through the guard."""
    conn = sqlite3.connect(knowledge_db.knowledge_db_path())
    try:
        return int(conn.execute("PRAGMA user_version").fetchone()[0])
    finally:
        conn.close()


class TestANewerStoreIsRefused:
    """AC1: loud, and it names both versions."""

    def test_opening_raises_and_names_both_versions(self):
        newer = knowledge_db.SCHEMA_VERSION + 1
        _make_store_at_version(newer)

        with pytest.raises(ServiceError) as e:
            knowledge_db.connect_knowledge_db(create=False)

        message = str(e.value)
        assert f"v{newer}" in message, "the store's version is missing from the message"
        assert f"v{knowledge_db.SCHEMA_VERSION}" in message, "this code's version is missing"
        assert "update tausik" in message.lower(), "the message does not say what to do"

    def test_the_message_says_nothing_was_touched(self):
        """A reader has to know whether their data is at risk before deciding."""
        _make_store_at_version(knowledge_db.SCHEMA_VERSION + 1)
        with pytest.raises(ServiceError) as e:
            knowledge_db.connect_knowledge_db(create=True)
        assert "left untouched" in str(e.value)

    def test_a_far_newer_store_is_refused_too(self):
        """Not an off-by-one check — any version above this one is unreadable."""
        _make_store_at_version(knowledge_db.SCHEMA_VERSION + 99)
        with pytest.raises(ServiceError):
            knowledge_db.connect_knowledge_db(create=False)


class TestTheStoreSurvivesTheRefusal:
    """The half that is easy to forget, and the one that harms every other project."""

    def test_the_version_stamp_is_not_written_down(self):
        """`init_knowledge_schema` stamps unconditionally — the guard must precede it.

        Without that ordering an older framework would quietly rewrite the marker
        DOWNWARD on every open, and the next project to look would see no skew at
        all. The evidence of the problem would be destroyed by the code meant to
        detect it.
        """
        newer = knowledge_db.SCHEMA_VERSION + 1
        _make_store_at_version(newer)

        with pytest.raises(ServiceError):
            knowledge_db.connect_knowledge_db(create=True)

        assert _raw_version() == newer, "the guard rewrote the newer store's version stamp"

    def test_existing_rows_are_still_there(self):
        _make_store_at_version(knowledge_db.SCHEMA_VERSION + 1)
        with pytest.raises(ServiceError):
            knowledge_db.connect_knowledge_db(create=False)

        conn = sqlite3.connect(knowledge_db.knowledge_db_path())
        try:
            assert conn.execute("SELECT COUNT(*) FROM memory").fetchone()[0] == 1
        finally:
            conn.close()


class TestNoSilentDegradation:
    """AC2: the read and write paths must not turn this into a shrug."""

    def test_a_shared_write_does_not_fall_back_to_the_project(self):
        _make_store_at_version(knowledge_db.SCHEMA_VERSION + 1)
        with pytest.raises(ServiceError) as e:
            knowledge_write.write_memory("pattern", "заголовок", "тело")
        assert "NEWER TAUSIK" in str(e.value)

    def test_a_shared_read_does_not_quietly_return_nothing(self):
        """The tempting failure: an empty result set that looks like an empty store."""
        _make_store_at_version(knowledge_db.SCHEMA_VERSION + 1)
        with pytest.raises(ServiceError):
            knowledge_read.search_shared_memory("что угодно")

    def test_the_guard_is_not_swallowed_by_the_read_path_error_handling(self):
        """`_open` catches sqlite3.Error and OSError; ServiceError must pass through.

        If the guard were caught there it would become an ordinary degradation
        notice — a line in the output rather than a stop — which is precisely the
        outcome the fatal choice exists to avoid.
        """
        _make_store_at_version(knowledge_db.SCHEMA_VERSION + 1)
        with pytest.raises(ServiceError):
            knowledge_read.read_shared_block(3)


class TestTheBlockReportsSkewWithoutTakingTheSessionDown:
    """Where the guard must NOT be fatal, and why that is not a loophole.

    A newer store in one project would otherwise stop every OTHER project on the
    machine from starting a session — punishing people for a skew they did not
    create, and far past what "tell the user to update" asks for. So the
    display-only aggregate renders the refusal instead of propagating it. It is
    still visible every session until fixed, which is the property AC2 wants;
    what it is not is a silent fallback.
    """

    def test_the_block_still_renders_and_names_the_skew(self):
        import service_knowledge_aggregates as agg

        _make_store_at_version(knowledge_db.SCHEMA_VERSION + 1)

        class Be:
            def decision_list(self, n):
                return [{"id": 1, "decision": "проектное решение"}]

            def memory_list(self, mem_type, n):
                return [{"id": 1, "title": f"проектная {mem_type}"}]

        block = agg.build_memory_block(Be())
        assert "проектное решение" in block, "the project's own block was lost to the skew"
        assert "NEWER TAUSIK" in block, "the skew was swallowed — this is the silent fallback"
        assert f"v{knowledge_db.SCHEMA_VERSION + 1}" in block

    def test_the_compact_tail_behaves_the_same(self):
        import service_knowledge_aggregates as agg

        _make_store_at_version(knowledge_db.SCHEMA_VERSION + 1)

        class Empty:
            def decision_list(self, n):
                return []

            def memory_list(self, mem_type, n):
                return []

        tail = "\n".join(agg.build_compact_memory_tail(Empty()))
        assert "NEWER TAUSIK" in tail


class TestAnOlderStoreIsNotAnError:
    """AC3: the reverse skew migrates rather than blocking."""

    def test_an_older_store_opens_and_is_brought_up_to_date(self):
        _make_store_at_version(0)
        conn = knowledge_db.connect_knowledge_db(create=False)
        assert conn is not None
        try:
            assert knowledge_db.stored_schema_version(conn) == knowledge_db.SCHEMA_VERSION
            assert conn.execute("SELECT COUNT(*) FROM memory").fetchone()[0] == 1, (
                "migration lost the rows it was supposed to carry forward"
            )
        finally:
            conn.close()

    def test_a_store_at_this_exact_version_is_untouched_and_usable(self):
        _make_store_at_version(knowledge_db.SCHEMA_VERSION)
        rows, warning = knowledge_read.search_shared_memory("запись")
        assert warning is None
        assert len(rows) == 1
