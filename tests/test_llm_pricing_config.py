"""v14-pricing-table-config — llm_pricing_usd_per_million validation + lookup."""

from __future__ import annotations

import logging

import pytest

from project_config import lookup_llm_usd_per_million_tokens, normalize_llm_pricing_config


def test_normalize_keeps_valid_prices():
    cfg = {"llm_pricing_usd_per_million": {"m1": 2.5, "m2": 0.0}}
    out = normalize_llm_pricing_config(cfg)
    assert out["llm_pricing_usd_per_million"] == {"m1": 2.5, "m2": 0.0}


def test_normalize_drops_negative_and_bad_types(caplog):
    caplog.set_level(logging.WARNING)
    cfg = {
        "llm_pricing_usd_per_million": {"ok": 1.0, "bad": -0.1, "nan": "x", "": 2.0},
        "gates": {},
    }
    out = normalize_llm_pricing_config(cfg)
    assert out["llm_pricing_usd_per_million"] == {"ok": 1.0}
    assert any("negative" in r.message.lower() for r in caplog.records)


def test_normalize_drops_non_object_block():
    cfg = {"llm_pricing_usd_per_million": [1, 2]}
    out = normalize_llm_pricing_config(cfg)
    assert "llm_pricing_usd_per_million" not in out


def test_lookup_unknown_model_returns_none():
    cfg = normalize_llm_pricing_config(
        {"llm_pricing_usd_per_million": {"a": 9.0}},
    )
    assert lookup_llm_usd_per_million_tokens(cfg, "missing") is None
    assert lookup_llm_usd_per_million_tokens(cfg, None) is None
    assert lookup_llm_usd_per_million_tokens(cfg, "  a  ") == pytest.approx(9.0)


def test_lookup_exact_hit():
    cfg = normalize_llm_pricing_config({"llm_pricing_usd_per_million": {"m": 12.0}})
    assert lookup_llm_usd_per_million_tokens(cfg, "m") == pytest.approx(12.0)
