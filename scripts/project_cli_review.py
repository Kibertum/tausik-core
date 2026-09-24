"""TAUSIK CLI handler for `tausik review` (SENAR Rule 10.15)."""

from __future__ import annotations

import json as _json
import sys
from typing import Any

from project_service import ProjectService

#: SENAR 1.5 §10.15(f): the assignment of CRITICAL is recorded with its reason.
_REASON_PREFIX = "CRITICAL reason: "
_REASON_REQUIRED = (
    "Error: --critical {n} needs --reason: the assignment of CRITICAL is recorded "
    "with its reason (SENAR 1.5 §10.15(f); scale: docs/en/severity-scale.md)."
)


def _notes_with_reason(critical: int, reason: str | None, notes: str | None) -> str | None:
    """Notes to store, or exit when a CRITICAL count arrives without a reason."""
    reason = (reason or "").strip()
    if critical > 0 and not reason:
        print(_REASON_REQUIRED.format(n=critical), file=sys.stderr)
        sys.exit(1)
    if not reason:
        return notes
    return _REASON_PREFIX + reason + (f"\n{notes}" if notes else "")


def _l3_notes_or_exit(args: Any, notes: str | None) -> str:
    """SENAR Rule 4 on the record: both models named, different families."""
    from review_separation import l3_refusal, models_note, resolve_author_model

    author = resolve_author_model(getattr(args, "author_model", None))
    reviewer = getattr(args, "reviewer_model", None)
    refusal = l3_refusal(author, reviewer)
    if refusal:
        print(f"Error: L3 review not recorded — {refusal}", file=sys.stderr)
        sys.exit(1)
    return models_note(str(author), str(reviewer)) + (f"\n{notes}" if notes else "")


def cmd_review(svc: ProjectService, args: Any) -> None:
    """tausik review — track L1/L2/L3 review runs (SENAR Rule 10.15)."""
    sub = getattr(args, "review_cmd", None)
    if sub == "record":
        try:
            svc.task_show(args.task)
        except Exception:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
            print(f"Error: task '{args.task}' not found", file=sys.stderr)
            sys.exit(1)
        notes = _notes_with_reason(args.critical, getattr(args, "reason", None), args.notes)
        if args.run_type == "L3":
            notes = _l3_notes_or_exit(args, notes)
        rid = svc.be.review_record(  # type: ignore[attr-defined]
            task_slug=args.task,
            run_type=args.run_type,
            critical_findings=args.critical,
            warnings=args.warnings,
            notes=notes,
        )
        print(
            f"Recorded review #{rid} (task={args.task}, type={args.run_type}, "
            f"critical={args.critical}, warnings={args.warnings})."
        )
        return
    if sub == "list":
        rows = svc.be.review_list(  # type: ignore[attr-defined]
            task_slug=args.task, run_type=args.run_type, limit=args.limit
        )
        if getattr(args, "json", False):
            print(_json.dumps(rows, indent=2, default=str))
            return
        if not rows:
            print("No reviews recorded.")
            return
        print(f"{'#':>4} {'type':>4} {'task':<32} {'crit':>4} {'warn':>4}  run_at")
        for r in rows:
            slug = (r.get("task_slug") or "")[:32]
            print(
                f"{r['id']:>4} {r['run_type']:>4} {slug:<32} "
                f"{r['critical_findings']:>4} {r['warnings']:>4}  {r['run_at']}"
            )
            first = str(r.get("notes") or "").split("\n", 1)[0]
            if first.startswith(_REASON_PREFIX):
                print(f"{'':>10}{first}")
        return
    if sub == "metrics":
        rm = svc.be.review_metrics()  # type: ignore[attr-defined]
        print(f"L3 reviewed tasks: {rm['l3_reviewed_tasks']}")
        print(f"L3 critical findings: {rm['l3_critical_findings']}")
        print(f"ADR: {rm['adr_pct']}% (critical findings / L3 tasks)")
        return
    print("Usage: tausik review {record|list|metrics} [...]", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
