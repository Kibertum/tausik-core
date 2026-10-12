"""Price-weighted token cost. Prices come from config; an unpriced model is ABSENT.

Output, uncached input and cached input are billed at different rates, so a change
that shrinks a request while adding a turn can cost more. Counting tokens cannot
show that; counting money can.

WHY NO DEFAULT PRICE TABLE SHIPS HERE. A rate is an external fact with a date and
a contract behind it: list prices move, enterprise agreements differ, and the same
model costs differently through different providers. A number baked in would be
right for nobody in particular and would rot without a sound. So prices live in
`.tausik/config.json` under `token_price`, and a model with no entry is reported
as UNPRICED rather than as zero -- a zero would understate the bill and read as
free work.

WHAT A "KIND" IS. The four counters the session hook already records:
`output`, `input` (uncached), `cache_read`, `cache_create`. Rates are per million
tokens, which is how every provider quotes them.
"""

from __future__ import annotations

import json
import os
from typing import Any

#: Billing kinds, in the order a report lists them. Output first: it is the most
#: expensive per token and the one a harness change is least able to shrink.
KINDS: tuple[str, ...] = ("output", "input", "cache_create", "cache_read")

#: Row field -> billing kind. The hook writes `input_tokens`/`output_tokens`;
#: the cache counters keep their own names.
_FIELD_OF_KIND: dict[str, str] = {
    "output": "output_tokens",
    "input": "input_tokens",
    "cache_create": "cache_create",
    "cache_read": "cache_read",
}

_CONFIG_KEY = "token_price"

#: Cache rates are not a second price list — they are published MULTIPLIERS of the input
#: rate: a cache read bills at a tenth of input, and writing a cache entry at one and a
#: quarter. Deriving them keeps one number per model; a second table would drift, and the
#: two would then disagree about the stream that dominates the bill.
CACHE_READ_MULTIPLIER: float = 0.1
CACHE_CREATE_MULTIPLIER: float = 1.25


def builtin_rates(model: str | None) -> dict[str, float] | None:
    """The shipped rate for `model`, with the cache kinds derived, or None if unpriced.

    WHY THIS FALLBACK EXISTS. Rates lived in two places that could not answer together:
    `cost_pricing` ships a table of input and output and prices no cache at all, while
    this module understands cache and read rates ONLY from a config nobody filled. So the
    cache-aware report printed UNPRICED over 5953 calls while the priced path quietly
    omitted 3.04 BILLION cache-read tokens — 776 times the output it did count. Note that
    `usage_events.cost_usd` still comes from `cost_pricing` and so stays input plus output:
    the hook that writes it sees no cache counters, because they arrive with the message
    in the transcript and not with a tool result. The two numbers mean different things
    and are not to be read as one.

    A DATE SUFFIX DOES NOT UNPRICE A MODEL. `claude-haiku-4-5-20251001` is the id this
    host actually reports, and the shipped table is keyed without the date — so the exact
    lookup misses and the canonical Haiku went unpriced. Trailing numeric segments are
    dropped one at a time until something matches.
    """
    try:
        from cost_pricing import get_pricing

        shipped = get_pricing(model)
        candidate = model or ""
        while not shipped and "-" in candidate:
            head, _, tail = candidate.rpartition("-")
            if not tail.isdigit():
                break
            candidate = head
            shipped = get_pricing(candidate)
    except Exception:  # noqa: BLE001 — an absent table is unpriced, never guessed at
        return None
    if not shipped:
        return None
    inp = shipped.get("input")
    out = shipped.get("output")
    if inp is None or out is None:
        return None
    return {
        "input": float(inp),
        "output": float(out),
        "cache_read": float(inp) * CACHE_READ_MULTIPLIER,
        "cache_create": float(inp) * CACHE_CREATE_MULTIPLIER,
    }


def load_prices(project_dir: str | None = None) -> dict[str, dict[str, float]]:
    """`{model prefix: {kind: usd per million}}` from config, or empty.

    Prefix match, not exact: a provider adds a date suffix to a model id
    (`claude-haiku-4-5-20251001`), and a table keyed on the full id would go
    unpriced the day the suffix changes.

    TWO CONFIG KEYS, ONE LADDER. `token_price` carries the four billing kinds
    directly; `llm_pricing_usd_per_million` carries the input/output pair the
    DB-write path (`cost_pricing`) prices with. This report used to see only
    the first, so a project that declared the documented pair priced its
    usage_events rows and still watched this report print UNPRICED — the
    split this closes. A `token_price` entry wins per model; pair entries are
    folded in with cache kinds derived from the input rate by the same
    multipliers `builtin_rates` applies to the shipped table. Pair entries
    keep this module's prefix matching here; the DB ladder stays exact-id,
    which is cost_pricing's own documented contract.
    """
    try:
        from project_config import find_tausik_dir

        base = project_dir or find_tausik_dir()
        with open(os.path.join(base, "config.json"), encoding="utf-8") as fh:
            raw = json.load(fh)
    except Exception:  # noqa: BLE001 — no config, bad config: unpriced, never guessed
        return {}
    out: dict[str, dict[str, float]] = {}
    node = raw.get(_CONFIG_KEY) if isinstance(raw, dict) else None
    if isinstance(node, dict):
        for model, rates in node.items():
            if not isinstance(model, str) or not isinstance(rates, dict):
                continue
            clean = {k: float(v) for k, v in rates.items() if k in KINDS and _is_number(v)}
            if clean:
                out[model] = clean
    for model, pair in _pair_rates(raw).items():
        out.setdefault(model, pair)
    return out


