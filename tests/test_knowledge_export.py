"""The shared store gets a backup that a person can read and a restore that works.

The round trip is the point. A backup nobody has restored is a hypothesis, and
this one has a specific way of being wrong: the frontmatter writer escapes the
backslash FIRST, and a reader that unescaped in the wrong order would read a
literal `\n` as a line break, corrupting a field while reporting success. So the
round trip is asserted on content, not on counts.

The backslashes are carried by `source_file` and by memory content rather than
by `origin_project`. That column held an absolute Windows path on every row
until it became a `basename@fingerprint` label, and the store now rewrites any
path it finds there on open — so a payload parked in it would be redacted
before the round trip could say anything about escaping.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import knowledge_db  # noqa: E402
import knowledge_export as kx  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/knowledge_export.py"]

_TS = "2026-08-02T00:00:00Z"

# Deliberately nasty: a Windows path (backslashes), an embedded newline, a quote,
# a tab, and Cyrillic. Each is a real shape the store holds, and each breaks a
# different naive reader.
AWKWARD_ORIGIN = r"D:\Work\Kibertum\clients\acme\repo"
AWKWARD_SOURCE_FILE = r"scripts\sub\dir\module.py"
AWKWARD_CONTENT = 'Первая строка\nВторая "в кавычках"\tи табуляция\\плюс слэш'


@pytest.fixture(autouse=True)
def home(monkeypatch, tmp_path):
    monkeypatch.setenv("TAUSIK_HOME", str(tmp_path / "home"))
    return tmp_path / "home"


def _seed(n: int = 2) -> None:
    conn = knowledge_db.connect_knowledge_db(create=True)
    assert conn is not None
    try:
        for i in range(n):
            conn.execute(
                "INSERT INTO memory (entry_uuid, type, title, content, tags, origin_project, "
                "origin_slug, created_at, updated_at) VALUES (?, 'pattern', ?, ?, ?, ?, ?, ?, ?)",
                (
                    f"m{i}",
                    f"запись {i}",
                    AWKWARD_CONTENT,
                    "a,b",
                    AWKWARD_ORIGIN,
                    "task-x",
                    _TS,
                    _TS,
                ),
            )
            conn.execute(
                "INSERT INTO decisions (entry_uuid, decision, rationale, origin_project, "
                "created_at) VALUES (?, ?, ?, ?, ?)",
                (f"d{i}", f"решение {i}", AWKWARD_CONTENT, AWKWARD_ORIGIN, _TS),
            )
            conn.execute(
                "INSERT INTO snippets (entry_uuid, hash, language, code, source_file, "
                "origin_project, created_at) VALUES (?, ?, 'python', ?, ?, ?, ?)",
                (
                    f"s{i}",
                    f"h{i}",
                    "def f():\n    pass\n",
                    AWKWARD_SOURCE_FILE,
                    AWKWARD_ORIGIN,
                    _TS,
                ),
            )
        conn.commit()
    finally:
        conn.close()


def _all_rows(table: str) -> list[dict]:
    conn = knowledge_db.connect_knowledge_db(create=False)
    assert conn is not None
    try:
        return [dict(r) for r in conn.execute(f"SELECT * FROM {table} ORDER BY entry_uuid")]
    finally:
        conn.close()


class TestRemoteDestinationsAreRefused:
    """AC1 — the guarantee decision #219 bought, and the one that must not erode."""

    @pytest.mark.parametrize(
        "dest",
        [
            "s3://bucket/knowledge",
            "https://example.com/backup",
            "http://example.com/backup",
            "ftp://host/dir",
            "sftp://host/dir",
            "gs://bucket/x",
            r"\\server\share\backup",
            "//server/share/backup",
        ],
    )
    def test_a_remote_destination_raises(self, dest):
        with pytest.raises(ServiceError) as e:
            kx.assert_local_destination(dest)
        assert "without redaction" in str(e.value).lower() or "not a local path" in str(e.value)

    def test_the_refusal_explains_why_rather_than_just_refusing(self):
        with pytest.raises(ServiceError) as e:
            kx.assert_local_destination("s3://bucket/x")
        msg = str(e.value)
        assert "free text" in msg, "the reason is missing"
        assert "local directory" in msg, "the message does not say what to do instead"
        # The reason has to be the CURRENT one. `origin_project` stopped being an
        # absolute path, so a message still naming one would send a reader to
        # look at a column that no longer discloses anything — and this test is
        # what would otherwise pin that stale claim in place.
        assert "absolute path of the project" not in msg

    @pytest.mark.parametrize("dest", ["D:/backups/kn", "/var/backups/kn", "backups", "./out"])
    def test_ordinary_local_paths_are_accepted(self, dest):
        assert os.path.isabs(kx.assert_local_destination(dest))

    def test_a_windows_drive_is_not_mistaken_for_a_url_scheme(self):
        """`urlparse("D:/x").scheme == "d"` — length is what tells them apart.

        The property under test is ACCEPTANCE: a drive letter must not be read
        as a network scheme and refused. The first version of this assertion
        checked that the returned string starts with `d:`, which is not the
        property — it is a side effect of `abspath` on Windows. On Linux
        `abspath("D:/backups/kn")` prepends the working directory, the drive
        letter stops being the first thing in the string, and the test failed
        while the code under test behaved exactly as intended.
        """
        result = kx.assert_local_destination("D:/backups/kn")
        assert "d:" in result.lower(), result
        assert "backups" in result and result.endswith("kn"), result

    def test_an_empty_destination_is_refused(self):
        with pytest.raises(ServiceError):
            kx.assert_local_destination("   ")


