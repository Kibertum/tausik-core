"""TAUSIK CLI handler for `tausik actz` subcommands.

RENAR ACTZ artifacts (Sec5A): create / point / sign / verify / show / list /
delta / link / unlink / delete / search / decided-in / decided-in-remove.
Closed lists (role, status, target_type) are enforced by the service + DB CHECK.
"""

from __future__ import annotations

import os
import sys
from typing import Any

from project_service import ProjectService
from service_actz import display_name
from tausik_utils import ServiceError


def cmd_actz(svc: ProjectService, args: Any) -> None:
    cmd = getattr(args, "actz_cmd", None) or "list"
    try:
        if cmd == "list":
            return _cmd_list(svc, args)
        if cmd == "show":
            return _cmd_show(svc, args.slug)
        if cmd == "create":
            print(svc.actz_create(args.slug, args.title, args.tz_ref))
            return None
        if cmd == "point":
            print(svc.actz_point_add(args.actz_slug, args.point_no, args.tz_ref, args.text))
            return None
        if cmd == "sign":
            print(svc.actz_sign(args.actz_slug, args.role, args.signed_by, os.getcwd()))
            return None
        if cmd == "verify":
            res = svc.actz_verify(args.slug, os.getcwd())
            print(
                f"ACTZ '{args.slug}': signed={res['signed']} valid={res['valid']} ({res['reason']})"
            )
            return None
        if cmd == "delta":
            print(
                svc.actz_delta(
                    args.parent_slug,
                    args.new_slug,
                    args.title,
                    args.tz_ref,
                    args.supersession_rationale,
                )
            )
            return None
        if cmd == "link":
            print(svc.actz_link(args.actz_slug, args.target_type, args.target_slug))
            return None
        if cmd == "unlink":
            print(svc.actz_unlink(args.actz_slug, args.target_type, args.target_slug))
            return None
        if cmd == "delete":
            print(svc.actz_delete(args.slug))
            return None
        if cmd == "search":
            return _cmd_search(svc, args)
        if cmd == "decided-in":
            print(
                svc.actz_decided_in(
                    args.adapt_slug,
                    args.finding_id,
                    args.actz_slug,
                    args.actz_point_no,
                    args.linked_by,
                )
            )
            return None
        if cmd == "decided-in-remove":
            print(
                svc.actz_decided_in_remove(
                    args.adapt_slug, args.finding_id, args.actz_slug, args.actz_point_no
                )
            )
            return None
        if cmd == "final-tz":
            return _cmd_final_tz(svc, args)
        if cmd == "orphans":
            return _cmd_orphans(svc)
    except ServiceError as e:
        # A CLI invocation IS the flow — a swallowed error that still exits 0 is
        # a silent failure (CLAUDE.md zero-tolerance). Route to stderr and exit
        # non-zero, consistent with cmd_adapt and the top-level handler in project.py.
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"Unknown actz subcommand: {cmd!r}")
    return None


def _cmd_list(svc: ProjectService, args: Any) -> None:
    rows = svc.actz_list(getattr(args, "status", None))
    if not rows:
        print("No ACTZ. Create one: tausik actz create <slug> <title> --tz-ref TZ-...")
        return
    for r in rows:
        delta = f" (delta {r['delta_n']} of {r['parent_actz']})" if r.get("parent_actz") else ""
        print(f"  {r['slug']:<24} {r['status']:<10} {r['display_name']}{delta}")


def _cmd_show(svc: ProjectService, slug: str) -> None:
    a = svc.actz_show(slug)
    print(f"ACTZ: {a['slug']} — {display_name(a)}")
    print(f"  title:   {a['title']}")
    print(f"  tz_ref:  {a['tz_ref']}")
    print(f"  status:  {a['status']}")
    if a.get("parent_actz"):
        print(f"  delta:   {a['delta_n']} of parent {a['parent_actz']}")
    points = a.get("points", [])
    if points:
        print(f"  points ({len(points)}):")
        for p in points:
            print(f"    {p['point_no']}. {p['text']}")
    sigs = a.get("signatures", [])
    if sigs:
        print(f"  signatures ({len(sigs)}/2):")
        for s in sigs:
            fp = f" fp={s['key_fingerprint']}" if s.get("key_fingerprint") else ""
            print(f"    - {s['role']}: {s['signed_by']} @ {s['signed_at']}{fp}")
    links = a.get("links", [])
    if links:
        print(f"  links ({len(links)}):")
        for ln in links:
            print(f"    - {ln['target_type']}: {ln['target_slug']}")


def _cmd_search(svc: ProjectService, args: Any) -> None:
    rows = svc.actz_search(args.query, args.limit)
    if not rows:
        print("No matching ACTZ.")
        return
    for r in rows:
        print(f"  {r['slug']:<24} {r['status']:<10} {r.get('_snippet', r['title'])}")


def _cmd_final_tz(svc: ProjectService, args: Any) -> None:
    rows = svc.final_tz_snapshot(getattr(args, "as_of", None))
    if not rows:
        print("No both-role-signed ACTZ points yet — nothing to derive a final TZ from.")
        return
    for r in rows:
        print(
            f"  {r['tz_ref']}: {r['governing_actz']}#{r['governing_point_no']} @ {r['completed_at']}"
        )
        print(f"    {r['governing_text']}")
        for o in r["overridden"]:
            print(f"    overrides: {o['actz_slug']}#{o['point_no']} @ {o['completed_at']}")


def _cmd_orphans(svc: ProjectService) -> None:
    rows = svc.orphan_signed_points()
    if not rows:
        print("No orphan signed points — every signed decision is reflected in an ADAPT.")
        return
    print(f"FATAL: {len(rows)} signed point(s) with no referencing ADAPT (§5A.4):")
    for r in rows:
        print(f"  {r['actz_slug']}#{r['point_no']} ({r['tz_ref']}): {r['text']}")


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
