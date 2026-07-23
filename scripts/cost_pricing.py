"""Shared Claude model pricing — single source of truth for cost telemetry.

Used by:
  - scripts/hooks/session_metrics.py (SessionEnd metrics rollup)
  - scripts/hooks/posttool_usage.py (per-tool usage_events writes)
  - scripts/project_service.py (recompute helpers)

Prices are USD per 1M tokens. Verified against Anthropic's published pricing on
2026-07-23 (cost-pricing-missing-opus-48).

WHAT THIS TABLE GOT WRONG, and why the shape changed:

* `claude-opus-4-8` was absent entirely while `model_profiles` already routed
  the `opus` rank to it — so every session on this project's own default model
  priced at $0.00. A cost meter that silently reads zero is worse than no cost
  meter: it reports success.
* Opus was carried at $15/$75. The Opus tier is $5/$25; the old figure
  overstated every Opus session threefold.
* Haiku 4.5 was carried at $0.80/$4.00 against a real $1.00/$5.00.
* The `[1m]` rows assumed a 2× long-context premium, extrapolated from Sonnet's
  old pricing. There is no such premium on the current Opus and Sonnet tiers:
  1M IS the standard context window at the standard rate. The suffix rows are
  kept — the lookup is public API — but priced AT PARITY with their base, which
  is the correction, not an omission.

Adding a model here is not optional bookkeeping: `tests/test_cost_pricing.py`
fails if any Claude id reachable from `model_profiles` / `model_routing_matrix`
/ `service_delegate` has no row, so a routing change that outruns this table
breaks the build instead of silently zeroing the meter.

Sonnet 5 carries an introductory rate ($2/$10 through 2026-08-31) that this
table deliberately does NOT encode: a static table cannot express "until a
date", and a stale discount would UNDER-report spend. The standard rate is the
honest default — over-reporting during the intro window is the safe direction.
"""

from __future__ import annotations

import re


_SUFFIX_RE = re.compile(r"\[[^\[\]]+\]\s*$")

_OPUS = {"input": 5.0, "output": 25.0}
_SONNET = {"input": 3.0, "output": 15.0}
_HAIKU = {"input": 1.0, "output": 5.0}
_FABLE = {"input": 10.0, "output": 50.0}

_MODEL_PRICING: dict[str, dict[str, float]] = {
    # Canonical IDs. Opus and Sonnet ship a 1M context window at these rates.
    "claude-fable-5": _FABLE,
    "claude-mythos-5": _FABLE,
    "claude-opus-4-8": _OPUS,
    "claude-opus-4-7": _OPUS,
    "claude-opus-4-6": _OPUS,
    "claude-sonnet-5": _SONNET,
    "claude-sonnet-4-6": _SONNET,
    "claude-haiku-4-5": _HAIKU,  # 200k context; no 1M tier exists
    # Explicit `[1m]` rows, at parity with their base — the suffix names the
    # context window, not a price tier. Without these the strip-suffix fallback
    # would produce the same answer; they are spelled out so a future published
    # long-context premium has an obvious place to land.
    "claude-fable-5[1m]": _FABLE,
    "claude-opus-4-8[1m]": _OPUS,
    "claude-opus-4-7[1m]": _OPUS,
    "claude-opus-4-6[1m]": _OPUS,
    "claude-sonnet-5[1m]": _SONNET,
    "claude-sonnet-4-6[1m]": _SONNET,
    # Short aliases — capability ranks, not ids (see model_profiles.RANKS).
    "fable": _FABLE,
    "opus": _OPUS,
    "sonnet": _SONNET,
    "haiku": _HAIKU,
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
    found = _MODEL_PRICING.get(key)
    if found is None:
        stripped = _SUFFIX_RE.sub("", key).strip()
        if stripped and stripped != key:
            found = _MODEL_PRICING.get(stripped)
    # A copy, not the stored row: tiers share one dict across their id and
    # suffix spellings, so handing out the original would let one caller's
    # mutation reprice every model that shares that tier.
    return dict(found) if found is not None else None


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


def routed_claude_model_ids(config: dict | None = None) -> set[str]:
    """Every Claude model id the framework can actually route work to.

    Read from the tables that decide which model runs — profiles, the routing
    matrix, the delegation default — rather than restated here, so the answer
    cannot drift from the thing it describes.

    Reads the EFFECTIVE config, not just the built-in defaults. A project may
    legitimately repoint a rank at another Claude id via
    `model_profiles.families.claude.<rank>.model`, or set a per-phase override
    in `model_routing.<phase>`; the first cut consulted only
    `DEFAULT_FAMILIES` and `_PROFILE_SLUG_BY_MODEL_ID`, so such an override to
    an unpriced id metered at $0.00 with the coverage guard staying green —
    the very defect this guard exists to prevent, reachable through the
    documented extension point (adversarial review, s130-review-fixes). Pass
    `config` to reflect a real project; the default (None) reads the framework's
    own effective config.

    Claude only: other families (GLM, and whatever a project adds) are not
    billed at Anthropic rates, so inventing prices for them would be worse than
    reporting nothing — pricing non-Claude routed models is
    `cost-pricing-non-claude-families-silent-zero`, not this guard.
    """
    ids: set[str] = set()
    if config is None:
        try:
            from project_config import load_config

            config = load_config()
        except Exception:  # noqa: BLE001 — no config just means "defaults only"
            config = None
    try:
        import model_profiles

        # load_families merges config over the built-in defaults, so a
        # rank the project repointed is seen, and the defaults still are.
        families = model_profiles.load_families(config)
        for spec in families.get("claude", {}).values():
            model = (spec or {}).get("model")
            if model:
                ids.add(str(model).strip().lower())
    except Exception:  # noqa: BLE001 — a missing table means nothing to check, not a failure
        pass
    try:
        import model_routing_matrix

        ids.update(str(m).strip().lower() for m in model_routing_matrix._PROFILE_SLUG_BY_MODEL_ID)
        # Per-phase overrides can name an arbitrary id that suggest_model hands
        # straight to pricing — scan them too.
        routing = (config or {}).get("model_routing")
        if isinstance(routing, dict):
            for val in routing.values():
                if isinstance(val, str) and val.strip():
                    ids.add(val.strip().lower())
    except Exception:  # noqa: BLE001
        pass
    try:
        import service_delegate

        default_id = service_delegate._DEFAULT_MODEL[0]
        if default_id:
            ids.add(str(default_id).strip().lower())
    except Exception:  # noqa: BLE001
        pass
    return {i for i in ids if i.startswith("claude")}


def models_missing_pricing(config: dict | None = None) -> set[str]:
    """Routable Claude ids with no price — the set that must stay empty.

    This is the defect `cost-pricing-missing-opus-48` closed, made mechanical:
    `claude-opus-4-8` was routed as the default `opus` rank for weeks while
    absent from the price table, so every session on it recorded $0.00 and the
    cost meter reported a confident zero. A table that must be updated by
    remembering is a table that drifts.

    `config` reaches the effective per-project routing (overrides included);
    None reads the framework's own.
    """
    return {m for m in routed_claude_model_ids(config) if get_pricing(m) is None}
