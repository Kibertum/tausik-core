"""Shared knowledge shows up in search and in the block — labelled, quota'd, never mute.

Three properties carry this feature, and each has a way of passing while being
wrong, so each is tested against that specific way rather than in general.

Labelling can pass by putting the shared row's own id in the output, which looks
right and points at a different real record. Quotas can pass by "the shared rows
are there" while project rows have silently been pushed out. Degradation can
pass by returning project results, which is exactly what a silent failure also
does.
"""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import knowledge_read  # noqa: E402
import service_knowledge_aggregates as agg  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/knowledge_read.py", "scripts/service_knowledge_aggregates.py"]

_TS = "2026-08-02T00:00:00Z"


@pytest.fixture(autouse=True)
def home(monkeypatch, tmp_path):
    monkeypatch.setenv("TAUSIK_HOME", str(tmp_path / "home"))
    return tmp_path / "home"


def _seed(memories=(), decisions=()):
    """Put rows in the shared store through the real write path's schema."""
    from knowledge_db import connect_knowledge_db

    conn = connect_knowledge_db(create=True)
    assert conn is not None
    try:
        for i, (mtype, title, content, origin) in enumerate(memories):
            conn.execute(
                "INSERT INTO memory (entry_uuid, type, title, content, origin_project, "
                "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (f"m{i}", mtype, title, content, origin, _TS, _TS),
            )
        for i, (text, origin) in enumerate(decisions):
            conn.execute(
                "INSERT INTO decisions (entry_uuid, decision, origin_project, created_at) "
                "VALUES (?, ?, ?, ?)",
                (f"d{i}", text, origin, _TS),
            )
        conn.commit()
    finally:
        conn.close()


class _Backend:
    """Project backend stub with a known, countable set of local rows."""

    def __init__(self, n=2):
        self._n = n

    def decision_list(self, n):
        return [{"id": i, "decision": f"локальное решение {i}"} for i in range(min(self._n, n))]

    def memory_list(self, mem_type, n):
        return [{"id": i, "title": f"локальная {mem_type} {i}"} for i in range(min(self._n, n))]


class TestSharedRowsAreLabelledAndAddressless:
    """AC1: provenance follows the cq precedent, and the id is deliberately absent."""

    def test_a_shared_hit_has_no_local_address(self):
        _seed(memories=[("pattern", "кэш по ключу", "тело", "D:/Work/clientA/repo")])
        rows, warning = knowledge_read.search_shared_memory("кэш")
        assert warning is None
        assert len(rows) == 1
        assert rows[0]["id"] is None, (
            "a shared row carried an address; printing it would send `memory show` "
            "to a different, real, local record"
        )
        assert rows[0]["source"] == knowledge_read.GLOBAL_SOURCE
        assert rows[0]["title"].startswith(knowledge_read.GLOBAL_LABEL)

    def test_a_legacy_absolute_origin_never_reaches_the_display(self):
        """Rows written before the label existed must not name their directories.

        Two things have to hold at once and the test asserts both: the store
        rewrites the stale value on open, and the display would not repeat the
        parent directories even if it had not.
        """
        _seed(memories=[("pattern", "тема", "тело", "D:/Work/Kibertum/clients/acme/repo")])
        rows, _ = knowledge_read.search_shared_memory("тема")
        assert rows[0]["origin_project"].startswith("repo@")
        assert "clients" not in rows[0]["origin_project"]
        assert "/" not in rows[0]["origin_project"]

    def test_search_reaches_the_service_layer(self, tmp_path, monkeypatch):
        from project_backend import SQLiteBackend
        from project_service import ProjectService

        root = tmp_path / "proj"
        (root / ".tausik").mkdir(parents=True)
        monkeypatch.chdir(root)
        svc = ProjectService(SQLiteBackend(str(root / ".tausik" / "tausik.db")))
        try:
            svc.memory_add("pattern", "локальная запись про кэш", "тело")
            _seed(memories=[("pattern", "общая запись про кэш", "тело", "/x/other")])

            rows = svc.memory_search("кэш", include_cq=False)
            shared = [r for r in rows if r.get("source") == knowledge_read.GLOBAL_SOURCE]
            project = [r for r in rows if r.get("id") is not None]

            assert shared, "the shared store was not searched"
            # NB: `None in [r.get("source") ...]` would be true for every local
            # row regardless — the project's `memory` table has no `source`
            # column at all — so it proves nothing. Count addressable rows.
            assert project, "project hits disappeared when the shared store was added"
            # Project first, shared after — most specific answers read first.
            assert rows.index(project[0]) < rows.index(shared[0])
        finally:
            svc.be.close()