class TestTheRoundTripPreservesContent:
    """AC2 — restored content matches, checked field by field rather than by count."""

    def test_every_field_survives_export_and_restore(self, tmp_path, home):
        _seed()
        before = {t: _all_rows(t) for t in ("memory", "decisions", "snippets")}

        kx.export_shared_knowledge(str(tmp_path / "backup"))
        os.remove(knowledge_db.knowledge_db_path())  # the disk died
        kx.restore_shared_knowledge(str(tmp_path / "backup"))

        after = {t: _all_rows(t) for t in ("memory", "decisions", "snippets")}
        for table, rows in before.items():
            assert len(after[table]) == len(rows), f"{table}: row count changed"
            for old, new in zip(rows, after[table]):
                for field in kx.FIELDS[table]:
                    assert new[field] == old[field], (
                        f"{table}.{field} changed across the round trip: "
                        f"{old[field]!r} -> {new[field]!r}"
                    )

    def test_the_windows_path_comes_back_intact(self, tmp_path, home):
        """The specific corruption a wrong unescape order would produce."""
        _seed(1)
        kx.export_shared_knowledge(str(tmp_path / "b"))
        os.remove(knowledge_db.knowledge_db_path())
        kx.restore_shared_knowledge(str(tmp_path / "b"))
        assert _all_rows("snippets")[0]["source_file"] == AWKWARD_SOURCE_FILE

    def test_embedded_newlines_and_quotes_come_back_intact(self, tmp_path, home):
        _seed(1)
        kx.export_shared_knowledge(str(tmp_path / "b"))
        os.remove(knowledge_db.knowledge_db_path())
        kx.restore_shared_knowledge(str(tmp_path / "b"))
        assert _all_rows("memory")[0]["content"] == AWKWARD_CONTENT

    def test_restoring_twice_converges_instead_of_doubling(self, tmp_path, home):
        _seed(2)
        kx.export_shared_knowledge(str(tmp_path / "b"))
        counts = kx.restore_shared_knowledge(str(tmp_path / "b"))
        again = kx.restore_shared_knowledge(str(tmp_path / "b"))
        assert len(_all_rows("memory")) == 2, "a second restore duplicated records"
        assert counts["memory"] == 0, "the store already held these rows; nothing was inserted"
        assert again["memory"] == 0

    def test_counts_are_inserts_not_files_read(self, tmp_path, home):
        """A count of files read would report success while rows were skipped."""
        _seed(2)
        kx.export_shared_knowledge(str(tmp_path / "b"))
        os.remove(knowledge_db.knowledge_db_path())
        fresh = kx.restore_shared_knowledge(str(tmp_path / "b"))
        assert fresh["memory"] == 2

        # Second pass over the same files: 2 files read, 0 rows inserted.
        repeat = kx.restore_shared_knowledge(str(tmp_path / "b"))
        assert repeat["memory"] == 0, (
            "the count follows files rather than inserts — a lossy restore would "
            "report the same number as a complete one"
        )

    def test_a_conflict_that_is_not_an_identity_conflict_raises(self, tmp_path, home):
        """The defect `INSERT OR IGNORE` hid: a fresh uuid the store cannot accept.

        Snippets carry a UNIQUE hash alongside the uuid. A backup record with a
        NEW identity whose code already exists under a different one is not a
        duplicate — it is knowledge the backup holds and the store would lack.
        Suppressing every constraint dropped it in silence and still reported a
        success.
        """
        _seed(1)
        kx.export_shared_knowledge(str(tmp_path / "b"))

        conn = knowledge_db.connect_knowledge_db(create=False)
        assert conn is not None
        conn.execute("DELETE FROM snippets")
        conn.execute(
            "INSERT INTO snippets (entry_uuid, hash, language, code, created_at) "
            "VALUES ('other-uuid', 'h0', 'python', 'x', ?)",
            (_TS,),
        )
        conn.commit()
        conn.close()

        with pytest.raises(ServiceError) as e:
            kx.restore_shared_knowledge(str(tmp_path / "b"))
        assert "NOT a duplicate identity" in str(e.value)
        assert "unchanged" in str(e.value).lower()

    def test_a_failed_restore_commits_nothing(self, tmp_path, home):
        """All-or-nothing: a half-restored store looks like a working one."""
        _seed(2)
        dest = tmp_path / "b"
        kx.export_shared_knowledge(str(dest))
        os.remove(knowledge_db.knowledge_db_path())
        # Corrupt one record so the pass fails mid-way, after earlier files
        # have already been executed against the connection.
        bad = sorted((dest / "memory").glob("*.md"))[-1]
        bad.write_text("---\nno_uuid_here: 1\n---\n", encoding="utf-8")

        with pytest.raises(ServiceError):
            kx.restore_shared_knowledge(str(dest))

        assert _all_rows("memory") == [], (
            "rows from before the failure were committed — the restore was not atomic"
        )

    def test_a_record_with_an_empty_string_survives(self, tmp_path, home):
        """`""` and NULL take different branches in the writer and must not merge."""
        conn = knowledge_db.connect_knowledge_db(create=True)
        assert conn is not None
        conn.execute(
            "INSERT INTO decisions (entry_uuid, decision, rationale, created_at) "
            "VALUES ('e0', 'решение', '', ?)",
            (_TS,),
        )
        conn.commit()
        conn.close()

        kx.export_shared_knowledge(str(tmp_path / "b"))
        os.remove(knowledge_db.knowledge_db_path())
        kx.restore_shared_knowledge(str(tmp_path / "b"))
        assert _all_rows("decisions")[0]["rationale"] == "", "an empty string came back as NULL"


