"""Optional subscription-credit weighting for exact Codex task observations.

Credits are neither API dollars nor remaining included allowance. Rates are
external and mutable, so TAUSIK ships no table: a project supplies a dated,
sourced card or the report stays explicitly unpriced.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from typing import Any

_KEY = "codex_subscription_credit_rates"
_KINDS = ("input", "cached_input", "output")
_UNIT = "credits_per_million_tokens"


def parse_rate_card(config: Mapping[str, Any]) -> tuple[dict[str, Any] | None, str]:
    """Return a validated card and status without turning bad config into zero."""
    raw = config.get(_KEY)
    if raw is None:
        return None, "rate-card-unconfigured"
    if not isinstance(raw, Mapping):
        return None, "rate-card-invalid"
    if raw.get("unit") != _UNIT:
        return None, "rate-card-invalid"
    if not _text(raw.get("source")) or not _text(raw.get("as_of")):
        return None, "rate-card-invalid"
    models = raw.get("models")
    if not isinstance(models, Mapping) or not models:
        return None, "rate-card-invalid"
    clean: dict[str, dict[str, float]] = {}
    for prefix, rates in models.items():
        if not _text(prefix) or not isinstance(rates, Mapping):
            return None, "rate-card-invalid"
        values: dict[str, float] = {}
        for kind in _KINDS:
            value = rates.get(kind)
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(value)
                or value < 0
            ):
                return None, "rate-card-invalid"
            values[kind] = float(value)
        clean[str(prefix)] = values
    return {
        "source": str(raw["source"]),
        "as_of": str(raw["as_of"]),
        "unit": _UNIT,
        "models": clean,
    }, "configured"


def attach_task_credits(
    report: dict[str, Any],
    observations: Iterable[dict[str, Any]],
    accepted_tasks: Iterable[str],
    config: Mapping[str, Any],
) -> None:
    """Attach exact per-task credit equivalents while preserving raw counters."""
    card, status = parse_rate_card(config)
    report["subscription_credit_rate_card"] = _public_card(card, status)
    tasks = {row["task"]: row for row in report.get("accepted_task_cost", {}).get("tasks", [])}
    accepted = {str(slug) for slug in accepted_tasks}
    grouped: dict[str, list[dict[str, Any]]] = {slug: [] for slug in accepted}
    seen: dict[tuple[Any, ...], dict[str, Any]] = {}
    conflict = False
    for row in observations:
        source = row.get("source", {})
        slug = source.get("task")
        if row.get("attribution") != "exact" or slug not in grouped:
            continue
        key = (
            row.get("identity", {}).get("host", {}).get("value"),
            source.get("project"),
            source.get("thread"),
            source.get("response"),
        )
        if all(key) and key in seen:
            if seen[key] != row:
                conflict = True
            continue
        if all(key):
            seen[key] = row
        grouped[str(slug)].append(row)
    for slug, task in tasks.items():
        credit = _task_credit(grouped.get(slug, []), card, status, conflict)
        task.update(credit)


def _task_credit(
    rows: list[dict[str, Any]],
    card: dict[str, Any] | None,
    card_status: str,
    conflict: bool,
) -> dict[str, Any]:
    if card is None:
        return _unknown(card_status)
    if conflict:
        return _unknown("conflicting-response-usage")
    if not rows:
        return _unknown("no-exact-task-responses")
    token_totals = dict.fromkeys(_KINDS, 0)
    credit_totals = dict.fromkeys(_KINDS, 0.0)
    used_models: set[str] = set()
    for row in rows:
        tokens = row.get("tokens", {})
        total_input = tokens.get("input")
        cached = tokens.get("cached_input")
        output = tokens.get("output")
        model = row.get("identity", {}).get("model", {}).get("value")
        if not all(type(value) is int for value in (total_input, cached, output)):
            return _unknown("incomplete-token-counters")
        rates = _rates_for(model, card["models"])
        if rates is None:
            return _unknown("unknown-model-rate")
        uncached = total_input - cached
        if uncached < 0:
            return _unknown("invalid-token-subset")
        used_models.add(str(model))
        counts = {"input": uncached, "cached_input": cached, "output": output}
        for kind, count in counts.items():
            token_totals[kind] += count
            credit_totals[kind] += count * rates[kind] / 1_000_000
    rounded = {kind: round(value, 6) for kind, value in credit_totals.items()}
    return {
        "subscription_credits": round(sum(credit_totals.values()), 6),
        "subscription_credit_status": "measured",
        "subscription_credit_breakdown": {
            "tokens": token_totals,
            "credits": rounded,
            "models": sorted(used_models),
            "as_of": card["as_of"],
            "source": card["source"],
            "unit": card["unit"],
            "reasoning_output_is_subset": True,
        },
    }


def _rates_for(model: Any, models: Mapping[str, dict[str, float]]) -> dict[str, float] | None:
    if not _text(model):
        return None
    matches = [
        (len(prefix), rates) for prefix, rates in models.items() if str(model).startswith(prefix)
    ]
    return max(matches, default=(0, None), key=lambda item: item[0])[1]


def _public_card(card: dict[str, Any] | None, status: str) -> dict[str, Any]:
    if card is None:
        return {"status": status, "credits_are_not_api_usd_or_remaining_quota": True}
    return {
        "status": status,
        "source": card["source"],
        "as_of": card["as_of"],
        "unit": card["unit"],
        "model_prefixes": sorted(card["models"]),
        "credits_are_not_api_usd_or_remaining_quota": True,
    }


def _unknown(reason: str) -> dict[str, Any]:
    return {
        "subscription_credits": None,
        "subscription_credit_status": reason,
        "subscription_credit_breakdown": None,
    }


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())
