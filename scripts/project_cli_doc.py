"""Documents this project generates about itself.

`doc` writes the generated constants and the roadmap; `update-claudemd` is the
Claude adapter projection; `context refresh --target` is the host-neutral entry.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from project_service import ProjectService


def cmd_doc(svc: ProjectService, args: Any) -> None:
    """`tausik doc <subcommand>` — extract via markitdown; constants JSON generator."""
    sub = getattr(args, "doc_cmd", None)
    if sub == "constants":
        import gen_doc_constants

        code = gen_doc_constants.run_main(
            gen_doc_constants.find_repo_root(),
            check=bool(getattr(args, "doc_constants_check", False)),
        )
        raise SystemExit(code)
    if sub == "roadmap":
        import release_roadmap
        from project_config import find_tausik_dir

        raise SystemExit(
            release_roadmap.run_main(
                svc.be._conn,
                os.path.dirname(find_tausik_dir()),
                check=bool(getattr(args, "doc_roadmap_check", False)),
            )
        )
    if sub == "extract":
        import doc_extract

        md = doc_extract.extract_to_markdown(
            args.path, format_hint=getattr(args, "format_hint", None)
        )
        if md is None:
            sys.exit(1)
        print(md)
        return
    print(
        "Usage: tausik doc extract <file> [--format=X] | "
        "tausik doc constants [--check] | tausik doc roadmap [--check]",
        file=sys.stderr,
    )
    sys.exit(2)


def cmd_update_claudemd(svc: ProjectService, args: Any) -> None:
    """Claude-only DYNAMIC refresh (compat). Does not auto-touch AGENTS.md.

    Prefer `tausik context refresh --target <id>` for host-neutral projections.
    Pass `--sibling` to also refresh AGENTS.md when it carries DYNAMIC markers.
    """
    from claudemd_state import build_dynamic_state, resolve_claudemd, resolve_project_dir
    from claudemd_writer import apply_dynamic_section, plan_dynamic_writes
    from context_refresh import ownership_of

    project_dir = resolve_project_dir(svc)
    if project_dir is None and not args.claudemd:
        print(
            "Error: cannot tell which project this database describes "
            "(no db_path, or it does not live in .tausik/). Use --claudemd to "
            "specify the file explicitly.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    claudemd = args.claudemd or resolve_claudemd(project_dir or "")
    if not claudemd or not os.path.exists(claudemd):
        err = {
            "status": "missing",
            "target": "claude",
            "message": "agent instruction file not found. Use --claudemd to specify path.",
        }
        print(json.dumps(err, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)

    kind = ownership_of(claudemd)
    if kind == "hand_maintained":
        err = {
            "status": "hand_maintained",
            "target": "claude",
            "path": claudemd,
            "message": "CLAUDE.md has no DYNAMIC markers — not modified",
        }
        print(json.dumps(err, ensure_ascii=False), file=sys.stderr)
        print(f"Error: {err['message']}", file=sys.stderr)
        raise SystemExit(2)

    dynamic_content = build_dynamic_state(svc, project_dir or os.path.dirname(claudemd))
    dry_run = bool(getattr(args, "dry_run", False))
    include_sibling = bool(getattr(args, "sibling", False))
    any_change = False
    failures: list[dict[str, str]] = []
    for path, content in plan_dynamic_writes(
        claudemd, dynamic_content, include_sibling=include_sibling
    ):
        own = ownership_of(path)
        if own == "hand_maintained":
            item = {
                "status": "hand_maintained",
                "path": path,
                "message": f"no DYNAMIC markers — skipped write: {path}",
            }
            print(json.dumps(item, ensure_ascii=False), file=sys.stderr)
            failures.append(item)
            continue
        msg, changed = apply_dynamic_section(path, content, dry_run)
        print(msg)
        any_change = any_change or changed
        if msg.startswith("Error reading "):
            failures.append({"status": "error", "path": path, "message": msg})
        elif "marker not found" in msg:
            failures.append({"status": "hand_maintained", "path": path, "message": msg})
    if failures:
        print(
            json.dumps({"status": "partial_failure", "failures": failures}, ensure_ascii=False),
            file=sys.stderr,
        )
        print("Error: dynamic-state refresh did not update every target.", file=sys.stderr)
        raise SystemExit(2)
    if dry_run and any_change:
        raise SystemExit(1)


def cmd_context(svc: ProjectService, args: Any) -> None:
    """Host-neutral projection commands."""
    sub = getattr(args, "context_cmd", None)
    if sub != "refresh":
        print("Usage: tausik context refresh --target <id>", file=sys.stderr)
        raise SystemExit(2)
    from claudemd_state import build_dynamic_state, resolve_project_dir
    from context_refresh import dump_outcome, outcome_is_success, refresh_target

    project_dir = resolve_project_dir(svc)
    if project_dir is None:
        err = {
            "status": "error",
            "message": "cannot resolve project directory from database",
        }
        print(json.dumps(err, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)
    target = getattr(args, "target", None)
    if not target:
        err = {
            "status": "target_required",
            "message": "context refresh requires --target (claude, cursor, agents, …)",
        }
        print(json.dumps(err, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)
    block = build_dynamic_state(svc, project_dir)
    outcome = refresh_target(
        project_dir, target, block, dry_run=bool(getattr(args, "dry_run", False))
    )
    print(dump_outcome(outcome))
    if not outcome_is_success(outcome):
        raise SystemExit(2)


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
