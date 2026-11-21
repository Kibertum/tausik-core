"""Refuse invalid `relevant_files` entries before scope honesty / gate work."""

from __future__ import annotations

from typing import Any, Callable

from relevant_files_input import early_refuse_message, invalid_scope_gate_result


def refuse_invalid_relevant_files(
    files: list[str],
    slug: str,
    append_notes_fn: Callable[[str, str], None] | None,
    details: dict[str, Any] | None,
) -> tuple[bool, list[dict[str, Any]], str] | None:
    """Return a synthetic verify failure for '.' / directories, else None."""
    refused = early_refuse_message(files)
    if not refused:
        return None
    if append_notes_fn is not None:
        append_notes_fn(slug, refused)
    if details is not None:
        details["scope_description"] = {
            "status": "unknown",
            "reason": "invalid-relevant-files-entry",
        }
    return invalid_scope_gate_result(refused)
