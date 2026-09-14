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

Sonnet 5's $2/$10 was once read here as an introductory rate "through
2026-08-31" that a static table could not express, so Sonnet 5 and Sonnet 4.6
shared $3/$15 and over-reporting was called the safe direction. That premise
expired with the date: $2/$10 is Sonnet 5's rate, and Sonnet 4.6's $3/$15 is a
different model's. They are now carried separately. Measured on this project's
own ledger in session #225: 3064 of 4777 rows (1,969,220 tokens) are Sonnet 5
and had been priced 50% high. A comment that justifies a number by a deadline
becomes wrong on its own schedule, with nothing to notice.

WHAT THIS TABLE STILL CANNOT SEE, stated so it is not mistaken for coverage.
`models_missing_pricing` reads the models the framework can ROUTE to; the model
that actually runs arrives in the host's telemetry payload and need not appear
in any routing table. In session #225 `claude-opus-5` was the running model,
was absent here, and 36.5% of the live ledger (1,133,486 tokens) recorded
cost_usd=0.00 while the coverage guard stayed green. The id is priced now, but
the blind spot is structural: closing it means deciding which generation
`model_profiles` routes to, which is an owner's call. The counter-measure that
does not depend on that decision is at the REPORTING end — `metrics` names a
model it cannot price instead of printing $0.00 for it.
"""

from __future__ import annotations

import re
import sys


_SUFFIX_RE = re.compile(r"\[[^\[\]]+\]\s*$")

# Models whose cost we have already reported as unpriced this process. The
# warning below fires ONCE per model id: a per-tool telemetry writer would
# otherwise repeat it on every event, and the point is to make "unknown ≠ free"
# audible, not to flood stderr. Process-scoped by design — a fresh hook run
# re-warns, which is correct: the operator should see it each session.
_WARNED_UNPRICED: set[str] = set()

_OPUS = {"input": 5.0, "output": 25.0}
# Sonnet is NOT one tier. Sonnet 5 is $2/$10; Sonnet 4.6 is $3/$15. The two
# shared `_SONNET` = $3/$15 until session #225, on the reasoning quoted below
# in the module docstring: that $2/$10 was an introductory rate "through
# 2026-08-31" which a static table cannot express, and over-reporting was the
# safe direction. The date has passed and $2/$10 is simply Sonnet 5's rate, so
# the premise is gone and the rate is now carried per model. Measured cost of
# the old assumption on this project's own ledger: 3064 of 4777 rows
# (1,969,220 tokens) are Sonnet 5 and were priced 50% high.
_SONNET_5 = {"input": 2.0, "output": 10.0}
_SONNET_46 = {"input": 3.0, "output": 15.0}
_HAIKU = {"input": 1.0, "output": 5.0}
_FABLE = {"input": 10.0, "output": 50.0}

_MODEL_PRICING: dict[str, dict[str, float]] = {
    # Canonical IDs. Opus and Sonnet ship a 1M context window at these rates.
    "claude-fable-5-1": _FABLE,
    "claude-mythos-5-1": _FABLE,
    "claude-fable-5": _FABLE,
    "claude-mythos-5": _FABLE,
    "claude-opus-5": _OPUS,
    "claude-opus-4-8": _OPUS,
    "claude-opus-4-7": _OPUS,
    "claude-opus-4-6": _OPUS,
    "claude-sonnet-5": _SONNET_5,
    "claude-sonnet-4-6": _SONNET_46,
    "claude-haiku-4-5": _HAIKU,  # 200k context; no 1M tier exists
    # Explicit `[1m]` rows, at parity with their base — the suffix names the
    # context window, not a price tier. Without these the strip-suffix fallback
    # would produce the same answer; they are spelled out so a future published
    # long-context premium has an obvious place to land.
    "claude-fable-5-1[1m]": _FABLE,
    "claude-mythos-5-1[1m]": _FABLE,
    "claude-fable-5[1m]": _FABLE,
    "claude-opus-5[1m]": _OPUS,
    "claude-opus-4-8[1m]": _OPUS,
    "claude-opus-4-7[1m]": _OPUS,
    "claude-opus-4-6[1m]": _OPUS,
    "claude-sonnet-5[1m]": _SONNET_5,
    "claude-sonnet-4-6[1m]": _SONNET_46,
    # Short aliases — capability ranks, not ids (see model_profiles.RANKS). A
    # rank prices as the id it ROUTES to, not as the newest model of that name:
    # `model_profiles.DEFAULT_FAMILIES` still maps `sonnet` to Sonnet 4.6, so
    # pricing the alias at Sonnet 5's rate would make the meter disagree with
    # the router. When the routing table moves to the current generation, this
    # row moves with it — one change, not two independent ones.
    "fable": _FABLE,
    "opus": _OPUS,
    "sonnet": _SONNET_46,
    "haiku": _HAIKU,
}


def get_pricing(model_id: str | None, config: dict | None = None) -> dict[str, float] | None:
    """Return {input, output} per-1M-token prices for the given model.

    Returns None for unknown models so callers can default cost_usd=0.0
    rather than raising. Lookup is case-insensitive. Suffix forms like
    `claude-opus-4-7[1m]` are matched explicitly first; if not present,
    the trailing `[...]` group is stripped and lookup falls back to the
    base canonical ID. A bare `[1m]` (no base) returns None.

    `config` opens the project override: when the built-in Claude table has no
    row, a flat `llm_pricing_usd_per_million[<model_id>]` rate from the effective
    config is applied to BOTH input and output. That key was normalized on every
    config load and never read — this is the consumer it was missing, and it is
    what lets a project on GLM / a custom model price its own telemetry instead
    of recording $0.00. It would also have priced `claude-opus-4-8` before the
    table caught up (cost-pricing-missing-opus-48), so it doubles as a guard.
    Anthropic rates are never invented for a non-Claude family — the project
    states its own tariff or the meter stays honestly unknown.
    """
    if not model_id:
        return None
    key = str(model_id).strip().lower()
    if not key:
        return None
    # CONFIG FIRST. The built-in table below is a shipped SEED, not the
    # authority: a project states its own tariffs in `.tausik/config.json`, and
    # what it states wins. The old order asked the hardcoded table first and
    # consulted the project only when the table missed, which meant a table
    # entry that had gone stale (Sonnet 5 at $3/$15 for months) could not be
    # corrected without editing Python.
    if config is not None:
        override = _config_override_pricing(config, model_id)
        if override is not None:
            return override
    found = _MODEL_PRICING.get(key)
    if found is None:
        stripped = _SUFFIX_RE.sub("", key).strip()
        if stripped and stripped != key:
            found = _MODEL_PRICING.get(stripped)
    # A copy, not the stored row: tiers share one dict across their id and
    # suffix spellings, so handing out the original would let one caller's
    # mutation reprice every model that shares that tier.
    return dict(found) if found is not None else None


def _config_override_pricing(config: dict | None, model_id: str | None) -> dict[str, float] | None:
    """`{input, output}` from the project config for `model_id`, or None.

    `load_config` already runs `normalize_llm_pricing_config`, but a
    caller-supplied dict might not have, so the lookup revalidates rather than
    trusting the shape. A price that is not a finite, non-negative number is
    treated as absent, never as $0.00.

    Exact ids only — a config entry is not tier-expanded and a `[1m]` suffix is
    not stripped here, because a project naming a spelling means that spelling.
    """
    try:
        from project_config import lookup_llm_pricing_pair

        pair = lookup_llm_pricing_pair(config, model_id)
    except Exception:  # noqa: BLE001 — a missing/broken config just means "no override"
        return None
    return dict(pair) if pair else None


def _load_config_safe() -> dict | None:
    """Effective project config, or None. Best-effort — never raises."""
    try:
        from project_config import load_config

        return load_config()
    except Exception:  # noqa: BLE001 — no config means "no override", not a failure
        return None


def _warn_unpriced_once(model_id: str | None, tokens_total: int) -> None:
    """Emit a single stderr warning that `model_id` has no price — once per id.

    The DB column is `cost_usd REAL NOT NULL` (schema forbids NULL), so the
    stored cost stays 0.0; the warning is what keeps "unknown" from reading as
    "free". Silent on zero-token events — nothing was going to be billed.
    """
    key = str(model_id or "").strip().lower()
    if not key or tokens_total <= 0 or key in _WARNED_UNPRICED:
        return
    _WARNED_UNPRICED.add(key)
    # ASCII only: this is a library-level message that hooks emit through a
    # stderr whose encoding is not guaranteed UTF-8 (hook-stderr-encoding-
    # locale-dependent). A non-ASCII glyph here mojibakes on a cp1252 pipe and
    # can even break a reader decoding as UTF-8 — the existing session_metrics
    # warning stays ASCII for the same reason.
    print(
        f"cost_pricing: no price for model '{model_id}' and no "
        f"llm_pricing_usd_per_million override -- recording cost_usd=0.00 for "
        f"{tokens_total} tokens (unknown is not free). Add "
        f"llm_pricing_usd_per_million['{model_id}'] to .tausik/config.json to price it.",
        file=sys.stderr,
    )


def calculate_cost_usd(
    model_id: str | None,
    tokens_input: int | None,
    tokens_output: int | None,
    config: dict | None = None,
) -> float | None:
    """USD cost for the given token counts, or None when it cannot be computed.

    THREE ANSWERS, NOT TWO, and the third is why this changed. Previously an
    unpriced model and a genuinely free one both returned 0.0, so "we do not
    know what this cost" was stored as "this cost nothing" and nothing anywhere
    could tell them apart. Measured before the change: 55,471 of 55,584 rows
    carried a cost of exactly 0 and not one carried NULL.

      * a priced model with measured tokens -> the number
      * a priced model whose price really is 0 (`free`) -> 0.0, a measurement
      * unmeasured tokens, or a model with no price -> None, an absence

    For an unknown Claude id the built-in table answers directly; only when it
    misses do we consult the project's `llm_pricing_usd_per_million` override
    (loading the effective config lazily if the caller didn't pass one), so the
    hot Claude path never touches disk.
    """
    if tokens_input is None and tokens_output is None:
        return None  # nothing was measured; there is no cost to compute
    ti = tokens_input or 0
    to = tokens_output or 0
    pricing = get_pricing(model_id, config=config)
    if pricing is None and config is None and model_id:
        # Table missed and the caller had no config in hand — give the project's
        # own pricing table a chance before declaring the model unpriced.
        pricing = get_pricing(model_id, config=_load_config_safe())
    if not pricing:
        _warn_unpriced_once(model_id, ti + to)
        return None
    return round(ti * pricing["input"] / 1_000_000 + to * pricing["output"] / 1_000_000, 4)


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
    None reads the framework's own. The same config also feeds `get_pricing`,
    so a Claude id the project priced through its `llm_pricing_usd_per_million`
    override counts as covered — the guard judges the effective price, not just
    the built-in table.
    """
    if config is None:
        config = _load_config_safe()
    return {m for m in routed_claude_model_ids(config) if get_pricing(m, config=config) is None}
