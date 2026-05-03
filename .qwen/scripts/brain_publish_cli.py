"""CLI entrypoints for `tausik brain draft` and `tausik brain publish`."""

from __future__ import annotations

import json
import sys
from typing import Any


def cmd_brain_draft(args: Any) -> None:
    import brain_config
    import brain_publish_flow

    try:
        payload = brain_publish_flow.load_payload_from_cli(args)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)
    kind = payload.pop("kind", None)
    if not kind:
        print('Error: JSON must include "kind": "pattern" or "gotcha"', file=sys.stderr)
        sys.exit(2)
    try:
        cat = brain_publish_flow.category_from_kind(str(kind))
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)
    cfg = brain_config.load_brain()
    out = brain_publish_flow.draft_artifact_publish(cat, payload, cfg)
    print(brain_publish_flow.format_draft_report(out))


def cmd_brain_publish(args: Any) -> None:
    import os

    import brain_config
    import brain_mcp_write
    import brain_publish_flow
    import brain_sync
    from brain_notion_client import NotionClient
    from project_config import load_config

    cfg_full = load_config() or {}
    brain = cfg_full.get("brain") or {}
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
    token = os.environ.get(token_env, "")
    if not token:
        print(
            f"Error: env var {token_env!r} is not set.",
            file=sys.stderr,
        )
        sys.exit(2)
    try:
        payload = brain_publish_flow.load_payload_from_cli(args)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)
    kind = payload.pop("kind", None)
    if not kind:
        print('Error: JSON must include "kind": "pattern" or "gotcha"', file=sys.stderr)
        sys.exit(2)
    try:
        cat = brain_publish_flow.category_from_kind(str(kind))
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

    cfg = brain_config.load_brain()
    db_ids = cfg.get("database_ids") or {}
    if not db_ids.get(cat):
        print(f"Error: brain.database_ids.{cat} is empty.", file=sys.stderr)
        sys.exit(2)

    from brain_config import get_brain_mirror_path

    conn = brain_sync.open_brain_db(get_brain_mirror_path())
    try:
        client = NotionClient(token)
        confirm = bool(getattr(args, "confirm_high_risk", False))
        result = brain_mcp_write.store_record(
            client,
            conn,
            cat,
            payload,
            cfg,
            confirm_high_risk=confirm,
        )
    finally:
        conn.close()
    txt = brain_mcp_write.format_store_result(result, cat)
    print(txt)
    if result.get("status") not in ("ok", "ok_not_mirrored"):
        sys.exit(1)
