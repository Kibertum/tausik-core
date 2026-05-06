"""Create-new-DBs branch for the brain init wizard.

Extracted from scripts/brain_init.py (v14b-followup-brain-init-filesize-debt)
to keep that module under the 400-line filesize gate. Pure structural split —
no semantic changes. Imports from brain_init are deferred to function-call
time to avoid a load-order cycle (brain_init imports brain_init_create only
inside run_wizard).
"""

from __future__ import annotations

import os
from typing import Any

import brain_project_registry
from brain_notion_client import NotionError


def run_create_branch(
    io: Any,
    config_ops: Any,
    existing: dict,
    client: Any,
    args: dict,
    parent_page_id: str,
    project_name: str,
    discovered: dict[str, str],
    force_create: bool,
    interactive: bool,
    token_env: str,
) -> dict:
    """--force-create OR clean-workspace branch of run_wizard.

    Prompts for missing parent_page_id / project_name in interactive mode,
    confirms with the user (unless --yes), creates 4 Notion databases,
    registers the project, merges + saves config. Raises WizardError on
    any failure (also surfaces orphan-cleanup guidance for partial creates
    or post-create save failures).
    """
    from brain_init import (
        WizardError,
        _print_orphan_cleanup_guidance,
        create_brain_databases,
        merge_brain_config,
    )
    from brain_init import PartialCreateError

    if not parent_page_id:
        if not interactive:
            raise WizardError("--parent-page-id is required in non-interactive mode")
        io.print(
            "\nParent page: open the Notion page where the 4 BRAIN databases will be\n"
            "created, then copy the 32-char page ID from the URL.\n"
            "  Example URL:  https://www.notion.so/your-workspace/Brain-1234abcd5678ef901234abcd5678ef90\n"
            "  Page ID:      1234abcd5678ef901234abcd5678ef90\n"
            "Make sure you've shared this page with the integration ('...' → 'Connections')."
        )
        parent_page_id = io.prompt("Notion parent page ID: ").strip()
        if not parent_page_id:
            raise WizardError("parent_page_id cannot be empty")

    if not project_name:
        default_name = os.path.basename(os.getcwd()) or "project"
        if interactive:
            entered = io.prompt(f"Project name [{default_name}]: ").strip()
            project_name = entered or default_name
        else:
            project_name = default_name

    if interactive and not args.get("yes"):
        if force_create and discovered:
            io.print(
                "\n⚠ --force-create: existing canonical BRAIN databases were "
                "detected in this workspace, but you asked to create new ones "
                "anyway. This will produce TWO independent brains in the same "
                "workspace — projects pointed at one will not see records "
                "from the other."
            )
        io.print(
            "\nAbout to create 4 Notion databases under the parent page and "
            "write .tausik/config.json. The token itself is NOT saved — only "
            "the env var name."
        )
        confirm = io.prompt("Proceed? [y/N]: ").strip().lower()
        if confirm not in ("y", "yes"):
            raise WizardError("Aborted by user.")

    io.print(f"Creating 4 Notion databases under page {parent_page_id}…")
    try:
        db_ids = create_brain_databases(client, parent_page_id)
    except PartialCreateError as e:
        # Surface real created_ids so user can archive partial orphans
        _print_orphan_cleanup_guidance(io, e.created_ids, e)
        raise WizardError(
            f"Notion databases_create partially failed: {e}. See orphan cleanup guidance above."
        ) from e
    except NotionError as e:
        raise WizardError(f"Notion databases_create failed: {e}") from e

    try:
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
    except Exception as e:
        _print_orphan_cleanup_guidance(io, db_ids, e)
        raise WizardError(
            f"Post-create step failed ({type(e).__name__}): {e}. "
            f"The 4 Notion databases were created but config was NOT saved — "
            f"see the cleanup guidance above to archive them manually."
        ) from e

    io.print("Brain configured. Next: run `.tausik/tausik brain sync` to pull existing data.")
    return {
        "parent_page_id": parent_page_id,
        "token_env": token_env,
        "project_name": resolved_name,
        "database_ids": db_ids,
        "mode": "create",
    }
