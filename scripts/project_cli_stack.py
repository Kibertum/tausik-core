"""TAUSIK CLI handler for `tausik stack {info,list}` (Epic 2 visibility)."""

from __future__ import annotations

from typing import Any

from project_service import ProjectService


def cmd_stack(svc: ProjectService, args: Any) -> None:
    """Handle stack subcommands: info, list."""
    if (args.stack_cmd or "list") == "list":
        for r in svc.stack_list():
            tag = " (custom)" if r.get("is_custom") else ""
            print(f"  {r['stack']:<12} ({r['applicable_gates']} gates){tag}")
        return
    info = svc.stack_info(args.stack)
    print(f"Stack: {info['stack']}")
    if not info["gates"]:
        print(f"  {info['gap_notice']}")
        return
    for g in info["gates"]:
        on = "ON" if g.get("enabled", True) else "off"
        sev, stacks = g.get("severity", "warn"), g.get("stacks") or "any"
        print(f"  [{on}] {g['name']:<14} severity={sev:<5} stacks={stacks}")
        print(f"        command: {g.get('command') or '(builtin)'}")
