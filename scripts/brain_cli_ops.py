"""`tausik brain` CLI — extracted from project_cli_ops for filesize gate."""

from __future__ import annotations

import sys
from typing import Any

from project_service import ProjectService


def cmd_brain(svc: ProjectService, args: Any) -> None:
    """`tausik brain <subcommand>` — init wizard, status."""
    sub = getattr(args, "brain_cmd", None)
    if sub == "draft":
        import brain_publish_cli

        brain_publish_cli.cmd_brain_draft(args)
        return
    if sub == "publish":
        import brain_publish_cli

        brain_publish_cli.cmd_brain_publish(args)
        return
    if sub == "status":
        import json as _json

        import brain_status

        snapshot = brain_status.collect_status()
        if getattr(args, "as_json", False):
            print(_json.dumps(snapshot, indent=2, ensure_ascii=False))
        else:
            print(brain_status.format_status(snapshot))
        return
    if sub == "sync":
        import json as _json
        import os as _os

        import brain_config
        import brain_sync
        from brain_notion_client import NotionClient
        from project_config import load_config

        cfg = load_config() or {}
        brain = cfg.get("brain") or {}
        if not brain.get("enabled"):
            print(
                "Error: brain is not configured in this project. "
                "Run `.tausik/tausik brain init` first.",
                file=sys.stderr,
            )
            sys.exit(2)
        token_env = brain.get("notion_integration_token_env") or str(
            brain_config.DEFAULT_BRAIN["notion_integration_token_env"]
        )
        token = _os.environ.get(token_env, "")
        if not token:
            print(
                f"Error: env var {token_env!r} is not set.\n"
                "  Export your Notion integration token and re-run "
                "`.tausik/tausik brain sync`.",
                file=sys.stderr,
            )
            sys.exit(2)
        db_ids = brain.get("database_ids") or {}
        category_filter = getattr(args, "category", None)
        if category_filter:
            db_ids = {category_filter: db_ids.get(category_filter)}
            if not db_ids[category_filter]:
                print(
                    f"Error: no database_id for category {category_filter!r} in config.",
                    file=sys.stderr,
                )
                sys.exit(2)
        client = NotionClient(token)
        from brain_config import get_brain_mirror_path

        conn = brain_sync.open_brain_db(get_brain_mirror_path())
        try:
            results = brain_sync.sync_all(client, conn, db_ids)
        finally:
            conn.close()
        if getattr(args, "as_json", False):
            print(_json.dumps(results, indent=2, ensure_ascii=False))
        else:
            print("Brain sync results:")
            had_error = False
            for cat, payload in results.items():
                if "error" in payload:
                    had_error = True
                    print(f"  {cat:>10}: ERROR — {payload['error']}")
                else:
                    pulled = payload.get("upserted", payload.get("fetched", 0))
                    print(f"  {cat:>10}: pulled {pulled}")
            if had_error:
                sys.exit(1)
        return
    if sub == "move":
        import json as _json

        import brain_move

        if getattr(args, "to_brain", False):
            kind = getattr(args, "kind", None)
            if not kind:
                print("Error: --kind is required with --to-brain", file=sys.stderr)
                sys.exit(2)
            try:
                src_id = int(args.source_id)
            except (TypeError, ValueError):
                print(
                    f"Error: source_id must be an integer, got {args.source_id!r}",
                    file=sys.stderr,
                )
                sys.exit(2)
            result = brain_move.move_to_brain(svc, kind, src_id, keep_source=args.keep_source)
        else:
            cat = getattr(args, "category", None)
            if not cat:
                print("Error: --category is required with --to-local", file=sys.stderr)
                sys.exit(2)
            result = brain_move.move_to_local(
                svc,
                args.source_id,
                cat,
                force=args.force,
                keep_source=args.keep_source,
            )
        print(_json.dumps(result, indent=2, ensure_ascii=False))
        if result.get("status") not in ("ok",):
            sys.exit(1 if result.get("status") in ("failed", "not_found") else 0)
        return
    if sub != "init":
        print(
            "Usage:\n"
            "  tausik brain init [--parent-page-id X] [--token-env Y] "
            "[--project-name Z] [--yes] [--force] [--non-interactive]\n"
            "                    [--join-existing [--decisions-id ID "
            "--web-cache-id ID --patterns-id ID --gotchas-id ID]]\n"
            "                    [--force-create]\n"
            "  tausik brain status [--json]\n"
            "  tausik brain sync   [--category decisions|patterns|gotchas|web_cache] [--json]\n"
            "  tausik brain draft   [--json TEXT | --file PATH]\n"
            "  tausik brain publish [--json TEXT | --file PATH] [--confirm-high-risk]\n"
            "  tausik brain move   <source_id> --to-brain --kind ... | --to-local --category ...",
            file=sys.stderr,
        )
        sys.exit(1)

    import brain_init
    from brain_notion_client import NotionClient
    from project_config import load_config, save_config

    class _ConfigOps:
        def load(self) -> dict:
            return load_config()

        def save(self, cfg: dict) -> None:
            save_config(cfg)

    def _factory(token: str):
        return NotionClient(token)

    interactive = None
    if getattr(args, "non_interactive", False):
        interactive = False

    wizard_args = {
        "parent_page_id": getattr(args, "parent_page_id", None),
        "token_env": getattr(args, "token_env", None),
        "project_name": getattr(args, "project_name", None),
        "yes": getattr(args, "yes", False),
        "force": getattr(args, "force", False),
        "interactive": interactive,
        "join_existing": getattr(args, "join_existing", False),
        "force_create": getattr(args, "force_create", False),
        "decisions_id": getattr(args, "decisions_id", None),
        "web_cache_id": getattr(args, "web_cache_id", None),
        "patterns_id": getattr(args, "patterns_id", None),
        "gotchas_id": getattr(args, "gotchas_id", None),
    }

    try:
        result = brain_init.run_wizard(wizard_args, brain_init.CliIO(), _factory, _ConfigOps())
    except brain_init.WizardError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    mode = result.get("mode", "create")
    if mode == "join":
        print("\nBrain joined existing workspace databases.")
    else:
        print("\nBrain initialized.")
        print(f"  parent_page_id: {result['parent_page_id']}")
    print(f"  token_env:      {result['token_env']}")
    print(f"  project_name:   {result['project_name']}")
    for cat, db_id in result["database_ids"].items():
        print(f"  {cat:>10}: {db_id}")
