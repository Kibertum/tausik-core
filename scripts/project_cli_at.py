"""TAUSIK CLI handler for `tausik at` subcommands.

RENAR AT (Acceptance Test) artifacts (Sec8A): create / show / list / delete /
search / check-freshness / record-result / diagnose / release-readiness.
"""

from __future__ import annotations

import sys
from typing import Any

from project_service import ProjectService
from tausik_utils import ServiceError


def cmd_at(svc: ProjectService, args: Any) -> None:
    cmd = getattr(args, "at_cmd", None) or "list"
    try:
        if cmd == "list":
            return _cmd_list(svc, args)
        if cmd == "show":
            return _cmd_show(svc, args.slug)
        if cmd == "create":
            print(
                svc.at_create(
                    args.slug,
                    args.tz_ref,
                    args.tz_text,
                    args.scenario,
                    args.source_as_of,
                    args.generated_by,
                )
            )
            return None
        if cmd == "delete":
            print(svc.at_delete(args.slug))
            return None
        if cmd == "search":
            return _cmd_search(svc, args)
        if cmd == "check-freshness":
            return _cmd_check_freshness(svc, args)
        if cmd == "record-result":
            print(svc.at_record_result(args.slug, args.outcome, args.note))
            return None
        if cmd == "diagnose":
            return _cmd_diagnose(svc, args)
        if cmd == "release-readiness":
            return _cmd_release_readiness(svc)
    except ServiceError as e:
        # A CLI invocation IS the flow — a swallowed error that still exits 0 is
        # a silent failure (CLAUDE.md zero-tolerance).
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"Unknown at subcommand: {cmd!r}")
    return None


def _cmd_list(svc: ProjectService, args: Any) -> None:
    rows = svc.at_list(getattr(args, "tz_ref", None))
    if not rows:
        print(
            "No AT records. Record one: tausik at create <slug> <tz_ref> <tz_text> <scenario> ..."
        )
        return
    for r in rows:
        print(f"  {r['slug']:<24} {r['tz_ref']:<16} {r['scenario']}")


def _cmd_show(svc: ProjectService, slug: str) -> None:
    a = svc.at_show(slug)
    print(f"AT: {a['slug']}")
    print(f"  tz_ref:        {a['tz_ref']}")
    print(f"  tz_text:       {a['tz_text']}")
    print(f"  scenario:      {a['scenario']}")
    print(f"  source_as_of:  {a['source_as_of']}")
    print(f"  generated_by:  {a['generated_by']}")


def _cmd_search(svc: ProjectService, args: Any) -> None:
    rows = svc.at_search(args.query, args.limit)
    if not rows:
        print("No matching AT records.")
        return
    for r in rows:
        print(f"  {r['slug']:<24} {r['tz_ref']:<16} {r.get('_snippet', r['scenario'])}")


def _cmd_check_freshness(svc: ProjectService, args: Any) -> None:
    stale = svc.at_check_freshness(getattr(args, "slug", None))
    if not stale:
        print("No stale AT records — every one matches the current final-TZ.")
        return
    print(f"STALE: {len(stale)} AT record(s) no longer match the current final-TZ (§8A):")
    for s in stale:
        print(f"  {s['slug']} ({s['tz_ref']}): {s['reason']}")


def _cmd_diagnose(svc: ProjectService, args: Any) -> None:
    d = svc.at_diagnose(args.slug, args.tc_outcome)
    print(f"AT '{d['at_slug']}': at={d['at_outcome']} tc={d['tc_outcome']}")
    print(f"  diagnosis: {d['diagnosis']}")
    print(f"  routes to: {d['routes_to'] or '(no divergence)'}")


def _cmd_release_readiness(svc: ProjectService) -> None:
    r = svc.at_release_readiness()
    if r["ready"]:
        print("READY (§8A.4): every AT is green and matches the current final-TZ.")
        return
    print(f"NOT READY (§8A.4): {len(r['blocking'])} blocking reason(s):")
    for b in r["blocking"]:
        print(f"  {b['slug']}: {b['reason']}")


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