def _pair_rates(raw: dict) -> dict[str, dict[str, float]]:
    """`token_price`-shaped rates folded from `llm_pricing_usd_per_million` entries.

    Reads the RAW config (not the normalized one) the same way the `token_price`
    node above does, and revalidates every entry through the public pair lookup
    rather than trusting the shape. An entry that fails validation is absent —
    never coerced to $0.00.
    """
    if not isinstance(raw, dict):
        return {}
    try:
        from project_config import lookup_llm_pricing_pair

        table = raw.get("llm_pricing_usd_per_million")
    except Exception:  # noqa: BLE001 — a missing lookup module is unpriced, never guessed
        return {}
    if not isinstance(table, dict):
        return {}
    out: dict[str, dict[str, float]] = {}
    for model in table:
        if not isinstance(model, str) or not model.strip():
            continue
        pair = lookup_llm_pricing_pair(raw, model)
        if pair is None:
            continue
        out[model] = {
            "input": float(pair["input"]),
            "output": float(pair["output"]),
            "cache_read": float(pair["input"]) * CACHE_READ_MULTIPLIER,
            "cache_create": float(pair["input"]) * CACHE_CREATE_MULTIPLIER,
        }
    return out


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def rates_for(model: str | None, prices: dict[str, dict[str, float]]) -> dict[str, float] | None:
    """Rates for `model`, or ``None`` when nothing in the table matches.

    The longest matching prefix wins, so a rate set for one snapshot of a model
    is not shadowed by a looser entry for its family.
    """
    if not model:
        return None
    best: tuple[int, dict[str, float]] | None = None
    for prefix, rates in prices.items():
        if model.startswith(prefix) and (best is None or len(prefix) > best[0]):
            best = (len(prefix), rates)
    if best is not None:
        # A project that declared its own price gets its own: the config OVERRIDES the
        # shipped table rather than merging with it, so a reader of the config can predict
        # the bill from what they wrote.
        return best[1]
    return builtin_rates(model)


def breakdown(rows: list[dict[str, Any]], prices: dict[str, dict[str, float]]) -> dict[str, Any]:
    """Cost by billing kind, plus what could not be priced.

    `unpriced_models` and `unpriced_calls` are part of the answer, not a footnote:
    a total computed over half the rows looks like a small bill.
    """
    by_kind: dict[str, float] = dict.fromkeys(KINDS, 0.0)
    tokens: dict[str, int] = dict.fromkeys(KINDS, 0)
    priced = 0
    unpriced: dict[str, int] = {}
    for row in rows:
        for kind, field in _FIELD_OF_KIND.items():
            tokens[kind] += int(row.get(field) or 0)
        rates = rates_for(row.get("model"), prices)
        if rates is None:
            model = str(row.get("model") or "unknown")
            unpriced[model] = unpriced.get(model, 0) + 1
            continue
        priced += 1
        for kind, field in _FIELD_OF_KIND.items():
            rate = rates.get(kind)
            if rate is not None:
                by_kind[kind] += (int(row.get(field) or 0) / 1_000_000) * rate
    return {
        "tokens": tokens,
        "usd": by_kind if priced else None,
        "usd_total": round(sum(by_kind.values()), 6) if priced else None,
        "priced_calls": priced,
        "unpriced_calls": sum(unpriced.values()),
        "unpriced_models": sorted(unpriced),
    }


def format_breakdown(result: dict[str, Any]) -> str:
    """Human lines. When nothing is priced the reason and the fix are named."""
    lines = ["Tokens by billing kind:"]
    for kind in KINDS:
        lines.append(f"  {kind:13s} {result['tokens'][kind]:>12,}")
    if result["usd"] is None:
        lines.append(
            "Cost: UNPRICED — no rates in .tausik/config.json under `token_price`. "
            "A zero here would read as free work, so none is printed."
        )
    else:
        lines.append("Cost by billing kind (USD):")
        for kind in KINDS:
            lines.append(f"  {kind:13s} {result['usd'][kind]:>12.4f}")
        lines.append(f"  {'total':13s} {result['usd_total']:>12.4f}")
        # THE SHARE, NOT JUST THE ROWS. Reading the rows alone, this project's own author
        # concluded that output was the bill and said so — because the priced path he
        # looked at omitted the cache entirely. The share is one line and it is the whole
        # conclusion: what costs money here is the number of CALLS, each re-sending the
        # prefix, not the length of what is written.
        total = result["usd_total"]
        if total:
            cache = result["usd"]["cache_read"] + result["usd"]["cache_create"]
            lines.append(
                f"  cache is {100 * cache / total:.1f}% of this bill and output is "
                f"{100 * result['usd']['output'] / total:.1f}%. Cache is re-sent context, "
                "so the lever is FEWER CALLS; shortening what is written moves the smaller "
                "share."
            )
    if result["unpriced_calls"]:
        lines.append(
            f"  {result['unpriced_calls']} call(s) left out — unpriced model(s): "
            f"{', '.join(result['unpriced_models'])}"
        )
    return "\n".join(lines)
