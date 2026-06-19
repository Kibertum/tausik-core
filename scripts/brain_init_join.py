"""Join-existing branch + finalize step for the brain init wizard.

Extracted from scripts/brain_init.py (v14b-followup-brain-init-filesize-debt)
to keep that module under the 400-line filesize gate. Pure structural split —
no semantic changes. Imports from brain_init are deferred to function-call
time to avoid a load-order cycle (brain_init imports brain_init_join only
inside run_wizard).
"""

from __future__ import annotations

import os
from typing import Any

import brain_project_registry
from brain_notion_client import NotionError


def run_join_branch(
    io: Any,
    config_ops: Any,
    existing: dict,
    client: Any,
    explicit_join_ids: dict[str, str],
    discovered: dict[str, str],
    pre_flight_skipped: bool,
    token_env: str,
    project_name: str,
    interactive: bool,
) -> dict:
    """--join-existing branch of run_wizard.

    Resolves DB IDs (explicit takes precedence over discovered), verifies them,
    and delegates to _finalize_join for config save. Raises WizardError on any
    failure (no IDs resolvable, verification fails, integration not shared).
    """
    from brain_discovery import inspect_workspace_brain_databases
    from brain_init import (
        CATEGORIES,
        WizardError,
        verify_brain_databases,
    )

    # v1.4 dead-end #72 + v1.4-polish: when discovery returns 0 and no
    # explicit IDs were passed, distinguish "integration sees nothing"
    # (likely not-shared) from "integration sees databases that don't
    # match canonical titles or schemas" (likely renamed BRAIN dbs).
    if not discovered and not explicit_join_ids and not pre_flight_skipped:
        try:
            inspection = inspect_workspace_brain_databases(client)
        except NotionError:
            inspection = {
                "visible": [],
                "matched": {},
                "unmatched_visible": [],
                "schema_conflicts": [],
            }
        visible = inspection.get("visible") or []
        if visible:
            listing = "\n".join(
                f"  - id={v['id']}  title={v['title']!r}  "
                f"parent_page={(v['parent_page_id'] or '?')[:8]}…"
                for v in visible
            )
            raise WizardError(
                "--join-existing: integration sees "
                f"{len(visible)} database(s) but none match canonical "
                "BRAIN titles ('Brain · Decisions' etc.) or the per-"
                "category property schema.\n"
                "\n"
                f"Visible databases:\n{listing}\n"
                "\n"
                "Probable cause: these are your BRAIN databases under "
                "non-canonical titles (renamed in Notion, or created by "
                "an older TAUSIK release). Two ways forward:\n"
                "  1. Rename them in Notion to the canonical titles "
                "('Brain · Decisions', 'Brain · Web Cache', "
                "'Brain · Patterns', 'Brain · Gotchas') and re-run.\n"
                "  2. Pass IDs explicitly:\n"
                "       --decisions-id <ID> --web-cache-id <ID> "
                "--patterns-id <ID> --gotchas-id <ID>"
            )
        raise WizardError(
            "--join-existing: search() returned 0 BRAIN databases in "
            "this workspace, and no explicit IDs were passed.\n"
            "\n"
            "Most likely cause: your Notion integration has not been "
            "shared with the BRAIN page yet, so search() cannot see "
            "the existing databases.\n"
            "\n"
            "Fix:\n"
            "  1. Open the BRAIN page in Notion (the parent that holds "
            "the 4 'Brain · …' databases).\n"
            "  2. Click `…` (top-right) → `Connections` → add your "
            "integration to the connection list.\n"
            "  3. Re-run `.tausik/tausik brain init --join-existing`.\n"
            "\n"
            "If you'd rather wire IDs by hand, pass them explicitly:\n"
            "  --decisions-id ... --web-cache-id ... "
            "--patterns-id ... --gotchas-id ..."
        )
    merged_ids: dict[str, str] = {}
    for c in CATEGORIES:
        if c in explicit_join_ids:
            merged_ids[c] = explicit_join_ids[c]
        elif c in discovered:
            merged_ids[c] = discovered[c]
    missing = [c for c in CATEGORIES if c not in merged_ids]
    if missing:
        raise WizardError(
            "--join-existing could not resolve all 4 database IDs. "
            f"Missing: {', '.join(missing)}. "
            "Either share existing canonical-titled BRAIN databases with "
            "the integration so search() finds them, or pass them "
            "explicitly with --decisions-id / --web-cache-id / "
            "--patterns-id / --gotchas-id."
        )
    verify_errors = verify_brain_databases(client, merged_ids)
    if verify_errors:
        details = "; ".join(f"{c}: {msg}" for c, msg in verify_errors.items())
        raise WizardError(
            f"--join-existing verification failed for some IDs: {details}. "
            "Fix the IDs (or share the databases with your integration) "
            "and re-run."
        )
    return _finalize_join(
        io, config_ops, existing, merged_ids, token_env, project_name, interactive
    )


def _finalize_join(
    io: Any,
    config_ops: Any,
    existing: dict,
    db_ids: dict[str, str],
    token_env: str,
    project_name: str,
    interactive: bool,
) -> dict:
    """Write config for --join-existing flow (no databases_create call).

    Mirrors the post-create config-save block, but skips orphan-cleanup
    guidance (no DBs were created here, so nothing to orphan).
    """
    from brain_init import merge_brain_config

    if not project_name:
        default_name = os.path.basename(os.getcwd()) or "project"
        if interactive:
            entered = io.prompt(f"Project name [{default_name}]: ").strip()
            project_name = entered or default_name
        else:
            project_name = default_name

    registry_entry = brain_project_registry.register_project(project_name, os.getcwd())
    resolved_name = registry_entry["name"]
    if resolved_name != project_name:
        io.print(
            f"Project name {project_name!r} collides in the brain registry; "
            f"using {resolved_name!r} instead."
        )

    existing_names = list((existing.get("brain") or {}).get("project_names") or [])
    union_names = list(existing_names)
    for n in brain_project_registry.all_project_names():
        if n not in union_names:
            union_names.append(n)

    updates = {
        "enabled": True,
        "notion_integration_token_env": token_env,
        "database_ids": db_ids,
        "project_names": union_names,
    }
    new_cfg = merge_brain_config(existing, updates)
    config_ops.save(new_cfg)

    io.print(
        "\nJoined existing BRAIN databases. This project now shares knowledge "
        "with every other project pointed at the same 4 databases. Per-project "
        "privacy is enforced via Source Project Hash on each row.\n"
        "Next: run `.tausik/tausik brain sync` to pull existing data."
    )
    return {
        "parent_page_id": "",
        "token_env": token_env,
        "project_name": resolved_name,
        "database_ids": db_ids,
        "mode": "join",
    }
