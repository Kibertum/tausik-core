"""Compact default task-start text (no full package JSON dump)."""

from __future__ import annotations

from typing import Any


def compact_start_contract_lines(package: dict[str, Any]) -> list[str]:
    """Surface Goal/AC/scope without dumping the full package JSON.

    The package stays persisted and lease-bound; ``task start --package`` and
    ``task show --package`` remain the structured retrieval paths.
    """
    required = package.get("required") or {}
    lines: list[str] = []
    goal = required.get("goal")
    if goal:
        lines.append(f"Goal: {goal}")
    ac = required.get("acceptance_criteria")
    if ac:
        lines.append(f"Acceptance criteria: {ac}")
    scope = required.get("scope")
    if scope:
        lines.append(f"Scope: {scope}")
    scope_exclude = required.get("scope_exclude")
    if scope_exclude:
        lines.append(f"Scope exclude: {scope_exclude}")
    fingerprint = package.get("fingerprint")
    if fingerprint:
        lines.append(
            "Package bound"
            f" (fingerprint={fingerprint}); full: task show --package / task start --package"
        )
    return lines


def append_start_context(
    messages: list[str],
    *,
    be: Any,
    slug: str,
    package: dict[str, Any] | None,
    include_memory: bool,
) -> None:
    if not include_memory:
        return
    from memory_relevance import lines_for_task

    messages.extend(lines_for_task(be, slug))
    if package is not None:
        messages.extend(compact_start_contract_lines(package))
