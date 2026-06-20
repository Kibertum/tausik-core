"""Brain database discovery — workspace search + schema-based fallback.

Extracted from scripts/brain_init.py:
  - to keep the discovery hot loop focused (title-match → schema-fallback),
  - and to give brain_init.py headroom under the 400-line filesize gate.

Two public entry points:

  find_workspace_brain_databases(client) -> {category: db_id}
      Title-first / schema-second discovery. Used by run_wizard
      Branch A (--join-existing) to wire existing BRAIN databases into
      .tausik/config.json without mutating Notion.

  inspect_workspace_brain_databases(client) -> structured detail dict
      Used by error reporting when discovery returned 0 hits but the
      integration sees N>0 databases — surfaces the candidates instead
      of the misleading "integration not shared" message.

Schema-fallback rationale: Notion users routinely rename databases (UI
rename, emoji prefix, translation) — strict title match was the only
matcher pre-v1.4 and produced silent zero-hit failures. Schema-match
checks a small whitelist of distinctive properties per category, derived
from db_schema(category) but trimmed so extra columns are tolerated.
"""

from __future__ import annotations

from typing import Any, Iterator


def _categories() -> tuple[str, ...]:
    """Late lookup — avoids circular import with brain_init at module load."""
    from brain_init import CATEGORIES

    return CATEGORIES


def _db_titles() -> dict[str, str]:
    """Late lookup — avoids circular import with brain_init at module load."""
    from brain_init import DB_TITLES

    return DB_TITLES


# Required-property whitelist per category. A visible database is assigned
# `category` by the schema-fallback pass when ALL of these properties exist
# with the matching Notion type. Extras are tolerated; missing or wrong-type
# means no match. Trimmed from full db_schema(category) to a distinctive
# subset so a renamed BRAIN database (the common case) still resolves while
# unrelated databases that happen to share a couple property names do not.
_REQUIRED_PROPS_BY_CATEGORY: dict[str, dict[str, str]] = {
    "decisions": {
        "Name": "title",
        "Decision": "rich_text",
        "Rationale": "rich_text",
        "Source Project Hash": "rich_text",
    },
    "web_cache": {
        "Name": "title",
        "URL": "url",
        "Content": "rich_text",
        "Content Hash": "rich_text",
    },
    "patterns": {
        "Name": "title",
        "Description": "rich_text",
        "When to Use": "rich_text",
    },
    "gotchas": {
        "Name": "title",
        "Description": "rich_text",
        "Wrong Way": "rich_text",
        "Right Way": "rich_text",
    },
}


def _required_props(category: str) -> dict[str, str]:
    """Return {prop_name: notion_type} required to call a database `category`."""
    if category not in _REQUIRED_PROPS_BY_CATEGORY:
        raise ValueError(f"unknown brain category: {category}")
    return dict(_REQUIRED_PROPS_BY_CATEGORY[category])


def _extract_db_title(db: dict) -> str:
    """Pull the plain-text title out of a Notion database object.

    Tolerates both `plain_text` (normal Notion shape) and `text.content`
    (occasional shape from older payloads / fixtures). Empty/missing → "".
    """
    pieces: list[str] = []
    for f in db.get("title") or []:
        if not isinstance(f, dict):
            continue
        pt = f.get("plain_text")
        if isinstance(pt, str):
            pieces.append(pt)
            continue
        text = f.get("text")
        if isinstance(text, dict):
            content = text.get("content")
            if isinstance(content, str):
                pieces.append(content)
    return "".join(pieces).strip()


def _schema_matches_category(props: dict, category: str) -> bool:
    """Soft schema check — every required property exists with matching type."""
    if not isinstance(props, dict):
        return False
    required = _required_props(category)
    for name, expected_type in required.items():
        prop = props.get(name)
        if not isinstance(prop, dict):
            return False
        if prop.get("type") != expected_type:
            return False
    return True


