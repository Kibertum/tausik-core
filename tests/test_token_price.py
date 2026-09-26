"""Cost is weighted by billing kind, and an unpriced model is ABSENT, not free.

MEASURED, session #277, over 5964 recorded calls: cache_read is 2,876,911,173
tokens against output 4,414,827, input 22,099 and cache_create 11,736,217 — 99.5%
of all input is the cached prefix being re-sent. That single number reorders the
whole token-economy story: shrinking the prefix lowers the price of every turn and
is worth doing, but an EXTRA turn costs roughly half a million cache_read tokens,
so a change that saves request tokens at the cost of one more turn loses by about
two orders of magnitude.

WHY NO DEFAULT PRICES SHIP. A rate is an external fact with a date and a contract:
list prices move, agreements differ, the same model costs differently through
different providers. A number baked in would be right for nobody and would rot
silently. Rates live in config; a model with no entry is reported UNPRICED.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import service_token_cost as cost  # noqa: E402
import token_price as tp  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/token_price.py", "scripts/service_token_cost.py"]

_RATES = {"claude-": {"output": 75.0, "input": 15.0, "cache_create": 18.75, "cache_read": 1.5}}


def _row(model: str = "claude-opus-5", **counts: int) -> dict:
    base = {"output_tokens": 0, "input_tokens": 0, "cache_create": 0, "cache_read": 0}
    base.update(counts)
    return {"model": model, **base}


class TestUnpricedIsAbsentNotZero:
    """A zero here reads as free work, and the report would understate the bill."""

    def test_no_rates_yields_none_not_zero(self):
        result = tp.breakdown([_row(output_tokens=1_000_000)], {})
        assert result["usd"] is None
        assert result["usd_total"] is None

    def test_the_unpriced_model_is_named(self):
        result = tp.breakdown([_row(model="some-other-model", output_tokens=10)], _RATES)
        assert result["unpriced_models"] == ["some-other-model"]
        assert result["unpriced_calls"] == 1

    def test_tokens_are_still_counted_when_unpriced(self):
        """The token side does not depend on knowing a price, and dropping it would
        leave the reader with nothing at all."""
        result = tp.breakdown([_row(cache_read=500)], {})
        assert result["tokens"]["cache_read"] == 500

    def test_the_text_says_why_and_how_to_fix_it(self):
        text = tp.format_breakdown(tp.breakdown([_row(output_tokens=1)], {}))
        assert "UNPRICED" in text and "token_price" in text
        assert "free work" in text

    def test_a_partly_priced_window_says_what_was_left_out(self):
        """A total computed over half the rows looks like a small bill."""
        rows = [_row(output_tokens=1_000_000), _row(model="mystery", output_tokens=1_000_000)]
        result = tp.breakdown(rows, _RATES)
        assert result["priced_calls"] == 1
        assert result["unpriced_calls"] == 1
        assert "left out" in tp.format_breakdown(result)


class TestEachBillingKindIsPricedSeparately:
    @pytest.mark.parametrize(
        ("kind", "field", "expected"),
        [
            pytest.param("output", "output_tokens", 75.0, id="output"),
            pytest.param("input", "input_tokens", 15.0, id="input_uncached"),
            pytest.param("cache_create", "cache_create", 18.75, id="cache_create"),
            pytest.param("cache_read", "cache_read", 1.5, id="cache_read"),
        ],
    )
    def test_one_million_tokens_costs_its_own_rate(self, kind, field, expected):
        result = tp.breakdown([_row(**{field: 1_000_000})], _RATES)
        assert result["usd"][kind] == pytest.approx(expected)
        assert result["usd_total"] == pytest.approx(expected)

    def test_the_rates_differ_enough_to_matter(self):
        """The premise of the whole module: if all four were the same, weighting by
        kind would be arithmetic with no consequence."""
        assert len(set(_RATES["claude-"].values())) == 4

    def test_output_is_listed_first(self):
        """Order carries a claim: output is dearest per token and the one a harness
        change can least shrink."""
        assert tp.KINDS[0] == "output"


class TestRatesMatchByLongestPrefix:
    def test_a_family_prefix_covers_a_dated_snapshot(self):
        """A provider appends a date to a model id; a table keyed on the full id
        goes unpriced the day that suffix changes."""
        assert tp.rates_for("claude-haiku-4-5-20251001", {"claude-haiku": {"output": 5.0}})

    def test_the_longer_prefix_wins(self):
        prices = {"claude-": {"output": 75.0}, "claude-haiku": {"output": 5.0}}
        assert tp.rates_for("claude-haiku-4-5", prices)["output"] == 5.0

    def test_an_unknown_model_matches_nothing(self):
        assert tp.rates_for("gpt-5.5", _RATES) is None

    def test_a_missing_model_field_matches_nothing(self):
        assert tp.rates_for(None, _RATES) is None


class TestConfigReadingNeverGuesses:
    def test_absent_config_means_no_prices(self, tmp_path):
        assert tp.load_prices(str(tmp_path)) == {}

    def test_broken_config_means_no_prices(self, tmp_path):
        (tmp_path / "config.json").write_text("{not json", encoding="utf-8")
        assert tp.load_prices(str(tmp_path)) == {}

    def test_non_numeric_rate_is_dropped_not_coerced(self, tmp_path):
        (tmp_path / "config.json").write_text(
            json.dumps({"token_price": {"m": {"output": "dear", "input": 2}}}), encoding="utf-8"
        )
        assert tp.load_prices(str(tmp_path)) == {"m": {"input": 2.0}}

    def test_an_unknown_kind_is_ignored(self, tmp_path):
        (tmp_path / "config.json").write_text(
            json.dumps({"token_price": {"m": {"thinking": 1, "output": 2}}}), encoding="utf-8"
        )
        assert tp.load_prices(str(tmp_path)) == {"m": {"output": 2.0}}


class TestCostIsAttributedPerTask:
    """Per request the turn count is invisible; per task it is the whole story."""

    _WINDOWS = [
        {
            "slug": "wide",
            "started_at": "2026-09-01T00:00:00Z",
            "completed_at": "2026-09-30T00:00:00Z",
        },
        {
            "slug": "narrow",
            "started_at": "2026-09-10T00:00:00Z",
            "completed_at": "2026-09-11T00:00:00Z",
        },
    ]

    def test_a_call_lands_in_the_narrowest_containing_window(self):
        """Tasks overlap — one opened while another waits — and the narrower window
        is the one the work was actually inside. The rule is stated, not implied."""
        rows = [{**_row(output_tokens=10), "ts": "2026-09-10T12:00:00.000Z"}]
        result = cost.per_task(rows, self._WINDOWS)
        assert [entry["slug"] for entry in result] == ["narrow"]

    def test_a_call_outside_every_window_is_dropped(self):
        rows = [{**_row(), "ts": "2025-01-01T00:00:00Z"}]
        assert cost.per_task(rows, self._WINDOWS) == []

    def test_turns_are_counted_per_task(self):
        rows = [{**_row(), "ts": "2026-09-10T0%d:00:00Z" % i} for i in range(1, 5)]
        result = cost.per_task(rows, self._WINDOWS)
        assert result[0]["turns"] == 4

    def test_the_cache_share_is_reported(self):
        rows = [{**_row(cache_read=990, input_tokens=10), "ts": "2026-09-10T01:00:00Z"}]
        assert cost.per_task(rows, self._WINDOWS)[0]["cache_hit_share"] == pytest.approx(0.99)

    def test_two_spellings_of_utc_still_compare(self):
        """This database holds both `+00:00` and `Z`. Plain string comparison
        between them is wrong in a way that shows up as "no data": `+` sorts before
        `Z`, so an older window never contains a newer call. Found by measurement,
        not by review — the first run attributed zero calls out of 5964."""
        windows = [
            {
                "slug": "old-era",
                "started_at": "2026-09-10T00:00:00+00:00",
                "completed_at": "2026-09-12T00:00:00+00:00",
            }
        ]
        rows = [{**_row(), "ts": "2026-09-11T10:00:00.123Z"}]
        assert [e["slug"] for e in cost.per_task(rows, windows)] == ["old-era"]


class TestTheReportSurvivesEmptyInput:
    def test_no_attribution_says_why(self):
        text = cost.format_cost(
            {"window_sessions": 3, "total": tp.breakdown([], {}), "per_task": []}
        )
        assert "nothing attributed" in text
        assert "unclosed task" in text

    def test_the_per_task_table_sorts_by_turns_not_dollars(self):
        """With an unpriced model the dollar column is absent by design; sorting on
        it would make the table collapse and read as a broken feature."""
        section = {
            "window_sessions": 1,
            "total": tp.breakdown([], {}),
            "per_task": [
                {
                    "slug": "few",
                    "turns": 2,
                    "usd_total": None,
                    "cache_hit_share": 0.5,
                    "tokens": {},
                    "unpriced_calls": 2,
                },
                {
                    "slug": "many",
                    "turns": 9,
                    "usd_total": None,
                    "cache_hit_share": 0.5,
                    "tokens": {},
                    "unpriced_calls": 9,
                },
            ],
        }
        text = cost.format_cost(section)
        assert text.index("many") < text.index("few")
        assert "unpriced" in text


class TestTheLiveLedgerConfirmsTheHeadline:
    """The number that reordered the story is re-measured, not quoted."""

    def test_cache_read_dominates_the_input_side(self):
        ledger = _REPO / ".tausik" / "token_metrics.jsonl"
        if not ledger.is_file():
            pytest.skip("no telemetry in this tree")
        rows = [
            json.loads(line)
            for line in ledger.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if len(rows) < 100:
            pytest.skip("too few rows to claim a share")
        result = tp.breakdown(rows, {})
        tokens = result["tokens"]
        fresh = tokens["input"] + tokens["cache_create"]
        share = tokens["cache_read"] / (tokens["cache_read"] + fresh)
        assert share > 0.9, (
            f"cache_read is {share:.1%} of input — the premise that the turn count "
            "dominates cost rests on this being the large majority"
        )
