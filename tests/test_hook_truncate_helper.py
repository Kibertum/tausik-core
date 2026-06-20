"""Tests for v14b-token-tier1-quick-wins T1.4 — hooks.truncate helper."""

from __future__ import annotations

import os
import sys

_HOOKS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts", "hooks"))
if _HOOKS not in sys.path:
    sys.path.insert(0, _HOOKS)

from _common import truncate  # noqa: E402


class TestTruncate:
    def test_short_string_passes_through(self):
        assert truncate("hello", 100) == "hello"

    def test_at_limit_unchanged(self):
        s = "x" * 100
        assert truncate(s, 100) == s

    def test_over_limit_truncated_with_ellipsis(self):
        s = "x" * 200
        out = truncate(s, 100)
        assert len(out) == 100
        assert out.endswith("…")
        assert out[:-1] == "x" * 99

    def test_default_limit_is_100(self):
        out = truncate("y" * 500)
        assert len(out) == 100
        assert out.endswith("…")

    def test_empty_string_returns_empty(self):
        # NEGATIVE: degenerate input must not crash.
        assert truncate("", 100) == ""

    def test_none_returns_empty(self):
        # NEGATIVE: None must be tolerated.
        assert truncate(None, 100) == ""

    def test_non_string_coerced(self):
        # int → "12345"; len 5 ≤ 100 → unchanged.
        assert truncate(12345, 100) == "12345"

    def test_zero_limit_returns_just_ellipsis(self):
        # Edge: limit=0 means "no chars allowed" — return ellipsis-only or empty.
        out = truncate("anything", 0)
        # Any of these is acceptable defensive output; pin to the actual impl.
        assert out in ("", "…")

    def test_one_char_limit(self):
        out = truncate("hello", 1)
        assert out == "…"
