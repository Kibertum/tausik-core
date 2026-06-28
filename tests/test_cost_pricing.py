"""Tests for scripts/cost_pricing.py — shared model pricing module."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from cost_pricing import calculate_cost_usd, get_pricing, known_models


class TestGetPricing:
    def test_known_canonical_id(self):
        p = get_pricing("claude-opus-4-7")
        assert p == {"input": 15.0, "output": 75.0}

    def test_short_alias_matches_canonical(self):
        assert get_pricing("opus") == get_pricing("claude-opus-4-7")
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
        # 1M input @ $15 + 1M output @ $75 = $90
        assert calculate_cost_usd("opus", 1_000_000, 1_000_000) == pytest.approx(90.0)

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
    """

    @pytest.mark.parametrize(
        "model_id,expected_input,expected_output",
        [
            # 1M-context premium is 2× base for documented Sonnet tier; opus
            # follows the same multiplier in cost_pricing pending separate rates.
            pytest.param("claude-opus-4-7[1m]", 30.0, 150.0, id="opus_1m_explicit_entry"),
            pytest.param("claude-sonnet-4-6[1m]", 6.0, 22.50, id="sonnet_1m_explicit_entry"),
            pytest.param("claude-haiku-4-5[1m]", 1.60, 8.0, id="haiku_1m_explicit_entry"),
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
        # 1M @ $30 + 100k @ $150 = $30 + $15 = $45
        assert cost == pytest.approx(45.0)

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
        assert "claude-opus-4-7" in models
        assert "claude-sonnet-4-6" in models
        assert "claude-haiku-4-5" in models
        assert "opus" in models
        assert "sonnet" in models
        assert "haiku" in models

    def test_returns_tuple(self):
        assert isinstance(known_models(), tuple)
