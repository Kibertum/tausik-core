"""Brain MCP write-path — build Notion payloads, scrub, create, mirror.

Pure-function core for the four `brain_store_*` MCP tools. The module
knows the shape of each Notion database (mirrors brain_sync._map_*)
and is responsible for:

  1) Composing the `pages.create` payload for the category.
  2) Running the concatenated text through `brain_scrubbing.scrub_with_config`.
     A block-severity match short-circuits the write and returns the
     formatted issue list.
  3) Calling `client.pages_create` and, on success, mirroring the
     returned page JSON into the local SQLite (brain_sync.map_page_to_row
     + upsert_page) for instant read-consistency.

Project hash resolution cascade:
  explicit arg > env TAUSIK_PROJECT_NAME > os.path.basename(cwd)

Design reference: references/brain-db-schema.md §3 + §5.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
from datetime import date as _date
from typing import Any, Callable

import brain_config
import brain_fallback
import brain_scrubbing
import brain_sync

CATEGORIES = ("decisions", "web_cache", "patterns", "gotchas")

_NOTION_RICH_TEXT_CHUNK = 2000  # Notion's per-block rich_text content limit


# ---- Project identity ----------------------------------------------------


def _resolve_project_name(explicit: str | None) -> str:
    if explicit and explicit.strip():
        return explicit.strip()
    env = os.environ.get("TAUSIK_PROJECT_NAME", "").strip()
    if env:
        return env
    return os.path.basename(os.getcwd()) or "unknown-project"


def compute_content_hash(content: str) -> str:
    """SHA256(content)[:16] — matches Source Project Hash sizing."""
    if not isinstance(content, str):
        raise TypeError("content must be a string")
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


# ---- Notion property helpers --------------------------------------------


def _chunk_rich_text(text: str | None) -> list[dict]:
    if not text:
        return []
    chunks: list[dict] = []
    for i in range(0, len(text), _NOTION_RICH_TEXT_CHUNK):
        chunk = text[i : i + _NOTION_RICH_TEXT_CHUNK]
        chunks.append({"text": {"content": chunk}})
    return chunks


def _title_prop(name: str) -> dict:
    if not name or not name.strip():
        raise ValueError("Name is required and cannot be empty")
    return {"title": [{"text": {"content": name}}]}


def _rich_text_prop(text: str | None) -> dict:
    return {"rich_text": _chunk_rich_text(text)}


def _multi_select_prop(names: list[str] | tuple[str, ...] | None) -> dict:
    if not names:
        return {"multi_select": []}
    out: list[dict] = []
    seen: set[str] = set()
    for n in names:
        if not isinstance(n, str):
            continue
        nv = n.strip()
        if not nv or nv in seen:
            continue
        out.append({"name": nv})
        seen.add(nv)
    return {"multi_select": out}


def _select_prop(name: str | None) -> dict | None:
    if name is None or not str(name).strip():
        return None
    return {"select": {"name": str(name).strip()}}


def _date_prop(iso: str | None) -> dict | None:
    if not iso:
        return None
    return {"date": {"start": iso}}


def _url_prop(url: str | None) -> dict | None:
    if not url:
        return None
    return {"url": url}


def _checkbox_prop(val: bool) -> dict:
    return {"checkbox": bool(val)}


def _number_prop(val: int | float | None) -> dict | None:
    if val is None:
        return None
    return {"number": val}


def _today_iso() -> str:
    return _date.today().isoformat()


def _clean_props(props: dict) -> dict:
    """Drop keys whose value is None (optional Notion props)."""
    return {k: v for k, v in props.items() if v is not None}


# ---- Per-category builders ----------------------------------------------


def build_properties_decision(
    *,
    name: str,
    decision: str,
    context: str = "",
    rationale: str = "",
    tags: list[str] | None = None,
    stack: list[str] | None = None,
    date: str | None = None,
    project_hash: str = "",
    generalizable: bool = True,
    superseded_by: str | None = None,
) -> dict:
    return _clean_props(
        {
            "Name": _title_prop(name),
            "Context": _rich_text_prop(context),
            "Decision": _rich_text_prop(decision),
            "Rationale": _rich_text_prop(rationale),
            "Tags": _multi_select_prop(tags),
            "Stack": _multi_select_prop(stack),
            "Date": _date_prop(date or _today_iso()),
            "Source Project Hash": _rich_text_prop(project_hash),
            "Generalizable": _checkbox_prop(generalizable),
            "Superseded By": _url_prop(superseded_by),
        }
    )


def build_properties_web_cache(
    *,
    name: str,
    url: str,
    content: str,
    query: str = "",
    fetched_at: str | None = None,
    ttl_days: int = 30,
    domain: str | None = None,
    tags: list[str] | None = None,
    project_hash: str = "",
    content_hash: str = "",
) -> dict:
    if not url:
        raise ValueError("url is required for web_cache")
    if not content:
        raise ValueError("content is required for web_cache")
    return _clean_props(
        {
            "Name": _title_prop(name),
            "URL": _url_prop(url),
            "Query": _rich_text_prop(query),
            "Content": _rich_text_prop(content),
            "Fetched At": _date_prop(fetched_at or _today_iso()),
            "TTL Days": _number_prop(ttl_days),
            "Domain": _select_prop(domain),
            "Tags": _multi_select_prop(tags),
            "Source Project Hash": _rich_text_prop(project_hash),
            "Content Hash": _rich_text_prop(content_hash),
        }
    )


def build_properties_pattern(
    *,
    name: str,
    description: str,
    when_to_use: str = "",
    example: str = "",
    tags: list[str] | None = None,
    stack: list[str] | None = None,
    date: str | None = None,
    project_hash: str = "",
    confidence: str | None = None,
) -> dict:
    return _clean_props(
        {
            "Name": _title_prop(name),
            "Description": _rich_text_prop(description),
            "When to Use": _rich_text_prop(when_to_use),
            "Example": _rich_text_prop(example),
            "Tags": _multi_select_prop(tags),
            "Stack": _multi_select_prop(stack),
            "Date": _date_prop(date or _today_iso()),
            "Source Project Hash": _rich_text_prop(project_hash),
            "Confidence": _select_prop(confidence),
        }
    )


def build_properties_gotcha(
    *,
    name: str,
    description: str,
    wrong_way: str = "",
    right_way: str = "",
    tags: list[str] | None = None,
    stack: list[str] | None = None,
    date: str | None = None,
    project_hash: str = "",
    severity: str | None = None,
    evidence_url: str | None = None,
) -> dict:
    return _clean_props(
        {
            "Name": _title_prop(name),
            "Description": _rich_text_prop(description),
            "Wrong Way": _rich_text_prop(wrong_way),
            "Right Way": _rich_text_prop(right_way),
            "Tags": _multi_select_prop(tags),
            "Stack": _multi_select_prop(stack),
            "Date": _date_prop(date or _today_iso()),
            "Source Project Hash": _rich_text_prop(project_hash),
            "Severity": _select_prop(severity),
            "Evidence URL": _url_prop(evidence_url),
        }
    )


_BUILDERS: dict[str, Callable[..., dict]] = {
    "decisions": build_properties_decision,
    "web_cache": build_properties_web_cache,
    "patterns": build_properties_pattern,
    "gotchas": build_properties_gotcha,
}


# ---- Scrubbing bridge ---------------------------------------------------


_TEXT_FIELDS_BY_CATEGORY = {
    "decisions": ("name", "context", "decision", "rationale"),
    "web_cache": ("name", "content", "query", "url"),
    "patterns": ("name", "description", "when_to_use", "example"),
    "gotchas": ("name", "description", "wrong_way", "right_way"),
}


def scrub_inputs(category: str, fields: dict, cfg: dict) -> dict:
    """Join text fields and run scrub_with_config (union with global registry)."""
    keys = _TEXT_FIELDS_BY_CATEGORY.get(category, ())
    joined = "\n".join(str(fields.get(k) or "") for k in keys)
    return brain_scrubbing.scrub_with_config(joined, cfg, union_with_registry=True)


# ---- Orchestration ------------------------------------------------------


def store_record(
    client: Any,
    conn: sqlite3.Connection,
    category: str,
    fields: dict,
    cfg: dict,
    *,
    project_name: str | None = None,
) -> dict:
    """End-to-end write: scrub → Notion create → local mirror upsert.

    Returns one of:
      {"status": "scrub_blocked", "issues": [...]}
      {"status": "notion_error", "error": str}
      {"status": "ok", "notion_page_id": str, "source_project_hash": str}
    """
    if category not in _BUILDERS:
        return {"status": "bad_category", "error": f"Unknown category: {category!r}"}

    scrub = scrub_inputs(category, fields, cfg)
    if not scrub["ok"]:
        return {"status": "scrub_blocked", "issues": scrub["issues"]}

    project_name_resolved = _resolve_project_name(project_name)
    project_hash = brain_config.compute_project_hash(project_name_resolved)
    effective = dict(fields)
    effective["project_hash"] = project_hash

    if category == "web_cache":
        effective.setdefault(
            "content_hash", compute_content_hash(effective.get("content") or "")
        )

    db_ids = cfg.get("database_ids") or {}
    db_id = db_ids.get(category)
    if not db_id:
        return {
            "status": "config_error",
            "error": f"brain.database_ids.{category} is empty",
        }

    try:
        properties = _BUILDERS[category](**effective)
    except (TypeError, ValueError) as e:
        return {"status": "bad_fields", "error": str(e)}

    try:
        page = client.pages_create(parent={"database_id": db_id}, properties=properties)
    except Exception as e:  # noqa: BLE001
        return {
            "status": "notion_error",
            "error_category": brain_fallback.classify_error(e),
            "error": str(e),
            "retry_after": brain_fallback.retry_after_from(e),
        }

    try:
        row = brain_sync.map_page_to_row(category, page)
        brain_sync.upsert_page(conn, category, row)
        conn.commit()
    except Exception as e:  # noqa: BLE001
        return {
            "status": "ok_not_mirrored",
            "notion_page_id": page.get("id", ""),
            "source_project_hash": project_hash,
            "warning": f"Notion write succeeded but local mirror failed: {e}",
        }

    return {
        "status": "ok",
        "notion_page_id": page.get("id", ""),
        "source_project_hash": project_hash,
    }


# ---- Markdown renderer --------------------------------------------------


def format_store_result(result: dict, category: str) -> str:
    status = result.get("status")
    if status == "ok":
        return (
            f"**Stored** in `{category}`.\n\n"
            f"- id: `{result.get('notion_page_id')}`\n"
            f"- project: `{result.get('source_project_hash')}`"
        )
    if status == "ok_not_mirrored":
        return (
            f"**Stored** in Notion but local mirror lagged.\n\n"
            f"- id: `{result.get('notion_page_id')}`\n"
            f"- warning: {result.get('warning')}"
        )
    if status == "scrub_blocked":
        return brain_scrubbing.format_issues(result.get("issues") or [])
    if status == "notion_error":
        cat = result.get("error_category") or "unknown"
        return brain_fallback.user_message(
            cat,
            op="store",
            detail=result.get("error") or "",
            retry_after=result.get("retry_after"),
        )
    if status == "config_error":
        return f"**Config error.** {result.get('error')}"
    if status == "bad_fields":
        return f"**Invalid fields.** {result.get('error')}"
    if status == "bad_category":
        return f"**Unknown category.** {result.get('error')}"
    return f"Unexpected result: {result!r}"
