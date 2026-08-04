"""A shared row says WHICH project it came from without saying WHERE it lives.

The store is one file under one OS account, and one person routinely works for
several clients out of one home directory — the path of this repository names a
client. So the property under test is not "the display is tidy", it is: open the
database with anything at all, read `origin_project`, and learn no directory
names. Every test here is written against the stored value for that reason, and
the read-path assertions live in `test_knowledge_read` where they belong.
"""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import knowledge_db  # noqa: E402
import knowledge_migrations as km  # noqa: E402
import knowledge_origin as ko  # noqa: E402
import knowledge_write  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/knowledge_origin.py", "scripts/knowledge_write.py"]

_TS = "2026-08-03T00:00:00Z"
CLIENT_PATH = r"D:\Work\Kibertum\clients\acme\repo"


@pytest.fixture(autouse=True)
def home(monkeypatch, tmp_path):
    monkeypatch.setenv("TAUSIK_HOME", str(tmp_path / "home"))
    return tmp_path / "home"


def _open() -> sqlite3.Connection:
    conn = knowledge_db.connect_knowledge_db(create=True)
    assert conn is not None
    return conn


def _origins(table: str) -> list[str | None]:
    conn = _open()
    try:
        return [r[0] for r in conn.execute(f"SELECT origin_project FROM {table} ORDER BY id")]
    finally:
        conn.close()


class TestTheLabelItself:
    """AC1-AC3: legible, stable, collision-free, and not a path."""

    def test_a_client_directory_does_not_survive_into_the_label(self):
        label = ko.origin_label_for(CLIENT_PATH)
        assert "acme" not in label
        assert "Kibertum" not in label
        assert "/" not in label and "\\" not in label
        assert label.startswith("repo@")

    def test_two_projects_with_the_same_basename_stay_distinguishable(self):
        """The reason the absolute root was stored in the first place."""
        a = ko.origin_label_for(r"D:\Work\clientA\core")
        b = ko.origin_label_for(r"D:\Work\clientB\core")
        assert a != b
        assert a.startswith("core@") and b.startswith("core@")

    def test_the_same_root_always_fingerprints_the_same(self):
        assert ko.origin_fingerprint(CLIENT_PATH) == ko.origin_fingerprint(CLIENT_PATH)

    def test_a_root_spelled_differently_is_still_the_same_project(self):
        """No mapping table can help here; canonicalisation has to."""
        assert ko.origin_fingerprint(r"D:\Work\repo") == ko.origin_fingerprint("D:/Work/repo")
        assert ko.origin_fingerprint(r"D:\Work\repo\\") == ko.origin_fingerprint(r"D:\Work\repo")

    def test_a_project_recognises_its_own_row_without_a_dictionary(self):
        """Why no reverse mapping is stored: the label is COMPUTED, not assigned."""
        mine = ko.origin_label_for(CLIENT_PATH)
        assert ko.origin_label_for(CLIENT_PATH) == mine
        assert ko.origin_label_for(r"D:\Work\somebody-else\repo") != mine

    def test_a_root_with_no_basename_produces_a_well_formed_label(self):
        """AC9 boundary: a drive root must not yield a label starting with `@`."""
        label = ko.origin_label_for("/")
        assert ko.is_origin_label(label), label
        assert not label.startswith("@")


