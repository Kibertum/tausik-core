"""Technology-neutral residual-assurance policy.

Stack and task declarations describe what must be proved.  Passed gates
contribute only the evidence capabilities declared by those gates.  The
policy never infers a capability from a gate name, stack name, or file type.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

EVIDENCE_CAPABILITIES = frozenset(
    {
        "syntax",
        "schema",
        "policy",
        "behavior",
        "idempotence",
        "rollback",
        "postconditions",
        "reproducibility",
        "provenance",
    }
)

PROFILE_REQUIREMENTS: dict[str, frozenset[str]] = {
    "declarative": frozenset({"behavior", "idempotence", "rollback", "postconditions"}),
    "executable": frozenset({"behavior", "rollback", "postconditions"}),
    "migration": frozenset({"behavior", "rollback", "postconditions"}),
    "research": frozenset({"reproducibility", "provenance"}),
}

_IMPACT_DEFAULTS: dict[str, Any] = {
    "level": "unknown",
    "blast_radius": "unknown",
    "reversibility": "unknown",
    "security_boundary": False,
    "governance_boundary": False,
    "privileged": False,
    "data_change": "none",
    "owner_escalation": False,
}

_IMPACT_ENUMS = {
    "level": frozenset({"low", "medium", "high", "unknown"}),
    "blast_radius": frozenset({"local", "bounded", "broad", "unknown"}),
    "reversibility": frozenset({"reversible", "conditional", "irreversible", "unknown"}),
    "data_change": frozenset({"none", "non_destructive", "destructive"}),
}
_IMPACT_BOOLS = frozenset(
    {
        "security_boundary",
        "governance_boundary",
        "privileged",
        "owner_escalation",
    }
)


def validate_profiles(value: Any) -> list[str]:
    """Return validation errors for a profile list."""
    if value is None:
        return []
    if not isinstance(value, list):
        return ["assurance_profiles must be a list"]
    errors: list[str] = []
    seen: set[str] = set()
    for index, profile in enumerate(value):
        if not isinstance(profile, str) or profile not in PROFILE_REQUIREMENTS:
            errors.append(
                f"assurance_profiles[{index}] must be one of {sorted(PROFILE_REQUIREMENTS)}"
            )
        elif profile in seen:
            errors.append(f"assurance_profiles[{index}] duplicates {profile!r}")
        else:
            seen.add(profile)
    return errors


def validate_capabilities(value: Any, field: str = "evidence_capabilities") -> list[str]:
    """Return validation errors for a capability list."""
    if value is None:
        return []
    if not isinstance(value, list):
        return [f"{field} must be a list"]
    errors: list[str] = []
    seen: set[str] = set()
    for index, capability in enumerate(value):
        if not isinstance(capability, str) or capability not in EVIDENCE_CAPABILITIES:
            errors.append(f"{field}[{index}] must be one of {sorted(EVIDENCE_CAPABILITIES)}")
        elif capability in seen:
            errors.append(f"{field}[{index}] duplicates {capability!r}")
        else:
            seen.add(capability)
    return errors


def validate_impact(value: Any) -> list[str]:
    """Return validation errors for an impact object."""
    if value is None:
        return []
    if not isinstance(value, dict):
        return ["assurance_impact must be an object"]
    errors: list[str] = []
    allowed = frozenset(_IMPACT_ENUMS) | _IMPACT_BOOLS
    for key in value:
        if key not in allowed:
            errors.append(f"assurance_impact has unknown field {key!r}")
    for key, choices in _IMPACT_ENUMS.items():
        if key in value and (not isinstance(value[key], str) or value[key] not in choices):
            errors.append(f"assurance_impact.{key} must be one of {sorted(choices)}")
    for key in _IMPACT_BOOLS:
        if key in value and not isinstance(value[key], bool):
            errors.append(f"assurance_impact.{key} must be boolean")
    return errors


def compose_declarations(
    stack_profiles: Iterable[str] | None,
    task_profiles: Iterable[str] | None,
    stack_impact: Mapping[str, Any] | None,
    task_impact: Mapping[str, Any] | None,
) -> tuple[list[str], dict[str, Any], bool]:
    """Compose stack defaults with task additions/overrides."""
    profiles = sorted(set(stack_profiles or ()) | set(task_profiles or ()))
    impact = dict(_IMPACT_DEFAULTS)
    impact.update(stack_impact or {})
    impact.update(task_impact or {})
    metadata_complete = bool(profiles) and all(
        impact[key] != "unknown" for key in ("level", "blast_radius", "reversibility")
    )
    return profiles, impact, metadata_complete


def observed_capabilities(
    gate_capabilities: Mapping[str, Iterable[str]],
    gate_results: Iterable[Mapping[str, Any]],
) -> list[str]:
    """Capabilities proved by passed, non-skipped gates only."""
    observed: set[str] = set()
    for result in gate_results:
        if not result.get("passed") or result.get("skipped"):
            continue
        observed.update(gate_capabilities.get(str(result.get("name", "")), ()))
    return sorted(observed & EVIDENCE_CAPABILITIES)


def evaluate_assurance(
    *,
    profiles: Iterable[str] | None,
    impact: Mapping[str, Any] | None,
    observed_evidence: Iterable[str] | None,
    metadata_complete: bool = True,
) -> dict[str, Any]:
    """Return a deterministic L1/L2/L3 residual-assurance decision."""
    profile_list = sorted(set(profiles or ()))
    impact_value = dict(_IMPACT_DEFAULTS)
    impact_value.update(impact or {})
    required = sorted(
        set().union(*(PROFILE_REQUIREMENTS[p] for p in profile_list)) if profile_list else set()
    )
    observed = sorted(set(observed_evidence or ()) & EVIDENCE_CAPABILITIES)
    residual = sorted(set(required) - set(observed))
    reasons: list[str] = []
    hard_reasons: list[str] = []

    for field, label in (
        ("security_boundary", "security boundary"),
        ("governance_boundary", "governance boundary"),
        ("privileged", "privileged state change"),
        ("owner_escalation", "owner escalation"),
    ):
        if impact_value[field]:
            hard_reasons.append(label)
    if impact_value["reversibility"] == "irreversible":
        hard_reasons.append("irreversible state change")
    if impact_value["data_change"] == "destructive":
        hard_reasons.append("destructive data migration")

    if hard_reasons:
        depth = "L3"
        hard_floor = "L3"
        reasons.append("non-downgradable L3 floor: " + ", ".join(hard_reasons))
    elif not metadata_complete or not profile_list:
        depth = "L2"
        hard_floor = None
        reasons.append("assurance metadata is incomplete; conservative L2 fallback")
    else:
        hard_floor = None
        elevated = impact_value["level"] == "high" or impact_value["blast_radius"] == "broad"
        if residual and elevated:
            depth = "L3"
            reasons.append("elevated impact retains uncovered assurance properties")
        elif residual:
            depth = "L2"
            reasons.append("required evidence remains uncovered")
        elif (
            impact_value["level"] == "low"
            and impact_value["blast_radius"] == "local"
            and impact_value["reversibility"] == "reversible"
        ):
            depth = "L1"
            reasons.append("low, local, reversible impact is fully evidenced")
        else:
            depth = "L2"
            reasons.append("evidence is complete but impact requires contextual review")

    return {
        "profiles": profile_list,
        "impact": impact_value,
        "required_evidence": required,
        "observed_evidence": observed,
        "residual_gaps": residual,
        "depth": depth,
        "reasons": reasons,
        "hard_floor": hard_floor,
    }
