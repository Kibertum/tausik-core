"""Move records between local TAUSIK store and shared brain.

`move_to_brain(svc, kind, source_id, *, keep_source)` — pulls a local
decision/pattern/gotcha and writes it to the brain via
`brain_mcp_write.store_record`. On success deletes the local row unless
`keep_source=True`.

`move_to_local(svc, notion_page_id, category, *, force, keep_source)` — pulls
a brain row by notion_page_id (decisions/patterns/gotchas only — `web_cache`
has no local counterpart and is refused) and writes it to local TAUSIK
(`decisions` table for decisions, `memory` table for patterns/gotchas).

Cross-project ownership: `move_to_local` refuses when the brain row's
`source_project_hash` doesn't match the current project's hash, unless
`force=True`. Prevents one project from "claiming" another project's
brain data accidentally.

Stack-agnostic, stdlib + brain_mcp_write only.
"""

from __future__ import annotations

import json
import os
import sqlite3
from typing import Any

import brain_config
import brain_mcp_write
import brain_runtime

VALID_TO_BRAIN_KINDS = ("decision", "pattern", "gotcha")
VALID_TO_LOCAL_CATEGORIES = ("decisions", "patterns", "gotchas")
_BRAIN_TABLES = {
    "decisions": "brain_decisions",
    "patterns": "brain_patterns",
    "gotchas": "brain_gotchas",
}


# --- helpers --------------------------------------------------------------


def _current_project_hash() -> str:
    """SHA256[:16] of the current project's canonical name."""
    name = (
        os.environ.get("TAUSIK_PROJECT_NAME")
        or os.path.basename(os.getcwd())
        or "project"
    )
    return brain_config.compute_project_hash(name)


def _decision_to_brain_fields(row: dict) -> dict:
    """Map a local decisions row → brain decision fields."""
    text = (row.get("decision") or "").strip()
    rationale = (row.get("rationale") or "").strip()
    name = text[:90] if text else f"Decision #{row.get('id')}"
    return {
        "name": name,
        "decision": text,
        "rationale": rationale,
        "context": "",
        "tags": [],
        "stack": [],
        "generalizable": True,
    }


def _memory_to_brain_fields(row: dict) -> dict:
    """Map a local memory row (pattern or gotcha) → brain fields."""
    title = (row.get("title") or "").strip() or f"Memory #{row.get('id')}"
    content = (row.get("content") or "").strip()
    tags_raw = row.get("tags")
    try:
        tags = json.loads(tags_raw) if tags_raw else []
    except (TypeError, ValueError):
        tags = []
    fields: dict[str, Any] = {
        "name": title,
        "tags": tags if isinstance(tags, list) else [],
        "stack": [],
    }
    if (row.get("type") or "") == "pattern":
        fields.update({"description": content, "when_to_use": "", "example": ""})
    else:
        fields.update({"description": content, "wrong_way": "", "right_way": ""})
    return fields


def _kind_to_category(kind: str) -> str:
    return {"decision": "decisions", "pattern": "patterns", "gotcha": "gotchas"}[kind]


def _read_brain_row(
    conn: sqlite3.Connection, category: str, notion_page_id: str
) -> dict | None:
    table = _BRAIN_TABLES[category]
    cur = conn.execute(
        f"SELECT * FROM {table} WHERE notion_page_id = ?", (notion_page_id,)
    )
    row = cur.fetchone()
    if row is None:
        return None
    return dict(row) if not isinstance(row, dict) else row


# --- to-brain -------------------------------------------------------------


