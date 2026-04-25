"""Lazy enum resolvers for service-layer field validation.

Extracted from service_task.py so that file stays under the 400-line gate.
Stack set is config-driven (cfg.custom_stacks), so it must resolve at
call time rather than at module import.
"""

from __future__ import annotations

from project_types import (
    VALID_COMPLEXITIES,
    VALID_TASK_STATUSES,
    VALID_TIERS,
    get_valid_stacks,
)


def load_stacks() -> frozenset[str]:
    try:
        from project_config import load_config

        return get_valid_stacks(load_config())
    except Exception:
        return get_valid_stacks(None)


def update_enums() -> tuple[tuple[str, frozenset[str]], ...]:
    return (
        ("status", VALID_TASK_STATUSES),
        ("complexity", VALID_COMPLEXITIES),
        ("stack", load_stacks()),
        ("tier", VALID_TIERS),
    )


def validate_task_add_inputs(
    stack: str | None,
    complexity: str | None,
    call_budget: int | None,
    tier: str | None,
) -> None:
    """Raise ServiceError if any task_add input is out of range."""
    from tausik_utils import ServiceError

    if complexity and complexity not in VALID_COMPLEXITIES:
        raise ServiceError(
            f"Invalid complexity '{complexity}'. Valid: {sorted(VALID_COMPLEXITIES)}"
        )
    valid_stacks = load_stacks()
    if stack and stack not in valid_stacks:
        raise ServiceError(f"Invalid stack '{stack}'. Valid: {sorted(valid_stacks)}")
    if call_budget is not None and call_budget < 0:
        raise ServiceError(
            f"Invalid call_budget '{call_budget}'; must be >=0 or omitted"
        )
    if tier is not None and tier not in VALID_TIERS:
        raise ServiceError(f"Invalid tier '{tier}'. Valid: {sorted(VALID_TIERS)}")
