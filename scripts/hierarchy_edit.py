"""`epic update` / `story update`, and the stale-description count they feed.

An epic's or a story's description is how a fresh agent reads the INTENT of a
group of tasks. Until this module existed it could not be changed at all — the
commands were add, list, done, delete — so it aged into a false standing claim
(found twice in one session, #189, and worked around by keeping the intent in
decisions, which helps only while someone reads them).

A MODULE, not five more members on ProjectService and two on SQLiteBackend.
The class-surface ratchet (`gate_class_surface`) only turns down, and it is
right to: those two are the god classes it exists to shrink, and the first
draft of this change grew both (118 → 123, 129 → 131) before the ratchet said
no. So the ONE implementation the CLI and the MCP tool share lives here and
takes the service as its first argument; neither caller carries logic of its
own, and a test asserts that on their ASTs.

A description edit is journaled as an event, and that event is what `stale`
measures against — no new column, no migration. `stale` is the number of tasks
created under the group AFTER its description was last edited (with no edit
ever, since the group was created). It NAMES, it never blocks: a description
rewritten to pass a check is worse than one honestly old, so nothing here is
consulted by `done`, and a test says so.
"""

from __future__ import annotations

from typing import Any

from tausik_utils import ServiceError, safe_single_line, validate_length

# The event's entity_type is the PLURAL kind ("epics" / "stories") — the same
# word `_project` and the backend dispatch on — where every other producer in
# the tree writes the singular noun ("task", "session", "role"). Deliberate and
# recorded here: a reader querying entity_type='epic' gets zero rows, and
# `staleness` then silently reads every group as never edited.
EDIT_EVENT = "description_updated"
_NOUN = {"epics": "Epic", "stories": "Story"}


def _require(svc: Any, kind: str, slug: str) -> dict[str, Any]:
    row = svc._require_epic(slug) if kind == "epics" else svc._require_story(slug)
    return dict(row)


def update(
    svc: Any,
    kind: str,
    slug: str,
    title: str | None = None,
    description: str | None = None,
) -> str:
    """Change the title and/or description of an epic (`kind='epics'`) or a story.

    The validation is the one `add` applies (length, single line); an unknown
    slug fails the way `done` and `delete` fail; nothing to change is refused,
    not silently accepted.
    """
    if title is None and description is None:
        raise ServiceError(
            f"nothing to update for {kind} '{slug}': pass --title and/or --description"
        )
    _require(svc, kind, slug)
    # An empty string is refused, not stored: blanking the description would
    # write the edit event and reset `stale` to 0 — the one way to "pass" the
    # report by destroying the intent it measures (review #208, record #23).
    # After `_require`, so an unknown slug still fails the way `done` does.
    for field, value in (("title", title), ("description", description)):
        if value is not None and not value.strip():
            raise ServiceError(f"empty {field} for {kind} '{slug}': pass text or omit the flag")
    fields: dict[str, Any] = {}
    if title is not None:
        validate_length("title", title)
        fields["title"] = safe_single_line(title) or title
    if description is not None:
        fields["description"] = safe_single_line(description)
    if kind == "epics":
        svc.be.epic_update(slug, **fields)
    else:
        svc.be.story_update(slug, **fields)
    if "description" in fields:
        svc.be.event_add(kind, slug, EDIT_EVENT)
    svc._project(kind, slug)
    return f"{_NOUN[kind]} '{slug}' updated ({' and '.join(sorted(fields))})."


def _last_edit_at(svc: Any, kind: str, slug: str) -> str | None:
    row = svc.be._q1(
        "SELECT MAX(created_at) AS at FROM events WHERE entity_type=? AND entity_id=? AND action=?",
        (kind, slug, EDIT_EVENT),
    )
    return row["at"] if row and row["at"] else None


def _tasks_created_after(svc: Any, kind: str, slug: str, since: str) -> int:
    if kind == "epics":
        sql = (
            "SELECT COUNT(*) AS cnt FROM tasks t "
            "JOIN stories s ON t.story_id=s.id JOIN epics e ON s.epic_id=e.id "
            "WHERE e.slug=? AND t.created_at > ?"
        )
    else:
        sql = (
            "SELECT COUNT(*) AS cnt FROM tasks t JOIN stories s ON t.story_id=s.id "
            "WHERE s.slug=? AND t.created_at > ?"
        )
    row = svc.be._q1(sql, (slug, since))
    return int(row["cnt"]) if row else 0


def staleness(svc: Any, kind: str, slug: str) -> int:
    """Tasks created under the epic/story after its description was last edited.

    Only CREATIONS count: moving a task between stories does not touch its
    `created_at`, and a title-only edit writes no event, or renaming would
    reset the number. A task created in the same second as the edit is NOT
    counted (strict `>`, pinned by a test) — the edit is taken to describe
    what existed when it was written. A number, not a verdict.
    """
    row = _require(svc, kind, slug)
    since = _last_edit_at(svc, kind, slug) or str(row["created_at"])
    return _tasks_created_after(svc, kind, slug, since)


def list_with_staleness(svc: Any, kind: str, epic_slug: str | None = None) -> list[dict[str, Any]]:
    """`epic_list()` / `story_list()` rows, each with its `stale` number."""
    rows = svc.epic_list() if kind == "epics" else svc.story_list(epic_slug)
    return [{**r, "stale": staleness(svc, kind, str(r["slug"]))} for r in rows]