class TestTheBlockGivesSharedItsOwnBudget:
    """AC5: the project's section must not shrink because sharing grew."""

    def test_project_section_is_unchanged_by_a_large_shared_store(self):
        be = _Backend(n=2)
        before = agg.build_memory_block(be)
        _seed(memories=[("convention", f"общая {i}", "тело", "/x/p") for i in range(50)])
        after = agg.build_memory_block(be)

        def project_part(block):
            """Everything up to the shared section — headers included.

            Comparing only `- #` bullets would miss a regression that kept the
            rows but mangled the section headers around them, and the changelog
            claims the project part is unchanged, not merely its bullets.
            """
            head, _, _ = block.partition("**Shared knowledge")
            # Trailing blank lines only: the separator line that introduces the
            # shared section belongs to that section, not to the project part.
            # Stripping them is the one difference this comparison must forgive.
            return head.rstrip("\n")

        assert project_part(before) == project_part(after), (
            "shared entries displaced or reshaped the project part of the block"
        )
        assert "Shared knowledge" in after
        assert "- [convention]" in after

    def test_shared_section_respects_its_own_cap(self):
        _seed(memories=[("convention", f"общая {i}", "тело", "/x/p") for i in range(20)])
        block = agg.build_memory_block(_Backend(), max_shared=3)
        assert len([ln for ln in block.splitlines() if ln.startswith("- [convention]")]) == 3

    def test_a_project_with_no_memory_still_sees_shared_knowledge(self):
        """The case where shared knowledge matters most must not hit an early return."""

        class Empty:
            def decision_list(self, n):
                return []

            def memory_list(self, mem_type, n):
                return []

        _seed(memories=[("convention", "общая конвенция", "тело", "/x/p")])
        assert "Shared knowledge" in agg.build_memory_block(Empty())
        assert any("общая конвенция" in ln for ln in agg.build_compact_memory_tail(Empty()))

    def test_the_tail_carries_the_section_too(self):
        _seed(decisions=[("общее решение", "/x/p")])
        tail = "\n".join(agg.build_compact_memory_tail(_Backend()))
        assert "Shared knowledge" in tail
        assert "общее решение" in tail


