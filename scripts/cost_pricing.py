"""Shared Claude model pricing — single source of truth for cost telemetry.

Used by:
  - scripts/hooks/session_metrics.py (SessionEnd metrics rollup)
  - scripts/hooks/posttool_usage.py (per-tool usage_events writes)
  - scripts/project_service.py (recompute helpers)

Prices are USD per 1M tokens. Source: Anthropic public pricing as of v1.4.0.
1M-context (extended) entries use the documented Sonnet 1M premium (2× base);
Opus 1M-context is priced consistently at 2× the 200k tier in absence of a
separately published rate. If Anthropic publishes a different Opus 1M tier
later, update the explicit rows below — the [Nm] suffix lookup will then
return the canonical figure rather than the strip-suffix fallback.
"""

from __future__ import annotations

import re


_SUFFIX_RE = re.compile(r"\[[^\[\]]+\]\s*$")

_MODEL_PRICING: dict[str, dict[str, float]] = {
    # Canonical IDs (200k context — base tier)
    "claude-opus-4-7": {"input": 15.0, "output": 75.0},
    "claude-opus-4-6": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.0},
    # 1M-context (extended) — Anthropic-documented 2× premium for Sonnet 1M;
    # applied uniformly to other models pending separate published rates.
    "claude-opus-4-7[1m]": {"input": 30.0, "output": 150.0},
    "claude-opus-4-6[1m]": {"input": 30.0, "output": 150.0},
    "claude-sonnet-4-6[1m]": {"input": 6.0, "output": 22.50},
    "claude-haiku-4-5[1m]": {"input": 1.60, "output": 8.0},
    # Short aliases (assume 200k unless caller passes the suffix variant)
    "opus": {"input": 15.0, "output": 75.0},
    "sonnet": {"input": 3.0, "output": 15.0},
    "haiku": {"input": 0.80, "output": 4.0},
}


def get_pricing(model_id: str | None) -> dict[str, float] | None:
    """Return {input, output} per-1M-token prices for the given model.

    Returns None for unknown models so callers can default cost_usd=0.0
    rather than raising. Lookup is case-insensitive. Suffix forms like
    `claude-opus-4-7[1m]` are matched explicitly first; if not present,
    the trailing `[...]` group is stripped and lookup falls back to the
    base canonical ID. A bare `[1m]` (no base) returns None.
    """
    if not model_id:
        return None
    key = str(model_id).strip().lower()
    if not key:
        return None
    direct = _MODEL_PRICING.get(key)
    if direct is not None:
        return direct
    stripped = _SUFFIX_RE.sub("", key).strip()
    if stripped and stripped != key:
        return _MODEL_PRICING.get(stripped)
    return None


def calculate_cost_usd(
    model_id: str | None,
    tokens_input: int,
    tokens_output: int,
) -> float:
    """Compute USD cost for the given token counts. Returns 0.0 for unknown models."""
    pricing = get_pricing(model_id)
    if not pricing:
        return 0.0
    return round(
        tokens_input * pricing["input"] / 1_000_000 + tokens_output * pricing["output"] / 1_000_000,
        4,
    )


def known_models() -> tuple[str, ...]:
    """All recognized model identifiers (canonical + aliases)."""
    return tuple(_MODEL_PRICING.keys())
