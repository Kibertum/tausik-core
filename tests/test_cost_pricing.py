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

    def test_case_insensitive_lookup(self):
        assert get_pricing("OPUS") == get_pricing("opus")
        assert get_pricing("Claude-Opus-4-7") == get_pricing("claude-opus-4-7")

    def test_whitespace_tolerated(self):
        assert get_pricing("  haiku  ") == get_pricing("haiku")

    def test_unknown_model_returns_none(self):
        assert get_pricing("claude-mystery-9-9") is None
        assert get_pricing("gpt-5") is None

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

    def test_unknown_model_returns_zero(self):
        assert calculate_cost_usd("unknown", 1_000_000, 1_000_000) == 0.0

    def test_zero_tokens_returns_zero(self):
        assert calculate_cost_usd("opus", 0, 0) == 0.0

    def test_rounding_to_4_decimals(self):
        # Tiny amount → must not raise / lose precision
        cost = calculate_cost_usd("haiku", 1, 1)
        assert cost == round(cost, 4)


class TestExtendedContextSuffix:
    """v14b-defect-cost-pricing-1m-suffix — `[Nm]` extended-context suffix
    must resolve to a non-None pricing row. Otherwise every 1M-context tool
    call writes cost_usd=0.0, defeating B4 cost telemetry.
    """

    def test_opus_1m_explicit_entry(self):
        p = get_pricing("claude-opus-4-7[1m]")
        assert p is not None
        # 1M-context premium is 2× base for documented Sonnet tier; opus
        # follows the same multiplier in cost_pricing pending separate rates.
        assert p["input"] == 30.0
        assert p["output"] == 150.0

    def test_sonnet_1m_explicit_entry(self):
        p = get_pricing("claude-sonnet-4-6[1m]")
        assert p is not None
        assert p["input"] == 6.0
        assert p["output"] == 22.50

    def test_haiku_1m_explicit_entry(self):
        p = get_pricing("claude-haiku-4-5[1m]")
        assert p is not None
        assert p["input"] == 1.60
        assert p["output"] == 8.0

    def test_unknown_base_with_suffix_falls_back_to_none(self):
        # No canonical entry for this base; strip-suffix fallback also misses.
        assert get_pricing("claude-mystery-9-9[1m]") is None

    def test_unknown_suffix_falls_back_to_canonical_base(self):
        # Suffix the table doesn't list explicitly should fall back to base.
        assert get_pricing("claude-opus-4-7[2m]") == get_pricing("claude-opus-4-7")
        assert get_pricing("claude-sonnet-4-6[batch]") == get_pricing("claude-sonnet-4-6")

    def test_calculate_cost_nonzero_for_1m_opus(self):
        cost = calculate_cost_usd("claude-opus-4-7[1m]", 1_000_000, 100_000)
        assert cost > 0.0
        # 1M @ $30 + 100k @ $150 = $30 + $15 = $45
        assert cost == pytest.approx(45.0)

    def test_bare_suffix_returns_none(self):
        assert get_pricing("[1m]") is None
        assert get_pricing("   [1m]   ") is None

    def test_calculate_cost_unknown_with_none_returns_zero(self):
        # Negative: explicit None model id
        assert calculate_cost_usd(None, 1000, 100) == 0.0

    def test_calculate_cost_unknown_base_with_suffix_returns_zero(self):
        assert calculate_cost_usd("claude-mystery-9-9[1m]", 1000, 100) == 0.0

    def test_case_insensitive_with_suffix(self):
        assert get_pricing("CLAUDE-OPUS-4-7[1m]") == get_pricing("claude-opus-4-7[1m]")
        assert get_pricing("Claude-Opus-4-7[1M]") == get_pricing("claude-opus-4-7[1m]")


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