class TestDegradationIsVisibleButNotNoisy:
    """AC3 — and the two halves that a silent failure would also satisfy."""

    def test_an_unreadable_store_warns_and_still_returns_project_results(self, home):
        _seed(memories=[("pattern", "тема", "тело", "/x/p")])
        # Corrupt the file: present, so it is not "never created", but unreadable.
        with open(home / "knowledge.db", "wb") as fh:
            fh.write(b"this is not a database")

        rows, warning = knowledge_read.search_shared_memory("тема")
        assert rows == []
        assert warning, "an unreadable shared store degraded SILENTLY"
        assert "showing this project only" in warning

    def test_the_block_shows_the_warning(self, home):
        _seed(memories=[("convention", "тема", "тело", "/x/p")])
        with open(home / "knowledge.db", "wb") as fh:
            fh.write(b"not a database")
        block = agg.build_memory_block(_Backend())
        assert "⚠" in block
        assert "- #" in block, "the project's own block was lost along with the shared store"

    @pytest.mark.parametrize(
        "call",
        [
            lambda: knowledge_read.search_shared_memory("тема"),
            lambda: knowledge_read.shared_memory_by_type("convention", 3),
            lambda: knowledge_read.shared_decisions(3),
        ],
        ids=["search", "by_type", "decisions"],
    )
    def test_a_query_that_fails_after_opening_also_warns(self, monkeypatch, call):
        """The failure that happens AFTER the store opened cleanly.

        A corrupt file fails at open, so the open path's warning covers it — and
        a probe showed that is the only path the other tests exercise, leaving
        each function's own query-error branch unproven. Those branches are not
        decoration: a store can open and still fail mid-query on a damaged index
        or a partially written page.

        The failure is injected because it cannot be staged reliably from
        outside. What is being asserted is the CONTRACT — a query error yields
        a warning rather than an empty, confident answer — and injection is the
        only way to reach it deterministically.
        """
        _seed(memories=[("convention", "тема", "тело", "/x/p")], decisions=[("тема", "/x/p")])
        real = knowledge_read.connect_knowledge_db

        class _FailsMidQuery:
            """Opens fine, raises on the query — sqlite3.Connection forbids
            patching `execute` in place, so the wrapper is the only route."""

            def __init__(self, conn):
                self._conn = conn

            def execute(self, *_a, **_k):
                raise sqlite3.DatabaseError("database disk image is malformed")

            def close(self):
                self._conn.close()

        monkeypatch.setattr(
            knowledge_read, "connect_knowledge_db", lambda *a, **k: _FailsMidQuery(real(*a, **k))
        )
        knowledge_read.pop_last_warning()  # clear anything a neighbour left behind
        rows, warning = call()
        assert rows == []
        assert warning, "a mid-query failure returned an empty result with NO warning"
        assert "showing this project only" in warning
        # The renderer's route to the same notice — a warning returned but not
        # recorded would leave `memory search` silent while the API looked fine.
        assert knowledge_read.pop_last_warning() == warning
        assert knowledge_read.pop_last_warning() is None, "the notice was not consumed on read"

    def test_the_warning_survives_a_block_that_overflows_its_line_budget(self, home):
        """The notice must not compete for the line budget it warns about.

        Reproduced by review before the placement changed: with
        max_conventions=15 — a value both the CLI and MCP accept — the block
        reached 51 lines, truncation dropped the last one, and the warning was
        it. What remained was the ordinary `_...(truncated, N more lines)_`,
        which reads exactly like a long block rather than like a broken store.
        """
        home.mkdir(parents=True, exist_ok=True)
        with open(home / "knowledge.db", "wb") as fh:
            fh.write(b"not a database")

        class Fat:
            def decision_list(self, n):
                return [{"id": i, "decision": f"решение {i}"} for i in range(n)]

            def memory_list(self, mem_type, n):
                return [{"id": i, "title": f"{mem_type} {i}"} for i in range(n)]

        # A larger cap than review's repro, and for a stated reason: their
        # overflow was partly made of shared ENTRIES, and a store that cannot be
        # read yields none. The conditions being tested — an overflowing block
        # plus a degraded store — only co-occur when the project side alone is
        # big enough, so the project side is made big enough.
        block = agg.build_memory_block(Fat(), max_conventions=30)
        assert "truncated" in block, "the block did not overflow — the case is not exercised"
        assert "showing this project only" in block, (
            "the degradation notice was truncated away; it is inside the budget again"
        )

    def test_the_mcp_surface_shows_the_warning_too(self, home, tmp_path, monkeypatch):
        """The interface CLAUDE.md tells agents to prefer must not be the mute one.

        The notice reached only `tausik memory search` at first. An agent working
        through MCP — as the project's own rules require — would have received a
        short list from a broken store with nothing to say it was short. That is
        the exact silent failure this whole read path exists to rule out, hiding
        on the surface that matters most.
        """
        sys.path.insert(
            0, os.path.join(os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project")
        )
        from handlers import handle_tool

        from project_backend import SQLiteBackend
        from project_service import ProjectService

        root = tmp_path / "mcpproj"
        (root / ".tausik").mkdir(parents=True)
        monkeypatch.chdir(root)
        svc = ProjectService(SQLiteBackend(str(root / ".tausik" / "tausik.db")))
        try:
            svc.memory_add("pattern", "локальная про кэш", "тело")
            home.mkdir(parents=True, exist_ok=True)
            with open(home / "knowledge.db", "wb") as fh:
                fh.write(b"not a database")

            out = handle_tool(svc, "tausik_memory_search", {"query": "кэш"})
            assert "локальная про кэш" in out, "project results were lost"
            assert "showing this project only" in out, (
                "MCP returned a truncated result set with no sign the shared store failed"
            )
        finally:
            svc.be.close()

    def test_a_store_that_was_never_created_says_nothing(self):
        """No degradation happened, so warning every session would be noise."""
        rows, warning = knowledge_read.search_shared_memory("что угодно")
        assert rows == []
        assert warning is None

        block = agg.build_memory_block(_Backend())
        # NB: the block opens with a "⚠ **Memory Policy**" line that predates
        # this feature, so a bare `"⚠" not in block` would assert nothing about
        # the shared store. Match the degradation sentence itself.
        assert "showing this project only" not in block
        assert "Shared knowledge" not in block


class TestRankingUsesFtsAndRecencyOnly:
    """AC2: no embeddings, and relevance beats insertion order."""

    def test_relevance_beats_insertion_order(self):
        """The strong match is seeded FIRST, so id order fights relevance.

        Seeded the other way round — weak first, strong second — an
        implementation that ignored bm25 and simply sorted by `id DESC` would
        also put the strong match on top, and the test would prove nothing. The
        two signals have to point in OPPOSITE directions for the assertion to
        isolate the one being claimed.
        """
        _seed(
            memories=[
                ("pattern", "кэш кэш кэш", "кэш", "/x/p"),  # strong, lowest id
                ("pattern", "что-то про кэш вскользь", "тело", "/x/p"),  # weak, highest id
            ]
        )
        rows, _ = knowledge_read.search_shared_memory("кэш")
        assert len(rows) == 2
        assert "кэш кэш кэш" in rows[0]["title"], (
            "the newest row won — ranking is by id, not by relevance"
        )

    def test_no_embedding_machinery_on_the_read_path(self):
        """A tripwire, and worth naming as one rather than overselling it.

        It greps one file for known names. It will catch someone importing a
        vector library — the realistic way this decision would erode — and it
        will NOT catch a hand-rolled similarity written without any of these
        words. It is cheap and it fails loudly at the likely point of entry;
        that is the whole claim.
        """
        src = open(knowledge_read.__file__, encoding="utf-8").read().lower()
        code = "\n".join(ln for ln in src.splitlines() if not ln.strip().startswith("#"))
        for banned in ("sentence_transformers", "faiss", "numpy", "import embedding"):
            assert banned not in code, f"{banned} appeared on the read path"
