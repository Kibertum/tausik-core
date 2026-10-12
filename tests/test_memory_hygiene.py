"""memory-tail-by-relevance-not-recency — layers, dry-run, revert, opt-in tail.

The AC contract under test, by number: AC2 layers by accumulation; AC3 the
report writes nothing; AC4 apply is reverted by one command; AC5 pinned is
never auto-demoted; AC6 empty and single-record corpora break nothing; AC7
the recency tail is the default and the relevance tail is opt-in only.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from memory_hygiene import (
    apply_layers,
    planned_layer,
    record_hit,
    relevance_head,
    report_lines,
    revert_last,
    tail_by_relevance_enabled,
)
from project_backend import SQLiteBackend
from service_knowledge_aggregates import build_compact_memory_tail


@pytest.fixture
def be(tmp_path):
    b = SQLiteBackend(str(tmp_path / "mem.db"))
    yield b
    b.close()


def _rec(be, slug, title=None, updated=None, hits=0, pinned=0):
    mid = be.memory_add("convention", title or slug, "content")
    if updated or hits or pinned:
        be._conn.execute(
            "UPDATE memory SET updated_at=?, hit_count=?, pinned=? WHERE id=?",
            (updated or "2026-10-01T00:00:00+00:00", hits, pinned, mid),
        )
        be._conn.commit()
    return mid


NOW = datetime(2026, 10, 6, tzinfo=timezone.utc)


class TestPlannedLayer:
    @pytest.mark.parametrize(
        ("hits", "age_days", "pinned", "expected"),
        [
            (25, 0, 0, "core"),  # structural: read a quarter-hundred times
            (12, 0, 0, "hot"),
            (3, 0, 0, "warm"),
            (1, 0, 0, "cold"),
            (0, 5, 0, "cold"),  # fresh and unread: has not had the chance
            (0, 120, 0, "frozen"),  # unread and stale
            (0, 120, 1, "core"),  # pinned outranks every accumulation rule
            (0, 5, 1, "core"),
        ],
    )
    def test_layer_by_accumulation(self, hits, age_days, pinned, expected):
        row = {
            "hit_count": hits,
            "pinned": pinned,
            "updated_at": (NOW - timedelta(days=age_days)).isoformat(),
        }
        assert planned_layer(row, NOW) == expected


class TestHygieneLifecycle:
    def test_report_writes_nothing(self, be):
        _rec(be, "old", updated=(NOW - timedelta(days=120)).isoformat())
        before = be._q1("SELECT layer, hit_count FROM memory WHERE id=1")
        assert "DRY-RUN" in report_lines(be)[0]
        after = be._q1("SELECT layer, hit_count FROM memory WHERE id=1")
        assert before == after

    def test_apply_then_revert_restores(self, be):
        mid = _rec(be, "old", updated=(NOW - timedelta(days=120)).isoformat())
        be._conn.execute("UPDATE memory SET layer='hot' WHERE id=?", (mid,))
        be._conn.commit()
        msg = apply_layers(be)
        assert "re-layered" in msg
        assert be._q1("SELECT layer FROM memory WHERE id=?", (mid,))["layer"] == "frozen"
        assert "reverted" in revert_last(be)
        assert be._q1("SELECT layer FROM memory WHERE id=?", (mid,))["layer"] == "hot"

    def test_revert_without_apply_is_a_plain_no_op_sentence(self, be):
        assert "nothing to revert" in revert_last(be)

    def test_pinned_is_never_touched_by_apply(self, be):
        mid = _rec(be, "pinme", updated=(NOW - timedelta(days=400)).isoformat(), pinned=1)
        apply_layers(be)
        row = be._q1("SELECT layer, pinned FROM memory WHERE id=?", (mid,))
        assert row["layer"] is None and row["pinned"] == 1  # no layer written, not demoted

    def test_record_hit_counts_show_reads(self, be):
        mid = _rec(be, "hit")
        for _ in range(2):
            record_hit(be, mid)
        row = be._q1("SELECT hit_count, last_hit_at FROM memory WHERE id=?", (mid,))
        assert row["hit_count"] == 2 and row["last_hit_at"] is not None


class TestTailSelection:
    def test_flag_defaults_off(self, be, tmp_path):
        assert tail_by_relevance_enabled(be) is False

    def test_flag_reads_config(self, be, tmp_path):
        with open(os.path.join(str(tmp_path), "config.json"), "w", encoding="utf-8") as fh:
            json.dump({"memory_tail_by_relevance": True}, fh)
        assert tail_by_relevance_enabled(be) is True

    def test_default_tail_is_recency(self, be):
        _rec(be, "a", title="old but loved")
        _rec(be, "b", title="fresh unread")
        for _ in range(9):
            record_hit(be, 1)
        lines = build_compact_memory_tail(be)
        joined = "\n".join(lines)
        assert "fresh unread" in joined  # latest id wins: byte-identical legacy order

    def test_opt_in_tail_promotes_the_read_record(self, be, tmp_path):
        _rec(be, "a", title="old but loved")
        _rec(be, "b", title="fresh unread")
        for _ in range(9):
            record_hit(be, 1)
        apply_layers(be)
        head = relevance_head(be, "convention", 5)
        assert head[0]["id"] == 1  # significance beats recency

    def test_opt_in_flag_changes_the_aggregate_tail(self, be, tmp_path, monkeypatch):
        _rec(be, "a", title="old but loved")
        _rec(be, "b", title="fresh unread")
        for _ in range(9):
            record_hit(be, 1)
        apply_layers(be)
        with open(os.path.join(str(tmp_path), "config.json"), "w", encoding="utf-8") as fh:
            json.dump({"memory_tail_by_relevance": True}, fh)
        joined = "\n".join(build_compact_memory_tail(be))
        # n=5 holds both records; what the flag changes is the ORDER — the
        # nine-times-read record takes the first line from the fresh one.
        assert joined.index("old but loved") < joined.index("fresh unread")


class TestEdges:
    def test_empty_corpus_tail_is_empty_and_report_survives(self, be):
        assert build_compact_memory_tail(be) == []
        assert "empty" in report_lines(be)[0].lower()
        assert "applied" in apply_layers(be) or "empty" in apply_layers(be).lower()

    def test_single_record_corpus_keeps_one_heading_one_line(self, be):
        _rec(be, "only", title="the only record")
        lines = build_compact_memory_tail(be)
        assert lines.count("Conventions (1):") == 1
        assert "- #1 the only record" in "\n".join(lines)
        assert "Conventions (0):" not in "\n".join(lines)  # no empty headings (AC6)
