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
    except Exception:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
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
    cost_budget_usd: float | None = None,
    token_budget: int | None = None,
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
        raise ServiceError(f"Invalid call_budget '{call_budget}'; must be >=0 or omitted")
    if tier is not None and tier not in VALID_TIERS:
        raise ServiceError(f"Invalid tier '{tier}'. Valid: {sorted(VALID_TIERS)}")
    if cost_budget_usd is not None:
        try:
            cb = float(cost_budget_usd)
        except (TypeError, ValueError):
            raise ServiceError(
                f"Invalid cost_budget_usd '{cost_budget_usd}'; must be a non-negative number or omitted"
            ) from None
        if cb < 0:
            raise ServiceError(
                f"Invalid cost_budget_usd '{cost_budget_usd}'; must be >=0 or omitted"
            )
    if token_budget is not None:
        try:
            tb = int(token_budget)
        except (TypeError, ValueError):
            raise ServiceError(
                f"Invalid token_budget '{token_budget}'; must be a non-negative integer or omitted"
            ) from None
        if tb < 0:
            raise ServiceError(f"Invalid token_budget '{token_budget}'; must be >=0 or omitted")


# Fields whose empty value is DESTRUCTION, not an instruction to clear.
#
# `task update <slug> --acceptance-criteria ""` used to erase a 3.5 KB
# acceptance-criteria block and print "Task updated." An unset shell variable
# expanded to an empty argument and the CLI agreed. Nothing here was a special
# case: NO field was checked for emptiness, so every one of these could be
# blanked the same way, and the value only came back if someone happened to
# re-read the row.
#
# The set is closed by GUARANTEE, not by the one field that was caught: a field
# belongs here when some gate reads it as an input. `title` is identity;
# `goal`, `acceptance_criteria` and `scope` are QG-0 start inputs;
# `rollback_plan` is SENAR Rule 6. Blanking any of them leaves a task that
# cannot be started, and says nothing about why.
#
# Deliberately ABSENT — clearing these is a legitimate instruction, not a loss:
#   - the ACL list fields (scope_paths, scope_tools, scope_exclude,
#     relevant_files): an empty list already MEANS "explicitly nothing allowed",
#     a distinction scope_acl.normalize_acl_json exists to preserve;
#   - `notes`: the append-only journal has its own, stricter guard
#     (task_notes_guard.guard_notes_overwrite) requiring --notes-overwrite.
#
# The enums (stack/complexity/role/tier) are covered too, but by a different
# hole: their validator reads `if v and v not in valid`, so an empty string
# skipped validation entirely instead of failing it. Listing them here fixes
# that without loosening the enum check.
_NON_BLANKABLE = (
    "title",
    "goal",
    "acceptance_criteria",
    "scope",
    "rollback_plan",
    "stack",
    "complexity",
    "role",
    "tier",
)


def reject_blank_updates(fields: dict) -> None:
    """Raise if a field that a gate reads was handed an empty/whitespace value.

    Called BEFORE any write, alongside the other validators, for the reason
    stated there: a refusal that fires after a partial write leaves the row
    changed, the projection stale, and the exit code claiming failure.
    """
    from tausik_utils import ServiceError

    # `None` counts as blanking, and that is not paranoia about a path nobody
    # takes. The CLI drops unset flags before calling (project_cli_task.py), so
    # a None arriving here was PASSED, not omitted — and the MCP server has no
    # input validation at all, so a null in a tool call reaches this dict
    # unchanged. Same erase, different door.
    blanked = [
        f
        for f in _NON_BLANKABLE
        if f in fields
        and (fields[f] is None or (isinstance(fields[f], str) and not fields[f].strip()))
    ]
    if not blanked:
        return
    names = ", ".join(blanked)
    plural = "s" if len(blanked) > 1 else ""
    raise ServiceError(
        f"Refusing to blank required field{plural}: {names}. "
        f"An empty value here erases what a gate reads and cannot be undone. "
        f"Pass the new text, or omit the flag to leave the field alone."
    )
