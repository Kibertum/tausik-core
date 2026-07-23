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

    def test_calculate_cost_unknown_with_none_returns_zero(self):
        # Negative: explicit None model id
        assert calculate_cost_usd(None, 1000, 100) == 0.0


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
        pytest.param("unknown", 1_000_000, 1_000_000, id="unknown_model_returns_zero"),
        pytest.param("opus", 0, 0, id="zero_tokens_returns_zero"),
        pytest.param(
            "claude-mystery-9-9[1m]",
            1000,
            100,
            id="calculate_cost_unknown_base_with_suffix_returns_zero",
        ),
    ],
)
def test_calculate_cost_zero(model_id, input_tokens, output_tokens):
    assert calculate_cost_usd(model_id, input_tokens, output_tokens) == 0.0


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


class TestNoPhantomLongContextPremium:
    @pytest.mark.parametrize(
        "base",
        [
            "claude-opus-4-8",
            "claude-opus-4-7",
            "claude-opus-4-6",
            "claude-sonnet-5",
            "claude-sonnet-4-6",
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
