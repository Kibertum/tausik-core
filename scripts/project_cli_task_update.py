"""CLI `task update` — contract edits rebind the live execution lease."""

from __future__ import annotations

import json
import sys
from typing import Any


def run_task_update(svc: Any, args: Any) -> None:
    """Apply CLI task update fields and widen scope under one lease consume."""
    from service_execution_lease import (
        ExecutionLeaseError,
        consume_mcp_authorization,
    )
    from task_scope_widen import refuse_conflicting_flags, widen

    refuse_conflicting_flags(args)
    fields: dict[str, Any] = {}
    for key in (
        "title",
        "goal",
        "notes",
        "stack",
        "complexity",
        "role",
        "scope",
        "scope_exclude",
        "scope_paths",
        "scope_tools",
        "rollback_plan",
        "call_budget",
        "tier",
        "cost_budget_usd",
        "token_budget",
        "assurance_profiles",
        "assurance_impact",
    ):
        value = getattr(args, key, None)
        if value is not None:
            fields[key] = value
    if getattr(args, "notes_overwrite", False):
        if getattr(args, "notes", None) is None:
            print("--notes-overwrite has no effect without --notes.", file=sys.stderr)
            return
        fields["notes_overwrite"] = True
    if args.ac is not None:
        fields["acceptance_criteria"] = args.ac
    relevant = getattr(args, "update_relevant_files", None)
    if relevant is not None:
        fields["relevant_files"] = json.dumps(list(relevant))
    tickets = getattr(args, "update_tickets", None)
    if tickets is not None:
        import tracker_ref

        fields["tracker_refs"] = tracker_ref.dumps(tracker_ref.normalise_all(list(tickets)))
    add_paths = getattr(args, "add_scope_paths", None)
    lease_id = None
    if add_paths is not None or fields:
        try:
            lease = consume_mcp_authorization(
                svc, route="cli_task_update", arguments={"slug": args.slug}
            )
        except ExecutionLeaseError as exc:
            if getattr(exc, "code", None) != "IDENTITY_MISSING":
                raise
            lease = None
        if lease is not None:
            lease_id = int(lease["id"])
    if add_paths is not None:
        print(widen(svc, args.slug, list(add_paths), execution_lease_id=lease_id))
    if fields:
        if lease_id is not None:
            fields["_execution_lease_id"] = lease_id
        print(svc.task_update(args.slug, **fields))
    elif add_paths is None:
        # A widening already printed what it did; saying this after one
        # would read as "nothing happened" over a change that did.
        print("No fields to update.")


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
