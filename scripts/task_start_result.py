"""One bounded start result shared by CLI and MCP transports."""

from __future__ import annotations

import json
from typing import Any

from task_context_package import DEFAULT_MAX_BYTES, load_task_context_package


def start_with_context(
    svc: Any,
    slug: str,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    execution_lease_id: int | None = None,
) -> dict[str, Any]:
    """Atomically start and return the package persisted by the transition."""
    start = svc.task_start(
        slug,
        include_memory=False,
        package_max_bytes=max_bytes,
        execution_lease_id=execution_lease_id,
    )
    result: dict[str, Any] = {
        "schema_version": 1,
        "ok": True,
        "started": True,
        "start": start,
    }
    context = load_task_context_package(svc, slug)
    if context is None:
        # memory-only intentionally keeps the legacy light start path.
        from task_context_package import build_task_context_package

        context = build_task_context_package(svc, slug, max_bytes=max_bytes)
    result["context"] = context
    return result


def serialize_start_with_context(
    svc: Any,
    slug: str,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    execution_lease_id: int | None = None,
) -> str:
    return json.dumps(
        start_with_context(svc, slug, max_bytes=max_bytes, execution_lease_id=execution_lease_id),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
