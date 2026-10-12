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


def _route_for_task(svc: Any, slug: str, *, deep: bool, fallback_depth: str = "L2") -> dict:
    """Canonical route, with a narrow compatibility fallback for legacy adapters."""
    from review_routing import build_review_route, force_deep_route

    try:
        if not hasattr(svc.be, "_q1"):
            raise AttributeError("legacy backend adapter")
        from task_context_package import build_task_context_package

        required = build_task_context_package(svc, slug)["required"]
        route = required["review_route"]
        return force_deep_route(route) if deep else route
    except (AttributeError, KeyError, TypeError):
        assurance = {
            "depth": fallback_depth,
            "profiles": [],
            "reasons": ["legacy review adapter has no task package"],
            "hard_floor": None,
        }
    return build_review_route(assurance, explicit_deep=deep)


def cmd_review(svc: ProjectService, args: Any) -> None:
    """tausik review — track L1/L2/L3 review runs (SENAR Rule 10.15)."""
    sub = getattr(args, "review_cmd", None)
    if sub == "route":
        route = _route_for_task(svc, args.task, deep=bool(args.deep))
        if args.json:
            print(_json.dumps(route, ensure_ascii=False, indent=2))
        else:
            execution = route["execution"]
            print(
                f"{route['depth']}{'-deep' if route['deep'] else ''}: "
                f"{execution['mode']}; reviewer calls={execution['reviewer_invocations']}"
            )
            for reason in route["reasons"]:
                print(f"- {reason}")
            if route["missing_inputs"]:
                print("Missing inputs: " + ", ".join(route["missing_inputs"]))
        return
    if sub == "record":
        try:
            svc.task_show(args.task)
        except Exception:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
            print(f"Error: task '{args.task}' not found", file=sys.stderr)
            sys.exit(1)
        from review_routing import (
            route_json,
            validate_review_record,
        )

        route = _route_for_task(
            svc,
            args.task,
            deep=bool(getattr(args, "deep", False)),
            fallback_depth=args.run_type,
        )
        reviewer_context = (
            getattr(args, "reviewer_context", None)
            or {
                "L1": "author",
                "L2": "fresh",
                "L3": "different-model",
            }[args.run_type]
        )
        reviewer_invocations = getattr(args, "reviewer_invocations", None)
        if reviewer_invocations is None:
            reviewer_invocations = int(route["execution"]["reviewer_invocations"])
        author_model = getattr(args, "author_model", None)
        reviewer_model = getattr(args, "reviewer_model", None)
        if args.run_type == "L3":
            from review_separation import resolve_author_model

            author_model = resolve_author_model(author_model)
        notes = _notes_with_reason(args.critical, getattr(args, "reason", None), args.notes)
        if args.run_type == "L3":
            notes = _l3_notes_or_exit(args, notes)
        blockers = validate_review_record(
            route,
            run_type=args.run_type,
            author_model=author_model,
            reviewer_model=reviewer_model,
            reviewer_context=reviewer_context,
            reviewer_invocations=reviewer_invocations,
            require_identities=hasattr(svc.be, "_q1"),
        )
        if blockers:
            print("Error: review record refused — " + "; ".join(blockers), file=sys.stderr)
            sys.exit(1)
        usage_fn = getattr(svc.be, "usage_events_cost_rollup_for_task", None)
        usage = usage_fn(args.task) if usage_fn else {"availability": "unavailable"}
        rid = svc.be.review_record(  # type: ignore[attr-defined]
            task_slug=args.task,
            run_type=args.run_type,
            critical_findings=args.critical,
            warnings=args.warnings,
            notes=notes,
            high_findings=int(getattr(args, "high", 0)),
            profiles_json=_json.dumps(route["profiles"], ensure_ascii=False),
            reasons_json=_json.dumps(route["reasons"], ensure_ascii=False),
            hard_floor=route["hard_floor"],
            author_model=author_model,
            reviewer_model=reviewer_model,
            reviewer_context=reviewer_context,
            reviewer_invocations=reviewer_invocations,
            usage_json=_json.dumps(usage, ensure_ascii=False, sort_keys=True),
            route_json=route_json(route),
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
        print(f"{'#':>4} {'type':>4} {'task':<32} {'crit':>4} {'high':>4} {'warn':>4}  run_at")
        for r in rows:
            slug = (r.get("task_slug") or "")[:32]
            print(
                f"{r['id']:>4} {r['run_type']:>4} {slug:<32} "
                f"{r['critical_findings']:>4} {r.get('high_findings', 0):>4} "
                f"{r['warnings']:>4}  {r['run_at']}"
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