def _iter_visible_databases(client: Any) -> Iterator[dict]:
    """Yield non-archived database objects visible to the integration.

    Uses Notion search (POST /v1/search) with `filter={object: database}` and
    no `query` — earlier code passed `query="Brain"` which silently dropped
    databases titled without that word (the renamed-database failure mode).
    """
    cursor: str | None = None
    while True:
        page = client.search(
            filter={"property": "object", "value": "database"},
            start_cursor=cursor,
            page_size=100,
        )
        for db in page.get("results") or []:
            if db.get("object") != "database":
                continue
            if db.get("archived"):
                continue
            yield db
        if not page.get("has_more"):
            return
        cursor = page.get("next_cursor")
        if not cursor:
            return


def find_workspace_brain_databases(client: Any) -> dict[str, str]:
    """Search Notion for canonical BRAIN databases (title + schema fallback).

    Pass 1 (title-match): a visible database whose title exactly equals
    _db_titles()[c] is assigned category `c`. First match per category wins.

    Pass 2 (schema-fallback): for any category not yet matched, scan the
    remaining unassigned visible databases and assign the FIRST one whose
    properties satisfy _required_props(category). Catches databases that
    were renamed in Notion or created outside our wizard.

    Returns {category: db_id}. Read-only — never mutates Notion. Callers
    that need duplicate detection or to render an actionable error should
    use inspect_workspace_brain_databases().
    """
    title_to_category = {v: k for k, v in _db_titles().items()}
    found: dict[str, str] = {}
    schema_candidates: list[dict] = []

    for db in _iter_visible_databases(client):
        title = _extract_db_title(db)
        cat = title_to_category.get(title)
        db_id = db.get("id") or ""
        if not db_id:
            continue
        if cat and cat not in found:
            found[cat] = db_id
            continue
        schema_candidates.append(db)

    used_ids = set(found.values())
    for cat in _categories():
        if cat in found:
            continue
        for db in schema_candidates:
            db_id = db.get("id") or ""
            if not db_id or db_id in used_ids:
                continue
            if _schema_matches_category(db.get("properties") or {}, cat):
                found[cat] = db_id
                used_ids.add(db_id)
                break

    return found


def inspect_workspace_brain_databases(client: Any) -> dict:
    """Structured discovery view — used to render an actionable error.

    Returns:
      {
        "visible":          [{"id", "title", "parent_page_id"}, ...],
        "matched":          {category: {"id", "title", "via": "title"|"schema"}},
        "unmatched_visible":[{"id", "title", "parent_page_id"}, ...],
        "schema_conflicts": [{"category": ..., "candidates": [{id,title}, ...]}],
      }

    Used by run_wizard Branch A: when title-only discovery returned 0 hits
    but the integration sees N>0 databases, surface the candidates so the
    user can either rename them canonically or pass --decisions-id explicitly.
    """
    title_to_category = {v: k for k, v in _db_titles().items()}
    visible: list[dict] = []

    for db in _iter_visible_databases(client):
        db_id = db.get("id") or ""
        if not db_id:
            continue
        parent = db.get("parent") or {}
        visible.append(
            {
                "id": db_id,
                "title": _extract_db_title(db),
                "parent_page_id": parent.get("page_id") or "",
                "_props": db.get("properties") or {},
            }
        )

    matched: dict[str, dict] = {}
    used_ids: set[str] = set()
    for rec in visible:
        cat = title_to_category.get(rec["title"])
        if cat and cat not in matched:
            matched[cat] = {"id": rec["id"], "title": rec["title"], "via": "title"}
            used_ids.add(rec["id"])

    schema_conflicts: list[dict] = []
    for cat in _categories():
        if cat in matched:
            continue
        candidates = [
            {"id": rec["id"], "title": rec["title"]}
            for rec in visible
            if rec["id"] not in used_ids and _schema_matches_category(rec["_props"], cat)
        ]
        if len(candidates) == 1:
            chosen = candidates[0]
            matched[cat] = {"id": chosen["id"], "title": chosen["title"], "via": "schema"}
            used_ids.add(chosen["id"])
        elif len(candidates) > 1:
            schema_conflicts.append({"category": cat, "candidates": candidates})

    def _strip(rec: dict) -> dict:
        return {"id": rec["id"], "title": rec["title"], "parent_page_id": rec["parent_page_id"]}

    return {
        "visible": [_strip(r) for r in visible],
        "matched": matched,
        "unmatched_visible": [_strip(r) for r in visible if r["id"] not in used_ids],
        "schema_conflicts": schema_conflicts,
    }
