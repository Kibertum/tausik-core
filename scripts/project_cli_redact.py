"""`tausik redact` CLI handler — strike a string out of project memory.

Decision #258. Dry-run by default: the irreversible half must be ASKED FOR, never
reached by accident. `--apply` overwrites every match with a visible marker and
writes one trace row per column touched.

What this command does NOT do, deliberately: restore. The original is not kept
anywhere — not in the trace, not in a shadow column — because a redaction that
stores the value has relocated the leak into a row nobody thinks to scan. The
only way back is a database backup taken beforehand, and the dry run says so
before it lets anyone write.
"""

from __future__ import annotations

from typing import Any

from project_service import ProjectService
from redact_engine import RedactionRequest, apply_redaction, plan_redaction
from tausik_utils import ServiceError


def _request(args: Any) -> RedactionRequest:
    pattern = (getattr(args, "pattern", "") or "").strip()
    if not pattern:
        # An empty pattern matches at every position: it would replace the whole
        # of every redactable column in the project with markers. Refusing is
        # the only safe reading of an empty argument here.
        raise ServiceError("redact: --pattern is empty; an empty pattern would match everything")
    label = (getattr(args, "label", "") or "").strip()
    if not label:
        raise ServiceError(
            "redact: --label is required — it is what the marker and the trace "
            "carry forever, for a reader who has no memory of this session"
        )
    reason = (getattr(args, "reason", "") or "").strip()
    if not reason:
        raise ServiceError(
            "redact: --reason is required — an unexplained overwrite of an "
            "append-only journal is indistinguishable from tampering"
        )
    return RedactionRequest(
        pattern=pattern, label=label, reason=reason, regex=bool(getattr(args, "regex", False))
    )


def _print_plan(hits: list) -> None:
    by_entity: dict[str, int] = {}
    for hit in hits:
        key = f"{hit.entity_type}.{hit.field}"
        by_entity[key] = by_entity.get(key, 0) + hit.occurrences
    for key in sorted(by_entity):
        print(f"  {by_entity[key]:>5}  {key}")


def cmd_redact(svc: ProjectService, args: Any) -> None:
    """`tausik redact --pattern X --label Y --reason Z [--regex] [--apply]`."""
    sub = getattr(args, "redact_cmd", None)
    if sub == "list":
        _list_trace(svc, args)
        return

    req = _request(args)
    hits = plan_redaction(svc, req)

    if not getattr(args, "apply", False):
        total = sum(h.occurrences for h in hits)
        if not hits:
            # Named outcome, not a silent success: a caller who believes a leak
            # exists and gets a clean exit learns nothing about a mistyped
            # pattern. "Could not find" and "found and fixed" are different
            # answers and must not share one.
            print(f"DRY RUN — no match for {req.pattern!r} in any redactable column.")
            print("  Nothing would change. If you expected a match, the pattern is wrong.")
            return
        print(f"DRY RUN — would redact {total} occurrence(s) in {len(hits)} column(s):")
        _print_plan(hits)
        print(f"  marker:  {req.label}")
        print(f"  reason:  {req.reason}")
        print()
        print("  IRREVERSIBLE. The original is kept nowhere — not in the trace, not in a")
        print("  shadow column. Back up .tausik/tausik.db first, then re-run with --apply.")
        return

    result = apply_redaction(svc, req)
    print(result.summary)
    if result.matched:
        _print_plan(hits)
        print("  Re-export the projection so the tree matches: tausik state export")


def _list_trace(svc: ProjectService, args: Any) -> None:
    """`tausik redact list` — what has been struck out of this project."""
    from redact_engine import ensure_redactions_table

    ensure_redactions_table(svc)
    limit = int(getattr(args, "limit", 50) or 50)
    rows = svc.be._conn.execute(
        "SELECT redacted_at, entity_type, entity_id, field, label, occurrences, reason "
        "FROM redactions ORDER BY redacted_at DESC, id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    if not rows:
        print("No redactions recorded in this project.")
        return
    print(f"Redactions ({len(rows)} shown):")
    for at, etype, eid, field, label, n, reason in rows:
        print(f"  {at}  {etype}#{eid}.{field}  [{label}] x{n}")
        print(f"      {reason}")


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
