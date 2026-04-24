"""Unit tests for scripts/hooks/memory_markers.py.

Regex precision matters here: false positives on cross-project
preferences would swamp the audit hook's stderr with noise, training
the user to ignore it.
"""

from __future__ import annotations

import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "hooks"))

from memory_markers import Match, PATTERNS, detect_markers  # noqa: E402


class TestPositive:
    @pytest.mark.parametrize(
        "text,expected_kind",
        [
            ("path D:/Work/Personal/claude/scripts/project.py:42", "abs_path"),
            ("/home/alice/projects/thing/main.py crashed", "abs_path"),
            ("C:/Users/bob/src/app/handler.py", "abs_path"),
            ("task mem-pretool-hook done", "slug"),
            ("ticket gate-false-positives-ruff-filesize", "slug"),
            ("run .tausik/tausik status", "tausik_cmd"),
            ("called tausik_task_start then tausik_memory_add", "tausik_cmd"),
            ("edited scripts/hooks/session_start.py", "src_file"),
            ("added tests/test_gates.py and bootstrap/bootstrap.py", "src_file"),
        ],
    )
    def test_kind_detected(self, text, expected_kind):
        matches = detect_markers(text)
        kinds = {m.kind for m in matches}
        assert expected_kind in kinds, (text, matches)

    def test_match_namedtuple_shape(self):
        matches = detect_markers("task mem-pretool-hook closed")
        assert matches
        m = matches[0]
        assert isinstance(m, Match)
        assert m.kind and m.match and isinstance(m.span, tuple)
        assert m.span[0] >= 0 and m.span[1] > m.span[0]

    def test_matches_sorted_by_position(self):
        text = (
            "first edit scripts/a.py then slug mem-foo-bar-baz then path "
            "D:/Work/Personal/x/b.py"
        )
        matches = detect_markers(text)
        positions = [m.span[0] for m in matches]
        assert positions == sorted(positions)


class TestNegative:
    """Cross-project preferences must NOT be flagged."""

    @pytest.mark.parametrize(
        "text",
        [
            "user prefers Russian responses",
            "likes pytest and python 3.11",
            "uses VS Code as editor",
            "prefers concise commit messages",
            "Claude responds in the user's language",
            "format code with prettier on save",
            "uses Docker for local dev",
            "enjoys clean architecture",
            "agent should always ask before git push",
            "explains code in plain English",
            "prefers kebab-case variable names",
            "use ts-node for scripts",
            "switch-case is fine",
            "double-quoted strings over single-quoted",
        ],
    )
    def test_clean_preferences_return_empty(self, text):
        matches = detect_markers(text)
        assert matches == [], f"{text!r} → {matches}"


class TestDedup:
    def test_repeated_slug_is_returned_once(self):
        text = (
            "task mem-pretool-hook started. task mem-pretool-hook logged. "
            "task mem-pretool-hook done."
        )
        matches = [m for m in detect_markers(text) if m.kind == "slug"]
        assert len(matches) == 1
        assert matches[0].match == "mem-pretool-hook"

    def test_different_slugs_both_kept(self):
        text = "closed mem-pretool-hook and mem-bypass-mechanism today"
        matches = [m.match for m in detect_markers(text) if m.kind == "slug"]
        assert set(matches) == {"mem-pretool-hook", "mem-bypass-mechanism"}


class TestEdgeCases:
    def test_empty_text(self):
        assert detect_markers("") == []

    def test_whitespace_only(self):
        assert detect_markers("   \n\t  ") == []

    def test_patterns_list_shape(self):
        assert len(PATTERNS) >= 4
        for kind, pattern in PATTERNS:
            assert isinstance(kind, str) and kind
            assert hasattr(pattern, "finditer")


class TestTwoSegmentSlugs:
    """2-seg slug regex widening (hooks-markers-slug-regex-widen).

    Widened _SLUG_RE to {1,} captures 2-seg slugs (my-app, brain-init),
    but detect_markers drops them unless corroborated by a higher-precision
    detector or a 3+ seg slug — otherwise English kebab compounds would
    flood the audit.
    """

    def test_two_seg_slug_alone_is_dropped(self):
        """Standalone 2-seg slug looks like English — no match."""
        assert detect_markers("closed brain-init today") == []
        assert detect_markers("shipped my-app") == []

    def test_two_seg_slug_with_abs_path_kept(self):
        """Path fires → 2-seg slug corroborated, both returned."""
        text = "task my-app done; edited /home/alice/projects/thing/x.py"
        matches = detect_markers(text)
        kinds = {m.kind for m in matches}
        assert "slug" in kinds and "abs_path" in kinds
        assert any(m.match == "my-app" for m in matches)

    def test_two_seg_slug_with_src_file_kept(self):
        """src_file fires → 2-seg slug corroborated."""
        text = "brain-init tweak in scripts/brain_init.py"
        matches = detect_markers(text)
        assert any(m.kind == "slug" and m.match == "brain-init" for m in matches)
        assert any(m.kind == "src_file" for m in matches)

    def test_two_seg_slug_with_tausik_cmd_kept(self):
        """tausik_cmd fires → 2-seg slug corroborated."""
        text = "hystolab-ru: run .tausik/tausik status"
        matches = detect_markers(text)
        assert any(m.kind == "slug" and m.match == "hystolab-ru" for m in matches)
        assert any(m.kind == "tausik_cmd" for m in matches)

    def test_three_seg_slug_corroborates_two_seg_slug(self):
        """3+ seg slug is strong enough to keep a 2-seg slug in the same text."""
        text = "closed brain-init and mem-pretool-hook"
        matches = [m.match for m in detect_markers(text) if m.kind == "slug"]
        assert "mem-pretool-hook" in matches
        assert "brain-init" in matches

    def test_three_seg_slug_alone_still_fires(self):
        """Regression: standalone 3+ seg slug was already strong — unchanged."""
        matches = [
            m.match
            for m in detect_markers("task mem-pretool-hook done")
            if m.kind == "slug"
        ]
        assert matches == ["mem-pretool-hook"]


class TestPerformance:
    def test_large_text_under_budget(self):
        big = (
            "D:/Work/Personal/claude/scripts/project.py:42 " * 500
            + "task mem-pretool-hook done " * 500
            + "user prefers Russian " * 500
        )
        start = time.perf_counter()
        matches = detect_markers(big)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 50, f"took {elapsed_ms:.1f} ms on {len(big)} chars"
        assert matches
