"""The bill, with the stream that makes it.

THE MEASUREMENT. Over the last ten sessions this project read 3,044,531,708 cached tokens
against 3,922,523 of output — 776 times as many. Priced, that is $1298.96 of cache read
against $82.44 of output: cache is 94.3% of the bill and output 5.7%.

WHY IT WENT UNSAID FOR SO LONG. Rates lived in two places that could not answer together.
`cost_pricing` ships a table of input and output and prices no cache at all, and it is what
writes `usage_events.cost_usd`. `token_price` understands cache but read rates only from a
config nobody had filled, so the cache-aware report printed UNPRICED. One path counted the
small stream; the other could see the large one and had no rate for it. Reading the first,
this project's own author concluded that output was the bill and said so out loud.

WHAT THESE TESTS GUARD. That the derivation stays one number per model, that a project's
own price still wins, and that an unpriced model is still an absence rather than a zero —
because a row claiming work was free is the failure the pricing code was rewritten against
once already.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import token_price as tp  # noqa: E402


class TestTheCacheRatesAreDerivedNotListed:
    def test_a_shipped_model_prices_all_four_kinds(self):
        """AC-1. No config entry, and the report still costs — the state before this was
        UNPRICED over 5953 calls."""
        rates = tp.builtin_rates("claude-opus-5")
        assert rates is not None
        assert set(rates) == set(tp.KINDS)

    def test_the_cache_rates_are_the_published_multiples_of_input(self):
        """AC-2 and AC-3, on a worked example. A second table would drift, and the two
        would then disagree about the stream that dominates the bill."""
        rates = tp.builtin_rates("claude-opus-5")
        assert rates is not None
        assert rates["cache_read"] == pytest.approx(rates["input"] * 0.1)
        assert rates["cache_create"] == pytest.approx(rates["input"] * 1.25)
        assert (tp.CACHE_READ_MULTIPLIER, tp.CACHE_CREATE_MULTIPLIER) == (0.1, 1.25)

    def test_the_arithmetic_on_a_named_example(self):
        """Opus ships at $5 input: a million cached reads cost $0.50 and a million cache
        writes $6.25. Pinned here so a change to either multiplier has to be deliberate."""
        rates = tp.builtin_rates("claude-opus-5")
        assert rates is not None and rates["input"] == pytest.approx(5.0)
        assert rates["cache_read"] == pytest.approx(0.5)
        assert rates["cache_create"] == pytest.approx(6.25)

    def test_a_dated_suffix_still_prices(self):
        """A provider adds a date to an id, and a table keyed on the full id would go
        unpriced the day the suffix changes."""
        assert tp.builtin_rates("claude-haiku-4-5-20251001") is not None


class TestAbsenceSurvives:
    @pytest.mark.parametrize("model", [None, "", "gpt-neverheardofit", "llama-local"])
    def test_a_model_with_no_price_gives_nothing_rather_than_zero(self, model):
        """NEGATIVE, AC-4. A row saying the work cost $0.00 is the failure this pricing
        code was rewritten against: 55,471 rows once asserted work had been free."""
        assert tp.builtin_rates(model) is None
        assert tp.rates_for(model, {}) is None

    def test_an_unpriced_model_is_left_out_and_counted(self):
        """It must be visible that something was NOT priced, or the total reads as whole."""
        rows = [{"model": "gpt-neverheardofit", "output": 10, "cache_read": 10}]
        got = tp.breakdown(rows, {})
        assert got["unpriced_calls"] == 1
        assert "gpt-neverheardofit" in got["unpriced_models"]


class TestAProjectsOwnPriceWins:
    def test_the_config_overrides_the_shipped_table(self):
        """NEGATIVE, AC-5. Overriding rather than merging is what lets a reader of the
        config predict the bill from what they wrote."""
        mine = {"claude-opus": {"input": 1.0, "output": 2.0}}
        got = tp.rates_for("claude-opus-5", mine)
        assert got == mine["claude-opus"], "no shipped keys leak in"
        assert "cache_read" not in got, "what the project did not declare is not invented"

    def test_the_shipped_table_answers_only_when_the_config_is_silent(self):
        got = tp.rates_for("claude-opus-5", {"claude-sonnet": {"input": 1.0}})
        assert got is not None and got["input"] == pytest.approx(5.0)

    def test_the_longest_matching_prefix_still_wins(self):
        prices = {"claude": {"input": 1.0}, "claude-opus-5": {"input": 9.0}}
        assert tp.rates_for("claude-opus-5", prices)["input"] == pytest.approx(9.0)


class TestTheReportNamesTheShare:
    @staticmethod
    def _priced(output: int, cache_read: int):
        rows = [{"model": "claude-opus-5", "output": output, "cache_read": cache_read}]
        return tp.breakdown(rows, {})

    def test_it_says_what_fraction_is_cache(self):
        """AC-6. Reading the rows alone is what produced the wrong conclusion once; the
        share is one line and it IS the conclusion."""
        text = tp.format_breakdown(self._priced(output=1_000_000, cache_read=1_000_000_000))
        assert "cache is" in text and "output is" in text
        assert "FEWER CALLS" in text

    def test_the_share_matches_the_rows_it_summarises(self):
        got = self._priced(output=1_000_000, cache_read=1_000_000_000)
        cache = got["usd"]["cache_read"] + got["usd"]["cache_create"]
        text = tp.format_breakdown(got)
        assert f"{100 * cache / got['usd_total']:.1f}%" in text

    def test_nothing_priced_prints_no_share_at_all(self):
        """NEGATIVE. A share of nothing would be a division by zero dressed as a finding."""
        text = tp.format_breakdown(tp.breakdown([], {}))
        assert "cache is" not in text


class TestTheTwoCostFieldsAreNotConfusedForEachOther:
    def test_the_module_says_why_usage_events_cost_stays_narrower(self):
        """AC-7. `usage_events.cost_usd` is input plus output and no cache, because the
        hook payload carries no cache counters — they come from the transcript. Two numbers
        that mean different things must not be read as one."""
        doc = tp.builtin_rates.__doc__ or ""
        assert "usage_events.cost_usd" in doc
        assert "not to be read as one" in doc
