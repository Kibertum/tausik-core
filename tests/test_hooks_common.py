"""Tests for scripts/hooks/_common.py — shared hook helpers.

Primary focus: marker_present_anchored and last_user_prompt_text, which
together close the substring-bypass hole (user quoting the hook's error
text should NOT re-enable the guard on the next turn).
"""

from __future__ import annotations

import json
import os
import sys

_HOOK_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "scripts", "hooks")
)
if _HOOK_DIR not in sys.path:
    sys.path.insert(0, _HOOK_DIR)

from _common import (  # noqa: E402
    last_user_prompt_text,
    marker_present_anchored,
)


class TestMarkerPresentAnchored:
    def test_exact_line_returns_true(self):
        assert marker_present_anchored(
            "confirm: cross-project", "confirm: cross-project"
        )

    def test_line_with_leading_trailing_whitespace(self):
        assert marker_present_anchored(
            "   confirm: cross-project  ", "confirm: cross-project"
        )

    def test_case_insensitive(self):
        assert marker_present_anchored(
            "CONFIRM: Cross-Project", "confirm: cross-project"
        )

    def test_multiline_marker_on_its_own_line(self):
        text = "First line\nconfirm: cross-project\nlast line"
        assert marker_present_anchored(text, "confirm: cross-project")

    def test_substring_only_returns_false(self):
        """Pre-fix behavior: this would incorrectly return True."""
        text = "I know I should reply with `confirm: cross-project` but I'm just asking"
        assert not marker_present_anchored(text, "confirm: cross-project")

    def test_marker_inside_fenced_code_block_returns_false(self):
        text = "Here's the hook message:\n```\nreply with `confirm: cross-project` in your next message\n```\nWhat do I do?"
        assert not marker_present_anchored(text, "confirm: cross-project")

    def test_marker_inside_multiline_fenced_block_returns_false(self):
        text = "```text\nconfirm: cross-project\n```"
        assert not marker_present_anchored(text, "confirm: cross-project")

    def test_marker_after_closing_fence_returns_true(self):
        text = "```\nquoted hook text\n```\nconfirm: cross-project"
        assert marker_present_anchored(text, "confirm: cross-project")

    def test_marker_before_opening_fence_returns_true(self):
        text = "confirm: cross-project\n```\nthen some quoted hook text\n```"
        assert marker_present_anchored(text, "confirm: cross-project")

    def test_empty_text_returns_false(self):
        assert not marker_present_anchored("", "confirm: cross-project")

    def test_empty_marker_returns_false(self):
        assert not marker_present_anchored("some text", "")

    def test_whitespace_only_marker_returns_false(self):
        assert not marker_present_anchored("some text", "   \n\t")

    def test_marker_as_part_of_sentence_returns_false(self):
        text = "Ok I confirm: cross-project settings are fine"
        assert not marker_present_anchored(text, "confirm: cross-project")

    def test_partial_line_match_returns_false(self):
        text = "confirm: cross-project -- but only for this file"
        assert not marker_present_anchored(text, "confirm: cross-project")

    # HIGH-2 regressions: close bypasses found in the second review pass.

    def test_u2028_line_separator_does_NOT_trigger_bypass(self):
        """U+2028 is invisible but splitlines() treats it as a line break —
        an attacker could sneak the marker into prose with U+2028 on each
        side and have it masquerade as a line of its own."""
        text = "hook said confirm: cross-project right?"
        assert not marker_present_anchored(text, "confirm: cross-project")

    def test_u2029_paragraph_separator_does_NOT_trigger_bypass(self):
        text = "hook said confirm: cross-project right?"
        assert not marker_present_anchored(text, "confirm: cross-project")

    def test_u0085_nel_does_NOT_trigger_bypass(self):
        """NEL (next line, U+0085) — same bypass class."""
        text = "hook saidconfirm: cross-projectright?"
        assert not marker_present_anchored(text, "confirm: cross-project")

    def test_tilde_fenced_block_does_NOT_trigger_bypass(self):
        """CommonMark allows ~~~ as a fence alternative to ```. A marker
        inside a tilde-fenced block must also be skipped."""
        text = "The hook said:\n~~~\nconfirm: cross-project\n~~~\nWhat do I do?"
        assert not marker_present_anchored(text, "confirm: cross-project")

    def test_tilde_fence_with_language_tag_does_NOT_trigger_bypass(self):
        text = "~~~text\nconfirm: cross-project\n~~~"
        assert not marker_present_anchored(text, "confirm: cross-project")

    def test_four_space_indented_line_does_NOT_trigger_bypass(self):
        """Markdown indented-code block — 4+ leading spaces makes the line
        render as code in most agents / UIs. Must not count as the marker."""
        text = "The hook said:\n\n    confirm: cross-project\n\nWhat do I do?"
        assert not marker_present_anchored(text, "confirm: cross-project")

    def test_tab_indented_line_does_NOT_trigger_bypass(self):
        text = "The hook said:\n\n\tconfirm: cross-project\n\nWhat do I do?"
        assert not marker_present_anchored(text, "confirm: cross-project")

    def test_three_space_indent_still_triggers_bypass(self):
        """3 spaces is not an indented-code block — still a regular line."""
        text = "   confirm: cross-project"
        assert marker_present_anchored(text, "confirm: cross-project")


