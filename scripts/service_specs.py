"""TAUSIK SpecsMixin — RENAR SPEC-artifact service methods.

A SPEC is a typed, versioned design artifact (RENAR v1.0-draft). ``type`` is a
CLOSED list of 9 — a new type requires a standard amendment, never a free-text
value. The closed list is validated here (friendly error) and again by the DB
CHECK constraint (hard guarantee). Mixed into ProjectService.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import sqlite3

from tausik_utils import ServiceError, validate_content, validate_length, validate_slug

if TYPE_CHECKING:
    from project_backend import SQLiteBackend

# RENAR SPEC types — CLOSED list of 9 (mirrors the DB CHECK on specs.type).
SPEC_TYPES: tuple[str, ...] = (
    "ARCH",
    "API",
    "DATA",
    "INT",
    "PROC",
    "UI",
    "AI",
    "SEC",
    "OPS",
)
# task↔SPEC link relations — CLOSED list (mirrors task_specs.relation CHECK).
SPEC_RELATIONS: tuple[str, ...] = ("implements", "constrained_by")
SPEC_STATUSES: tuple[str, ...] = ("draft", "active", "deprecated")


class SpecsMixin:
    """Manage RENAR SPEC artifacts and their task links."""

    be: SQLiteBackend

    def spec_add(
        self,
        slug: str,
        type_: str,
        title: str,
        version: str,
        content_ref: str | None = None,
        status: str = "draft",
    ) -> str:
        """Create a SPEC. ``type_`` must be one of the 9 closed RENAR types.

        Validated against the closed list here (friendly error) and again by the
        DB CHECK constraint (hard guarantee).
        """
        # Validate all inputs first (fail-fast), then business constraints.
        # validate_slug/validate_length raise ValueError; the CLI/MCP layers only
        # catch ServiceError, so convert here — else a bad slug leaks a traceback.
        try:
            validate_slug(slug)
            if not title:
                raise ValueError("SPEC title is required.")
            validate_length("title", title)
            if not version:
                raise ValueError("SPEC version is required.")
            validate_length("version", version, 64)
            validate_content("content_ref", content_ref)
        except ValueError as e:
            raise ServiceError(str(e)) from e
        type_ = type_.upper()
        if type_ not in SPEC_TYPES:
            raise ServiceError(
                f"Invalid SPEC type '{type_}'. Valid (closed list): {', '.join(SPEC_TYPES)}"
            )
        if status not in SPEC_STATUSES:
            raise ServiceError(f"Invalid SPEC status '{status}'. Valid: {', '.join(SPEC_STATUSES)}")
        if self.be.spec_get(slug):
            raise ServiceError(f"SPEC '{slug}' already exists.")
        try:
            self.be.spec_add(slug, type_, title, version, content_ref, status)
        except sqlite3.IntegrityError as e:
            raise ServiceError(f"Could not create SPEC '{slug}': {e}") from e
        return f"SPEC '{slug}' ({type_}, {version}) created."

    def spec_list(self, type_: str | None = None) -> list[dict[str, Any]]:
        """List SPECs, optionally filtered by type."""
        if type_:
            type_ = type_.upper()
            if type_ not in SPEC_TYPES:
                raise ServiceError(f"Invalid SPEC type '{type_}'. Valid: {', '.join(SPEC_TYPES)}")
        return self.be.spec_list(type_)

    def spec_show(self, slug: str) -> dict[str, Any]:
        """Return a SPEC plus the tasks linked to it."""
        spec = self.be.spec_get(slug)
        if not spec:
            raise ServiceError(f"SPEC '{slug}' not found")
        spec["linked_tasks"] = self.be.tasks_for_spec(slug)
        return spec

    def spec_update(self, slug: str, **fields: Any) -> str:
        """Patch mutable SPEC fields (title, version, content_ref, status)."""
        if not self.be.spec_get(slug):
            raise ServiceError(f"SPEC '{slug}' not found")
        status = fields.get("status")
        if status is not None and status not in SPEC_STATUSES:
            raise ServiceError(f"Invalid SPEC status '{status}'. Valid: {', '.join(SPEC_STATUSES)}")
        try:
            if fields.get("title") is not None:
                validate_length("title", fields["title"])
            if fields.get("version") is not None:
                validate_length("version", fields["version"], 64)
            validate_content("content_ref", fields.get("content_ref"))
        except ValueError as e:
            raise ServiceError(str(e)) from e
        n = self.be.spec_update(
            slug,
            title=fields.get("title"),
            version=fields.get("version"),
            content_ref=fields.get("content_ref"),
            status=status,
        )
        if not n:
            return f"SPEC '{slug}' unchanged (no fields given)."
        return f"SPEC '{slug}' updated."

    def spec_delete(self, slug: str) -> str:
        """Delete a SPEC and cascade-remove its task links."""
        if not self.be.spec_get(slug):
            raise ServiceError(f"SPEC '{slug}' not found")
        self.be.spec_delete(slug)
        return f"SPEC '{slug}' deleted."

    def spec_link(self, task_slug: str, spec_slug: str, relation: str = "implements") -> str:
        """Link a task to a SPEC it implements / is constrained by.

        Both the task and the SPEC must exist (checked here for a friendly
        error; the DB FKs are the hard guarantee — no silent dangling link).
        """
        if relation not in SPEC_RELATIONS:
            raise ServiceError(f"Invalid relation '{relation}'. Valid: {', '.join(SPEC_RELATIONS)}")
        if not self.be.task_get(task_slug):
            raise ServiceError(f"Task '{task_slug}' not found")
        if not self.be.spec_get(spec_slug):
            raise ServiceError(f"SPEC '{spec_slug}' not found")
        try:
            self.be.spec_link(task_slug, spec_slug, relation)
        except sqlite3.IntegrityError:
            raise ServiceError(
                f"Task '{task_slug}' already links to SPEC '{spec_slug}' as '{relation}'."
            ) from None
        return f"Task '{task_slug}' linked to SPEC '{spec_slug}' ({relation})."

    def spec_unlink(self, task_slug: str, spec_slug: str, relation: str = "implements") -> str:
        """Remove a task↔SPEC link."""
        n = self.be.spec_unlink(task_slug, spec_slug, relation)
        if not n:
            raise ServiceError(
                f"No '{relation}' link between task '{task_slug}' and SPEC '{spec_slug}'."
            )
        return f"Unlinked task '{task_slug}' from SPEC '{spec_slug}' ({relation})."

    def specs_for_task(self, task_slug: str) -> list[dict[str, Any]]:
        """SPECs linked to a task."""
        return self.be.specs_for_task(task_slug)

    def spec_search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """FTS5 search over SPECs.

        ``limit`` is capped to keep an unbounded MCP/CLI request from pulling the
        whole table into memory. A syntactically malformed FTS5 query (unbalanced
        quotes/parens) raises sqlite3.OperationalError in the backend — converted
        to a friendly ServiceError so it never crashes the CLI / MCP server.
        """
        limit = max(1, min(int(limit), 200))
        try:
            return self.be.spec_search(query, limit)
        except sqlite3.OperationalError as e:
            raise ServiceError(f"Invalid search query '{query}': {e}") from e
