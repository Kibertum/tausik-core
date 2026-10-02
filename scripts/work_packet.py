"""One bounded retrieval packet for a task.

The composer is transport-free: CLI and MCP pass the same arguments here.  It
uses the existing task-context, project search and memory readers, and adds a
strict source reader whose addresses are project-relative and scope checked.
Nothing is shortened silently: whole optional units fit or receive an explicit
``omitted`` record.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from scope_acl import match_path
from task_context_package import MAX_MAX_BYTES, MIN_MAX_BYTES, build_task_context_package

DEFAULT_MAX_BYTES = 16_384
MAX_SOURCES = 16
RESULT_LIMIT = 5


def _json_bytes(value: Any) -> int:
    return len(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    )


def _set_exact_size(packet: dict[str, Any]) -> None:
    size = -1
    while packet.get("bytes") != size:
        packet["bytes"] = size
        size = _json_bytes(packet)


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if isinstance(item, str) and item.strip()]
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        decoded = json.loads(value)
    except ValueError:
        return []
    return [str(item) for item in decoded] if isinstance(decoded, list) else []


def _exclude_patterns(value: Any) -> list[str]:
    """Interpret path-shaped exclusions while harmless prose remains unmatched."""
    decoded = _list(value)
    if decoded:
        return decoded
    if not isinstance(value, str):
        return []
    return [part.strip() for part in re.split(r"[,;\n]+", value) if part.strip()]


def _normal_search_hit(group: str, row: dict[str, Any]) -> dict[str, Any]:
    if group == "tasks":
        ident = row.get("slug")
        label = row.get("title")
        address = f"task:{ident}"
    elif group == "decisions":
        ident = row.get("id")
        label = row.get("decision")
        address = f"decision:{ident}"
    else:
        ident = row.get("id")
        label = row.get("title")
        address = f"memory:{ident}"
    return {
        "address": address,
        "label": label,
        "snippet": row.get("_snippet") or "",
    }


def _normal_memory_hit(row: dict[str, Any]) -> dict[str, Any]:
    mid = row.get("id")
    source = row.get("source") or "project"
    if mid is not None and source == "project":
        address = f"memory:{mid}"
    else:
        identity = "\x00".join(
            str(row.get(key) or "") for key in ("origin_project", "title", "content")
        )
        digest = hashlib.sha256(identity.encode()).hexdigest()[:16]
        address = f"knowledge:{source}:{digest}"
    return {
        "address": address,
        "type": row.get("type"),
        "title": row.get("title"),
        "content": row.get("content"),
        "source": source,
    }


def _source_result(
    root: Path,
    raw: str,
    allowed: list[str],
    excluded: list[str],
    max_bytes: int,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    requested = str(raw).replace("\\", "/")
    try:
        path = (root / raw).resolve(strict=True)
        rel = path.relative_to(root).as_posix()
    except (OSError, ValueError):
        return None, {"address": f"file:{requested}", "reason": "unreadable_or_outside_project"}
    if not path.is_file():
        return None, {"address": f"file:{rel}", "reason": "not_a_regular_file"}
    if any(match_path(rel, [pattern]) for pattern in excluded):
        return None, {"address": f"file:{rel}", "reason": "scope_excluded"}
    if not match_path(rel, allowed):
        return None, {"address": f"file:{rel}", "reason": "out_of_task_scope"}
    try:
        with path.open("rb") as handle:
            raw_bytes = handle.read(max_bytes + 1)
        if len(raw_bytes) > max_bytes:
            return None, {"address": f"file:{rel}", "reason": "source_exceeds_packet_ceiling"}
        text = raw_bytes.decode("utf-8")
    except (OSError, UnicodeError):
        return None, {"address": f"file:{rel}", "reason": "unreadable_utf8"}
    line_count = max(1, text.count("\n") + (not text.endswith("\n")))
    return {
        "address": f"file:{rel}#L1-L{line_count}",
        "path": rel,
        "content": text,
        "content_bytes": len(raw_bytes),
    }, None


def _admit(
    packet: dict[str, Any],
    section: str,
    item: dict[str, Any],
    *,
    max_bytes: int,
    omitted: dict[str, Any],
) -> bool:
    candidate = dict(packet)
    candidate[section] = [*packet[section], item]
    candidate["omitted"] = [*packet["omitted"], omitted]
    _set_exact_size(candidate)
    if candidate["bytes"] > max_bytes:
        packet["overflow"] = True
        packet["omitted"].append(omitted)
        _set_exact_size(packet)
        if packet["bytes"] > max_bytes:
            raise ValueError("byte ceiling cannot hold required omission metadata")
        return False
    packet[section].append(item)
    return True


def _record_omission(packet: dict[str, Any], omission: dict[str, Any], *, max_bytes: int) -> None:
    packet["overflow"] = True
    packet["omitted"].append(omission)
    _set_exact_size(packet)
    if packet["bytes"] > max_bytes:
        raise ValueError("byte ceiling cannot hold required omission metadata")


def build_work_packet(
    svc: Any,
    slug: str,
    query: str | None,
    sources: list[str] | None = None,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> dict[str, Any]:
    """Compose task context, search, memory and source reads in one response."""
    if type(max_bytes) is not int or not MIN_MAX_BYTES <= max_bytes <= MAX_MAX_BYTES:
        raise ValueError(f"max_bytes must be {MIN_MAX_BYTES}..{MAX_MAX_BYTES}")
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be non-empty")
    requested_sources = list(sources or [])
    if len(requested_sources) > MAX_SOURCES:
        raise ValueError(f"at most {MAX_SOURCES} sources may be requested")
    if len(set(requested_sources)) != len(requested_sources):
        raise ValueError("source addresses must be unique")

    task = svc.task_show(slug)
    context_budget = max(MIN_MAX_BYTES, min(max_bytes // 2, 8_192))
    context = build_task_context_package(svc, slug, max_bytes=context_budget)
    if context["bytes"] > context_budget:
        raise ValueError("byte ceiling cannot hold the required task context")
    packet: dict[str, Any] = {
        "schema_version": 1,
        "task": slug,
        "query": query.strip(),
        "max_bytes": max_bytes,
        "allocations": {"task_context_max_bytes": context_budget},
        "bytes": 0,
        "overflow": bool(context.get("overflow")),
        "context": context,
        "search": [],
        "memory": [],
        "sources": [],
        "omitted": [],
    }
    if context.get("overflow"):
        packet["omitted"].append(
            {"address": "task-context:relevant_memory", "reason": "context_budget_exceeded"}
        )
    _set_exact_size(packet)
    if packet["bytes"] > max_bytes:
        raise ValueError("byte ceiling cannot hold the required packet metadata")

    results = svc.search(query.strip(), "all", RESULT_LIMIT + 1)
    packet["routing"] = {
        "search.memory": "deduplicated_into_memory_section",
    }
    for group in ("tasks", "decisions"):
        rows = results.get(group, [])
        if len(rows) > RESULT_LIMIT:
            _record_omission(
                packet,
                {
                    "address": f"search:{group}[{RESULT_LIMIT}:]",
                    "reason": "result_limit",
                    "count_at_least": len(rows) - RESULT_LIMIT,
                },
                max_bytes=max_bytes,
            )
        for row in rows[:RESULT_LIMIT]:
            item = _normal_search_hit(group, row)
            _admit(
                packet,
                "search",
                item,
                max_bytes=max_bytes,
                omitted={"address": item["address"], "reason": "packet_ceiling"},
            )

    memory_rows = svc.memory_search(query.strip())
    if len(memory_rows) > RESULT_LIMIT:
        _record_omission(
            packet,
            {
                "address": f"memory-search[{RESULT_LIMIT}:]",
                "reason": "result_limit",
                "count": len(memory_rows) - RESULT_LIMIT,
            },
            max_bytes=max_bytes,
        )
    for row in memory_rows[:RESULT_LIMIT]:
        item = _normal_memory_hit(row)
        _admit(
            packet,
            "memory",
            item,
            max_bytes=max_bytes,
            omitted={"address": item["address"], "reason": "packet_ceiling"},
        )

    root = Path(svc.tausik_dir()).parent.resolve(strict=True)
    allowed = [*_list(task.get("scope_paths")), *_list(task.get("relevant_files"))]
    excluded = _exclude_patterns(task.get("scope_exclude"))
    for source in requested_sources:
        source_item, refusal = _source_result(root, source, allowed, excluded, max_bytes)
        if refusal:
            _record_omission(packet, refusal, max_bytes=max_bytes)
            continue
        assert source_item is not None
        _admit(
            packet,
            "sources",
            source_item,
            max_bytes=max_bytes,
            omitted={
                "address": f"file:{source_item['path']}",
                "reason": "packet_ceiling",
            },
        )

    _set_exact_size(packet)
    if packet["bytes"] > max_bytes:
        raise ValueError("byte ceiling exceeded")
    return packet


def serialize_work_packet(
    svc: Any,
    slug: str,
    query: str | None,
    sources: list[str] | None = None,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> str:
    return json.dumps(
        build_work_packet(svc, slug, query, sources, max_bytes=max_bytes),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
