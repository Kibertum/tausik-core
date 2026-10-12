"""Widening a task's declared write scope without restating it.

MEASURED. A task's scope is declared BEFORE the work reveals which files it will touch, so
the ACL refuses in almost every non-trivial task: seven refusals across three consecutive
tasks in the session that filed this, the last of them on this very module — which could
not have been named in a declaration written before it existed. Each refusal cost two
calls: the refusal, then a `task update --scope-paths` that had to RESTATE the whole list,
because that flag replaces rather than adds. At the measured 482 000 tokens of prefix
re-sent per call that is about a million tokens per refusal, and restating a list by hand
is also how a path gets silently dropped from it.

RULE 2 IS NOT WEAKENED. Widening stays an explicit act by the agent, named path by path,
and nothing is added that was not asked for. What changes is that asking costs one short
call instead of one long one.
"""

from __future__ import annotations

import json
from typing import Any

#: Printed by the refusals so a caller reads back the wrapper it types.
CLI = ".tausik/tausik"


def declared_paths(svc: Any, slug: str) -> list[str]:
    """The task's scope_paths as a list; [] when it declares none."""
    row = svc.task_show(slug) or {}
    raw = row.get("scope_paths")
    if not raw:
        return []
    if isinstance(raw, list):
        return list(raw)
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return list(parsed) if isinstance(parsed, list) else []


def refuse_conflicting_flags(args: Any) -> None:
    """`--scope-paths` replaces and `--add-scope-paths` adds; together they are ambiguous."""
    if getattr(args, "scope_paths", None) is not None and getattr(args, "add_scope_paths", None):
        from project_service import ServiceError

        raise ServiceError(
            "task update: --scope-paths REPLACES the declared scope and --add-scope-paths "
            "ADDS to it. Given both, which one won would not be visible in the output. "
            "Pass one."
        )


def widen(svc: Any, slug: str, add: list[str]) -> str:
    """Add `add` to the task's declared scope. Returns what a reader needs to see."""
    from project_service import ServiceError

    if not add:
        # An empty list is almost always a shell glob that matched nothing, and silently
        # clearing a declared ACL would turn a widening into a total revocation.
        raise ServiceError(
            "task update --add-scope-paths was given no paths. It adds to the declared "
            "scope and cannot add nothing; to clear the scope on purpose, say so with "
            "--scope-paths."
        )

    current = declared_paths(svc, slug)
    already = [p for p in add if p in current]
    new = [p for p in add if p not in current]
    if not new:
        return f"Task '{slug}': already declared — {', '.join(already)}. Nothing changed."

    svc.task_update(slug, scope_paths=current + new)
    said = f"Task '{slug}': scope widened by {', '.join(new)} ({len(current) + len(new)} total)."
    if already:
        said += f" Already declared: {', '.join(already)}."
    return said


def widen_command(slug: str, blocked: list[str]) -> str:
    """The command a refusal should print: additive, and only the paths it refused.

    The refusals used to print `--scope-paths <existing...> <path>`, which asks the reader
    to retype the whole declared list — the expensive half of the two calls this module
    exists to remove, and the half where a path goes missing.
    """
    return f"{CLI} task update {slug} --add-scope-paths " + " ".join(sorted(set(blocked)))


if __name__ == "__main__":  # pragma: no cover - exercised via the CLI
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
