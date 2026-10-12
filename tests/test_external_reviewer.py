"""Tests for scripts/external_reviewer.py (v15s-rule4-external-reviewer).

SENAR Rule 4 separation of duties: the recommended reviewer model is always a
different family than the author's; an unknown reviewer is never accepted as a
separate duty; the delegation hint never crashes on an unknown author.
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
        "author_id",
        [
            "claude-opus-4-8",
            "claude-opus-4-7[1m]",
            "claude-sonnet-4-6",
            "claude-haiku-4-5",
            "claude-fable-5",
        ],
    )
    def test_reviewer_family_differs_from_author(self, author_id):
        from model_routing import _model_family

        reviewer = er.recommend_reviewer_model(author_id)
        assert reviewer != _model_family(author_id)

    def test_opus_author_falls_back_to_fable(self):
        # Opus author -> can't pick opus -> next preference is fable.
        assert er.recommend_reviewer_model("claude-opus-4-8") == "fable"

    def test_non_opus_author_gets_opus(self):
        assert er.recommend_reviewer_model("claude-sonnet-4-6") == "opus"

    def test_unknown_author_defaults_to_opus(self):
        # AC4: unknown/None author must not crash and yields the strongest pick.
        assert er.recommend_reviewer_model(None) == "opus"
        assert er.recommend_reviewer_model("gpt-9-turbo") == "opus"


class TestIsSeparateDuty:
    def test_different_family_is_separate(self):
        assert er.is_separate_duty("claude-sonnet-4-6", "claude-opus-4-8") is True

    def test_same_family_is_not_separate(self):
        # opus-4-7 author vs opus-4-8 reviewer = same family = NOT a second opinion.
        assert er.is_separate_duty("claude-opus-4-7", "claude-opus-4-8") is False

    def test_unknown_reviewer_is_not_separate(self):
        # Cannot prove independence of an unrecognised reviewer -> False.
        assert er.is_separate_duty("claude-sonnet-4-6", "mystery-model") is False
        assert er.is_separate_duty("claude-sonnet-4-6", None) is False


class TestReviewerHint:
    def test_hint_names_subagent_and_model(self):
        hint = er.reviewer_hint("claude-sonnet-4-6")
        assert "@tausik-external-reviewer" in hint
        assert "Opus" in hint  # different from the Sonnet author
        assert "Sonnet" in hint  # names the author it differs from

    def test_hint_on_unknown_author_does_not_crash(self):
        # AC4 boundary: no transcript -> author None -> still a valid hint.
        hint = er.reviewer_hint(None)
        assert "@tausik-external-reviewer" in hint
        assert "Opus" in hint
