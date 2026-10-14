"""Tests for scripts/external_reviewer.py (v15s-rule4-external-reviewer).

1.11.6 one-family rule: the recommended reviewer is the author's own family —
the model the host already runs; separation of duties is the isolated read-only
context. An unrecognised reviewer is never accepted; a reviewer from another
family is not a separate duty but a prohibited pull; the delegation hint never
crashes on an unknown author.
"""

from __future__ import annotations

import os
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import external_reviewer as er  # noqa: E402


class TestRecommendReviewerModel:
    @pytest.mark.parametrize(
        "author_id, expected",
        [
            ("claude-opus-4-8", "opus"),
            ("claude-sonnet-4-6", "sonnet"),
            ("glm-5.2", "glm-5.2"),
            ("zai-coding-plan/glm-4.7 [200k]", "glm-4.7"),
        ],
        ids=["claude-tier", "other-claude-tier", "released-glm", "host-spelling"],
    )
    def test_reviewer_family_is_the_authors_own(self, author_id, expected):
        assert er.recommend_reviewer_model(author_id) == expected

    def test_unknown_author_names_the_rule_instead_of_guessing_a_family(self):
        # Unknown author must not crash and must not invent a family the host
        # may not run — the hint then asks for --author-model.
        assert er.recommend_reviewer_model(None) == "the model this host already runs"
        assert er.recommend_reviewer_model("mystery-model") == "the model this host already runs"


class TestIsSeparateDuty:
    @pytest.mark.parametrize(
        "author, reviewer",
        [
            ("claude-sonnet-4-6", "claude-opus-4-8"),
            ("glm-5.2", "glm-5.2"),
        ],
        ids=["same-vendor-family", "same-model"],
    )
    def test_same_family_is_the_duty_form(self, author, reviewer):
        # 1.11.6: the author's own family — down to the identical model — is
        # the reviewer form; separation is the isolated context.
        assert er.is_separate_duty(author, reviewer) is True

    def test_another_family_is_prohibited_not_separate(self):
        # Pulling another family is a rule violation, not a second opinion.
        assert er.is_separate_duty("claude-sonnet-4-6", "glm-5.2") is False
        assert er.is_separate_duty("glm-5.2", "claude-opus-5-5") is False

    def test_unknown_reviewer_is_not_separate(self):
        # Cannot prove the reviewer is a real model -> False.
        assert er.is_separate_duty("claude-sonnet-4-6", "mystery-model") is False
        assert er.is_separate_duty("claude-sonnet-4-6", None) is False


class TestReviewerHint:
    def test_hint_names_subagent_and_the_one_family_rule(self):
        hint = er.reviewer_hint("claude-sonnet-4-6")
        assert "@tausik-external-reviewer" in hint
        assert "SAME model family" in hint
        assert "Author model: claude-sonnet-4-6" in hint

    def test_hint_on_unknown_author_does_not_crash(self):
        # Boundary: no transcript -> author None -> still a valid hint.
        hint = er.reviewer_hint(None)
        assert "@tausik-external-reviewer" in hint
        assert "pass --author-model" in hint
