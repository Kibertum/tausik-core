"""Delegation is the one programmatic model choice the host offers, so the advice became that.

THE MEASUREMENT. Of 218 closed tasks carrying a model id, 195 ran on the premium tier — 47 of
them rated `simple`, 90 rated `medium`. The recommendation printed at every `task start` and
was followed almost never.

WHY IT COULD ONLY ASK. The host does not switch a running session's model; decision #183
settled that the adherence metric is CALIBRATION rather than compliance for exactly that
reason. A SUBAGENT, however, is started on a model the caller picks — and it begins with a
fresh context while the session that spawned it re-sends about half a million tokens of prefix
on every call. Both multipliers of the price move at once, and the second is the larger.

WHAT THE TESTS REFUSE TO LET SLIDE: delegating complex work, delegating when the session is
already cheap enough, and delegating the CLOSURE. The last is the one that matters — a receipt
signed by a worker nobody reviewed is the failure QG-2 exists to prevent.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import model_delegation as md  # noqa: E402


class TestOnlySimpleWorkIsHandedDown:
    @pytest.mark.parametrize(
        ("complexity", "expected"),
        [
            pytest.param("simple", True, id="simple"),
            pytest.param("medium", False, id="medium"),
            pytest.param("complex", False, id="complex"),
            pytest.param(None, False, id="unset"),
            pytest.param("", False, id="empty"),
        ],
    )
    def test_the_tier_decides(self, complexity, expected):
        got = md.advise(complexity, "Sonnet 4.6", active_tier=3, recommended_tier=1)
        assert got.delegate is expected

    def test_an_unset_complexity_is_not_guessed(self):
        assert md.advise(None, "Sonnet 4.6").delegate is False


class TestDelegatingMustActuallySaveSomething:
    @pytest.mark.parametrize(
        ("complexity", "active", "recommended", "needle"),
        [
            pytest.param("complex", 3, 3, "not delegated", id="complex_points_up"),
            pytest.param("simple", 1, 1, "round-trip", id="already_cheap_enough"),
        ],
    )
    def test_a_refusal_says_why_instead_of_returning_a_bare_false(
        self, complexity, active, recommended, needle
    ):
        """Two different refusals with one shape: complex work would buy tokens with the
        thing the project sells, and a session already at the tier would buy a round-trip.
        A bare False would make them the same answer."""
        got = md.advise(complexity, "Sonnet 4.6", active_tier=active, recommended_tier=recommended)
        assert got.delegate is False
        assert needle in got.reason

    def test_a_session_below_the_recommendation_delegates_nothing_either(self):
        got = md.advise("simple", "Sonnet 4.6", active_tier=0, recommended_tier=1)
        assert got.delegate is False

    def test_no_recommended_model_means_nothing_to_delegate_to(self):
        assert md.advise("simple", None, active_tier=3, recommended_tier=1).delegate is False

    def test_without_tier_numbers_the_tier_name_still_decides(self):
        """`task start` knows the tiers; other callers may not, and the advice must not
        refuse just because the comparison is unavailable."""
        assert md.advise("simple", "Sonnet 4.6").delegate is True


class TestTheReasonCarriesBothHalvesOfTheSaving:
    def test_it_names_the_model_and_the_fresh_context(self):
        """The model tier is the visible saving; the context reset is the larger one and the
        one nobody counts."""
        reason = md.advise("simple", "Sonnet 4.6", active_tier=3, recommended_tier=1).reason
        assert "Sonnet 4.6" in reason
        assert "FRESH context" in reason
        assert f"{md.context_multiple()}x" in reason

    def test_the_context_multiple_comes_from_the_measurement(self):
        assert md.FRESH_CONTEXT_TOKENS == 42_000
        assert md.CARRIED_CONTEXT_TOKENS == 500_000
        assert md.context_multiple() == 12

    def test_the_reason_says_the_closure_stays(self):
        """THE ONE THAT MATTERS: a receipt signed by a worker nobody reviewed is the failure
        QG-2 exists to prevent."""
        reason = md.advise("simple", "Sonnet 4.6", active_tier=3, recommended_tier=1).reason
        assert "task done" in reason and "not delegated" in reason


class TestTheBannerLine:
    def test_nothing_is_printed_when_nothing_is_advised(self):
        assert md.banner_line(md.advise("complex", "Opus 4.8")) is None

    def test_the_line_is_marked_so_a_driver_can_find_it(self):
        line = md.banner_line(md.advise("simple", "Sonnet 4.6", active_tier=3, recommended_tier=1))
        assert line is not None and line.strip().startswith("↪ DELEGATE:")

    def test_task_start_prints_it_for_simple_work_on_a_premium_session(self):
        from model_routing import format_task_start_banner

        banner = format_task_start_banner("simple", active_model="claude-opus-5")
        assert "DELEGATE" in banner

    def test_task_start_says_nothing_about_delegation_for_complex_work(self):
        from model_routing import format_task_start_banner

        assert "DELEGATE" not in format_task_start_banner("complex", active_model="claude-opus-5")


class TestTheDriverRuleFollowedTheMeasurement:
    def test_the_run_skill_no_longer_forbids_delegation_outright(self):
        """It used to say "do not delegate unless the individual task says to", written
        before anything measured how often the cheaper model was actually used."""
        text = (_REPO / "harness" / "skills" / "run" / "SKILL.md").read_text(encoding="utf-8")
        assert "Do not delegate to a" not in text
        assert "Delegate what `task start` tells you to" in text

    def test_the_run_skill_keeps_the_closure_at_home(self):
        raw = (_REPO / "harness" / "skills" / "run" / "SKILL.md").read_text(encoding="utf-8")
        # Whitespace-normalised: the sentence wraps in the file, and an assertion that broke
        # on a line break would be testing the line width rather than the rule.
        text = " ".join(raw.split()).lower()
        assert "the closure is not delegated" in text
        assert "loop, not a dispatcher" in text, "the old rule still holds for everything else"
