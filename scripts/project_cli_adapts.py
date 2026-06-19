"""TAUSIK CLI handler for `tausik adapt` subcommands (v16r-adapt).

RENAR ADAPT artifacts (§7): create / interpret / finding / sign / verify /
show / list / delta / link / unlink / delete / search. Closed lists (finding
category, signature role, link target) are enforced by the service + DB CHECK.
"""

from __future__ import annotations

import os
from typing import Any

from project_service import ProjectService
from tausik_utils import ServiceError


def cmd_adapt(svc: ProjectService, args: Any) -> None:
    cmd = getattr(args, "adapt_cmd", None) or "list"
    try:
        if cmd == "list":
            return _cmd_list(svc, args)
        if cmd == "show":
            return _cmd_show(svc, args.slug)
        if cmd == "create":
            print(svc.adapt_create(args.slug, args.title, args.tz_ref))
            return None
        if cmd == "interpret":
            print(
                svc.adapt_interpret(
                    args.adapt_slug,
                    args.tz_ref,
                    args.citation,
                    args.engineering_interpretation,
                    args.scope_in,
                    args.scope_out,
                    args.term_mapping,
                    args.scenarios,
                )
            )
            return None
        if cmd == "finding":
            print(
                svc.adapt_finding(
                    args.adapt_slug, args.category, args.description, args.tz_ref, args.resolution
                )
            )
            return None
        if cmd == "sign":
            print(svc.adapt_sign(args.adapt_slug, args.role, args.signed_by, os.getcwd()))
            return None
        if cmd == "verify":
            res = svc.adapt_verify(args.slug, os.getcwd())
            print(
                f"ADAPT '{args.slug}': signed={res['signed']} valid={res['valid']} ({res['reason']})"
            )
            return None
        if cmd == "delta":
            print(svc.adapt_delta(args.parent_slug, args.new_slug, args.title, args.tz_ref))
            return None
        if cmd == "link":
            print(svc.adapt_link(args.adapt_slug, args.target_type, args.target_slug))
            return None
        if cmd == "unlink":
            print(svc.adapt_unlink(args.adapt_slug, args.target_type, args.target_slug))
            return None
        if cmd == "delete":
            print(svc.adapt_delete(args.slug))
            return None
        if cmd == "search":
            return _cmd_search(svc, args)
    except ServiceError as e:
        print(f"Error: {e}")
        return None
    print(f"Unknown adapt subcommand: {cmd!r}")
    return None


def _cmd_list(svc: ProjectService, args: Any) -> None:
    rows = svc.adapt_list(getattr(args, "status", None))
    if not rows:
        print("No ADAPTs. Create one: tausik adapt create <slug> <title> --tz-ref TZ-...")
        return
    for r in rows:
        delta = f" (delta {r['delta_n']} of {r['parent_adapt']})" if r.get("parent_adapt") else ""
        print(f"  {r['slug']:<24} {r['status']:<11} {r['tz_ref']:<16} {r['title']}{delta}")


def _cmd_show(svc: ProjectService, slug: str) -> None:
    a = svc.adapt_show(slug)
    print(f"ADAPT: {a['slug']}")
    print(f"  title:   {a['title']}")
    print(f"  tz_ref:  {a['tz_ref']}")
    print(f"  status:  {a['status']}")
    if a.get("parent_adapt"):
        print(f"  delta:   {a['delta_n']} of parent {a['parent_adapt']}")
    interps = a.get("interpretations", [])
    if interps:
        print(f"  forward interpretation ({len(interps)}):")
        for i in interps:
            print(f"    - {i['tz_ref']}: {i['engineering_interpretation']}")
            print(f"        in: {i['scope_in']}  |  out: {i['scope_out']}")
    findings = a.get("findings", [])
    if findings:
        print(f"  backward findings ({len(findings)}):")
        for f in findings:
            res = f"  -> {f['resolution']}" if f.get("resolution") else ""
            print(f"    - [{f['category']}] {f['description']}{res}")
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
    rows = svc.adapt_search(args.query, args.limit)
    if not rows:
        print("No matching ADAPTs.")
        return
    for r in rows:
        print(f"  {r['slug']:<24} {r['status']:<11} {r.get('_snippet', r['title'])}")