def move_to_brain(
    svc, kind: str, source_id: int, *, keep_source: bool = False
) -> dict[str, Any]:
    """Move a local row into the brain. See module docstring for contract."""
    if kind not in VALID_TO_BRAIN_KINDS:
        return {
            "status": "bad_input",
            "reason": f"kind must be one of {VALID_TO_BRAIN_KINDS}, got {kind!r}",
        }

    if kind == "decision":
        row = svc.be.decision_get(int(source_id))
    else:
        # patterns + gotchas live in `memory` table
        row = svc.be._q1("SELECT * FROM memory WHERE id = ?", (int(source_id),))
        if row and (row.get("type") or "") not in (kind, kind + "s"):
            return {
                "status": "bad_input",
                "reason": f"memory row #{source_id} type='{row.get('type')}' "
                f"!= kind='{kind}'",
            }
    if row is None:
        return {"status": "not_found", "reason": f"local {kind} #{source_id}"}

    conn, client, cfg = brain_runtime.open_brain_deps()
    if conn is None or not cfg.get("enabled"):
        return {"status": "failed", "reason": "brain disabled"}
    if client is None:
        return {"status": "failed", "reason": "Notion token env var not set"}

    fields = (
        _decision_to_brain_fields(row)
        if kind == "decision"
        else _memory_to_brain_fields(row)
    )
    category = _kind_to_category(kind)
    result = brain_mcp_write.store_record(client, conn, category, fields, cfg)
    if result.get("status") not in ("ok", "ok_not_mirrored"):
        # scrub_blocked / notion_error / config_error / bad_fields → keep source
        return {
            "status": "skipped"
            if result.get("status") == "scrub_blocked"
            else "failed",
            "reason": result.get("status") or "unknown",
            "store_result": result,
        }
    if not keep_source:
        if kind == "decision":
            svc.be._ex("DELETE FROM decisions WHERE id = ?", (int(source_id),))
        else:
            svc.be._ex("DELETE FROM memory WHERE id = ?", (int(source_id),))
    return {
        "status": "ok",
        "notion_page_id": result.get("notion_page_id"),
        "category": category,
        "source_kept": keep_source,
    }


# --- to-local -------------------------------------------------------------


def move_to_local(
    svc,
    notion_page_id: str,
    category: str,
    *,
    force: bool = False,
    keep_source: bool = False,
) -> dict[str, Any]:
    """Move a brain row into local TAUSIK. See module docstring for contract."""
    if category == "web_cache":
        return {
            "status": "bad_input",
            "reason": "web_cache has no local counterpart; refused",
        }
    if category not in VALID_TO_LOCAL_CATEGORIES:
        return {
            "status": "bad_input",
            "reason": f"category must be one of {VALID_TO_LOCAL_CATEGORIES} "
            f"or web_cache, got {category!r}",
        }

    conn, client, cfg = brain_runtime.open_brain_deps()
    if conn is None or not cfg.get("enabled"):
        return {"status": "failed", "reason": "brain disabled"}

    row = _read_brain_row(conn, category, notion_page_id)
    if row is None:
        return {
            "status": "not_found",
            "reason": f"brain {category} notion_page_id={notion_page_id}",
        }

    src_hash = (row.get("source_project_hash") or "").strip()
    cur_hash = _current_project_hash()
    if src_hash and src_hash != cur_hash and not force:
        return {
            "status": "skipped",
            "reason": (
                f"source_project_hash {src_hash[:8]} != current {cur_hash[:8]}; "
                "use --force to override (you'll claim another project's record)"
            ),
        }

    # Map brain row → local insert
    if category == "decisions":
        text = (row.get("decision") or row.get("name") or "").strip()
        local_id = svc.be.decision_add(text, rationale=row.get("rationale") or None)
    else:
        title = (row.get("name") or "").strip() or "(untitled)"
        body = (row.get("description") or "").strip()
        try:
            tags_raw = row.get("tags") or "[]"
            tags = json.loads(tags_raw) if isinstance(tags_raw, str) else list(tags_raw)
        except (TypeError, ValueError):
            tags = []
        mem_type = "pattern" if category == "patterns" else "gotcha"
        local_id = svc.be.memory_add(mem_type, title, body, tags=tags)

    archive_status = "skipped"
    if not keep_source:
        # Archive in Notion if client available; always remove from local mirror
        if client is not None:
            try:
                client.pages_update(notion_page_id, archived=True)
                archive_status = "notion_archived"
            except Exception as e:
                archive_status = f"notion_archive_failed: {e}"
        else:
            archive_status = "notion_skipped (no token)"
        try:
            table = _BRAIN_TABLES[category]
            conn.execute(
                f"DELETE FROM {table} WHERE notion_page_id = ?",
                (notion_page_id,),
            )
            conn.commit()
        except sqlite3.Error as e:
            archive_status += f"; mirror_delete_failed: {e}"

    return {
        "status": "ok",
        "local_id": local_id,
        "category": category,
        "source_archive": archive_status,
        "source_kept": keep_source,
    }
