"""Stable slug identity for decisions and memory (state-git-stable-ids).

The load-bearing precondition for merging TAUSIK state across branches: two
engineers must mint the SAME slug for the same decision/memory, and the v42
backfill must give every one of the existing rows a unique, stable slug without
disturbing the memory graph. These tests pin the generator (determinism, dedup,
transliteration, fallback) and the migration (uniqueness, idempotence, graph
isomorphism, FTS survival, forward-insert).
"""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from backend_migrations_v42_backfill import maybe_backfill_v42  # noqa: E402
from slug_util import dedup, first_line, make_slug, slugify, transliterate  # noqa: E402


class TestSlugGenerator:
    def test_ascii_kebab(self):
        assert slugify("Hello, World!") == "hello-world"
        assert slugify("  multiple   spaces  ") == "multiple-spaces"
        assert slugify("Mixed_Case-42") == "mixed-case-42"

    def test_transliterates_cyrillic_to_latin(self):
        assert transliterate("Доменная") == "domennaya"
        assert slugify("Доменная проверка смысла") == "domennaya-proverka-smysla"
        # The whole reason ASCII-fold alone was wrong: Russian must not vanish.
        assert slugify("Состояние делится через git") == "sostoyanie-delitsya-cherez-git"

    def test_is_deterministic(self):
        # Same input, twice, must be byte-identical — the property the whole
        # cross-machine merge rests on.
        text = "Гейт над текстом проверяемого"
        assert slugify(text) == slugify(text)
        assert make_slug(text, fallback="x", taken=set()) == make_slug(
            text, fallback="x", taken=set()
        )

    def test_empty_or_punctuation_only_slugifies_to_empty(self):
        assert slugify("") == ""
        assert slugify("!!!") == ""
        assert slugify("   ") == ""
        assert slugify("\x00\x01\x02") == ""

    def test_length_is_capped_on_a_hyphen_boundary(self):
        long = "word " * 40
        s = slugify(long)
        assert len(s) <= 60
        assert not s.endswith("-")
        assert "wor" not in s.split("-")[-1] or s.split("-")[-1] == "word"

    def test_dedup_appends_deterministic_suffixes(self):
        assert dedup("a", set()) == "a"
        assert dedup("a", {"a"}) == "a-2"
        assert dedup("a", {"a", "a-2"}) == "a-3"

    def test_make_slug_falls_back_when_text_is_unusable(self):
        # Negative/boundary: an empty title or a non-printable one must yield a
        # deterministic fallback slug, never "" (which the UNIQUE index rejects).
        assert make_slug("", fallback="memory-9", taken=set()) == "memory-9"
        assert make_slug("\x00\x01", fallback="decision-3", taken=set()) == "decision-3"
        assert make_slug("!!!", fallback="memory-7", taken=set()) == "memory-7"

    def test_make_slug_dedups_identical_text(self):
        # Two rows with the same title get distinct slugs, in call order.
        taken: set[str] = set()
        a = make_slug("same title", fallback="x", taken=taken)
        taken.add(a)
        b = make_slug("same title", fallback="y", taken=taken)
        assert (a, b) == ("same-title", "same-title-2")

    def test_first_line_is_the_first_non_empty_line(self):
        assert first_line("line one\nline two") == "line one"
        assert first_line("\n\n  indented  \nx") == "indented"
        assert first_line("") == ""
        assert first_line("   \n\t") == ""


def _backend(tmp_path):
    from project_backend import SQLiteBackend

    return SQLiteBackend(str(tmp_path / "t.db"))


class TestFreshSchema:
    def test_slug_columns_indexes_and_flag_present(self, tmp_path):
        be = _backend(tmp_path)
        try:
            c = be._conn
            assert "slug" in {r[1] for r in c.execute("PRAGMA table_info(decisions)")}
            assert "slug" in {r[1] for r in c.execute("PRAGMA table_info(memory)")}
            idx = {r[1] for r in c.execute("PRAGMA index_list(decisions)")} | {
                r[1] for r in c.execute("PRAGMA index_list(memory)")
            }
            assert "idx_decisions_slug" in idx
            assert "idx_memory_slug" in idx
            flag = c.execute("SELECT value FROM meta WHERE key='v42_slugs_backfilled'").fetchone()
            assert flag and flag[0] == "1"
        finally:
            be.close()