class TestTheBackupIsReadableAndStable:
    """AC3 + AC5 — one file per record, deterministic, and idempotent."""

    def test_one_file_per_record_with_a_readable_name(self, tmp_path, home):
        _seed(2)
        kx.export_shared_knowledge(str(tmp_path / "b"))
        files = sorted(os.listdir(tmp_path / "b" / "memory"))
        assert files == ["m0.md", "m1.md"]

    def test_field_order_is_fixed_not_taken_from_the_cursor(self, tmp_path, home):
        """Schema order would reshuffle every file the day a column is added."""
        _seed(1)
        kx.export_shared_knowledge(str(tmp_path / "b"))
        text = (tmp_path / "b" / "memory" / "m0.md").read_text(encoding="utf-8")
        keys = [ln.split(":", 1)[0] for ln in text.splitlines() if ":" in ln and ln != "---"]
        assert keys == list(kx.FIELDS["memory"])

    def test_a_second_backup_of_an_unchanged_store_writes_no_files(
        self, tmp_path, home, monkeypatch
    ):
        """Counts writes, not mtimes.

        An mtime comparison would pass FALSELY whenever both exports land in the
        same clock tick — and on Windows the default timer granularity is about
        15 ms, comfortably wider than two calls in a row. It would then be unable
        to tell "the file was left alone" from "the file was rewritten so fast
        the clock did not notice", which is precisely the regression it exists to
        catch. Counting the opens leaves no such gap.
        """
        _seed(2)
        dest = str(tmp_path / "b")
        kx.export_shared_knowledge(dest)

        opened: list[str] = []
        real_open = open

        def spy(path, mode="r", *a, **kw):
            if "w" in mode:
                opened.append(str(path))
            return real_open(path, mode, *a, **kw)

        monkeypatch.setattr("builtins.open", spy)
        kx.export_shared_knowledge(dest)
        assert opened == [], f"an unchanged store rewrote {len(opened)} file(s): {opened}"

    def test_a_deleted_record_disappears_from_the_backup(self, tmp_path, home):
        _seed(2)
        dest = str(tmp_path / "b")
        kx.export_shared_knowledge(dest)
        conn = knowledge_db.connect_knowledge_db(create=False)
        assert conn is not None
        conn.execute("DELETE FROM memory WHERE entry_uuid = 'm1'")
        conn.commit()
        conn.close()

        kx.export_shared_knowledge(dest)
        assert sorted(os.listdir(tmp_path / "b" / "memory")) == ["m0.md"], (
            "a deleted record lived on in the backup and would be resurrected by a restore"
        )

    def test_every_backup_file_is_readable_text_not_a_binary_dump(self, tmp_path, home):
        """AC3: logical export, asserted on CONTENT rather than on file names.

        Checking only for a `.db` suffix would miss the WAL and SHM companions,
        and would miss a byte copy renamed to anything else — while the claim
        being made is about the CONTENT: no binary pages, no FTS shadow tables.
        Every file must parse as UTF-8 and open with the record fence.
        """
        _seed(1)
        dest = tmp_path / "b"
        kx.export_shared_knowledge(str(dest))

        files = [os.path.join(dp, f) for dp, _d, fs in os.walk(dest) for f in fs]
        assert files, "the export produced nothing"
        for path in files:
            with open(path, "rb") as fh:
                raw = fh.read()
            assert b"SQLite format" not in raw[:64], f"{path} is a database file"
            text = raw.decode("utf-8")  # raises if binary
            assert text.startswith("---\n"), f"{path} is not a record file"

    def test_the_field_list_matches_the_real_schema(self, tmp_path, home):
        """The oracle has to be the SCHEMA, not the same constant the code uses.

        Comparing a round trip against `kx.FIELDS` compares the module with
        itself: add a column and forget to list it, and every such test stays
        green while the column silently stops being backed up — which is the
        exact regression the fixed field order exists to prevent. Reading
        `PRAGMA table_info` makes the database the judge.
        """
        conn = knowledge_db.connect_knowledge_db(create=True)
        assert conn is not None
        try:
            for table, fields in kx.FIELDS.items():
                columns = [
                    r[1] for r in conn.execute(f"PRAGMA table_info({table})") if r[1] != "id"
                ]
                assert sorted(columns) == sorted(fields), (
                    f"{table}: the backup covers {sorted(fields)} but the table has "
                    f"{sorted(columns)} — a column would be lost on every backup"
                )
                # TEXT affinity is what makes the reader's "everything comes back
                # as a string" correct. An INTEGER column would round-trip to a
                # string and change type silently, so the assumption is pinned.
                types = {r[1]: r[2].upper() for r in conn.execute(f"PRAGMA table_info({table})")}
                for field in fields:
                    assert types[field] == "TEXT", (
                        f"{table}.{field} is {types[field]}, not TEXT — the reader returns "
                        "strings, so this column would change type across a round trip"
                    )
        finally:
            conn.close()


