"""Tests for scripts/brain_hook_utils.py — shared cache-lookup helpers.

Covers: ISO parsing edge cases, freshness rules, exact-URL lookup with
mixed timestamp formats and multi-row URL collisions.
"""

from __future__ import annotations

import datetime as _dt
import os
import sqlite3
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from brain_hook_utils import (  # noqa: E402
    is_fresh,
    lookup_exact_url,
    parse_iso_to_epoch,
)
from brain_schema import apply_schema  # noqa: E402


# ---- parse_iso_to_epoch -------------------------------------------------


class TestParseIsoToEpoch:
    def test_z_suffix(self):
        epoch = parse_iso_to_epoch("2026-04-24T10:00:00Z")
        assert epoch is not None
        dt = _dt.datetime.fromtimestamp(epoch, tz=_dt.timezone.utc)
        assert dt.year == 2026 and dt.month == 4 and dt.day == 24
        assert dt.hour == 10 and dt.minute == 0

    def test_micros_with_z(self):
        epoch = parse_iso_to_epoch("2026-04-24T10:00:00.123Z")
        assert epoch is not None
        dt = _dt.datetime.fromtimestamp(epoch, tz=_dt.timezone.utc)
        assert dt.hour == 10

    def test_offset_form(self):
        epoch = parse_iso_to_epoch("2026-04-24T13:00:00+03:00")
        expected = parse_iso_to_epoch("2026-04-24T10:00:00Z")
        assert epoch == expected

    def test_naive_assumed_utc(self):
        # fromisoformat accepts naive; we stamp it as UTC.
        epoch = parse_iso_to_epoch("2026-04-24T10:00:00")
        expected = parse_iso_to_epoch("2026-04-24T10:00:00Z")
        assert epoch == expected

    def test_empty_string_returns_none(self):
        assert parse_iso_to_epoch("") is None

    def test_non_string_returns_none(self):
        assert parse_iso_to_epoch(None) is None  # type: ignore[arg-type]
        assert parse_iso_to_epoch(123) is None  # type: ignore[arg-type]

    def test_garbage_returns_none(self):
        assert parse_iso_to_epoch("not a date") is None
        assert parse_iso_to_epoch("2026-13-99T99:99:99Z") is None


# ---- is_fresh -----------------------------------------------------------


class TestIsFresh:
    def _now(self) -> float:
        return _dt.datetime.now(tz=_dt.timezone.utc).timestamp()

    def _iso(self, delta_days: float) -> str:
        when = _dt.datetime.now(tz=_dt.timezone.utc) - _dt.timedelta(days=delta_days)
        return when.isoformat().replace("+00:00", "Z")

    def test_none_ttl_always_fresh(self):
        # Even an ancient row is fresh when ttl is None (never expire).
        ancient = (_dt.datetime(2000, 1, 1, tzinfo=_dt.timezone.utc)).isoformat()
        assert is_fresh(ancient, None, self._now()) is True

    def test_recent_within_ttl(self):
        assert is_fresh(self._iso(1), 30, self._now()) is True

    def test_stale_beyond_ttl(self):
        assert is_fresh(self._iso(45), 30, self._now()) is False

    def test_boundary_exactly_at_ttl(self):
        # 30 days old, ttl 30 → still fresh (<=).
        assert is_fresh(self._iso(29.99), 30, self._now()) is True

    def test_zero_ttl_never_fresh(self):
        assert is_fresh(self._iso(0.0), 0, self._now()) is False

    def test_negative_ttl_never_fresh(self):
        assert is_fresh(self._iso(0.0), -1, self._now()) is False

    def test_non_int_ttl_never_fresh(self):
        assert is_fresh(self._iso(0.0), "30", self._now()) is False  # type: ignore[arg-type]

    def test_unparseable_timestamp_is_stale(self):
        assert is_fresh("garbage", 30, self._now()) is False

    def test_empty_timestamp_is_stale(self):
        assert is_fresh("", 30, self._now()) is False


# ---- lookup_exact_url ---------------------------------------------------


@pytest.fixture
def mirror_conn(tmp_path):
    path = tmp_path / "brain.db"
    c = sqlite3.connect(str(path))
    c.row_factory = sqlite3.Row
    apply_schema(c)
    c.commit()
    yield c
    c.close()


def _insert_row(
    conn: sqlite3.Connection,
    *,
    notion_page_id: str,
    url: str,
    fetched_at: str,
    name: str = "row",
    content: str = "body",
) -> None:
    conn.execute(
        "INSERT INTO brain_web_cache("
        "  notion_page_id, name, url, query, content, fetched_at,"
        "  domain, tags, source_project_hash, content_hash,"
        "  last_edited_time, created_time) "
        "VALUES(?, ?, ?, '', ?, ?, '', '[]', 'ph', 'ch', ?, ?)",
        (notion_page_id, name, url, content, fetched_at, fetched_at, fetched_at),
    )
    conn.commit()


class TestLookupExactUrl:
    def test_empty_url_returns_none(self, mirror_conn):
        assert lookup_exact_url(mirror_conn, "") is None

    def test_no_match_returns_none(self, mirror_conn):
        _insert_row(
            mirror_conn,
            notion_page_id="p1",
            url="https://a.example",
            fetched_at="2026-04-01T00:00:00Z",
        )
        assert lookup_exact_url(mirror_conn, "https://b.example") is None

    def test_single_match_returned(self, mirror_conn):
        _insert_row(
            mirror_conn,
            notion_page_id="p1",
            url="https://a.example/x",
            fetched_at="2026-04-01T00:00:00Z",
            name="title-a",
        )
        hit = lookup_exact_url(mirror_conn, "https://a.example/x")
        assert hit is not None
        assert hit["notion_page_id"] == "p1"
        assert hit["url"] == "https://a.example/x"
        assert hit["name"] == "title-a"

    def test_multi_row_picks_freshest(self, mirror_conn):
        _insert_row(
            mirror_conn,
            notion_page_id="old",
            url="https://a.example/x",
            fetched_at="2026-01-01T00:00:00Z",
        )
        _insert_row(
            mirror_conn,
            notion_page_id="new",
            url="https://a.example/x",
            fetched_at="2026-04-01T00:00:00Z",
        )
        hit = lookup_exact_url(mirror_conn, "https://a.example/x")
        assert hit is not None
        assert hit["notion_page_id"] == "new"

    def test_multi_row_mixed_iso_formats_picks_freshest(self, mirror_conn):
        """'.000Z' and 'Z' suffixes sort differently lexicographically vs chronologically.

        Correctness gate: lookup_exact_url must pick by parsed epoch, not
        by the raw TEXT.
        """
        _insert_row(
            mirror_conn,
            notion_page_id="ancient_padded",
            url="https://same.example",
            fetched_at="2020-01-01T00:00:00.000Z",
        )
        _insert_row(
            mirror_conn,
            notion_page_id="new_terse",
            url="https://same.example",
            fetched_at="2026-04-01T00:00:00Z",
        )
        hit = lookup_exact_url(mirror_conn, "https://same.example")
        assert hit is not None
        assert hit["notion_page_id"] == "new_terse"

    def test_sqlite_error_returns_none(self, tmp_path):
        # Connect to a path that exists but has no brain_web_cache table.
        path = tmp_path / "empty.db"
        c = sqlite3.connect(str(path))
        c.row_factory = sqlite3.Row
        try:
            assert lookup_exact_url(c, "https://x.example") is None
        finally:
            c.close()
