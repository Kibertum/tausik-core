"""Two stores spelled a tag list two ways, and nothing broke — yet.

That is the whole shape of this defect. Neither the CLI search nor the MCP
formatter printed tags, so a shared row storing `a,b` next to a project row
storing `["a", "b"]` was invisible. It was armed rather than harmless: the next
obvious improvement is one tag renderer over a result set holding both kinds of
row, and that renderer either swallows the JSONDecodeError the project code
already catches — showing "no tags" for rows that have them — or it raises.

So the tests here are written against the STORED value and against a single
renderer applied to both sources, because those are the two places the
divergence would have surfaced.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import knowledge_db  # noqa: E402
import knowledge_migrations as km  # noqa: E402
import knowledge_tags as kt  # noqa: E402
import knowledge_write  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/knowledge_tags.py", "scripts/knowledge_write.py"]

_TS = "2026-08-03T00:00:00Z"


@pytest.fixture(autouse=True)
def home(monkeypatch, tmp_path):
    monkeypatch.setenv("TAUSIK_HOME", str(tmp_path / "home"))
    return tmp_path / "home"


@pytest.fixture
def project(tmp_path, monkeypatch):
    root = tmp_path / "proj"
    (root / ".tausik").mkdir(parents=True)
    monkeypatch.setenv("TAUSIK_DIR", str(root / ".tausik"))
    monkeypatch.chdir(root)
    return root


def _open() -> sqlite3.Connection:
    conn = knowledge_db.connect_knowledge_db(create=True)
    assert conn is not None
    return conn


def _stored_tags() -> list[str | None]:
    conn = _open()
    try:
        return [r[0] for r in conn.execute("SELECT tags FROM memory ORDER BY id")]
    finally:
        conn.close()


def _seed_legacy(raw: str | None, uuid: str = "m0") -> None:
    conn = _open()
    try:
        conn.execute(
            "INSERT INTO memory (entry_uuid, type, title, content, tags, created_at, "
            "updated_at) VALUES (?, 'pattern', 'т', 'тело', ?, ?, ?)",
            (uuid, raw, _TS, _TS),
        )
        conn.commit()
    finally:
        conn.close()


class TestTheWritePathIsCanonical:
    """AC1: the store stops producing the legacy spelling."""

    def test_tags_are_written_as_json(self, project):
        knowledge_write.write_memory("pattern", "заголовок", "тело", ["альфа", "бета"])
        raw = _stored_tags()[0]
        assert raw is not None
        assert json.loads(raw) == ["альфа", "бета"]

    def test_an_absent_list_stays_absent_rather_than_becoming_empty(self, project):
        knowledge_write.write_memory("pattern", "заголовок", "тело", None)
        assert _stored_tags() == [None]

    def test_cyrillic_survives_the_encoding(self, project):
        """`ensure_ascii=False`: an escaped tag is a different string to search."""
        knowledge_write.write_memory("pattern", "заголовок", "тело", ["память"])
        raw = _stored_tags()[0]
        assert "память" in raw
        assert "\\u" not in raw


class TestReadingEitherSpelling:
    """The renderer stays total even for a store nothing has migrated yet."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ('["a", "b"]', ["a", "b"]),
            ("a,b", ["a", "b"]),
            ("a, b ", ["a", "b"]),
            ("solo", ["solo"]),
            (None, []),
            ("", []),
            ("   ", []),
            ("[not json", ["[not json"]),
            ('{"a": 1}', ['{"a": 1}']),
        ],
    )
    def test_load_tags_never_raises_and_never_invents(self, raw, expected):
        assert kt.load_tags(raw) == expected


class TestTheMigration:
    """AC2/AC5: legacy rows are fixed, and nothing else is touched."""

    def test_a_csv_row_becomes_json_on_open(self):
        _seed_legacy("альфа,бета")
        raw = _stored_tags()[0]
        assert json.loads(raw) == ["альфа", "бета"]

    def test_it_is_idempotent(self):
        _seed_legacy("a,b")
        first = _stored_tags()
        assert _stored_tags() == first

    @pytest.mark.parametrize("raw", ["[1, 2]", '[null, "tag"]', '[["a","b"], "c"]'])
    def test_a_json_list_of_NON_strings_is_not_canonical(self, raw):
        """This migration is the one chance to repair these.

        Left alone, such a row is read forever through `str(item)` — rendering
        as `None` or `['a', 'b']` on every screen — while never being flagged as
        needing repair, because it parses as valid JSON.
        """
        canonical = kt.normalized_tags(raw)
        assert canonical is not None, f"{raw} was treated as already canonical"
        assert all(isinstance(t, str) for t in json.loads(canonical))

    def test_an_already_canonical_row_is_not_rewritten(self):
        _seed_legacy('["a", "b"]')
        assert kt.normalized_tags('["a", "b"]') is None
        assert json.loads(_stored_tags()[0]) == ["a", "b"]

    @pytest.mark.parametrize("raw", [None, "", "   "])
    def test_an_empty_list_is_left_absent_not_turned_into_an_empty_one(self, raw):
        """`[]` and NULL are different claims, and the read side would then have
        to tell them apart for no gain."""
        _seed_legacy(raw)
        assert _stored_tags()[0] in (None, "", "   ")

    def test_the_count_is_an_honest_measure(self):
        _seed_legacy("a,b", "m0")
        _seed_legacy('["c"]', "m1")
        conn = sqlite3.connect(knowledge_db.knowledge_db_path())
        try:
            conn.execute("UPDATE memory SET tags = 'a,b' WHERE entry_uuid = 'm0'")
            conn.commit()
            assert km.normalize_stored_tags(conn) == 1
            conn.commit()
            assert km.normalize_stored_tags(conn) == 0
        finally:
            conn.close()

    def test_search_still_finds_a_migrated_row(self):
        """`tags` is in the FTS index, so the rewrite has to re-index it —
        otherwise the migration silently makes rows unfindable by tag."""
        _seed_legacy("альфа,бета")
        conn = _open()
        try:
            hits = conn.execute(
                "SELECT rowid FROM fts_memory WHERE fts_memory MATCH ?", ("альфа",)
            ).fetchall()
        finally:
            conn.close()
        assert hits, "a migrated row fell out of the tag index"


class TestOneRendererForBothSources:
    """AC4: the improvement the divergence was waiting to break."""

    def test_a_shared_row_and_a_project_row_render_identically(self):
        from project_cli_extra import _render_tags

        project_row = json.dumps(["альфа", "бета"], ensure_ascii=False)
        shared_row_legacy = "альфа,бета"
        assert _render_tags(project_row) == _render_tags(shared_row_legacy)
        assert _render_tags(project_row) == " альфа, бета"

    def test_no_tags_renders_as_nothing_rather_than_an_empty_bracket(self):
        from project_cli_extra import _render_tags

        assert _render_tags(None) == ""
        assert _render_tags("") == ""
        assert _render_tags("[]") == ""


class TestTheCommaInsideATagIsAcknowledgedNotGuessed:
    """AC5(в): the CSV write destroyed this, and the migration does not pretend."""

    def test_it_is_read_as_two_tags(self):
        assert kt.load_tags("a,b") == ["a", "b"]

    def test_and_a_canonical_row_can_still_hold_one(self):
        """Nothing is lost going FORWARD — only the already-written rows are
        ambiguous, which is why the loss is documented rather than repaired."""
        assert kt.load_tags(kt.dump_tags(["a,b"])) == ["a,b"]