class TestWhatCountsAsAlreadyDone:
    """AC4/AC9: the migration must not touch what it did not create."""

    @pytest.mark.parametrize("value", [None, "", "brain:c857d09db23e6822", "repo@deadbeef"])
    def test_values_that_disclose_nothing_are_left_alone(self, value):
        assert ko.redacted_origin(value) is None

    @pytest.mark.parametrize("value", ["team/backend", "a/b", "some\\tag"])
    def test_a_free_text_value_that_merely_contains_a_separator_is_not_a_path(self, value):
        """`origin_project` is free text by design, and the rewrite is one-way.

        A predicate of "contains a slash" would fingerprint a hand-set tag into
        `backend@a52261f0` on the next open, destroying a legitimate value
        irreversibly to remove a disclosure that was never there.
        """
        assert ko.redacted_origin(value) is None

    @pytest.mark.parametrize(
        "value",
        [
            r"D:\Work\Kibertum\clients\acme\repo",
            "D:/Work/Kibertum/clients/acme/repo",
            "/home/me/work/clients/acme/repo",
        ],
    )
    def test_an_absolute_path_is_rewritten_whatever_platform_wrote_it(self, value):
        """A row written on Windows must be redacted when read on Linux too —
        which is why this cannot be `os.path.isabs`."""
        rewritten = ko.redacted_origin(value)
        assert rewritten is not None
        assert rewritten.startswith("repo@")
        assert "acme" not in rewritten

    def test_the_migration_never_touches_the_filesystem(self, monkeypatch):
        """A stored origin may name a share that no longer answers.

        This runs on EVERY open of the shared store, in every project on the
        machine. `realpath` on an unreachable UNC or a disconnected mapped drive
        blocks for the OS's full network timeout — freezing not one command but
        all of them, uninterruptibly. A label computed lexically is worth
        incomparably more than one computed correctly two minutes later.
        """
        calls: list[str] = []
        real = os.path.realpath
        monkeypatch.setattr(os.path, "realpath", lambda p: (calls.append(p), real(p))[1])
        assert ko.redacted_origin(r"\\unreachable-server\share\proj") is not None
        assert ko.redacted_origin(CLIENT_PATH) is not None
        assert calls == [], f"the migration consulted the filesystem: {calls}"

    @pytest.mark.parametrize(
        ("a", "b"),
        [
            (r"D:\Work\Kibertum\clients\acme\repo", "D:/Work/Kibertum/clients/acme/repo"),
            (r"D:\Work\Repo", r"d:\work\repo"),
        ],
    )
    def test_a_stored_path_fingerprints_the_same_on_any_platform(self, a, b):
        """The store is shared across a machine, WSL included, so the same row
        must not acquire two identities depending on who opened it first.
        `normcase` is a no-op on POSIX, which is why case folding is explicit."""
        assert ko.origin_label_for(a, resolve=False) == ko.origin_label_for(b, resolve=False)

    def test_rewriting_is_idempotent(self):
        once = ko.redacted_origin(CLIENT_PATH)
        assert ko.redacted_origin(once) is None


class TestTheStoredRowsGetFixed:
    """AC4/AC5: the fix reaches rows written before it existed, in all three tables."""

    def _seed_legacy(self) -> None:
        conn = _open()
        try:
            conn.execute(
                "INSERT INTO memory (entry_uuid, type, title, content, origin_project, "
                "created_at, updated_at) VALUES ('m0', 'pattern', 'т', 'тело', ?, ?, ?)",
                (CLIENT_PATH, _TS, _TS),
            )
            conn.execute(
                "INSERT INTO decisions (entry_uuid, decision, origin_project, created_at) "
                "VALUES ('d0', 'решение', ?, ?)",
                (CLIENT_PATH, _TS),
            )
            conn.execute(
                "INSERT INTO snippets (entry_uuid, hash, language, code, origin_project, "
                "created_at) VALUES ('s0', 'h0', 'python', 'x = 1', ?, ?)",
                (CLIENT_PATH, _TS),
            )
            conn.commit()
        finally:
            conn.close()

    @pytest.mark.parametrize("table", ["memory", "decisions", "snippets"])
    def test_every_table_is_migrated_not_just_the_first(self, table):
        """The form is closed, not the one case that was noticed."""
        self._seed_legacy()
        stored = _origins(table)[0]
        assert stored is not None
        assert "acme" not in stored
        assert stored.startswith("repo@")

    def test_a_second_open_changes_nothing(self):
        self._seed_legacy()
        first = _origins("memory")
        assert _origins("memory") == first

    def test_the_migration_reports_how_much_was_disclosed(self):
        """The count is the evidence; a silent pass would be indistinguishable
        from a pass that matched nothing."""
        self._seed_legacy()
        # Opened raw, so nothing migrates behind the assertion: `_seed_legacy`
        # inserted its three rows AFTER the open that would have caught them.
        conn = sqlite3.connect(knowledge_db.knowledge_db_path())
        try:
            assert km.redact_stored_origins(conn) == 3
            conn.commit()
            assert km.redact_stored_origins(conn) == 0
        finally:
            conn.close()

    def test_a_row_with_no_origin_survives_the_migration(self):
        """AC9: NULL is not a disclosure and must not become a fabricated label."""
        conn = _open()
        try:
            conn.execute(
                "INSERT INTO decisions (entry_uuid, decision, origin_project, created_at) "
                "VALUES ('d-null', 'решение', NULL, ?)",
                (_TS,),
            )
            conn.commit()
        finally:
            conn.close()
        assert _origins("decisions") == [None]


