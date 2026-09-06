"""SENAR Rule 5 verify CLI handler.

Lives in its own file so project_cli_extra.py stays under the 400-line
filesize gate. The dispatch in project.py imports `cmd_verify` from here.

cli-verify-bypasses-cache-guards: this module used to run its own gate cycle
— `run_gates` + `record_run` called directly — and so carried none of
`run_gates_with_cache`'s guards (`has_real_pass`, the `no-test-mapped` block,
the refusal to cache an empty declared scope). A run in which every gate was
SKIPPED was therefore written as a fully cacheable green, and `task done`
would close on it. It is now a presentation layer over
`GatesMixin.run_verify_for_task`: it decides nothing about what gets recorded.
"""

from __future__ import annotations

from typing import Any


def cmd_verify(svc: Any, args: Any) -> None:
    """Scoped per-task verification, recorded in DB.

    With --task: gates are scoped to the task's relevant_files. Without:
    file scope is empty (full suite for pytest) and nothing is cached.

    All gate-running, cache and recording decisions belong to
    `run_verify_for_task` -> `run_gates_with_cache`. What is left here is what
    belongs to the CLI and nowhere else: argparse, the scope declaration, and
    the exit code. The REPORT is built by `render_verify`, which the MCP handler
    also calls — it used to be built twice, and the two copies had drifted in
    both directions.
    """
    from project_service import ServiceError
    from render_verify import verify_lines

    task_slug = getattr(args, "task", None)
    scope = getattr(args, "scope", "manual")

    # verify-warn-names-a-flag-verify-does-not-have: declaring the scope IS part
    # of verifying it — a verify over an undeclared scope skips every gate and
    # still signs a receipt. The declaration is persisted rather than used
    # ad-hoc so `task done` reads the same list and hits the cache; one source
    # of truth, the task row.
    declared = getattr(args, "relevant_files", None)
    if declared is not None:
        if not task_slug:
            print(
                "verify --relevant-files needs --task: the scope is a property "
                "of a task, and there is nowhere to record it otherwise."
            )
            raise SystemExit(2)
        if declared:
            import json as _json

            svc.task_update(task_slug, relevant_files=_json.dumps(list(declared)))
            print(f"Scope declared for '{task_slug}': {len(declared)} file(s).")
        else:
            # An empty list is almost always a shell glob that matched nothing.
            # Silently wiping a declared scope would turn it into an unnoticed
            # unscoped run — the exact state this flag exists to leave.
            print(
                "verify --relevant-files was given no paths — keeping the "
                "scope already declared on the task. Pass paths to change it."
            )

    try:
        report = svc.run_verify_for_task(
            task_slug,
            scope=scope,
            trigger="verify",
            no_tests_expected=bool(getattr(args, "no_tests_expected", False)),
        )
    except ServiceError as exc:
        print(str(exc))
        raise SystemExit(2) from exc

    print("\n".join(verify_lines(svc, report, task_slug, scope)))

    if report.get("cache_hit") is not None:
        # A hit with no task means the cache layer changed shape under this
        # caller; the report says so, and the exit code has to agree with it.
        if not task_slug:
            raise SystemExit(2)
        return
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
