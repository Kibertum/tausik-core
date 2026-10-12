"""Rewrite a memory record in place, because the doctrine says rewrite and the CLI said delete.

WHY THIS EXISTS. The project's own rule is that a record whose reference rotted but whose CLAIM is
still true gets REWRITTEN, not deleted. The CLI offered `delete` and `supersede` and nothing else,
so the sixteen records corrected in one sweep had to be edited through the git projection and
re-imported. That works — the tree is a declared source and `state import` says git wins — but it
is a workaround standing in for a command, and a workaround is what the next person copies.

WHY A MODULE FUNCTION AND NOT A METHOD. `SQLiteBackend` and `ProjectService` are capped by the
class-surface ratchet, which may only shrink; `memory_relevance` lives out here for the same
reason and says so. A god class that grows one convenience at a time is the thing the cap exists
against, and a single caller is not an argument for a public member.

WHAT IT REFUSES. An empty title or body — a rewrite that empties the record is a delete wearing
another name, and `delete` already exists for that. An archived record, because editing one would
quietly resurrect a decision that was already taken.
"""

from __future__ import annotations

from typing import Any

from tausik_utils import ServiceError, utcnow_iso


def edit_memory(
    svc: Any,
    mid: int,
    title: str | None = None,
    content: str | None = None,
) -> str:
    """Rewrite the title and/or body of memory ``mid``, keeping its identity.

    The id, the slug and `created_at` do not move: this is the SAME record with a corrected
    claim, not a new one. That distinction is the whole point — a supersede chain would say the
    old text was a different fact, when what happened is that one sentence in it was wrong.
    """
    row = svc.be.memory_get(mid)
    if not row:
        raise ServiceError(f"Memory #{mid} not found")
    if row.get("archived_at"):
        raise ServiceError(
            f"Memory #{mid} is archived ({row['archived_at']}) — editing it would quietly "
            f"revive a decision that was already taken. Add a new record instead."
        )
    new_title = row["title"] if title is None else title.strip()
    new_content = row["content"] if content is None else content.strip()
    if not new_title or not new_content:
        raise ServiceError(
            "A rewrite that empties the title or the body is a delete under another name — "
            "use `memory delete` if that is what you mean."
        )
    if new_title == row["title"] and new_content == row["content"]:
        return f"Memory #{mid} unchanged — the text given is the text it already had."
    svc.be._ex(
        "UPDATE memory SET title=?, content=?, updated_at=? WHERE id=?",
        (new_title, new_content, utcnow_iso(), mid),
    )
    slug = row.get("slug")
    if slug:
        from state_triggers import auto_export_entity  # fail-open by design

        auto_export_entity(svc, "memory", slug)
    return f"Memory #{mid} rewritten."
