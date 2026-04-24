"""tausik-brain MCP handlers — dispatch calls to brain_mcp_read helpers.

Connection + client setup lives in `brain_runtime.open_brain_deps` so
the same contract is shared with service_knowledge, the PostToolUse
WebFetch hook, and the cursor sibling of this module.
"""

from __future__ import annotations

import os
import sys

_SCRIPTS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "scripts")
)
if os.path.isdir(_SCRIPTS_DIR):
    if _SCRIPTS_DIR not in sys.path:
        sys.path.insert(0, _SCRIPTS_DIR)
else:
    print(
        f"[tausik-brain] scripts dir missing: {_SCRIPTS_DIR}",
        file=sys.stderr,
    )

import brain_mcp_read  # noqa: E402
import brain_mcp_write  # noqa: E402
from brain_runtime import open_brain_deps as _open_deps  # noqa: E402


def _not_configured_msg() -> str:
    return (
        "_Brain is not enabled in this project._\n\n"
        "To enable: run `.tausik/tausik brain init` — it creates the 4 "
        "Notion databases and writes `.tausik/config.json` for you. "
        "Non-interactive flags: `--parent-page-id X --token-env Y "
        "--project-name Z --yes --non-interactive`."
    )


def _token_missing_warning(cfg: dict) -> str:
    env_name = (cfg.get("notion_integration_token_env") or "").strip()
    if env_name:
        return (
            f"Brain integration token is not set (env var `{env_name}` is empty). "
            "Notion fallback disabled — only local mirror results shown. "
            f"Set `{env_name}` to enable Notion fallback and writes."
        )
    return (
        "Brain integration token is not set (no `notion_integration_token_env` "
        "configured). Notion fallback disabled — only local mirror results shown."
    )


def handle_brain_search(args: dict) -> str:
    query = (args.get("query") or "").strip()
    if not query:
        return "_brain_search: query is empty._"
    conn, client, cfg = _open_deps()
    if not cfg.get("enabled") or conn is None:
        return _not_configured_msg()
    category = args.get("category")
    categories = [category] if category else None
    try:
        limit = int(args.get("limit") or 10)
    except (TypeError, ValueError):
        limit = 10
    enable_fallback = bool(args.get("use_notion_fallback", True))

    result = brain_mcp_read.search_with_fallback(
        conn,
        client,
        query,
        categories=categories,
        limit=limit,
        database_ids=cfg.get("database_ids"),
        enable_fallback=enable_fallback,
    )
    warnings = list(result["warnings"])
    if client is None:
        warnings.insert(0, _token_missing_warning(cfg))
    return brain_mcp_read.format_search_results(
        result["results"], warnings, query=query
    )


def handle_brain_get(args: dict) -> str:
    notion_page_id = (args.get("id") or "").strip()
    category = args.get("category") or ""
    if not notion_page_id or not category:
        return "_brain_get: `id` and `category` are required._"
    conn, client, cfg = _open_deps()
    if not cfg.get("enabled") or conn is None:
        return _not_configured_msg()
    enable_fallback = bool(args.get("use_notion_fallback", True))

    rec, warnings = brain_mcp_read.get_with_fallback(
        conn,
        client,
        notion_page_id,
        category,
        enable_fallback=enable_fallback,
    )
    warnings = list(warnings)
    if client is None:
        warnings.insert(0, _token_missing_warning(cfg))
    if rec is None:
        tail = "\n".join(f"- {w}" for w in warnings)
        head = f"_No record: category=`{category}`, id=`{notion_page_id}`._"
        return f"{head}\n\n{tail}" if tail else head
    body = brain_mcp_read.format_record(rec)
    if warnings:
        body += "\n\n" + "\n".join(f"- {w}" for w in warnings)
    return body


_STORE_CATEGORY_BY_TOOL = {
    "brain_store_decision": "decisions",
    "brain_store_pattern": "patterns",
    "brain_store_gotcha": "gotchas",
    "brain_cache_web": "web_cache",
}


def _extract_fields(tool_name: str, args: dict) -> dict:
    """Pass-through dict trimmed to non-None values; drops project_name."""
    return {k: v for k, v in args.items() if k != "project_name" and v is not None}


def _handle_store(tool_name: str, args: dict) -> str:
    category = _STORE_CATEGORY_BY_TOOL[tool_name]
    conn, client, cfg = _open_deps()
    if not cfg.get("enabled") or conn is None:
        return _not_configured_msg()
    if client is None:
        return (
            "_Brain integration token is not set in env. "
            "Set the env var named by `brain.notion_integration_token_env` "
            "and retry._"
        )
    fields = _extract_fields(tool_name, args)
    project_name = args.get("project_name")
    result = brain_mcp_write.store_record(
        client, conn, category, fields, cfg, project_name=project_name
    )
    return brain_mcp_write.format_store_result(result, category)


def handle_brain_store_decision(args: dict) -> str:
    return _handle_store("brain_store_decision", args)


def handle_brain_store_pattern(args: dict) -> str:
    return _handle_store("brain_store_pattern", args)


def handle_brain_store_gotcha(args: dict) -> str:
    return _handle_store("brain_store_gotcha", args)


def handle_brain_cache_web(args: dict) -> str:
    return _handle_store("brain_cache_web", args)


def handle_tool(name: str, args: dict) -> str:
    if name == "brain_search":
        return handle_brain_search(args)
    if name == "brain_get":
        return handle_brain_get(args)
    if name in _STORE_CATEGORY_BY_TOOL:
        return _handle_store(name, args)
    return f"Unknown tool: {name}"