class TestTheBackupNeverDeletesSomeoneElsesFiles:
    """The finding a reviewer reproduced live: a human's ADR vanished.

    The export reconciles deletions, and reconciliation over a directory it does
    not own is not a backup, it is a file shredder. The danger is concrete
    rather than theoretical: `state_export` writes `decisions/` and `memory/`
    under a project's own `tausik/` tree — the SAME names — so `--to` pointed at
    that tree would have removed the project's records on the first run.
    """

    def test_a_directory_with_foreign_files_is_refused(self, tmp_path, home):
        _seed(1)
        foreign = tmp_path / "docs"
        (foreign / "decisions").mkdir(parents=True)
        adr = foreign / "decisions" / "ADR-001-use-postgres.md"
        adr.write_text("# ADR 001\n", encoding="utf-8")

        with pytest.raises(ServiceError) as e:
            kx.export_shared_knowledge(str(foreign))

        assert "not a knowledge backup" in str(e.value)
        assert adr.exists(), "the file was deleted despite the refusal"
        assert adr.read_text(encoding="utf-8") == "# ADR 001\n"

    def test_an_empty_directory_is_fine(self, tmp_path, home):
        _seed(1)
        empty = tmp_path / "empty"
        empty.mkdir()
        kx.export_shared_knowledge(str(empty))
        assert (empty / kx.MANIFEST).exists()

    def test_a_previous_backup_directory_is_reused(self, tmp_path, home):
        """The guard must not block the normal case — backing up twice."""
        _seed(1)
        dest = str(tmp_path / "b")
        kx.export_shared_knowledge(dest)
        kx.export_shared_knowledge(dest)

    def test_pruning_spares_a_file_that_is_not_a_record(self, tmp_path, home):
        """Second line of defence, for a file dropped in after the first backup."""
        _seed(2)
        dest = tmp_path / "b"
        kx.export_shared_knowledge(str(dest))
        stray = dest / "memory" / "NOTES on this backup.md"
        stray.write_text("написано человеком", encoding="utf-8")

        kx.export_shared_knowledge(str(dest))
        assert stray.exists(), "reconciliation deleted a file the export never wrote"

    def test_a_record_whose_identity_is_not_a_safe_filename_is_refused(self, tmp_path, home):
        """`entry_uuid` becomes a path component and has no CHECK behind it."""
        conn = knowledge_db.connect_knowledge_db(create=True)
        assert conn is not None
        conn.execute(
            "INSERT INTO memory (entry_uuid, type, title, content, created_at, updated_at) "
            "VALUES ('../../escaped', 'pattern', 't', 'c', ?, ?)",
            (_TS, _TS),
        )
        conn.commit()
        conn.close()

        with pytest.raises(ServiceError) as e:
            kx.export_shared_knowledge(str(tmp_path / "b"))
        assert "safe filename" in str(e.value)


