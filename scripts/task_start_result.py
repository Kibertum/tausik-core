"""One bounded start result shared by CLI and MCP transports."""

from __future__ import annotations

import json
from typing import Any

from task_context_package import DEFAULT_MAX_BYTES, build_task_context_package


def start_with_context(
    svc: Any,
    slug: str,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> dict[str, Any]:
    """Start under QG-0, then attach context without hiding partial failure."""
    start = svc.task_start(slug, include_memory=False)
    result: dict[str, Any] = {
        "schema_version": 1,
        "ok": True,
        "started": True,
        "start": start,
    }
    try:
        result["context"] = build_task_context_package(svc, slug, max_bytes=max_bytes)
    except Exception as exc:  # noqa: BLE001 - activation committed; report partial state
        result["ok"] = False
        result["context"] = {
            "ok": False,
            "error": type(exc).__name__,
            "message": str(exc),
            "recovery": f".tausik/tausik task show {slug} --package",
        }
    return result


def serialize_start_with_context(
    svc: Any,
    slug: str,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> str:
    return json.dumps(
        start_with_context(svc, slug, max_bytes=max_bytes),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
