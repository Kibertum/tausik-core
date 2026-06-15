"""Markdown rendering for brain_mcp_write store results (filesize split)."""

from __future__ import annotations

import brain_fallback
import brain_scrubbing


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
    if status == "taxonomy_blocked":
        return f"**Taxonomy.** {result.get('error')}"
    if status == "card_schema_blocked":
        return f"**Artifact card.** {result.get('error')}"
    if status == "risk_blocked":
        return f"**Publish blocked (risk).** {result.get('error')}"
    return f"Unexpected result: {result!r}"
