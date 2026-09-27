"""Documents this project generates about itself.

`doc` writes the generated constants and the roadmap; `update-claudemd` writes the
dynamic half of the instruction file. Both produce a tracked document from the
live database, which is one subject and not two.
"""

from __future__ import annotations

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
    """Update <!-- DYNAMIC:START --> section in CLAUDE.md."""
    import os

    # Both the block AND the file lookup live in claudemd_state, shared with the
    # MCP handler. Each side used to carry its own copy, and the copies drifted
    # silently — the MCP one lost the memory tail and the AGENTS.md refresh
    # (mcp-update-claudemd-erases-the-memory-tail).
    from claudemd_state import build_dynamic_state, resolve_claudemd, resolve_project_dir

    # Адрес выводится ИЗ БАЗЫ, а не из cwd. Здесь стояло `os.getcwd()` в обеих
    # строках — тот же дефект, что в MCP-обработчике: содержимое из `svc`, адрес
    # из текущего каталога. Заодно это чинит запуск из подкаталога проекта:
    # раньше `resolve_claudemd(os.getcwd())` там не находил файла, хотя база
    # находилась подъёмом (claudemd-dynamic-block-wiped-to-an-empty-project).
    # Явный `--claudemd` уважается: это высказанное намерение пользователя.
    project_dir = resolve_project_dir(svc)
    if project_dir is None and not args.claudemd:
        print(
            "Error: cannot tell which project this database describes "
            "(no db_path, or it does not live in .tausik/). Use --claudemd to "
            "specify the file explicitly."
        )
        return

    claudemd = args.claudemd or resolve_claudemd(project_dir or "")
    if not claudemd or not os.path.exists(claudemd):
        print("Error: CLAUDE.md not found. Use --claudemd to specify path.")
        return

    dynamic_content = build_dynamic_state(svc, project_dir or os.path.dirname(claudemd))

    # Refresh CLAUDE.md AND its AGENTS.md sibling from the same dynamic source so
    # no IDE's onboarding file goes stale mid-session (v15p-agents-md-bootstrap).
    from claudemd_writer import apply_dynamic_section, plan_dynamic_writes

    dry_run = getattr(args, "dry_run", False)
    any_change = False
    for path, content in plan_dynamic_writes(claudemd, dynamic_content):
        msg, changed = apply_dynamic_section(path, content, dry_run)
        print(msg)
        any_change = any_change or changed
    if dry_run and any_change:
        import sys

        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
