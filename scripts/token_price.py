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


def load_prices(project_dir: str | None = None) -> dict[str, dict[str, float]]:
    """`{model prefix: {kind: usd per million}}` from config, or empty.

    Prefix match, not exact: a provider adds a date suffix to a model id
    (`claude-haiku-4-5-20251001`), and a table keyed on the full id would go
    unpriced the day the suffix changes.
    """
    try:
        from project_config import find_tausik_dir

        base = project_dir or find_tausik_dir()
        with open(os.path.join(base, "config.json"), encoding="utf-8") as fh:
            node = json.load(fh).get(_CONFIG_KEY)
    except Exception:  # noqa: BLE001 — no config, bad config: unpriced, never guessed
        return {}
    if not isinstance(node, dict):
        return {}
    out: dict[str, dict[str, float]] = {}
    for model, rates in node.items():
        if not isinstance(model, str) or not isinstance(rates, dict):
            continue
        clean = {k: float(v) for k, v in rates.items() if k in KINDS and _is_number(v)}
        if clean:
            out[model] = clean
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
    return best[1] if best else None


def cost_of_row(row: dict[str, Any], prices: dict[str, dict[str, float]]) -> float | None:
    """Dollars for one recorded call, or ``None`` when its model is unpriced."""
    rates = rates_for(row.get("model"), prices)
    if rates is None:
        return None
    total = 0.0
    for kind, field in _FIELD_OF_KIND.items():
        rate = rates.get(kind)
        if rate is None:
            continue
        total += (int(row.get(field) or 0) / 1_000_000) * rate
    return total


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
    if result["unpriced_calls"]:
        lines.append(
            f"  {result['unpriced_calls']} call(s) left out — unpriced model(s): "
            f"{', '.join(result['unpriced_models'])}"
        )
    return "\n".join(lines)
