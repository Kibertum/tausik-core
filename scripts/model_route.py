"""Provider-neutral route for work delegated to a fresh worker context."""

from __future__ import annotations

from typing import Any

import model_profiles
from agent_model_source import AUTO, resolve
from model_routing_matrix import _load_config_safe, suggest_model

_SPAWN_CAPABLE = frozenset({"claude", "codex"})
_VALID_RISK = frozenset({"normal", "high"})
_VALID_QUALITY_SIGNALS = frozenset({"verify_failed", "review_high", "retry_exhausted"})


def _openai_route(
    complexity: str | None,
    risk: str,
    quality_signal: str | None,
    families: dict[str, dict[str, dict[str, str]]],
) -> tuple[dict[str, str], str, str | None]:
    """Apply the explicit 1.11 policy for a new OpenAI worker.

    The phase matrix remains the provider-neutral default.  Codex workers use a
    narrower policy: bounded simple/medium work starts on Terra; a declared
    complex task or one bounded quality failure moves to Sol; Astra is reserved
    for an independently declared high-risk surface.
    """
    if risk == "high":
        spec = model_profiles.spec_for("openai", "fable", families)
        assert spec is not None
        return spec, "high-risk work requires Astra", "risk=high"
    if complexity == "complex":
        spec = model_profiles.spec_for("openai", "opus", families)
        assert spec is not None
        return spec, "declared complex work requires Sol", "complexity=complex"
    if quality_signal is not None:
        spec = model_profiles.spec_for("openai", "opus", families)
        assert spec is not None
        return (
            spec,
            f"bounded work escalated to Sol after {quality_signal}",
            quality_signal,
        )
    spec = model_profiles.spec_for("openai", "sonnet", families)
    assert spec is not None
    return spec, "bounded simple/medium worker work defaults to Terra", None


def route_work(
    complexity: str | None,
    *,
    phase: str = "implement",
    risk: str = "normal",
    quality_signal: str | None = None,
    host: str | None = None,
    active_model: str | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Select a worker route without claiming to switch the running session."""
    if risk not in _VALID_RISK:
        raise ValueError(f"Unknown risk {risk!r}; expected one of {sorted(_VALID_RISK)}")
    if quality_signal is not None and quality_signal not in _VALID_QUALITY_SIGNALS:
        raise ValueError(
            f"Unknown quality signal {quality_signal!r}; "
            f"expected one of {sorted(_VALID_QUALITY_SIGNALS)}"
        )
    cfg = config if config is not None else _load_config_safe()
    if host == AUTO:
        try:
            from skill_profile_detect import detect_ide

            host = detect_ide()
        except Exception:  # noqa: BLE001 — missing host detection means advisory-only
            host = None
    source = None
    if active_model is None and host is not None:
        resolved = resolve(ide=host)
        active_model = resolved["model_id"]
        source = resolved["source"]
    families = model_profiles.load_families(cfg)
    family = model_profiles.vendor_of(active_model, families)
    if family is None:
        family = model_profiles.default_family(cfg)
    suggestion = suggest_model(complexity, phase, config=cfg, family=family)
    route_reason = suggestion["rationale"]
    escalation_reason = None
    eligible = complexity in {"simple", "medium", "complex"}
    if family == "openai" and eligible:
        suggestion, route_reason, escalation_reason = _openai_route(
            complexity, risk, quality_signal, families
        )
    elif family == "openai":
        route_reason = "complexity is unclassified; no worker route selected"
    elif quality_signal is not None:
        current_rank = model_profiles.rank_of(suggestion["model"], families)
        if current_rank in model_profiles.RANKS:
            next_index = min(
                model_profiles.RANKS.index(current_rank) + 1, len(model_profiles.RANKS) - 1
            )
            stronger = model_profiles.spec_for(family, model_profiles.RANKS[next_index], families)
            if stronger is not None:
                suggestion = {
                    "model": stronger["model"],
                    "display": stronger["display"],
                    "rationale": suggestion["rationale"]
                    + f"; escalated one tier after {quality_signal}",
                }
                escalation_reason = quality_signal
    if family == "openai" and risk == "normal" and quality_signal is None and complexity is None:
        flagship = families.get("openai", {}).get("fable", {}).get("model")
        balanced = families.get("openai", {}).get("opus")
        if flagship and suggestion["model"] == flagship and balanced:
            suggestion = {
                "model": balanced["model"],
                "display": balanced["display"],
                "rationale": suggestion["rationale"]
                + "; capped at the balanced OpenAI tier unless risk=high",
            }
    reasoning = "high" if risk == "high" else "medium"
    return {
        **suggestion,
        "family": family,
        "host": host,
        "active_model": active_model,
        "active_model_source": source,
        "reasoning_effort": reasoning,
        "speed_mode": "standard",
        "risk": risk,
        "quality_signal": quality_signal,
        "route_reason": route_reason,
        "escalation_reason": escalation_reason,
        "capability": "spawn_subagent" if host in _SPAWN_CAPABLE and eligible else "advisory",
        "eligible": eligible,
        "applied": False,
        "max_delegation_depth": 1,
        "root_session_switch": "unsupported",
    }
