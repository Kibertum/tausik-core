"""Tests for scripts/cost_pricing.py — shared model pricing module.

cost-pricing-missing-opus-48 rewrote the expectations in this file, because the
old ones asserted the defect. They locked in Opus at $15/$75 (the real tier is
$5/$25) and a 2x "1M-context premium" that does not exist on the current Opus
and Sonnet tiers — so the suite stayed green while `tausik metrics --cost`
reported figures that were wrong in both directions, and said nothing at all
about `claude-opus-4-8`, the model this project actually runs on, which had no
price row and therefore metered at $0.00.

A test that asserts today's table is worth little; `TestPricingCoverage` is the
part that earns its keep, because it fails when a model becomes routable
without a price instead of waiting for someone to notice the zero.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from cost_pricing import calculate_cost_usd, get_pricing, known_models


class TestGetPricing:
    def test_known_canonical_id(self):
        p = get_pricing("claude-opus-4-7")
        assert p == {"input": 5.0, "output": 25.0}

    def test_short_alias_matches_canonical(self):
        assert get_pricing("opus") == get_pricing("claude-opus-4-8")
        assert get_pricing("sonnet") == get_pricing("claude-sonnet-4-6")
        assert get_pricing("haiku") == get_pricing("claude-haiku-4-5")

    def test_whitespace_tolerated(self):
        assert get_pricing("  haiku  ") == get_pricing("haiku")

    def test_empty_or_none_returns_none(self):
        assert get_pricing(None) is None
        assert get_pricing("") is None
        assert get_pricing("   ") is None


class TestCalculateCostUsd:
    def test_known_model_computes_expected_cost(self):
        # 1M input @ $5 + 1M output @ $25 = $30
        assert calculate_cost_usd("opus", 1_000_000, 1_000_000) == pytest.approx(30.0)

    def test_haiku_cheaper_than_opus(self):
        same = (10_000, 5_000)
        assert calculate_cost_usd("haiku", *same) < calculate_cost_usd("opus", *same)

    def test_rounding_to_4_decimals(self):
        # Tiny amount → must not raise / lose precision
        cost = calculate_cost_usd("haiku", 1, 1)
        assert cost == round(cost, 4)


class TestExtendedContextSuffix:
    """v14b-defect-cost-pricing-1m-suffix — `[Nm]` extended-context suffix
    must resolve to a non-None pricing row. Otherwise every 1M-context tool
    call writes cost_usd=0.0, defeating B4 cost telemetry.

    The RATE these rows carry changed in cost-pricing-missing-opus-48: 1M is the
    standard context window on the current Opus and Sonnet tiers, billed at the
    standard rate, so the suffix names a window and not a price tier. The old
    2x expectation here was extrapolated from a superseded Sonnet tier.
    """

    @pytest.mark.parametrize(
        "model_id,expected_input,expected_output",
        [
            # At parity with the base tier — no long-context premium exists.
            pytest.param("claude-opus-4-8[1m]", 5.0, 25.0, id="opus_48_1m_explicit_entry"),
            pytest.param("claude-opus-4-7[1m]", 5.0, 25.0, id="opus_1m_explicit_entry"),
            pytest.param("claude-sonnet-4-6[1m]", 3.0, 15.0, id="sonnet_1m_explicit_entry"),
            # Haiku 4.5 has no 1M tier at all; the suffix strips to the base row.
            pytest.param("claude-haiku-4-5[1m]", 1.0, 5.0, id="haiku_1m_strips_to_base"),
        ],
    )
    def test_1m_explicit_entry(self, model_id, expected_input, expected_output):
        p = get_pricing(model_id)
        assert p is not None
        assert p["input"] == expected_input
        assert p["output"] == expected_output

    def test_unknown_base_with_suffix_falls_back_to_none(self):
        # No canonical entry for this base; strip-suffix fallback also misses.
        assert get_pricing("claude-mystery-9-9[1m]") is None

    def test_calculate_cost_nonzero_for_1m_opus(self):
        cost = calculate_cost_usd("claude-opus-4-7[1m]", 1_000_000, 100_000)
        assert cost > 0.0
        # 1M @ $5 + 100k @ $25 = $5.00 + $2.50 = $7.50
        assert cost == pytest.approx(7.5)

    def test_calculate_cost_unknown_with_none_is_absent_not_zero(self):
        """Negative: explicit None model id. There is no price to apply, so
        there is no cost — which is not the same claim as a cost of zero."""
        assert calculate_cost_usd(None, 1000, 100) is None


# Module-level: G43 — None returned across two TestGetPricing/TestExtendedContextSuffix scenarios
@pytest.mark.parametrize(
    "model_id",
    [
        pytest.param("claude-mystery-9-9", id="unknown_model_returns_none"),
        pytest.param("gpt-5", id="unknown_model_returns_none_gpt"),
        pytest.param("[1m]", id="bare_suffix_returns_none"),
        pytest.param("   [1m]   ", id="bare_suffix_returns_none_padded"),
    ],
)
def test_get_pricing_returns_none(model_id):
    assert get_pricing(model_id) is None


# Module-level: G47 — case-insensitive / fallback equivalence across two classes
@pytest.mark.parametrize(
    "lhs,rhs",
    [
        pytest.param("OPUS", "opus", id="case_insensitive_lookup_alias"),
        pytest.param("Claude-Opus-4-7", "claude-opus-4-7", id="case_insensitive_lookup_canonical"),
        pytest.param(
            "claude-opus-4-7[2m]",
            "claude-opus-4-7",
            id="unknown_suffix_falls_back_to_canonical_base_opus",
        ),
        pytest.param(
            "claude-sonnet-4-6[batch]",
            "claude-sonnet-4-6",
            id="unknown_suffix_falls_back_to_canonical_base_sonnet",
        ),
        pytest.param(
            "CLAUDE-OPUS-4-7[1m]",
            "claude-opus-4-7[1m]",
            id="case_insensitive_with_suffix_upper",
        ),
        pytest.param(
            "Claude-Opus-4-7[1M]",
            "claude-opus-4-7[1m]",
            id="case_insensitive_with_suffix_mixed",
        ),
    ],
)
def test_pricing_lookup_equivalence(lhs, rhs):
    assert get_pricing(lhs) == get_pricing(rhs)


# Module-level: G48 — calculate_cost_usd returns 0.0 across multiple zero-cost scenarios
@pytest.mark.parametrize(
    "model_id,input_tokens,output_tokens",
    [
        pytest.param("unknown", 1_000_000, 1_000_000, id="unknown_model_is_absent"),
        pytest.param(
            "claude-mystery-9-9[1m]",
            1000,
            100,
            id="unknown_base_with_suffix_is_absent",
        ),
    ],
)
def test_calculate_cost_absent_when_unpriced(model_id, input_tokens, output_tokens):
    """An unpriced model yields ABSENCE. It used to yield 0.0, and that is how
    55,471 rows came to assert that work had been free."""
    assert calculate_cost_usd(model_id, input_tokens, output_tokens) is None


def test_a_priced_model_with_zero_tokens_really_does_cost_zero():
    """The other direction, and the one that must not be lost: zero tokens on a
    PRICED model is a measurement whose answer happens to be nought."""
    assert calculate_cost_usd("opus", 0, 0) == 0.0


class TestKnownModels:
    def test_includes_canonical_and_aliases(self):
        models = known_models()
        assert "claude-opus-4-8" in models
        assert "claude-opus-4-7" in models
        assert "claude-sonnet-4-6" in models
        assert "claude-haiku-4-5" in models
        assert "opus" in models
        assert "sonnet" in models
        assert "haiku" in models

    def test_returns_tuple(self):
        assert isinstance(known_models(), tuple)


class TestPricingCoverage:
    """The guard that makes the $0.00-meter defect non-repeatable.

    `claude-opus-4-8` was routed as the default `opus` rank while absent from
    the price table. Nothing failed — the cost meter simply reported zero. This
    class fails instead, and names the file to fix.
    """

    def test_every_routed_claude_model_has_a_price(self):
        from cost_pricing import models_missing_pricing

        missing = models_missing_pricing()
        assert not missing, (
            f"these Claude models can be routed to but carry no price row, so any "
            f"work sent to them records cost_usd=0.0: {sorted(missing)}. "
            f"Add them to scripts/cost_pricing.py::_MODEL_PRICING."
        )

    def test_the_guard_reads_the_real_routing_tables(self):
        """A guard judging its own copy of the data proves nothing (convention
        #266) — this asserts it reaches the tables that actually decide routing."""
        import model_profiles
        from cost_pricing import routed_claude_model_ids

        declared = {
            str(spec["model"]).lower()
            for spec in model_profiles.DEFAULT_FAMILIES["claude"].values()
        }
        assert declared <= routed_claude_model_ids()

    def test_guard_reads_the_effective_config_not_only_defaults(self):
        """The gap adversarial review found: the guard read DEFAULT_FAMILIES,
        never `load_families(config)`, so a project that repointed a rank at an
        unpriced Claude id via `.tausik/config.json` kept metering it at $0.00
        while the guard stayed green (s130-review-fixes). A config override to
        an unpriced Claude id must now be reported."""
        from cost_pricing import models_missing_pricing, routed_claude_model_ids

        cfg = {"model_profiles": {"families": {"claude": {"opus": {"model": "claude-opus-99-0"}}}}}
        assert "claude-opus-99-0" in routed_claude_model_ids(cfg)
        assert "claude-opus-99-0" in models_missing_pricing(cfg)

    def test_guard_reads_per_phase_routing_overrides(self):
        """`model_routing.<phase>` can name an arbitrary id that suggest_model
        hands straight to pricing — it must be covered too."""
        from cost_pricing import models_missing_pricing

        cfg = {"model_routing": {"implement": "claude-sonnet-88-0"}}
        assert "claude-sonnet-88-0" in models_missing_pricing(cfg)

    def test_guard_fires_on_an_unpriced_routed_model(self, monkeypatch):
        """Fail-then-pass: the guard must actually catch something, not return
        an empty set because it looks nowhere."""
        import cost_pricing

        monkeypatch.setattr(
            cost_pricing,
            "routed_claude_model_ids",
            lambda *a, **k: {"claude-opus-9-9", "claude-opus-4-8"},
        )
        assert cost_pricing.models_missing_pricing() == {"claude-opus-9-9"}

    def test_non_claude_families_are_excluded(self):
        """GLM and other configured families are not billed at Anthropic rates;
        inventing a price for them would be worse than reporting none."""
        from cost_pricing import routed_claude_model_ids

        assert not [m for m in routed_claude_model_ids() if not m.startswith("claude")]


class TestConfigPricingOverride:
    """cost-pricing-non-claude-families-silent-zero (A): the project override.

    `llm_pricing_usd_per_million` was normalized on every config load and never
    read — the consumer it was missing. Wiring it lets a project on GLM / a
    custom model price its own telemetry instead of recording $0.00.
    """

    def test_override_prices_a_non_claude_model_flat(self):
        cfg = {"llm_pricing_usd_per_million": {"glm-4.6": 2.0}}
        assert get_pricing("glm-4.6", config=cfg) == {"input": 2.0, "output": 2.0}

    def test_override_ignored_without_config(self):
        """No config in hand → the override is invisible; behaviour is unchanged."""
        assert get_pricing("glm-4.6") is None

    def test_override_computes_nonzero_cost(self):
        cfg = {"llm_pricing_usd_per_million": {"glm-4.6": 2.0}}
        # 1M input @ $2 + 500k output @ $2 = $2.00 + $1.00 = $3.00
        assert calculate_cost_usd("glm-4.6", 1_000_000, 500_000, config=cfg) == pytest.approx(3.0)

    @pytest.mark.parametrize(
        "cfg_prices,expected",
        [
            # PRECEDENCE REVERSED in session #225, deliberately. This used to
            # assert the opposite — the built-in table beating the project's own
            # config — which made the setting a gap-filler rather than a setting.
            # Measured consequence: `claude-sonnet-5` sat in the table at $3/$15
            # for months (it is $2/$10) and no project could correct it without
            # editing Python.
            ({"claude-opus-4-8": 999.0}, {"input": 999.0, "output": 999.0}),
            # ...and the other half: authority is PER MODEL, not all-or-nothing.
            # Pricing one model must not blank every other model's shipped rate.
            ({"glm-4.6": 2.0}, {"input": 5.0, "output": 25.0}),
        ],
    )
    def test_config_authority_is_per_model(self, cfg_prices, expected):
        cfg = {"llm_pricing_usd_per_million": cfg_prices}
        assert get_pricing("claude-opus-4-8", config=cfg) == expected

    def test_lazy_config_load_when_caller_passes_none(self, monkeypatch):
        """calculate_cost_usd loads the effective config on a table miss, so a
        priced GLM model is non-zero even when the caller threads no config."""
        import cost_pricing

        monkeypatch.setattr(
            cost_pricing,
            "_load_config_safe",
            lambda: {"llm_pricing_usd_per_million": {"glm-4.6": 4.0}},
        )
        assert cost_pricing.calculate_cost_usd("glm-4.6", 1_000_000, 0) == pytest.approx(4.0)

    def test_hot_claude_path_does_not_load_config(self, monkeypatch):
        """A known Claude id must be priced without ever touching the config
        loader — the override lookup is a miss-only fallback, not a hot path."""
        import cost_pricing

        def _boom():
            raise AssertionError("config loaded on the hot Claude path")

        monkeypatch.setattr(cost_pricing, "_load_config_safe", _boom)
        assert cost_pricing.calculate_cost_usd("opus", 1_000, 1_000) > 0.0

    @pytest.mark.parametrize(
        "cfg",
        [
            pytest.param({"llm_pricing_usd_per_million": {"other": 1.0}}, id="model_absent"),
            pytest.param({"llm_pricing_usd_per_million": "not-a-dict"}, id="table_not_dict"),
            pytest.param({}, id="key_absent"),
            pytest.param(
                {"llm_pricing_usd_per_million": {"glm-4.6": -5.0}}, id="negative_rejected"
            ),
            pytest.param(
                {"llm_pricing_usd_per_million": {"glm-4.6": float("nan")}}, id="nan_rejected"
            ),
        ],
    )
    def test_override_absent_or_invalid_yields_none(self, cfg):
        """NEGATIVE/boundary (a,b): no usable override → None, never a bogus $0/price."""
        assert get_pricing("glm-4.6", config=cfg) is None

    def test_override_covers_a_claude_gap_in_the_guard(self):
        """(A) also closes the Claude-class hole: a rank repointed at an unpriced
        Claude id is NO LONGER flagged once the project prices it via override —
        fail-then-pass against the same defect cost-pricing-missing-opus-48 hit."""
        from cost_pricing import models_missing_pricing

        base = {"model_profiles": {"families": {"claude": {"opus": {"model": "claude-opus-99-0"}}}}}
        assert "claude-opus-99-0" in models_missing_pricing(base)  # unpriced → flagged
        priced = dict(base, llm_pricing_usd_per_million={"claude-opus-99-0": 5.0})
        assert "claude-opus-99-0" not in models_missing_pricing(priced)  # override → covered


class TestUnpricedWarning:
    """cost-pricing-non-claude-families-silent-zero (B): unknown must be audible.

    The DB column is `cost_usd REAL NOT NULL`, so the stored cost stays 0.0; the
    once-per-id stderr warning is what keeps "unknown" from reading as "free".
    """

    def _reset_warned(self):
        import cost_pricing

        cost_pricing._WARNED_UNPRICED.clear()

    def test_unpriced_model_warns_once(self, capsys):
        self._reset_warned()
        assert calculate_cost_usd("glm-4.6", 1000, 500) is None
        first = capsys.readouterr().err
        assert "no price for model 'glm-4.6'" in first
        assert "unknown is not free" in first
        # Second call, same id → no repeat noise.
        assert calculate_cost_usd("glm-4.6", 2000, 100) is None
        assert "glm-4.6" not in capsys.readouterr().err

    def test_zero_tokens_no_warning(self, capsys):
        """Zero tokens on an unpriced model: still no price, so still absent —
        but nothing was spent either, so the warning stays quiet."""
        self._reset_warned()
        assert calculate_cost_usd("glm-4.6", 0, 0) is None
        assert capsys.readouterr().err == ""

    def test_empty_model_no_warning(self, capsys):
        """NEGATIVE: nothing to price → no warning (distinct from an unpriced id)."""
        self._reset_warned()
        assert calculate_cost_usd(None, 1000, 100) is None
        assert capsys.readouterr().err == ""

    def test_priced_override_does_not_warn(self, capsys):
        self._reset_warned()
        cfg = {"llm_pricing_usd_per_million": {"glm-4.6": 2.0}}
        assert calculate_cost_usd("glm-4.6", 1000, 500, config=cfg) > 0.0
        assert capsys.readouterr().err == ""

    def test_explicit_zero_override_is_honoured_not_a_warning(self, capsys):
        """A genuinely free local model priced at 0.0 is distinct from unpriced:
        cost is 0.0 AND no 'unknown ≠ free' warning fires (the doc's claim)."""
        self._reset_warned()
        cfg = {"llm_pricing_usd_per_million": {"ollama/llama3": 0.0}}
        assert get_pricing("ollama/llama3", config=cfg) == {"input": 0.0, "output": 0.0}
        assert calculate_cost_usd("ollama/llama3", 1000, 500, config=cfg) == 0.0
        assert capsys.readouterr().err == ""


class TestNoPhantomLongContextPremium:
    @pytest.mark.parametrize(
        "base",
        [
            "claude-opus-5",
            "claude-opus-4-8",
            "claude-opus-4-7",
            "claude-opus-4-6",
            "claude-sonnet-5",
            "claude-sonnet-4-6",
            "claude-fable-5-1",
            "claude-fable-5",
        ],
    )
    def test_suffix_matches_base(self, base):
        """1M is the standard window on these tiers, not a priced upgrade."""
        assert get_pricing(f"{base}[1m]") == get_pricing(base)


class TestReturnedRowIsACopy:
    def test_mutation_does_not_reprice_the_tier(self):
        """Tiers share one dict across several ids and suffix spellings, so
        handing out the stored row would let one caller's mutation reprice
        every model in that tier."""
        row = get_pricing("claude-opus-4-8")
        row["input"] = 999.0
        assert get_pricing("claude-opus-4-8")["input"] == 5.0
        assert get_pricing("claude-opus-4-7")["input"] == 5.0


class TestTheRunningGenerationIsPriced:
    """Measured in session #225 on the live ledger, with the coverage guard GREEN.

    `claude-opus-5` was the model this project actually ran on, was absent from
    the table, and 1,133,486 tokens — 36.5% of the ledger — recorded
    cost_usd=0.00. `models_missing_pricing` did not see it because it reads the
    models the framework can ROUTE to (`model_profiles` still names Opus 4.8 and
    Sonnet 4.6), while the price is applied to the id the HOST reports.
    """

    @pytest.mark.parametrize(
        "model_id,expected",
        [
            ("claude-opus-5", {"input": 5.0, "output": 25.0}),
            ("claude-fable-5-1", {"input": 10.0, "output": 50.0}),
            ("claude-mythos-5-1", {"input": 10.0, "output": 50.0}),
            # Sonnet is NOT one tier. These two shared $3/$15 until #225 on the
            # reasoning that $2/$10 was an introductory rate "through
            # 2026-08-31"; the date passed and the premise with it.
            ("claude-sonnet-5", {"input": 2.0, "output": 10.0}),
            ("claude-sonnet-4-6", {"input": 3.0, "output": 15.0}),
        ],
    )
    def test_priced_at_its_own_rate(self, model_id, expected):
        assert get_pricing(model_id) == expected

    def test_the_two_sonnets_do_not_share_a_rate(self):
        """The regression this closes is exactly the two collapsing again."""
        assert get_pricing("claude-sonnet-5") != get_pricing("claude-sonnet-4-6")


class TestConfigCarriesARealTariff:
    """A single number cannot express a tariff, and every config price was one.

    `llm_pricing_usd_per_million` accepted `model -> number` and the consumer
    applied that number to BOTH directions, so a project pricing GLM at its
    input rate silently over-charged its output (or the reverse). The object
    form states input and output separately; the bare number is kept because it
    is what existing configs contain, and it now means what it always meant.
    """

    @pytest.mark.parametrize(
        "value,expected",
        [
            ({"input": 0.6, "output": 2.2}, {"input": 0.6, "output": 2.2}),
            (2.0, {"input": 2.0, "output": 2.0}),  # legacy flat form
            ({"input": 0, "output": 0}, {"input": 0.0, "output": 0.0}),  # a real zero
        ],
    )
    def test_accepted_shapes(self, value, expected):
        cfg = {"llm_pricing_usd_per_million": {"glm-4-plus": value}}
        assert get_pricing("glm-4-plus", config=cfg) == expected

    @pytest.mark.parametrize(
        "value",
        [
            {"input": 1.0},  # half a tariff is not a tariff
            {"output": 1.0},
            {"input": -1.0, "output": 1.0},
            {"input": "cheap", "output": 1.0},
            {"input": float("nan"), "output": 1.0},
            "free",
            None,
        ],
    )
    def test_unusable_shapes_yield_absence_not_zero(self, value):
        """NEGATIVE, and the whole point: a price we cannot read is UNKNOWN.

        Returning $0.00 here would make an unreadable config indistinguishable
        from a free model — the defect this module exists to prevent.
        """
        cfg = {"llm_pricing_usd_per_million": {"glm-4-plus": value}}
        assert get_pricing("glm-4-plus", config=cfg) is None

    def test_normalizer_stores_one_shape(self):
        from tausik_constants import normalize_llm_pricing_config

        out = normalize_llm_pricing_config(
            {"llm_pricing_usd_per_million": {"a": 1.5, "b": {"input": 2.0, "output": 8.0}}}
        )
        assert out["llm_pricing_usd_per_million"] == {
            "a": {"input": 1.5, "output": 1.5},
            "b": {"input": 2.0, "output": 8.0},
        }

    def test_output_rate_actually_reaches_the_cost(self):
        """The bug the object form fixes, stated as arithmetic: 1M in + 1M out
        at 0.6/2.2 is $2.80, not $1.20 (flat input) or $4.40 (flat output)."""
        cfg = {"llm_pricing_usd_per_million": {"glm-4-plus": {"input": 0.6, "output": 2.2}}}
        cost = calculate_cost_usd("glm-4-plus", 1_000_000, 1_000_000, config=cfg)
        assert cost == pytest.approx(2.8)


class TestMetricsNamesWhatItCannotPrice:
    """Decision #334 at the REPORTING end, where it does not need a routing decision.

    The stored cost of an unpriced model is 0.0 because the DB column is NOT
    NULL. That zero is indistinguishable from "free" in the database — but not
    here, where the table can still be consulted.
    """

    @pytest.mark.parametrize(
        "model_id,tokens,cost,expect_dollars",
        [
            ("claude-opus-5", 842_558, 12.5, True),  # priced → a figure
            ("some-unpriced-model", 842_558, 0.0, False),  # unpriced → named absence
            ("claude-opus-5", 0, 0.0, True),  # zero TOKENS is a measurement
        ],
    )
    def test_cost_cell(self, model_id, tokens, cost, expect_dollars):
        from model_pinning import format_model_usage_section

        line = format_model_usage_section(
            [{"model_id": model_id, "event_count": 1, "tokens_total": tokens, "cost_usd": cost}]
        )[-1]
        assert ("$" in line.split("|")[-1]) is expect_dollars
        if not expect_dollars:
            assert "not priced" in line and "unmetered" in line


class TestUnmeasuredIsNotZero:
    """The distinction the whole task turns on, asserted in one place."""

    def test_absent_tokens_yield_absent_cost_even_on_a_priced_model(self):
        assert calculate_cost_usd("claude-opus-5", None, None) is None

    def test_one_measured_side_is_still_a_measurement(self):
        """Input measured, output missing. Half a measurement is not none of
        one, and calling the missing half zero is a price nobody derived — but
        the half that WAS measured still has a price."""
        cost = calculate_cost_usd("claude-opus-5", 1_000_000, None)
        assert cost is not None and cost > 0

    def test_a_free_model_and_an_unpriced_model_are_told_apart(self):
        cfg = {"llm_pricing_usd_per_million": {"ollama/llama3": 0.0}}
        assert calculate_cost_usd("ollama/llama3", 1000, 500, config=cfg) == 0.0
        assert calculate_cost_usd("ollama/other", 1000, 500, config=cfg) is None
