"""SENAR Rule 5 verify CLI handler.

Lives in its own file so project_cli_extra.py stays under the 400-line
filesize gate. The dispatch in project.py imports `cmd_verify` from here.
"""

from __future__ import annotations

from typing import Any

from project_service import ProjectService


def cmd_verify(svc: ProjectService, args: Any) -> None:
    """Scoped per-task verification, recorded in DB.

    With --task: looks up the task's relevant_files and runs gates scoped
    to them. Without --task: runs gates with no file scope (full suite for
    pytest). Either way, records a verification_run row so future
    `task done` calls can reuse the result via cache lookup.
    """
    import json as _json
    import time as _time

    from gate_runner import format_results, run_gates
    from service_verification import (
        compute_files_hash,
        is_cache_allowed,
        is_declared_consistent_with_git_diff,
        lookup_recent_for_task,
        record_run,
        resolve_gate_signature,
    )

    relevant_files: list[str] = []
    task_slug = getattr(args, "task", None)
    task_created_at: str | None = None
    if task_slug:
        task = svc.be.task_get(task_slug)
        if task is None:
            print(f"Task '{task_slug}' not found.")
            raise SystemExit(2)
        rf_raw = task.get("relevant_files") or "[]"
        try:
            relevant_files = _json.loads(rf_raw) if rf_raw else []
        except (TypeError, ValueError):
            relevant_files = []
        task_created_at = task.get("created_at")

    scope = getattr(args, "scope", "manual")
    files_hash = compute_files_hash(relevant_files)
    gate_sig = resolve_gate_signature("task-done")
    cache_command = (
        f"trigger=task-done|sig={gate_sig}|files={','.join(sorted(relevant_files))}"
    )

    cache_consistent = not (
        task_created_at and relevant_files
    ) or is_declared_consistent_with_git_diff(relevant_files, task_created_at)
    if task_slug and is_cache_allowed(relevant_files) and cache_consistent:
        hit = lookup_recent_for_task(
            svc.be._conn,
            task_slug,
            files_hash=files_hash,
            command=cache_command,
        )
        if hit is not None:
            print(
                f"Verify cache HIT for '{task_slug}' "
                f"(verify run #{hit['id']}, ran_at={hit['ran_at']}, "
                f"scope={hit['scope']}, exit={hit['exit_code']}). "
                "Skipping gate run."
            )
            try:
                svc.be.event_add(
                    "task",
                    task_slug,
                    "verify_cache_hit",
                    f"verify_run_id={hit['id']} scope={hit['scope']}",
                )
            except Exception:
                # Telemetry is best-effort; never block the verify flow.
                import logging

                logging.getLogger("tausik.verify").warning(
                    "event_add failed for verify_cache_hit", exc_info=True
                )
            return

    t0 = _time.monotonic()
    passed, results = run_gates("task-done", relevant_files)
    duration_ms = int((_time.monotonic() - t0) * 1000)

    print(f"Verify (scope={scope}, task={task_slug or '-'}):")
    print(format_results(results))
    print(f"Duration: {duration_ms} ms")

    summary = (
        ", ".join(
            r["name"] + "=" + ("PASS" if r["passed"] else "FAIL") for r in results
        )
        or "(no gates configured)"
    )
    record_run(
        svc.be._conn,
        task_slug=task_slug or None,
        scope=scope,
        command=cache_command,
        exit_code=0 if passed else 1,
        summary=summary,
        files_hash=files_hash,
        duration_ms=duration_ms,
    )
    print(
        f"Recorded verification_run "
        f"(task_slug={task_slug or '-'}, exit={'0' if passed else '1'})."
    )
    if not passed:
        raise SystemExit(1)
