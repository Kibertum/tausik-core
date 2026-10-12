"""Pricing status for native usage reports — measured, free, unknown: three answers.

`metrics tokens --host kilo` reported tokens per provider/model but carried no
pricing decision at all (`pricing_applied` hard-coded false), while a subscription
provider (zai-coding-plan) bills a flat plan rather than per token — so no honest
per-token tariff exists for it and none may be invented. The ladder for every
observed model mirrors `cost_pricing.calculate_cost_usd`:

  * priced  — rates exist (config keys or the shipped table) -> the number
  * free    — rates exist and are all zero -> 0.0, a measured zero
  * unknown — no rates anywhere -> null, the model named, a warning once

A zero printed for an unknown model would read as free work; that is the one
shape this module must never emit. Models whose counters were never measured
stay `usd: null` too — unmeasured is not zero (the report's own decision #334).
Task attribution stays whatever the source states; money attribution is not
invented here for rows the adapter could not attribute.
"""

from __future__ import annotations

import sys
from typing import Any

_WARNED_UNKNOWN: set[str] = set()

#: Native usage counters -> billing kinds of `token_price`. Reasoning tokens bill
#: as output: they are generated tokens, quoted on the completion side by every
#: provider that reports them separately.
_KIND_OF_SOURCE: dict[str, str] = {
    "input": "input",
    "cached_input": "cache_read",
    "cache_write": "cache_create",
    "output": "output",
    "reasoning_output": "output",
}

_KIND_ORDER = ("output", "input", "cache_create", "cache_read")


def _group(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """`{display key: {provider, model, kinds, measured}}` over usage observations.

    The display key is `provider/model` when both identity fields are present and
    the bare value otherwise — a row without identity is still a row somebody
    measured, so it lands under "unknown" instead of being dropped.
    """
    groups: dict[str, dict[str, Any]] = {}
    for row in rows:
        identity = row.get("identity") or {}
        provider = (identity.get("provider") or {}).get("value")
        model = (identity.get("model") or {}).get("value")
        key = "/".join(part for part in (str(provider) if provider else None, model) if part)
        key = key or "unknown"
        group = groups.setdefault(
            key, {"provider": provider, "model": model, "kinds": {}, "measured": False}
        )
        tokens = row.get("tokens") or {}
        for source, kind in _KIND_OF_SOURCE.items():
            value = tokens.get(source)
            if type(value) is int:
                group["kinds"][kind] = group["kinds"].get(kind, 0) + value
                group["measured"] = True
    return groups


def _status_of(rates: dict[str, float] | None) -> str:
    if rates is None:
        return "unknown"
    return "free" if not any(rates.values()) else "priced"


def _usd_of(kinds: dict[str, int], rates: dict[str, float]) -> float:
    return round(sum(kinds.get(kind, 0) / 1_000_000 * rate for kind, rate in rates.items()), 6)


def _warn_unknown_once(key: str, tokens_total: int) -> None:
    """One stderr line per unknown model with measured tokens — per process.

    ASCII only: this message goes through a stderr whose encoding is not
    guaranteed UTF-8, and a non-ASCII glyph can break a cp1252 pipe reader.
    """
    if key in _WARNED_UNKNOWN:
        return
    _WARNED_UNKNOWN.add(key)
    print(
        f"usage_pricing: no price for model '{key}' -- {tokens_total} tokens stay "
        "unpriced (unknown is not free). Add llm_pricing_usd_per_million['<model>'] "
        "or a token_price entry to .tausik/config.json to price it.",
        file=sys.stderr,
    )


def section(
    rows: list[dict[str, Any]],
    prices: dict[str, dict[str, float]] | None = None,
    *,
    warn: bool = True,
) -> dict[str, Any]:
    """Classify usage observations per model: priced / free / unknown.

    `rows` are observations in the `usage_observation` shape (identity + token
    counters). `prices` defaults to one `token_price.load_prices()` read — pass
    a preloaded table to keep a long report on a single config read.

    Returns:
      {
        "applied": bool,   # every model with BILLABLE tokens got a price decision
        "models": [
          {"model": "provider/model", "provider": ..., "rates_key": ...,
           "status": "priced"|"free"|"unknown", "measured": bool,
           "tokens": {kinds}, "usd": float | None}
        ],
        "unpriced_models": [...],  # the unknown ones that measured tokens
      }

    A model with no measured counters keeps `usd: null` even when rates exist:
    pricing nothing measured would print 0 where nothing was observed.
    """
    if prices is None:
        from token_price import load_prices

        prices = load_prices()
    from token_price import rates_for

    out: list[dict[str, Any]] = []
    unpriced: list[str] = []
    for key, group in sorted(_group(rows).items()):
        rates = rates_for(group["model"], prices)
        status = _status_of(rates)
        usd: float | None = None
        if group["measured"] and rates is not None:
            usd = _usd_of(group["kinds"], rates)
        elif group["measured"] and sum(group["kinds"].values()) > 0:
            # Silent on zero-token events — nothing was going to be billed
            # (the same rule `cost_pricing` applies before warning).
            unpriced.append(key)
            if warn:
                _warn_unknown_once(key, sum(group["kinds"].values()))
        out.append(
            {
                "model": key,
                "provider": group["provider"],
                "rates_key": group["model"],
                "status": status,
                "measured": group["measured"],
                "tokens": {kind: group["kinds"].get(kind, 0) for kind in _KIND_ORDER},
                "usd": usd,
            }
        )
    return {
        "applied": not unpriced,
        "models": out,
        "unpriced_models": sorted(unpriced),
    }


__all__ = ["section"]
