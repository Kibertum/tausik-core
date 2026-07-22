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


# ---------------------------------------------------------------------------
# l26-memory-dedupe-perf: quick-ratio pruning must be exact + cheaper
# ---------------------------------------------------------------------------


def _brute_force_dedupe(rows, threshold):
    """The pre-optimization all-pairs full-ratio() reference implementation."""
    import difflib

    out = []
    n = len(rows)
    for i in range(n):
        ra = rows[i]
        ta = (ra.get("title") or "") + " " + (ra.get("content") or "")
        for j in range(i + 1, n):
            rb = rows[j]
            if ra.get("type") != rb.get("type"):
                continue
            tb = (rb.get("title") or "") + " " + (rb.get("content") or "")
            score = difflib.SequenceMatcher(a=ta, b=tb, autojunk=False).ratio()
            if score >= threshold:
                lo, hi = sorted([ra, rb], key=lambda r: int(r.get("id") or 0))
                out.append(
                    {
                        "id_a": int(lo["id"]),
                        "id_b": int(hi["id"]),
                        "ratio": round(score, 4),
                        "type": ra.get("type"),
                        "title_a": lo.get("title") or "",
                        "title_b": hi.get("title") or "",
                    }
                )
    out.sort(key=lambda r: (-r["ratio"], r["id_a"], r["id_b"]))
    return out


def _synthetic_rows(seed, n):
    import random

    rnd = random.Random(seed)
    words = "alpha beta gamma delta epsilon zeta eta theta iota kappa".split()
    types = ["pattern", "gotcha", "convention"]
    rows = []
    for i in range(1, n + 1):
        k = rnd.randint(3, 9)
        title = " ".join(rnd.choice(words) for _ in range(rnd.randint(1, 3)))
        content = " ".join(rnd.choice(words) for _ in range(k))
        rows.append({"id": i, "type": rnd.choice(types), "title": title, "content": content})
    # Guarantee some genuine near-duplicates survive pruning.
    for src in (1, 4, 7):
        if src < len(rows):
            twin = dict(rows[src])
            twin["id"] = 1000 + src
            twin["content"] = rows[src]["content"] + " x"
            rows.append(twin)
    return rows


class TestDedupePerf:
    @pytest.mark.parametrize("threshold", [0.5, 0.7, 0.85, 0.95])
    @pytest.mark.parametrize("seed", [1, 2, 3])
    def test_exact_same_result_as_brute_force(self, seed, threshold):
        """AC2: the quick-ratio prunings are true upper bounds, so the optimized
        output must be byte-identical to the all-pairs reference."""
        rows = _synthetic_rows(seed, 40)
        assert find_dedupe_candidates(rows, threshold) == _brute_force_dedupe(rows, threshold)

    def test_prunes_the_expensive_full_ratio_calls(self, monkeypatch):
        """AC3: far fewer full SequenceMatcher.ratio() calls than same-type pairs
        — the expensive step is gated behind the cheap upper bounds."""
        import difflib

        import memory_cleanup

        counter = {"ratio": 0}

        class _CountingSM(difflib.SequenceMatcher):
            def ratio(self):
                counter["ratio"] += 1
                return super().ratio()

        monkeypatch.setattr(memory_cleanup, "SequenceMatcher", _CountingSM)

        rows = _synthetic_rows(seed=7, n=60)
        # Count same-type pairs — the number of full ratio()s the brute force ran.
        from collections import Counter

        tc = Counter(r["type"] for r in rows)
        same_type_pairs = sum(c * (c - 1) // 2 for c in tc.values())

        find_dedupe_candidates(rows, threshold=0.85)
        assert counter["ratio"] < same_type_pairs, (
            f"ratio() ran {counter['ratio']}x for {same_type_pairs} same-type pairs "
            "— pruning did not fire"
        )
        # At a high threshold most random pairs are pruned; expect a big cut.
        assert counter["ratio"] <= same_type_pairs // 2

    def test_sort_order_preserved(self):
        rows = _synthetic_rows(seed=2, n=30)
        out = find_dedupe_candidates(rows, threshold=0.6)
        keys = [(-r["ratio"], r["id_a"], r["id_b"]) for r in out]
        assert keys == sorted(keys)