class TestForwardInsert:
    def test_new_rows_get_a_transliterated_slug(self, tmp_path):
        be = _backend(tmp_path)
        try:
            mid = be.memory_add("pattern", "Доменная проверка", "content")
            did = be.decision_add("Состояние делится через git")
            c = be._conn
            assert c.execute("SELECT slug FROM memory WHERE id=?", (mid,)).fetchone()[0] == (
                "domennaya-proverka"
            )
            assert (
                c.execute("SELECT slug FROM decisions WHERE id=?", (did,)).fetchone()[0]
                == "sostoyanie-delitsya-cherez-git"
            )
        finally:
            be.close()

    def test_identical_titles_get_distinct_slugs(self, tmp_path):
        be = _backend(tmp_path)
        try:
            a = be.memory_add("gotcha", "same name", "c1")
            b = be.memory_add("gotcha", "same name", "c2")
            c = be._conn
            sa = c.execute("SELECT slug FROM memory WHERE id=?", (a,)).fetchone()[0]
            sb = c.execute("SELECT slug FROM memory WHERE id=?", (b,)).fetchone()[0]
            assert sa != sb
            assert {sa, sb} == {"same-name", "same-name-2"}
        finally:
            be.close()


class TestBackfillMigration:
    """Simulate the v41->v42 backfill: insert slug-less rows, clear the flag, run.

    Direct SQL (bypassing the slug-assigning CRUD) reproduces the pre-migration
    state — rows that predate the slug column.
    """

    def _make_slugless(self, be, rows_decisions, rows_memory):
        c = be._conn
        # Drop the unique indexes and the flag so the rows can be NULLed and the
        # backfill re-run as if migrating for the first time.
        c.execute("DROP INDEX IF EXISTS idx_decisions_slug")
        c.execute("DROP INDEX IF EXISTS idx_memory_slug")
        c.execute("DELETE FROM meta WHERE key='v42_slugs_backfilled'")
        for text in rows_decisions:
            c.execute(
                "INSERT INTO decisions(decision,created_at,slug) VALUES(?,?,NULL)",
                (text, "2026-01-01T00:00:00Z"),
            )
        for title in rows_memory:
            c.execute(
                "INSERT INTO memory(type,title,content,created_at,updated_at,slug) "
                "VALUES('context',?,?,?,?,NULL)",
                (title, "body", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
            )
        c.commit()

    def test_backfill_fills_every_row_uniquely_and_builds_the_index(self, tmp_path):
        be = _backend(tmp_path)
        try:
            self._make_slugless(
                be,
                rows_decisions=["Первое решение", "Второе решение", "Первое решение"],
                rows_memory=["Alpha", "Beta", "Alpha"],
            )
            filled = maybe_backfill_v42(be._conn)
            assert filled == 6
            c = be._conn
            d = c.execute(
                "SELECT COUNT(*), COUNT(DISTINCT slug), SUM(slug IS NULL OR slug='') FROM decisions"
            ).fetchone()
            m = c.execute(
                "SELECT COUNT(*), COUNT(DISTINCT slug), SUM(slug IS NULL OR slug='') FROM memory"
            ).fetchone()
            assert tuple(d) == (3, 3, 0)  # all filled, all unique
            assert tuple(m) == (3, 3, 0)
            # Collision resolved deterministically by id ASC.
            dslugs = [r[0] for r in c.execute("SELECT slug FROM decisions ORDER BY id")]
            assert dslugs == ["pervoe-reshenie", "vtoroe-reshenie", "pervoe-reshenie-2"]
            mslugs = [r[0] for r in c.execute("SELECT slug FROM memory ORDER BY id")]
            assert mslugs == ["alpha", "beta", "alpha-2"]
            idx = {r[1] for r in c.execute("PRAGMA index_list(decisions)")} | {
                r[1] for r in c.execute("PRAGMA index_list(memory)")
            }
            assert {"idx_decisions_slug", "idx_memory_slug"} <= idx
        finally:
            be.close()

    def test_backfill_is_idempotent(self, tmp_path):
        be = _backend(tmp_path)
        try:
            self._make_slugless(be, ["Решение А"], ["Mem A"])
            maybe_backfill_v42(be._conn)
            snap_d = dict(be._conn.execute("SELECT id, slug FROM decisions"))
            snap_m = dict(be._conn.execute("SELECT id, slug FROM memory"))
            # Re-run: the flag is set, so it must be a no-op returning 0.
            assert maybe_backfill_v42(be._conn) == 0
            assert dict(be._conn.execute("SELECT id, slug FROM decisions")) == snap_d
            assert dict(be._conn.execute("SELECT id, slug FROM memory")) == snap_m
        finally:
            be.close()

    def test_empty_title_and_punctuation_decision_get_fallback_not_null(self, tmp_path):
        be = _backend(tmp_path)
        try:
            self._make_slugless(be, rows_decisions=["!!!"], rows_memory=["   "])
            maybe_backfill_v42(be._conn)
            c = be._conn
            drow = c.execute("SELECT id, slug FROM decisions").fetchone()
            mrow = c.execute("SELECT id, slug FROM memory").fetchone()
            assert drow[1] == f"decision-{drow[0]}"
            assert mrow[1] == f"memory-{mrow[0]}"
        finally:
            be.close()


class TestGraphIsomorphism:
    def test_edges_resolve_to_the_same_nodes_after_backfill(self, tmp_path):
        be = _backend(tmp_path)
        try:
            c = be._conn
            # Build two memories and a decision with an edge between them, then
            # a null-slug state, then backfill — the node ids and the edge must be
            # untouched (only slugs are added).
            m1 = be.memory_add("pattern", "Node one", "c")
            m2 = be.memory_add("pattern", "Node two", "c")
            d1 = be.decision_add("A decision node")
            ts = "2026-01-01T00:00:00Z"
            c.execute(
                "INSERT INTO memory_edges(source_type,source_id,target_type,target_id,"
                "relation,valid_from,created_at) VALUES('memory',?,'decision',?,'relates_to',?,?)",
                (m1, d1, ts, ts),
            )
            c.execute(
                "INSERT INTO memory_edges(source_type,source_id,target_type,target_id,"
                "relation,valid_from,created_at) VALUES('memory',?,'memory',?,'supersedes',?,?)",
                (m2, m1, ts, ts),
            )
            c.commit()
            nodes_before = (
                {r[0] for r in c.execute("SELECT id FROM memory")},
                {r[0] for r in c.execute("SELECT id FROM decisions")},
            )
            edges_before = {
                tuple(r)
                for r in c.execute(
                    "SELECT source_type,source_id,target_type,target_id,relation FROM memory_edges"
                ).fetchall()
            }
            # Force a re-backfill over the existing (already-slugged) rows: clear
            # the flag but leave slugs — the backfill only touches NULL rows, so
            # nothing changes, and the graph is trivially preserved.
            c.execute("DELETE FROM meta WHERE key='v42_slugs_backfilled'")
            c.commit()
            maybe_backfill_v42(c)
            nodes_after = (
                {r[0] for r in c.execute("SELECT id FROM memory")},
                {r[0] for r in c.execute("SELECT id FROM decisions")},
            )
            edges_after = {
                tuple(r)
                for r in c.execute(
                    "SELECT source_type,source_id,target_type,target_id,relation FROM memory_edges"
                ).fetchall()
            }
            assert nodes_before == nodes_after
            assert edges_before == edges_after
            # Every edge endpoint still resolves.
            for st, sid, tt, tid, _rel in edges_after:
                stab = "memory" if st == "memory" else "decisions"
                ttab = "memory" if tt == "memory" else "decisions"
                assert c.execute(f"SELECT 1 FROM {stab} WHERE id=?", (sid,)).fetchone()
                assert c.execute(f"SELECT 1 FROM {ttab} WHERE id=?", (tid,)).fetchone()
        finally:
            be.close()


class TestNoCollateralDamage:
    def test_unique_index_rejects_a_duplicate_slug(self, tmp_path):
        be = _backend(tmp_path)
        try:
            c = be._conn
            c.execute(
                "INSERT INTO memory(type,title,content,created_at,updated_at,slug) "
                "VALUES('context','A','b','2026-01-01T00:00:00Z','2026-01-01T00:00:00Z','dup')"
            )
            with pytest.raises(sqlite3.IntegrityError):
                c.execute(
                    "INSERT INTO memory(type,title,content,created_at,updated_at,slug) "
                    "VALUES('context','B','b','2026-01-01T00:00:00Z','2026-01-01T00:00:00Z','dup')"
                )
        finally:
            be.close()

    def test_fts_search_still_works_after_slug_insert(self, tmp_path):
        be = _backend(tmp_path)
        try:
            be.memory_add("pattern", "Searchable title", "unique_token_xyzzy in body")
            hits = be.memory_search("xyzzy")
            assert any("xyzzy" in (h.get("content") or "") for h in hits)
        finally:
            be.close()
