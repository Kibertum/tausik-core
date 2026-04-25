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
