"""Pricing status is three-valued: priced, free, unknown — and unknown is never 0.

The negative this exists for: a subscription provider (zai-coding-plan) has no
per-token tariff, so an honest meter prints null and names the model; a printed
$0.00 would read as free work. A declared free local model is the opposite case
and must stay a measured zero, not drift into unknown.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import usage_pricing as up  # noqa: E402

_CROSSCUTTING_SCOPE = ["scripts/usage_pricing.py", "scripts/token_price.py"]

_GLM_KINDS = {"output": 2.0, "input": 0.6, "cache_create": 0.75, "cache_read": 0.06}
_ZERO_KINDS = {kind: 0.0 for kind in ("output", "input", "cache_create", "cache_read")}
_PRICES = {"glm-4.7": _GLM_KINDS, "local-model": _ZERO_KINDS}


def _row(model: str, provider: str | None = None, **counters: int) -> dict:
    identity = {
        "provider": {"value": provider, "basis": "observed"},
        "model": {"value": model, "basis": "observed"},
    }
    return {"identity": identity, "tokens": dict(counters)}


def _full_counters() -> dict:
    return {
        "input": 1_000_000,
        "cached_input": 2_000_000,
        "cache_write": 500_000,
        "output": 100_000,
    }


@pytest.mark.parametrize(
    ("kinds", "status", "usd"),
    [
        pytest.param(_GLM_KINDS, "priced", 2.0 * 0.1 + 0.6 + 0.75 * 0.5 + 0.06 * 2.0, id="priced"),
        pytest.param(_ZERO_KINDS, "free", 0.0, id="free_is_a_measured_zero"),
    ],
)
def test_priced_and_free_statuses(kinds, status, usd):
    prices = {"glm-4.7": kinds, "local-model": kinds}
    result = up.section(
        [_row("glm-4.7", "zai-coding-plan", **_full_counters())], prices, warn=False
    )
    entry = result["models"][0]
    assert entry["status"] == status
    assert entry["usd"] == pytest.approx(usd)
    assert result["applied"] is True and result["unpriced_models"] == []


def test_unknown_is_named_and_never_zero():
    result = up.section(
        [_row("~z-ai/glm-flash-latest", "zai-coding-plan", output=77_000)], _PRICES, warn=False
    )
    entry = result["models"][0]
    assert entry["status"] == "unknown" and entry["usd"] is None
    assert result["unpriced_models"] == ["zai-coding-plan/~z-ai/glm-flash-latest"]
    assert result["applied"] is False


def test_unmeasured_counters_stay_null_even_when_priced():
    """Never print 0 where nothing was measured — the report's own decision #334."""
    result = up.section([_row("glm-4.7", "zai-coding-plan")], _PRICES, warn=False)
    entry = result["models"][0]
    assert entry["measured"] is False and entry["usd"] is None
    assert result["applied"] is True  # nothing was measured, so nothing went unpriced


def test_reasoning_tokens_bill_as_output():
    prices = {"glm-4.7": _GLM_KINDS}
    result = up.section(
        [_row("glm-4.7", "zai-coding-plan", output=500_000, reasoning_output=250_000)],
        prices,
        warn=False,
    )
    assert result["models"][0]["usd"] == pytest.approx(750_000 / 1_000_000 * 2.0)
    assert result["models"][0]["tokens"]["output"] == 750_000


def test_the_unknown_model_warns_once_per_process(capsys):
    model = "warn-once-only-model"
    up.section([_row(model, output=10)], {}, warn=True)
    up.section([_row(model, output=10)], {}, warn=True)
    err = capsys.readouterr().err
    assert err.count("no price for model") == 1
    assert "unknown is not free" in err


def test_an_unmeasured_unknown_is_silent(capsys):
    up.section([_row("silent-unmeasured-model")], {}, warn=True)
    assert "silent-unmeasured-model" not in capsys.readouterr().err


def test_a_zero_token_unknown_neither_warns_nor_blocks_applied(capsys):
    """A model that reported all-zero counters billed nothing — warning about it
    (or calling the window unapplied) would be noise, not honesty."""
    result = up.section([_row("zero-token-model", output=0, input=0)], {}, warn=True)
    assert "zero-token-model" not in capsys.readouterr().err
    assert result["applied"] is True
    assert result["models"][0]["status"] == "unknown" and result["models"][0]["usd"] is None


def test_a_row_without_identity_is_kept_not_dropped():
    result = up.section([{"tokens": {"output": 5}}], {}, warn=False)
    assert result["models"][0]["model"] == "unknown"
    assert result["models"][0]["status"] == "unknown"


class TestThePairKeyPricesTheReportPath:
    """`llm_pricing_usd_per_million` priced usage_events but this report printed
    UNPRICED over the same rows — one declaration must price both paths."""

    def test_a_pair_declaration_prices_the_ladder(self, tmp_path):
        (tmp_path / "config.json").write_text(
            json.dumps({"llm_pricing_usd_per_million": {"glm-4.7": {"input": 0.6, "output": 2.0}}}),
            encoding="utf-8",
        )
        from token_price import load_prices, rates_for

        prices = load_prices(str(tmp_path))
        rates = rates_for("glm-4.7", prices)
        assert rates is not None
        assert rates["input"] == pytest.approx(0.6)
        assert rates["cache_read"] == pytest.approx(0.6 * 0.1)
        assert rates["cache_create"] == pytest.approx(0.6 * 1.25)

    def test_token_price_wins_per_model_over_the_pair(self, tmp_path):
        (tmp_path / "config.json").write_text(
            json.dumps(
                {
                    "token_price": {"glm-4.7": {"output": 9.0, "input": 1.0}},
                    "llm_pricing_usd_per_million": {"glm-4.7": {"input": 0.6, "output": 2.0}},
                }
            ),
            encoding="utf-8",
        )
        from token_price import load_prices

        assert load_prices(str(tmp_path))["glm-4.7"]["output"] == 9.0

    def test_an_invalid_pair_entry_is_absent_not_zero(self, tmp_path):
        (tmp_path / "config.json").write_text(
            json.dumps({"llm_pricing_usd_per_million": {"glm-4.7": {"input": "dear"}}}),
            encoding="utf-8",
        )
        from token_price import load_prices, rates_for

        assert rates_for("glm-4.7", load_prices(str(tmp_path))) is None

    def test_a_negative_price_is_refused_by_the_pair_lookup(self, tmp_path):
        (tmp_path / "config.json").write_text(
            json.dumps({"llm_pricing_usd_per_million": {"glm-4.7": -1}}),
            encoding="utf-8",
        )
        from token_price import load_prices, rates_for

        assert rates_for("glm-4.7", load_prices(str(tmp_path))) is None
