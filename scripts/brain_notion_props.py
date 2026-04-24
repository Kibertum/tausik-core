"""Notion property readers + per-category page→row mappers.

Extracted from brain_sync.py to keep that module under the 400-line
filesize gate. Pure functions: given a Notion page JSON object, return
the row dict that upsert_page writes into the brain_* tables.

Convention: the whitelist in brain_sync._ALLOWED_COLS_OF is the source
of truth for allowed row keys — these mappers must stay in sync with it.
"""

from __future__ import annotations

import json


# --- Notion property readers -----------------------------------------


def _concat_text(items: list | None) -> str:
    if not items:
        return ""
    return "".join(item.get("plain_text", "") for item in items)


def _read_prop(page: dict, name: str) -> dict:
    return (page.get("properties") or {}).get(name) or {}


def _prop_title(page: dict, name: str) -> str:
    return _concat_text(_read_prop(page, name).get("title"))


def _prop_rich_text(page: dict, name: str) -> str:
    return _concat_text(_read_prop(page, name).get("rich_text"))


def _prop_multi_select(page: dict, name: str) -> str:
    items = _read_prop(page, name).get("multi_select") or []
    return json.dumps([x.get("name") for x in items if x.get("name")])


def _prop_select(page: dict, name: str) -> str | None:
    sel = _read_prop(page, name).get("select")
    if not sel:
        return None
    val = sel.get("name")
    return val if isinstance(val, str) else None


def _prop_date(page: dict, name: str) -> str | None:
    d = _read_prop(page, name).get("date")
    if not d:
        return None
    val = d.get("start")
    return val if isinstance(val, str) else None


def _prop_checkbox(page: dict, name: str, default: int = 0) -> int:
    val = _read_prop(page, name).get("checkbox")
    if val is None:
        return default
    return 1 if val else 0


def _prop_url(page: dict, name: str) -> str | None:
    return _read_prop(page, name).get("url") or None


def _prop_number(page: dict, name: str) -> float | int | None:
    val = _read_prop(page, name).get("number")
    return val


# --- Mappers ---------------------------------------------------------


def map_decision(page: dict) -> dict:
    return {
        "name": _prop_title(page, "Name"),
        "context": _prop_rich_text(page, "Context"),
        "decision": _prop_rich_text(page, "Decision"),
        "rationale": _prop_rich_text(page, "Rationale"),
        "tags": _prop_multi_select(page, "Tags"),
        "stack": _prop_multi_select(page, "Stack"),
        "date_value": _prop_date(page, "Date"),
        "source_project_hash": _prop_rich_text(page, "Source Project Hash"),
        "generalizable": _prop_checkbox(page, "Generalizable", default=1),
        "superseded_by": _prop_url(page, "Superseded By"),
    }


def map_web_cache(page: dict) -> dict:
    ttl = _prop_number(page, "TTL Days")
    return {
        "name": _prop_title(page, "Name"),
        "url": _prop_url(page, "URL"),
        "query": _prop_rich_text(page, "Query"),
        "content": _prop_rich_text(page, "Content"),
        "fetched_at": _prop_date(page, "Fetched At") or "",
        "ttl_days": int(ttl) if ttl is not None else 30,
        "domain": _prop_select(page, "Domain"),
        "tags": _prop_multi_select(page, "Tags"),
        "source_project_hash": _prop_rich_text(page, "Source Project Hash"),
        "content_hash": _prop_rich_text(page, "Content Hash"),
    }


def map_pattern(page: dict) -> dict:
    return {
        "name": _prop_title(page, "Name"),
        "description": _prop_rich_text(page, "Description"),
        "when_to_use": _prop_rich_text(page, "When to Use"),
        "example": _prop_rich_text(page, "Example"),
        "tags": _prop_multi_select(page, "Tags"),
        "stack": _prop_multi_select(page, "Stack"),
        "source_project_hash": _prop_rich_text(page, "Source Project Hash"),
        "date_value": _prop_date(page, "Date"),
        "confidence": _prop_select(page, "Confidence"),
    }


def map_gotcha(page: dict) -> dict:
    return {
        "name": _prop_title(page, "Name"),
        "description": _prop_rich_text(page, "Description"),
        "wrong_way": _prop_rich_text(page, "Wrong Way"),
        "right_way": _prop_rich_text(page, "Right Way"),
        "tags": _prop_multi_select(page, "Tags"),
        "stack": _prop_multi_select(page, "Stack"),
        "source_project_hash": _prop_rich_text(page, "Source Project Hash"),
        "date_value": _prop_date(page, "Date"),
        "severity": _prop_select(page, "Severity"),
        "evidence_url": _prop_url(page, "Evidence URL"),
    }


MAPPERS_BY_CATEGORY = {
    "decisions": map_decision,
    "web_cache": map_web_cache,
    "patterns": map_pattern,
    "gotchas": map_gotcha,
}
