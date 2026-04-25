"""TAUSIK CLI handler for `tausik stack` subcommands.

Subcommands:
  list   — list all known stacks with gate counts
  info   — show enabled gates for a stack
  export — print the resolved stack.json (built-in + user merge) as JSON
  diff   — show diff between built-in and user override
  reset  — remove user override for a stack (deletes .tausik/stacks/<name>/)
  lint   — validate every user-override stack.json against the schema
"""

from __future__ import annotations

import json
import os
import shutil
from typing import Any

from project_service import ProjectService


def cmd_stack(svc: ProjectService, args: Any) -> None:
    cmd = args.stack_cmd or "list"
    if cmd == "list":
        return _cmd_list(svc)
    if cmd == "info":
        return _cmd_info(svc, args.stack)
    if cmd == "export":
        return _cmd_export(args.stack)
    if cmd == "diff":
        return _cmd_diff(args.stack)
    if cmd == "reset":
        return _cmd_reset(args.stack, getattr(args, "yes", False))
    if cmd == "lint":
        return _cmd_lint()
    print(f"Unknown stack subcommand: {cmd!r}")


def _cmd_list(svc: ProjectService) -> None:
    for r in svc.stack_list():
        tag = " (custom)" if r.get("is_custom") else ""
        print(f"  {r['stack']:<12} ({r['applicable_gates']} gates){tag}")


def _cmd_info(svc: ProjectService, stack: str) -> None:
    info = svc.stack_info(stack)
    print(f"Stack: {info['stack']}")
    if not info["gates"]:
        print(f"  {info['gap_notice']}")
        return
    for g in info["gates"]:
        on = "ON" if g.get("enabled", True) else "off"
        sev, stacks = g.get("severity", "warn"), g.get("stacks") or "any"
        print(f"  [{on}] {g['name']:<14} severity={sev:<5} stacks={stacks}")
        print(f"        command: {g.get('command') or '(builtin)'}")


def _cmd_export(stack: str) -> None:
    """Dump the resolved (built-in + user-merged) decl as JSON."""
    from stack_registry import default_registry

    reg = default_registry()
    if stack not in reg.all_stacks():
        print(f"Unknown stack: {stack!r}. Available: {sorted(reg.all_stacks())}")
        return
    decl = {
        "name": stack,
        "source": reg.source_for(stack),
        "detect": reg.signatures_for(stack),
        "extensions": sorted(reg.extensions_for(stack)),
        "filenames": sorted(reg.filenames_for(stack)),
        "path_hints": sorted(reg.path_hints_for(stack)),
        "gates": reg.gates_for(stack),
    }
    print(json.dumps(decl, indent=2, ensure_ascii=False))


def _cmd_diff(stack: str) -> None:
    """Side-by-side compare of built-in stack.json vs user override."""
    import difflib

    builtin_path, user_path = _stack_paths(stack)
    if not os.path.isfile(builtin_path):
        print(f"No built-in decl at {builtin_path}")
        return
    if not os.path.isfile(user_path):
        print(f"No user override at {user_path} — nothing to diff.")
        return
    with open(builtin_path, encoding="utf-8") as f:
        builtin_lines = f.readlines()
    with open(user_path, encoding="utf-8") as f:
        user_lines = f.readlines()
    diff = difflib.unified_diff(
        builtin_lines,
        user_lines,
        fromfile=f"builtin:{stack}",
        tofile=f"user:{stack}",
        lineterm="",
    )
    out = "".join(diff)
    print(out if out else "(no differences)")


def _cmd_reset(stack: str, assume_yes: bool) -> None:
    """Delete .tausik/stacks/<stack>/ — restore built-in default."""
    _, user_path = _stack_paths(stack)
    user_dir = os.path.dirname(user_path)
    if not os.path.isdir(user_dir):
        print(f"No user override at {user_dir} — nothing to reset.")
        return
    if not assume_yes:
        resp = input(f"Delete user override {user_dir}? [y/N] ").strip().lower()
        if resp not in ("y", "yes"):
            print("Aborted.")
            return
    shutil.rmtree(user_dir)
    print(f"Removed {user_dir}.")


def _cmd_lint() -> None:
    """Validate every user override under .tausik/stacks/<name>/stack.json."""
    from stack_schema import validate_decl

    user_root = os.path.join(os.getcwd(), ".tausik", "stacks")
    if not os.path.isdir(user_root):
        print("No .tausik/stacks/ directory — nothing to lint.")
        return
    total = 0
    bad = 0
    for entry in sorted(os.listdir(user_root)):
        if entry.startswith((".", "_")):
            continue
        decl_path = os.path.join(user_root, entry, "stack.json")
        if not os.path.isfile(decl_path):
            continue
        total += 1
        try:
            with open(decl_path, encoding="utf-8") as f:
                decl = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"FAIL {decl_path}: {e}")
            bad += 1
            continue
        errs = validate_decl(decl, source=decl_path)
        if errs:
            bad += 1
            print(f"FAIL {decl_path}: {len(errs)} error(s)")
            for err in errs:
                print(f"  - {err}")
        else:
            print(f"OK   {decl_path}")
    print(f"\nLinted {total} file(s); {bad} failed.")


def _stack_paths(stack: str) -> tuple[str, str]:
    """Return (built-in stack.json, user-override stack.json) paths."""
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(here)
    builtin = os.path.join(repo_root, "stacks", stack, "stack.json")
    user = os.path.join(os.getcwd(), ".tausik", "stacks", stack, "stack.json")
    return builtin, user
