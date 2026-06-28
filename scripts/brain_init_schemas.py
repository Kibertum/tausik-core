"""Brain database schemas + create/verify helpers.

Extracted from scripts/brain_init.py (v14b-followup-brain-init-filesize-debt)
to keep that module under the 400-line filesize gate. Pure structural split —
no semantic changes. brain_init re-exports the public names so external
callers (tests, brain_cli_ops) keep working unchanged.
"""

from __future__ import annotations

from typing import Any, Callable

from brain_notion_client import NotionError, NotionNotFoundError


CATEGORIES = ("decisions", "web_cache", "patterns", "gotchas")

DB_TITLES: dict[str, str] = {
    "decisions": "Brain · Decisions",
    "web_cache": "Brain · Web Cache",
    "patterns": "Brain · Patterns",
    "gotchas": "Brain · Gotchas",
}


# --- Schemas (one function per category so test assertions target the shape) ---


def _decisions_schema() -> dict:
    return {
        "Name": {"title": {}},
        "Context": {"rich_text": {}},
        "Decision": {"rich_text": {}},
        "Rationale": {"rich_text": {}},
        "Tags": {"multi_select": {}},
        "Stack": {"multi_select": {}},
        "Date": {"date": {}},
        "Source Project Hash": {"rich_text": {}},
        "Generalizable": {"checkbox": {}},
        "Superseded By": {"url": {}},
    }


def _web_cache_schema() -> dict:
    return {
        "Name": {"title": {}},
        "URL": {"url": {}},
        "Query": {"rich_text": {}},
        "Content": {"rich_text": {}},
        "Fetched At": {"date": {}},
        "TTL Days": {"number": {"format": "number"}},
        "Domain": {"select": {}},
        "Tags": {"multi_select": {}},
        "Source Project Hash": {"rich_text": {}},
        "Content Hash": {"rich_text": {}},
    }


def _patterns_schema() -> dict:
    return {
        "Name": {"title": {}},
        "Description": {"rich_text": {}},
        "When to Use": {"rich_text": {}},
        "Example": {"rich_text": {}},
        "Tags": {"multi_select": {}},
        "Stack": {"multi_select": {}},
        "Source Project Hash": {"rich_text": {}},
        "Date": {"date": {}},
        "Confidence": {
            "select": {
                "options": [
                    {"name": "experimental"},
                    {"name": "tested"},
                    {"name": "proven"},
                ]
            }
        },
    }


def _gotchas_schema() -> dict:
    return {
        "Name": {"title": {}},
        "Description": {"rich_text": {}},
        "Wrong Way": {"rich_text": {}},
        "Right Way": {"rich_text": {}},
        "Tags": {"multi_select": {}},
        "Stack": {"multi_select": {}},
        "Source Project Hash": {"rich_text": {}},
        "Date": {"date": {}},
        "Severity": {
            "select": {
                "options": [
                    {"name": "low"},
                    {"name": "medium"},
                    {"name": "high"},
                ]
            }
        },
        "Evidence URL": {"url": {}},
    }


_SCHEMAS: dict[str, Callable[[], dict]] = {
    "decisions": _decisions_schema,
    "web_cache": _web_cache_schema,
    "patterns": _patterns_schema,
    "gotchas": _gotchas_schema,
}


def db_schema(category: str) -> dict:
    """Return Notion property schema for a brain category.

    Raises ValueError for unknown category.
    """
    if category not in _SCHEMAS:
        raise ValueError(f"Unknown brain category: {category!r}")
    return _SCHEMAS[category]()


# --- Notion database creation ---


class PartialCreateError(NotionError):
    """Raised when create_brain_databases fails mid-batch.

    Carries the `created_ids` dict of categories that DID land in Notion before
    the failure so callers can emit accurate orphan-cleanup guidance instead of
    `<missing>` placeholders.
    """

    def __init__(self, message: str, created_ids: dict[str, str]):
        super().__init__(message)
        self.created_ids = created_ids


def create_brain_databases(client: Any, parent_page_id: str) -> dict[str, str]:
    """Create 4 brain databases under parent_page_id. Returns {category: db_id}.

    Raises `PartialCreateError` (subclass of NotionError) when any category
    fails after at least one succeeded — carries `created_ids` for cleanup.
    On the very first call failure (zero successes), re-raises the original
    NotionError unchanged.
    """
    if not parent_page_id:
        raise ValueError("parent_page_id is required")
    ids: dict[str, str] = {}
    for category in CATEGORIES:
        try:
            resp = client.databases_create(
                parent_page_id=parent_page_id,
                title=DB_TITLES[category],
                properties=db_schema(category),
            )
        except NotionError as e:
            if ids:
                raise PartialCreateError(
                    f"databases_create failed mid-batch on '{category}': {e}",
                    ids,
                ) from e
            raise
        ids[category] = resp.get("id") or ""
    return ids


def verify_brain_databases(client: Any, db_ids: dict[str, str]) -> dict[str, str]:
    """Verify each db_id resolves to a queryable Notion database.

    Returns {category: error_message} for IDs that fail verification.
    Empty dict means all four IDs are valid. Used by --join-existing to
    catch typos before writing config.json.
    """
    errors: dict[str, str] = {}
    for category in CATEGORIES:
        db_id = (db_ids.get(category) or "").strip()
        if not db_id:
            errors[category] = "missing id"
            continue
        try:
            client.databases_query(db_id, page_size=1)
        except NotionNotFoundError as e:
            errors[category] = f"not found: {e}"
        except NotionError as e:
            errors[category] = f"verify failed: {e}"
    return errors
