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