class TestAFailedMigrationDoesNotLeakTheHandle:
    """The store is shared, so a leaked connection is everyone's problem.

    `connect_knowledge_db` closed the handle when the VERSION CHECK raised, on
    the reading that the schema setup beside it was CREATE-IF-NOT-EXISTS and
    could not realistically fail. The migration made that reading false: it does
    per-row work, so a contended lock is now a way to raise holding a live
    handle the caller never receives and therefore can never close — and a
    leaked handle keeps the WAL open for every other project on the machine.
    """

    def test_the_connection_is_closed_when_the_migration_raises(self, monkeypatch):
        _open().close()  # the store must already exist, so this is not the create path

        opened: list[sqlite3.Connection] = []
        real_configure = knowledge_db._configure

        def _spy(conn):
            opened.append(conn)
            return real_configure(conn)

        def _boom(_conn):
            raise sqlite3.OperationalError("database is locked")

        monkeypatch.setattr(knowledge_db, "_configure", _spy)
        monkeypatch.setattr(knowledge_db, "apply_open_migrations", _boom)

        with pytest.raises(sqlite3.OperationalError):
            knowledge_db.connect_knowledge_db(create=True)

        assert opened, "the test did not observe a connection being opened"
        for conn in opened:
            with pytest.raises(sqlite3.ProgrammingError):
                conn.execute("SELECT 1")


class TestSnippetSourceFiles:
    """AC6/AC9: the other column that carried the machine's directory layout."""

    def test_a_path_inside_the_project_becomes_relative(self):
        root = os.path.join(os.sep, "work", "clients", "acme", "repo")
        got = ko.relative_source_file(os.path.join(root, "scripts", "a.py"), root)
        assert got == "scripts/a.py"

    def test_a_path_outside_the_project_does_not_climb_out_of_it(self):
        """A `../../` chain would spell the same directory names, relatively."""
        root = os.path.join(os.sep, "work", "clients", "acme", "repo")
        got = ko.relative_source_file(
            os.path.join(os.sep, "work", "clients", "bravo", "x.py"), root
        )
        assert got == "x.py"
        assert ".." not in got
        assert "bravo" not in got

    @pytest.mark.parametrize("value", [None, "", "already/relative.py"])
    def test_values_that_are_not_absolute_are_returned_unchanged(self, value):
        assert ko.relative_source_file(value, os.sep + "root") == value

    def test_the_stored_row_is_relative_and_not_just_the_helper(self, tmp_path, monkeypatch):
        """The helper is unit-tested above; this is the WIRING.

        A wrong root, a swapped argument or a normalisation applied after the
        INSERT would all leave the pure function correct and the stored row
        absolute — which is the only thing a reader of the store ever sees.
        """
        root = tmp_path / "proj"
        (root / ".tausik").mkdir(parents=True)
        (root / "scripts").mkdir()
        monkeypatch.setenv("TAUSIK_DIR", str(root / ".tausik"))
        monkeypatch.chdir(root)

        knowledge_write.write_snippet(
            code="x = 1\n",
            language="python",
            source_file=str(root / "scripts" / "a.py"),
        )

        conn = _open()
        try:
            row = conn.execute("SELECT source_file, origin_project FROM snippets").fetchone()
        finally:
            conn.close()
        assert row[0] == "scripts/a.py"
        assert not os.path.isabs(row[0])
        assert row[1].startswith("proj@")


