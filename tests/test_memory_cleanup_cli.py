"""Tests for `tausik memory archive --before` + `memory dedupe` (B9).

Covers ``scripts/memory_cleanup.py`` helpers + ``KnowledgeMixin.memory_archive`` /
``KnowledgeMixin.memory_dedupe`` + the v26 schema migration:

- duration parser accepts d/w/m/y; rejects garbage and non-positive
- archive dry-run lists candidates; --confirm stamps archived_at; idempotent
- memory_list / memory_search filter archived_at IS NOT NULL by default
- include_archived=True surfaces archived rows
- dedupe suggests near-duplicate pairs above threshold; rejects bad threshold
- dedupe never recommends pairs across different memory types
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from memory_cleanup import (  # noqa: E402
    find_dedupe_candidates,
    parse_duration_to_days,
)
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402


# ---------------------------------------------------------------------------
# Duration parser
# ---------------------------------------------------------------------------


class TestParseDurationToDays:
    @pytest.mark.parametrize(
        "input_str,expected",
        [
            pytest.param("90d", 90, id="days"),
            pytest.param("12w", 84, id="weeks"),
            pytest.param("2m", 60, id="months_30day"),
            pytest.param("1y", 365, id="years_365day"),
            pytest.param("3D", 3, id="case_insensitive"),
            pytest.param("  7d  ", 7, id="whitespace"),
        ],
    )
    def test_parse_valid(self, input_str, expected):
        assert parse_duration_to_days(input_str) == expected

    @pytest.mark.parametrize(
        "bad_input",
        [
            pytest.param("5h", id="invalid_unit"),
            pytest.param("90", id="no_unit"),
            pytest.param("0d", id="zero_rejected"),
            pytest.param("", id="empty_rejected"),
        ],
    )
    def test_parse_invalid_raises(self, bad_input):
        with pytest.raises(ValueError):
            parse_duration_to_days(bad_input)


# ---------------------------------------------------------------------------
# Service archive flow
# ---------------------------------------------------------------------------


@pytest.fixture
def svc(tmp_path):
    be = SQLiteBackend(str(tmp_path / "tausik.db"))
    s = ProjectService(be)
    yield s
    be.close()


def _seed_memory(svc, mem_type: str, title: str, content: str, created_at: str) -> int:
    mid = svc.be.memory_add(mem_type, title, content, None, None)
    svc.be._conn.execute(
        "UPDATE memory SET created_at=?, updated_at=? WHERE id=?",
        (created_at, created_at, mid),
    )
    svc.be._conn.commit()
    return mid


class TestMemoryArchive:
    def test_dry_run_lists_candidates(self, svc):
        _seed_memory(svc, "pattern", "Old A", "old content", "2020-01-01T00:00:00Z")
        _seed_memory(svc, "pattern", "Recent", "fresh content", "2099-01-01T00:00:00Z")

        result = svc.memory_archive("90d", confirm=False)
        assert result["applied"] is False
        assert result["archived"] == 0
        slugs = [c["title"] for c in result["candidates"]]
        assert "Old A" in slugs
        assert "Recent" not in slugs

    def test_confirm_stamps_archived_at(self, svc):
        old = _seed_memory(svc, "gotcha", "Old G", "stale", "2020-01-01T00:00:00Z")

        result = svc.memory_archive("90d", confirm=True)
        assert result["applied"] is True
        assert result["archived"] == 1

        row = svc.be._conn.execute("SELECT archived_at FROM memory WHERE id=?", (old,)).fetchone()
        assert row[0]

    def test_confirm_idempotent(self, svc):
        _seed_memory(svc, "context", "Old C", "stale", "2020-01-01T00:00:00Z")
        first = svc.memory_archive("90d", confirm=True)
        second = svc.memory_archive("90d", confirm=True)
        assert first["archived"] == 1
        assert second["archived"] == 0

    def test_invalid_duration_raises(self, svc):
        with pytest.raises(ServiceError, match="Invalid duration"):
            svc.memory_archive("garbage", confirm=False)


# ---------------------------------------------------------------------------
# memory_list / memory_search archived filter
# ---------------------------------------------------------------------------


class TestMemoryListSearchFilter:
    def test_list_default_hides_archived(self, svc):
        live = _seed_memory(svc, "pattern", "Active", "fresh", "2099-01-01T00:00:00Z")
        old = _seed_memory(svc, "pattern", "Stale", "old text", "2020-01-01T00:00:00Z")
        svc.memory_archive("90d", confirm=True)

        ids = [r["id"] for r in svc.memory_list()]
        assert live in ids
        assert old not in ids

    def test_list_include_archived(self, svc):
        live = _seed_memory(svc, "pattern", "Active", "fresh", "2099-01-01T00:00:00Z")
        old = _seed_memory(svc, "pattern", "Stale", "old text", "2020-01-01T00:00:00Z")
        svc.memory_archive("90d", confirm=True)

        ids = [r["id"] for r in svc.memory_list(include_archived=True)]
        assert live in ids
        assert old in ids

    def test_search_default_hides_archived(self, svc):
        _seed_memory(svc, "pattern", "Findme1", "kappa zebra", "2099-01-01T00:00:00Z")
        _seed_memory(svc, "pattern", "Findme2", "kappa zebra", "2020-01-01T00:00:00Z")
        svc.memory_archive("90d", confirm=True)

        rows = svc.memory_search("zebra", include_cq=False)
        titles = [r["title"] for r in rows]
        assert "Findme1" in titles
        assert "Findme2" not in titles

    def test_search_include_archived(self, svc):
        _seed_memory(svc, "pattern", "Findme1", "kappa zebra", "2099-01-01T00:00:00Z")
        _seed_memory(svc, "pattern", "Findme2", "kappa zebra", "2020-01-01T00:00:00Z")
        svc.memory_archive("90d", confirm=True)

        rows = svc.memory_search("zebra", include_cq=False, include_archived=True)
        titles = [r["title"] for r in rows]
        assert "Findme1" in titles
        assert "Findme2" in titles


# ---------------------------------------------------------------------------
# Dedupe suggestions
# ---------------------------------------------------------------------------


class TestMemoryDedupe:
    def test_finds_near_duplicate(self, svc):
        a = _seed_memory(
            svc,
            "pattern",
            "pytest tmp_path with sqlite",
            "Use pytest tmp_path fixture for SQLite tests.",
            "2024-01-01T00:00:00Z",
        )
        b = _seed_memory(
            svc,
            "pattern",
            "pytest tmp_path with sqlite",
            "Use pytest tmp_path fixture for SQLite tests!",
            "2024-01-02T00:00:00Z",
        )

        pairs = svc.memory_dedupe(threshold=0.85)
        assert any(p["id_a"] in (a, b) and p["id_b"] in (a, b) for p in pairs)

    def test_skips_different_types(self, svc):
        _seed_memory(svc, "pattern", "Same wording verbatim", "x", "2024-01-01T00:00:00Z")
        _seed_memory(svc, "gotcha", "Same wording verbatim", "x", "2024-01-02T00:00:00Z")
        pairs = svc.memory_dedupe(threshold=0.5)
        assert pairs == []

    def test_threshold_above_one_rejected(self, svc):
        with pytest.raises(ServiceError, match="threshold"):
            svc.memory_dedupe(threshold=1.5)

    def test_threshold_zero_rejected(self, svc):
        with pytest.raises(ServiceError, match="threshold"):
            svc.memory_dedupe(threshold=0.0)

    def test_dedupe_skips_archived_rows(self, svc):
        _seed_memory(svc, "pattern", "Twin A", "shared body", "2020-01-01T00:00:00Z")
        _seed_memory(svc, "pattern", "Twin B", "shared body", "2099-01-01T00:00:00Z")
        # Archive the older twin → dedupe should not pair it.
        svc.memory_archive("90d", confirm=True)

        pairs = svc.memory_dedupe(threshold=0.5)
        assert pairs == []


# ---------------------------------------------------------------------------
# Pure-helper coverage (no service)
# ---------------------------------------------------------------------------


class TestFindDedupeCandidatesPure:
    def test_returns_pair_above_threshold(self):
        rows = [
            {"id": 1, "type": "pattern", "title": "alpha beta gamma", "content": "x"},
            {"id": 2, "type": "pattern", "title": "alpha beta gamma!", "content": "x"},
        ]
        out = find_dedupe_candidates(rows, threshold=0.5)
        assert out and out[0]["id_a"] == 1 and out[0]["id_b"] == 2

    def test_lower_id_first(self):
        rows = [
            {"id": 5, "type": "pattern", "title": "duplicate", "content": "same"},
            {"id": 3, "type": "pattern", "title": "duplicate", "content": "same"},
        ]
        out = find_dedupe_candidates(rows, threshold=0.5)
        assert out[0]["id_a"] == 3
        assert out[0]["id_b"] == 5