class TestFailuresAreLoud:
    """AC6 — the negative scenario, both halves."""

    def test_backing_up_a_store_that_does_not_exist_raises(self, tmp_path):
        with pytest.raises(ServiceError) as e:
            kx.export_shared_knowledge(str(tmp_path / "b"))
        assert "nothing was written" in str(e.value).lower()
        assert not os.path.exists(tmp_path / "b"), "a failed backup left a directory behind"

    def test_restoring_from_a_missing_directory_raises(self, tmp_path, home):
        with pytest.raises(ServiceError) as e:
            kx.restore_shared_knowledge(str(tmp_path / "nope"))
        assert "nothing was restored" in str(e.value).lower()

    def test_restoring_from_a_directory_that_is_not_a_backup_raises(self, tmp_path, home):
        stray = tmp_path / "stray"
        stray.mkdir()
        (stray / "readme.md").write_text("не бэкап", encoding="utf-8")
        with pytest.raises(ServiceError) as e:
            kx.restore_shared_knowledge(str(stray))
        assert "manifest" in str(e.value).lower()

    def test_a_backup_from_a_newer_schema_is_refused(self, tmp_path, home):
        _seed(1)
        dest = tmp_path / "b"
        kx.export_shared_knowledge(str(dest))
        (dest / "manifest.md").write_text(
            f"---\nschema_version: {knowledge_db.SCHEMA_VERSION + 1}\n---\n", encoding="utf-8"
        )
        with pytest.raises(ServiceError) as e:
            kx.restore_shared_knowledge(str(dest))
        assert "update tausik" in str(e.value).lower()