class TestAWriteThatCannotAttributeItselfFails:
    """AC9: `find_tausik_dir` falls back to the cwd; this path must not accept it."""

    def test_writing_from_outside_any_project_raises_and_names_why(self, tmp_path, monkeypatch):
        elsewhere = tmp_path / "not-a-project"
        elsewhere.mkdir()
        monkeypatch.chdir(elsewhere)
        monkeypatch.delenv("TAUSIK_DIR", raising=False)
        with pytest.raises(ServiceError) as excinfo:
            knowledge_write.write_memory("pattern", "заголовок", "тело")
        message = str(excinfo.value)
        assert "no TAUSIK project" in message
        assert "Nothing was written" in message

    def test_nothing_was_written(self, tmp_path, monkeypatch):
        """The message claims it; this is the claim being checked."""
        elsewhere = tmp_path / "not-a-project"
        elsewhere.mkdir()
        monkeypatch.chdir(elsewhere)
        monkeypatch.delenv("TAUSIK_DIR", raising=False)
        with pytest.raises(ServiceError):
            knowledge_write.write_memory("pattern", "заголовок", "тело")
        if os.path.isfile(knowledge_db.knowledge_db_path()):
            assert _origins("memory") == []


class TestAbsolutenessIsSpellingNotInterpreterOpinion:
    """The redaction must not depend on the OS, or on the Python minor.

    `relative_source_file` asked `os.path.isabs`, and Python 3.13 changed
    `ntpath.isabs`: on Windows a path with one leading separator and no drive
    letter stopped being absolute. The function then returned such a path
    unchanged — the machine's directory layout left in the column this redaction
    exists to clear, on one platform, from one minor release on, silently. The
    assertions below name no platform and no version on purpose: that they hold
    everywhere is the property.
    """

    def test_the_predicate_reads_the_spelling_on_every_platform(self):
        """The unit-level property: what counts as absolute is fixed text.

        This is the assertion `os.path.isabs` could not make. A drive-less
        rooted path is absolute here on Linux and on Windows, on 3.12 and on
        3.13 — because the question is about the string, not about the host.
        """
        assert ko._ABSOLUTE_RE.match("/work/clients/acme/repo/a.py")
        assert ko._ABSOLUTE_RE.match(r"\work\clients\acme\repo\a.py")
        assert ko._ABSOLUTE_RE.match(r"D:\Work\clients\acme")
        assert ko._ABSOLUTE_RE.match("d:/Work/clients/acme")
        assert not ko._ABSOLUTE_RE.match("team/backend")
        assert not ko._ABSOLUTE_RE.match("already/relative.py")

    def test_a_rooted_path_in_this_platforms_spelling_is_redacted(self):
        """End to end, in the separator this host actually uses.

        A backslash path handed to a POSIX host cannot be split into segments
        by anyone, so the end-to-end claim is made in the spelling of the
        running platform; the cross-platform half is the predicate above. On
        Windows this is exactly the case Python 3.13 broke.
        """
        root = os.path.join(os.sep, "work", "clients", "acme", "repo")
        got = ko.relative_source_file(os.path.join(root, "scripts", "a.py"), root)
        assert got == "scripts/a.py"
        assert "clients" not in got and "acme" not in got

    def test_a_path_outside_the_project_still_collapses_to_a_basename(self):
        """NEGATIVE: the redaction must not weaken to make the check above pass."""
        got = ko.relative_source_file("/work/clients/bravo/x.py", "/work/clients/acme/repo")
        assert got == "x.py"
        assert ".." not in got and "bravo" not in got

    def test_a_value_that_merely_contains_a_separator_is_left_alone(self):
        """NEGATIVE: `origin_project` is free text; `team/backend` is not a path."""
        assert ko.relative_source_file("team/backend", "/root") == "team/backend"
        assert ko.relative_source_file("already/relative.py", "/root") == "already/relative.py"
