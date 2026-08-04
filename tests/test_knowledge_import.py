"""Bringing the wiki mirror home: once, idempotently, and honest about origin.

Years of decisions were mirrored to Notion by a classifier deciding on their
behalf. That mirroring is gone (decision #221); what remains is a local copy
holding records the framework can otherwise no longer read. This import walks it
into the shared store so the knowledge outlives the account it was published to.

The two properties worth guarding are idempotence — because a rerun that
re-imports everything silently triples a knowledge base — and honesty about
provenance, because the mirror knows a project HASH and not a name, and dressing
a hash up as a path would invent a directory that never existed.
"""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import knowledge_db  # noqa: E402
import knowledge_import as ki  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/knowledge_import.py"]

_TS = "2026-08-03T00:00:00Z"


@pytest.fixture(autouse=True)
def home(monkeypatch, tmp_path):
    monkeypatch.setenv("TAUSIK_HOME", str(tmp_path / "home"))
    return tmp_path / "home"


@pytest.fixture
def mirror(tmp_path, monkeypatch):
    """A stand-in for ~/.tausik-brain/brain.db with one row of each kind."""
    path = tmp_path / "brain.db"
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE brain_decisions (notion_page_id TEXT, decision TEXT, rationale TEXT,
            source_project_hash TEXT, created_at TEXT);
        CREATE TABLE brain_patterns (notion_page_id TEXT, name TEXT, description TEXT,
            tags TEXT, source_project_hash TEXT, created_at TEXT);
        CREATE TABLE brain_gotchas (notion_page_id TEXT, name TEXT, description TEXT,
            source_project_hash TEXT, created_at TEXT);
        CREATE TABLE brain_web_cache (notion_page_id TEXT, url TEXT, content TEXT);
        """
    )
    conn.execute(
        "INSERT INTO brain_decisions VALUES ('page-1', 'Не строить прогноз на шуме', "
        f"'обоснование', 'c857d09db23e6822', '{_TS}')"
    )
    conn.execute(
        "INSERT INTO brain_patterns VALUES ('page-2', 'Backoff с джиттером', "
        f"'описание', 'a,b', 'c857d09db23e6822', '{_TS}')"
    )
    conn.execute(
        "INSERT INTO brain_gotchas VALUES ('page-3', 'Флаги внешних бинарей', "
        f"'описание', 'c857d09db23e6822', '{_TS}')"
    )
    conn.execute("INSERT INTO brain_web_cache VALUES ('page-4', 'https://x', 'чужая статья')")
    conn.commit()
    conn.close()
    monkeypatch.setattr(ki, "_mirror_path", lambda: str(path))
    return path


def _rows(table: str) -> list[dict]:
    conn = knowledge_db.connect_knowledge_db(create=False)
    if conn is None:
        return []
    try:
        return [dict(r) for r in conn.execute(f"SELECT * FROM {table}")]
    finally:
        conn.close()


class TestTheImportIsIdempotent:
    """Rerunning must add nothing — a fresh uuid per run would triple the store."""

    def test_a_second_run_imports_nothing(self, mirror):
        first = ki.import_from_brain_mirror()
        assert first["brain_decisions"] == 1

        second = ki.import_from_brain_mirror()
        assert second["brain_decisions"] == 0, "the rerun re-imported records"
        assert len(_rows("decisions")) == 1

    def test_identity_is_derived_from_the_page_not_invented(self, mirror):
        """Same page id, same uuid — on any machine, on any run."""
        ki.import_from_brain_mirror()
        first = _rows("decisions")[0]["entry_uuid"]

        os.remove(knowledge_db.knowledge_db_path())
        ki.import_from_brain_mirror()
        assert _rows("decisions")[0]["entry_uuid"] == first, (
            "the uuid is random, so every re-import looks like new knowledge"
        )

    def test_a_row_without_a_page_id_is_counted_not_dropped(self, mirror):
        """No page id means no stable identity — but silence would hide the loss."""
        conn = sqlite3.connect(mirror)
        conn.execute(f"INSERT INTO brain_decisions VALUES ('', 'без страницы', '', 'h', '{_TS}')")
        conn.commit()
        conn.close()

        counts = ki.import_from_brain_mirror()
        assert counts.get("skipped_no_page_id") == 1
        assert len(_rows("decisions")) == 1


class TestTagsArriveInTheCanonicalShape:
    """An import is a write like any other.

    The mirror spells tags however Notion did — the fixture's pattern carries
    `a,b`. Passing that through unchanged would make the import a second
    producer of the legacy shape, and the migration would be cleaning up after
    its own codebase forever rather than after history.
    """

    def test_an_imported_tag_list_is_stored_as_json(self, mirror):
        import json

        ki.import_from_brain_mirror()
        rows = [r for r in _rows("memory") if r["tags"]]
        assert rows, "the fixture's tagged pattern did not arrive"
        assert json.loads(rows[0]["tags"]) == ["a", "b"]

    def test_an_untagged_record_stays_untagged(self, mirror):
        ki.import_from_brain_mirror()
        gotchas = [r for r in _rows("memory") if r["type"] == "gotcha"]
        assert gotchas and gotchas[0]["tags"] is None


class TestProvenanceIsHonest:
    """The mirror knows a hash. It must not be presented as a path."""

    def test_origin_is_marked_as_coming_from_the_brain(self, mirror):
        ki.import_from_brain_mirror()
        origin = _rows("decisions")[0]["origin_project"]
        assert origin.startswith("brain:"), (
            "an imported record claims a project path the wiki never held"
        )
        assert "c857d09db23e6822" in origin

    def test_locally_written_records_stay_distinguishable(self, mirror):
        """A reader must be able to tell what came from the wiki."""
        ki.import_from_brain_mirror()
        conn = knowledge_db.connect_knowledge_db(create=True)
        assert conn is not None
        conn.execute(
            "INSERT INTO decisions (entry_uuid, decision, origin_project, created_at) "
            f"VALUES ('local-1', 'своё решение', 'D:/Work/repo', '{_TS}')"
        )
        conn.commit()
        conn.close()

        origins = {r["origin_project"] for r in _rows("decisions")}
        assert any(o.startswith("brain:") for o in origins)
        # The locally written row is stored as a label, so it is asserted by its
        # shape rather than by the path that was inserted — a path in this column
        # is exactly what the store no longer keeps.
        assert any(o.startswith("repo@") for o in origins)
        assert len(origins) == 2, "the mirror row and the local row collapsed into one origin"


class TestWhatIsAndIsNotBroughtOver:
    def test_decisions_patterns_and_gotchas_arrive(self, mirror):
        counts = ki.import_from_brain_mirror()
        assert counts["brain_decisions"] == 1
        assert counts["brain_patterns"] == 1
        assert counts["brain_gotchas"] == 1
        kinds = {r["type"] for r in _rows("memory")}
        assert kinds == {"pattern", "gotcha"}

    def test_cached_web_pages_are_not_imported(self, mirror):
        """Fetched material has no author — importing it would pass someone
        else's article off as a note."""
        ki.import_from_brain_mirror()
        assert "brain_web_cache" not in ki.SOURCES
        contents = {r["content"] for r in _rows("memory")}
        assert "чужая статья" not in contents

    def test_an_older_mirror_missing_a_table_is_not_an_error(self, tmp_path, monkeypatch):
        """Absent is not broken: there is simply nothing of that kind."""
        path = tmp_path / "old.db"
        conn = sqlite3.connect(path)
        conn.executescript(
            "CREATE TABLE brain_decisions (notion_page_id TEXT, decision TEXT, "
            "rationale TEXT, source_project_hash TEXT, created_at TEXT);"
        )
        conn.execute(f"INSERT INTO brain_decisions VALUES ('p', 'd', '', 'h', '{_TS}')")
        conn.commit()
        conn.close()
        monkeypatch.setattr(ki, "_mirror_path", lambda: str(path))

        counts = ki.import_from_brain_mirror()
        assert counts["brain_decisions"] == 1
        assert counts["brain_patterns"] == 0


class TestFailuresAndDryRun:
    def test_a_dry_run_writes_nothing(self, mirror, home):
        counts = ki.import_from_brain_mirror(dry_run=True)
        assert counts["brain_decisions"] == 1
        assert not knowledge_db.knowledge_db_exists(), (
            "a dry run created the shared store — the point is to look first"
        )

    def test_a_missing_mirror_raises_rather_than_reporting_success(self, tmp_path, monkeypatch):
        monkeypatch.setattr(ki, "_mirror_path", lambda: str(tmp_path / "absent.db"))
        with pytest.raises(ServiceError) as e:
            ki.import_from_brain_mirror()
        assert "nothing to import" in str(e.value).lower()

    def test_the_mirror_is_opened_read_only(self, mirror):
        """The source is someone's accumulated record; the import must not touch it."""
        before = os.stat(mirror).st_size
        ki.import_from_brain_mirror()
        conn = sqlite3.connect(mirror)
        try:
            assert conn.execute("SELECT COUNT(*) FROM brain_decisions").fetchone()[0] == 1
        finally:
            conn.close()
        assert os.stat(mirror).st_size == before
