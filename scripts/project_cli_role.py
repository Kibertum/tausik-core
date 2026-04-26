"""TAUSIK CLI handler for `tausik role` subcommands."""

from __future__ import annotations

import json
from typing import Any

from project_service import ProjectService


def cmd_role(svc: ProjectService, args: Any) -> None:
    cmd = args.role_cmd or "list"
    if cmd == "list":
        return _cmd_list(svc)
    if cmd == "show":
        return _cmd_show(svc, args.slug)
    if cmd == "create":
        return _cmd_create(svc, args)
    if cmd == "update":
        return _cmd_update(svc, args)
    if cmd == "delete":
        return _cmd_delete(svc, args)
    if cmd == "seed":
        return _cmd_seed(svc)
    print(f"Unknown role subcommand: {cmd!r}")


def _cmd_list(svc: ProjectService) -> None:
    from service_roles import role_list

    rows = role_list(svc.be)
    if not rows:
        print("No roles. Run `tausik role seed` to bootstrap from agents/roles/*.md.")
        return
    for r in rows:
        cnt = r.get("task_count", 0)
        desc = r.get("description") or ""
        print(f"  {r['slug']:<14} {r['title']:<28} {cnt:>4} task(s)  {desc[:60]}")


def _cmd_show(svc: ProjectService, slug: str) -> None:
    from service_roles import role_show

    try:
        row = role_show(svc.be, slug)
    except Exception as e:
        print(f"Error: {e}")
        return
    print(f"Role: {row['slug']}")
    print(f"  title:       {row['title']}")
    print(f"  description: {row.get('description') or '(none)'}")
    print(f"  task_count:  {row.get('task_count', 0)}")
    print(f"  profile:     {row.get('profile_path_source')}")
    profile = row.get("profile")
    if profile:
        print("  --- profile (first 20 lines) ---")
        for line in profile.splitlines()[:20]:
            print(f"  {line}")


def _cmd_create(svc: ProjectService, args: Any) -> None:
    from service_roles import role_create

    try:
        row = role_create(svc.be, args.slug, args.title, args.description, args.extends)
    except Exception as e:
        print(f"Error: {e}")
        return
    print(
        f"Role '{row['slug']}' created (profile at {row.get('profile_path_source')})."
    )


def _cmd_update(svc: ProjectService, args: Any) -> None:
    from service_roles import role_update

    try:
        row = role_update(svc.be, args.slug, args.title, args.description)
    except Exception as e:
        print(f"Error: {e}")
        return
    print(f"Role '{row['slug']}' updated.")


def _cmd_delete(svc: ProjectService, args: Any) -> None:
    from service_roles import role_delete

    try:
        msg = role_delete(svc.be, args.slug, args.force)
    except Exception as e:
        print(f"Error: {e}")
        return
    print(msg)


def _cmd_seed(svc: ProjectService) -> None:
    from service_roles import seed_existing_roles

    out = seed_existing_roles(svc.be)
    print(json.dumps(out, indent=2))
