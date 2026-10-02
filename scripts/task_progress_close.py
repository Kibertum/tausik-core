"""Compound deterministic task progress and closure.

The order is deliberately ordinary: call the same public service methods an
agent would call separately, stop at the first refusal, and never roll back a
successful earlier operation.  The envelope makes that partial state explicit
without introducing a second task-state implementation.
"""

from __future__ import annotations

import json
from typing import Any


def _validate(
    message: str | None,
    step_num: int | None,
    *,
    close: bool,
    verify: bool,
    verify_handle: str | None,
    ac_verified: bool,
    relevant_files: list[str] | None,
    evidence: str | None,
    evidence_json: str | None,
    no_knowledge: bool,
    no_file_changes: bool,
    no_changelog: bool,
    zero_gate_ack: bool,
) -> tuple[str, int]:
    if not isinstance(message, str) or not message.strip():
        raise ValueError("message must be non-empty")
    if type(step_num) is not int or step_num < 1:
        raise ValueError("step_num must be a positive integer")
    for name, value in (
        ("close", close),
        ("verify", verify),
        ("ac_verified", ac_verified),
        ("no_knowledge", no_knowledge),
        ("no_file_changes", no_file_changes),
        ("no_changelog", no_changelog),
        ("zero_gate_ack", zero_gate_ack),
    ):
        if type(value) is not bool:
            raise ValueError(f"{name} must be boolean")
    if verify and verify_handle:
        raise ValueError("verify and verify_handle are mutually exclusive")
    if verify_handle is not None and not isinstance(verify_handle, str):
        raise ValueError("verify_handle must be a string")
    if evidence is not None and not isinstance(evidence, str):
        raise ValueError("evidence must be a string")
    if evidence_json is not None and not isinstance(evidence_json, str):
        raise ValueError("evidence_json must be a string")
    if evidence is not None and evidence_json is not None:
        raise ValueError("evidence and evidence_json are mutually exclusive")
    if relevant_files is not None and (
        not isinstance(relevant_files, list)
        or any(not isinstance(path, str) or not path.strip() for path in relevant_files)
    ):
        raise ValueError("relevant_files must be a list of non-empty strings")
    if not close and any(
        (
            verify,
            verify_handle is not None,
            ac_verified,
            relevant_files is not None,
            evidence is not None,
            evidence_json is not None,
            no_knowledge,
            no_file_changes,
            no_changelog,
            zero_gate_ack,
        )
    ):
        raise ValueError("close-only arguments require close=true")
    return message, step_num


def _state(svc: Any, slug: str) -> dict[str, Any]:
    task = svc.task_show(slug)
    raw_plan = task.get("plan")
    if isinstance(raw_plan, str):
        try:
            plan = json.loads(raw_plan)
        except ValueError:
            plan = raw_plan
    else:
        plan = raw_plan or []
    return {"status": task.get("status"), "plan": plan}


def _verification_projection(
    svc: Any, report: dict[str, Any], slug: str, scope: str
) -> dict[str, Any]:
    """Return the shared bounded report, not a second unbounded gate-output path."""
    from render_verify import verify_lines

    fields = (
        "passed",
        "status",
        "scope",
        "trigger",
        "run_id",
        "verify_handle",
        "handle_expires_at",
        "no_handle_reason",
        "relevant_files",
    )
    projected = {field: report.get(field) for field in fields}
    projected["summary"] = verify_lines(svc, report, slug, scope)
    projected["results"] = [
        {
            key: row.get(key)
            for key in ("name", "passed", "skipped", "severity", "duration_ms", "scope")
            if key in row
        }
        for row in report.get("results") or []
    ]
    return projected


def _failure(
    svc: Any,
    slug: str,
    result: dict[str, Any],
    stage: str,
    message: str,
) -> dict[str, Any]:
    result["failure"] = {"stage": stage, "message": message}
    try:
        result["state"] = _state(svc, slug)
    except Exception as exc:  # noqa: BLE001 - original failure remains primary
        result["state"] = {"unavailable": str(exc)}
    return result


def run_progress_close(
    svc: Any,
    slug: str,
    message: str | None,
    step_num: int | None,
    *,
    close: bool = False,
    verify: bool = False,
    verify_handle: str | None = None,
    ac_verified: bool = False,
    relevant_files: list[str] | None = None,
    evidence: str | None = None,
    evidence_json: str | None = None,
    no_knowledge: bool = False,
    no_file_changes: bool = False,
    no_changelog: bool = False,
    zero_gate_ack: bool = False,
    progress_fn: Any | None = None,
) -> dict[str, Any]:
    """Run deterministic progress operations and optionally verify + close."""
    message, step_num = _validate(
        message,
        step_num,
        close=close,
        verify=verify,
        verify_handle=verify_handle,
        ac_verified=ac_verified,
        relevant_files=relevant_files,
        evidence=evidence,
        evidence_json=evidence_json,
        no_knowledge=no_knowledge,
        no_file_changes=no_file_changes,
        no_changelog=no_changelog,
        zero_gate_ack=zero_gate_ack,
    )
    result: dict[str, Any] = {
        "schema_version": 1,
        "slug": slug,
        "ok": False,
        "completed": [],
    }
    try:
        result["log"] = svc.task_log(slug, message)
        result["completed"].append("task_log")
    except Exception as exc:  # noqa: BLE001 - envelope preserves the producer's diagnostic
        return _failure(svc, slug, result, "task_log", str(exc))
    try:
        result["step"] = svc.task_step(slug, step_num)
        result["completed"].append("task_step")
    except Exception as exc:  # noqa: BLE001 - earlier log is intentionally durable
        return _failure(svc, slug, result, "task_step", str(exc))

    handle = verify_handle
    if close and verify:
        try:
            verify_report = svc.run_verify_for_task(
                slug,
                relevant_files=relevant_files,
                scope="manual",
                trigger="verify",
            )
            result["verification"] = _verification_projection(svc, verify_report, slug, "manual")
            result["completed"].append("verification")
        except Exception as exc:  # noqa: BLE001 - log/step stay written
            return _failure(svc, slug, result, "verification", str(exc))
        if not verify_report.get("passed"):
            failed = [
                str(row.get("name") or "unknown")
                for row in verify_report.get("results") or []
                if not row.get("passed") and not row.get("skipped")
            ]
            diagnostic = "verification failed"
            if failed:
                diagnostic += ": " + ", ".join(failed)
            return _failure(svc, slug, result, "verification", diagnostic)
        handle = verify_report.get("verify_handle") or None

    if close:
        try:
            result["close"] = svc.task_done(
                slug,
                relevant_files,
                ac_verified,
                no_knowledge,
                evidence=evidence,
                evidence_json=evidence_json,
                progress_fn=progress_fn,
                no_file_changes=no_file_changes,
                no_changelog=no_changelog,
                verify_handle=handle,
                zero_gate_ack=zero_gate_ack,
            )
            result["completed"].append("task_done")
            result["closed"] = True
        except Exception as exc:  # noqa: BLE001 - all prior producer state remains authoritative
            return _failure(svc, slug, result, "task_done", str(exc))

    result["ok"] = True
    result["state"] = _state(svc, slug)
    return result


def serialize_progress_close(*args: Any, **kwargs: Any) -> str:
    return json.dumps(
        run_progress_close(*args, **kwargs),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
