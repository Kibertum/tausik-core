"""TAUSIK CLI handler for `tausik review` (SENAR Rule 10.15)."""

from __future__ import annotations

import json as _json
import sys
from typing import Any

from project_service import ProjectService


def cmd_review(svc: ProjectService, args: Any) -> None:
    """tausik review — track L1/L2/L3 review runs (SENAR Rule 10.15)."""
    sub = getattr(args, "review_cmd", None)
    if sub == "record":
        try:
            svc.task_show(args.task)
        except Exception:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
            print(f"Error: task '{args.task}' not found", file=sys.stderr)
            sys.exit(1)
        rid = svc.be.review_record(  # type: ignore[attr-defined]
            task_slug=args.task,
            run_type=args.run_type,
            critical_findings=args.critical,
            warnings=args.warnings,
            notes=args.notes,
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
        return
    if sub == "metrics":
        rm = svc.be.review_metrics()  # type: ignore[attr-defined]
        print(f"L3 reviewed tasks: {rm['l3_reviewed_tasks']}")
        print(f"L3 critical findings: {rm['l3_critical_findings']}")
        print(f"ADR: {rm['adr_pct']}% (critical findings / L3 tasks)")
        return
    print("Usage: tausik review {record|list|metrics} [...]", file=sys.stderr)
    sys.exit(1)