class TestLastUserPromptText:
    def _write(self, tmp_path, events):
        p = tmp_path / "t.jsonl"
        with open(p, "w", encoding="utf-8") as f:
            for ev in events:
                f.write(json.dumps(ev) + "\n")
        return str(p)

    def test_missing_file_returns_empty(self):
        assert last_user_prompt_text("") == ""
        assert last_user_prompt_text("/nope/does/not/exist.jsonl") == ""

    def test_last_user_content_string(self, tmp_path):
        path = self._write(
            tmp_path,
            [
                {"type": "user", "message": {"content": "first"}},
                {"type": "assistant", "message": {"content": "ignore me"}},
                {"type": "user", "message": {"content": "second and latest"}},
            ],
        )
        assert last_user_prompt_text(path) == "second and latest"

    def test_user_content_list_of_text_parts(self, tmp_path):
        path = self._write(
            tmp_path,
            [
                {
                    "type": "user",
                    "message": {
                        "content": [
                            {"type": "text", "text": "line one"},
                            {"type": "text", "text": "line two"},
                        ]
                    },
                }
            ],
        )
        assert last_user_prompt_text(path) == "line one\nline two"

    def test_malformed_jsonl_lines_skipped(self, tmp_path):
        p = tmp_path / "t.jsonl"
        with open(p, "w", encoding="utf-8") as f:
            f.write('{"broken')
            f.write("\n")
            f.write(json.dumps({"type": "user", "message": {"content": "good"}}))
            f.write("\n")
        assert last_user_prompt_text(str(p)) == "good"

    def test_no_user_events_returns_empty(self, tmp_path):
        path = self._write(
            tmp_path,
            [
                {"type": "assistant", "message": {"content": "hi"}},
                {"type": "system", "message": {"content": "setup"}},
            ],
        )
        assert last_user_prompt_text(path) == ""

    def test_empty_file_returns_empty(self, tmp_path):
        p = tmp_path / "t.jsonl"
        p.write_text("")
        assert last_user_prompt_text(str(p)) == ""

    def test_huge_transcript_uses_tail_read(self, tmp_path):
        """v1.3.4 (med-batch-1-hooks #5): 1MB transcript still works without
        loading the whole file. The function should pick up the LAST user
        record even when it sits past 50KB of leading garbage events."""
        p = tmp_path / "huge.jsonl"
        # Padding: ~1MB of assistant/system events that should NOT match
        padding_event = json.dumps(
            {"type": "assistant", "message": {"content": "x" * 200}}
        )
        # ~1MB padding: each line ~250 bytes; 4000 lines = 1MB
        with open(p, "w", encoding="utf-8") as f:
            for _ in range(4000):
                f.write(padding_event + "\n")
            # Real user event at the very end (within the last 50KB)
            f.write(
                json.dumps({"type": "user", "message": {"content": "TARGET"}}) + "\n"
            )
        assert last_user_prompt_text(str(p)) == "TARGET"

    def test_user_event_outside_tail_window_not_found(self, tmp_path):
        """Documents the bound: if the most recent user event is >50KB from
        end, it's correctly not returned (only assistant/system in the
        tail). Acceptable cost for the memory bound."""
        p = tmp_path / "huge.jsonl"
        # Old user event
        with open(p, "w", encoding="utf-8") as f:
            f.write(json.dumps({"type": "user", "message": {"content": "OLD"}}) + "\n")
            # Now write >50KB of assistant padding so the user event ends up
            # before the seek window
            padding = json.dumps(
                {"type": "assistant", "message": {"content": "x" * 500}}
            )
            for _ in range(200):  # ~110KB of padding
                f.write(padding + "\n")
        out = last_user_prompt_text(str(p))
        # The OLD user event is past the tail window; no user in the tail.
        # The function returns "" (no user found in scanned tail).
        assert out == ""

    def test_partial_first_line_after_seek_dropped(self, tmp_path):
        """Tail-read drops the first (potentially partial) line so
        json.loads doesn't choke on a half-record at the seek boundary."""
        p = tmp_path / "transcript.jsonl"
        # Put a complete user event near the start, then enough padding
        # so the seek lands mid-record. The mid-record line should be
        # dropped and the LATER user event picked up.
        padding = json.dumps({"type": "assistant", "message": {"content": "y" * 500}})
        with open(p, "w", encoding="utf-8") as f:
            for _ in range(150):
                f.write(padding + "\n")
            f.write(
                json.dumps({"type": "user", "message": {"content": "LATEST"}}) + "\n"
            )
        assert last_user_prompt_text(str(p)) == "LATEST"


class TestIntegration:
    """Regression: the concrete user scenario that motivated this fix."""

    def test_quoted_hook_text_in_fenced_block_does_not_trigger_bypass(self, tmp_path):
        """User pastes the hook error text while asking a question. The bypass
        MUST stay armed — reply the real marker on its own line to override."""
        hook_error = (
            "BLOCKED: Writing to Claude auto-memory.\n"
            "reply explicitly with the marker `confirm: cross-project`"
        )
        prompt = (
            f"The hook said:\n```\n{hook_error}\n```\n"
            "What does that mean — is my config wrong?"
        )
        p = tmp_path / "t.jsonl"
        with open(p, "w", encoding="utf-8") as f:
            f.write(json.dumps({"type": "user", "message": {"content": prompt}}))
            f.write("\n")
        text = last_user_prompt_text(str(p))
        assert not marker_present_anchored(text, "confirm: cross-project")

    def test_deliberate_bypass_on_own_line_works(self, tmp_path):
        prompt = "I really mean this — I want the cross-project setting.\nconfirm: cross-project"
        p = tmp_path / "t.jsonl"
        with open(p, "w", encoding="utf-8") as f:
            f.write(json.dumps({"type": "user", "message": {"content": prompt}}))
            f.write("\n")
        text = last_user_prompt_text(str(p))
        assert marker_present_anchored(text, "confirm: cross-project")
