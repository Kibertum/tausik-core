"""TAUSIK CLI handler for `tausik spec` subcommands (v16r-spec-types).

RENAR SPEC artifacts: add / list / show / update / delete / link / unlink /
search. ``type`` is a closed list of 9 enforced by the service + DB CHECK.
"""

from __future__ import annotations

from typing import Any

from project_service import ProjectService
from tausik_utils import ServiceError


def cmd_spec(svc: ProjectService, args: Any) -> None:
    cmd = getattr(args, "spec_cmd", None) or "list"
    try:
        if cmd == "list":
            return _cmd_list(svc, args)
        if cmd == "show":
            return _cmd_show(svc, args.slug)
        if cmd == "add":
            print(
                svc.spec_add(
                    args.slug,
                    args.type,
                    args.title,
                    args.version,
                    args.content_ref,
                    args.status,
                )
            )
            return None
        if cmd == "update":
            print(
                svc.spec_update(
                    args.slug,
                    title=args.title,
                    version=args.version,
                    content_ref=args.content_ref,
                    status=args.status,
                )
            )
            return None
        if cmd == "delete":
            print(svc.spec_delete(args.slug))
            return None
        if cmd == "link":
            print(svc.spec_link(args.task_slug, args.spec_slug, args.relation))
            return None
        if cmd == "unlink":
            print(svc.spec_unlink(args.task_slug, args.spec_slug, args.relation))
            return None
        if cmd == "search":
            return _cmd_search(svc, args)
    except ServiceError as e:
        print(f"Error: {e}")
        return None
    print(f"Unknown spec subcommand: {cmd!r}")
    return None


def _cmd_list(svc: ProjectService, args: Any) -> None:
    rows = svc.spec_list(getattr(args, "type", None))
    if not rows:
        print("No SPECs. Create one: tausik spec add <slug> <TYPE> <title> --version v1")
        return
    for r in rows:
        ref = f"  -> {r['content_ref']}" if r.get("content_ref") else ""
        print(
            f"  [{r['type']:<4}] {r['slug']:<24} {r['version']:<8} {r['status']:<10} {r['title']}{ref}"
        )


def _cmd_show(svc: ProjectService, slug: str) -> None:
    spec = svc.spec_show(slug)
    print(f"SPEC: {spec['slug']}")
    print(f"  type:        {spec['type']}")
    print(f"  title:       {spec['title']}")
    print(f"  version:     {spec['version']}")
    print(f"  status:      {spec['status']}")
    print(f"  content_ref: {spec.get('content_ref') or '(none)'}")
    print(f"  created_at:  {spec['created_at']}")
    tasks = spec.get("linked_tasks", [])
    if tasks:
        print(f"  linked tasks ({len(tasks)}):")
        for t in tasks:
            print(f"    - {t['slug']} [{t['status']}] ({t['relation']}) {t['title']}")


def _cmd_search(svc: ProjectService, args: Any) -> None:
    rows = svc.spec_search(args.query, args.limit)
    if not rows:
        print("No matching SPECs.")
        return
    for r in rows:
        print(f"  [{r['type']:<4}] {r['slug']:<24} {r['version']}  {r.get('_snippet', r['title'])}")
