"""Pricing and presentation support for natural cohort comparisons."""

from __future__ import annotations

import json
import math
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_DISTRIBUTIONS = (
    "response_rounds",
    "tool_calls",
    "active_duration_ms",
    "attempts",
    "retries",
    "input",
    "cached_input",
    "uncached_input",
    "output",
    "reasoning_output",
    "total_tokens",
)


def measured_reviewer_invocations(rows: Iterable[Mapping[str, Any]]) -> int | None:
    """Sum only review counts whose modern route metadata proves provenance."""
    total = 0
    seen = False
    for row in rows:
        seen = True
        value = row.get("reviewer_invocations") if row.get("route_json") else None
        if value is None:
            return None
        total += int(value)
    return total if seen else None


def persist_snapshot(report: Mapping[str, Any], path: str | Path) -> Path:
    """Persist the report without task slugs or conversation content."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    clean = json.loads(json.dumps(report))
    for cohort in (clean.get("cohorts") or {}).values():
        cohort.pop("tasks", None)
    with target.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(clean, ensure_ascii=False, indent=2) + "\n")
    return target


def render_comparison(report: Mapping[str, Any]) -> str:
    lines = [
        f"Comparison: {report['status']} ({', '.join(report.get('reasons') or ['eligible'])})",
        str(report["claim_boundary"]),
    ]
    for side in ("left", "right"):
        cohort = report["cohorts"][side]
        identity = cohort.get("identity") or {}
        lines.append(
            f"{side}: n={cohort['sample_size']} "
            f"TAUSIK={identity.get('tausik_version') or 'mixed/unknown'} "
            f"model={identity.get('provider') or 'unknown'}/{identity.get('model') or 'mixed/unknown'} "
            f"API-equivalent USD={_display(cohort['api_equivalent_usd']['total'])}"
        )
        for metric in _DISTRIBUTIONS:
            item = cohort["metrics"][metric]
            lines.append(
                f"  {metric}: median={_display(item['median'])}, p90={_display(item['p90'])}, "
                f"coverage={item['coverage']['known']}/{item['coverage']['total']}"
            )
        quality = cohort["quality"]
        lines.append(
            "  quality: "
            f"verify failure={_display(quality['verification_failure_rate'])}, "
            f"review={quality['review_mix']}, findings={quality['confirmed_findings']}, "
            f"defect escapes={_display(quality['downstream_defect_escapes'])}"
        )
    for warning in report.get("task_mix_warnings") or []:
        lines.append(f"Task-mix warning: {warning}")
    lines.append("Subscription credits/included quota: unknown and reported separately.")
    return "\n".join(lines)


def parse_rate_card(config: Mapping[str, Any], generated_at: str) -> dict[str, Any]:
    raw = config.get("api_equivalent_usd_rate_card")
    public: dict[str, Any] = {
        "status": "rate-card-unconfigured",
        "unit": "usd_per_million_tokens",
    }
    if not isinstance(raw, Mapping):
        return {"status": public["status"], "models": {}, "public": public}
    required = ("source", "as_of", "valid_until", "models")
    if (
        raw.get("unit") != "usd_per_million_tokens"
        or any(not raw.get(key) for key in required)
        or not isinstance(raw.get("models"), Mapping)
    ):
        return _invalid(public)
    try:
        as_of = _date(str(raw["as_of"]))
        valid_until = _date(str(raw["valid_until"]))
        generated = _date(generated_at)
        if as_of > valid_until or as_of > generated:
            raise ValueError("invalid rate-card date order")
        stale = generated > valid_until
    except ValueError:
        return _invalid(public)
    models: dict[str, dict[str, float]] = {}
    for key, rates in raw["models"].items():
        if not isinstance(key, str) or not isinstance(rates, Mapping):
            return _invalid(public)
        clean = {}
        for kind in ("uncached_input", "cached_input", "output"):
            value = rates.get(kind)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value < 0
            ):
                return _invalid(public)
            clean[kind] = float(value)
        models[key] = clean
    status = "rate-card-stale" if stale else "configured"
    public = {
        "status": status,
        "source": str(raw["source"]),
        "as_of": str(raw["as_of"]),
        "valid_until": str(raw["valid_until"]),
        "unit": str(raw["unit"]),
        "models": sorted(models),
    }
    return {"status": status, "models": models if not stale else {}, "public": public}


def task_cost(task: Mapping[str, Any], card: Mapping[str, Any]) -> dict[str, Any]:
    identity = task.get("identity") or {}
    rates = card["models"].get(f"{identity.get('provider')}/{identity.get('model')}")
    if card["status"] != "configured":
        return {"total": None, "reason": card["status"]}
    if rates is None:
        return {"total": None, "reason": "unknown-model-rate"}
    counts = {
        "uncached_input": task.get("uncached_input"),
        "cached_input": task.get("cached_input"),
        "output": task.get("output"),
    }
    if any(value is None for value in counts.values()):
        return {"total": None, "reason": "incomplete-token-counters"}
    parts = {kind: counts[kind] * rates[kind] / 1_000_000 for kind in counts}
    return {"total": sum(parts.values()), "parts": parts, "reason": "measured"}


def cost_breakdown(costs: list[dict[str, Any]], total: int) -> dict[str, Any] | None:
    if not costs or any(cost.get("parts") is None for cost in costs):
        return None
    return {
        kind: round(sum(cost["parts"][kind] for cost in costs), 6)
        for kind in ("uncached_input", "cached_input", "output")
    } | {"coverage": {"known": len(costs), "total": total}}


def cost_reason(costs: list[dict[str, Any]], card: Mapping[str, Any]) -> str:
    reasons = {
        str(cost["reason"])
        for cost in costs
        if cost.get("total") is None and cost.get("reason") is not None
    }
    if len(reasons) == 1:
        return next(iter(reasons))
    return card["status"] if not costs else "mixed-unknown-cost"


def _invalid(public: dict[str, Any]) -> dict[str, Any]:
    public["status"] = "rate-card-invalid"
    return {"status": public["status"], "models": {}, "public": public}


def _date(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _display(value: Any) -> str:
    return "unknown" if value is None else str(value)
