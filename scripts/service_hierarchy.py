"""TAUSIK service layer — epic/story hierarchy CRUD.

Extracted from project_service.py for filesize compliance. Mixed into
ProjectService via the class declaration there, so the public surface
(``svc.epic_add()`` etc.) is unchanged. Pure code move. ``_require_epic`` /
``_require_story`` resolve via the composed ProjectService MRO at runtime.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tausik_utils import validate_length, validate_slug

if TYPE_CHECKING:
    from project_backend import SQLiteBackend


class HierarchyMixin:
    """Epic/story CRUD with validation."""

    be: SQLiteBackend

    if TYPE_CHECKING:
        # Resolved via the composed ProjectService MRO at runtime (see module
        # docstring); declared here so mypy sees them on the standalone mixin.
        def _require_epic(self, slug: str) -> dict[str, Any]: ...
        def _require_story(self, slug: str) -> dict[str, Any]: ...

    def epic_add(self, slug: str, title: str, description: str | None = None) -> str:
        from tausik_utils import safe_single_line

        validate_slug(slug)
        validate_length("title", title)
        title = safe_single_line(title) or title
        self.be.epic_add(slug, title, safe_single_line(description))
        return f"Epic '{slug}' created."

    def epic_list(self) -> list[dict[str, Any]]:
        return self.be.epic_list()

    def epic_done(self, slug: str) -> str:
        self._require_epic(slug)
        self.be.epic_update(slug, status="done")
        return f"Epic '{slug}' marked done."

    def epic_delete(self, slug: str) -> str:
        self._require_epic(slug)
        self.be.epic_delete(slug)
        return f"Epic '{slug}' deleted."

    def story_add(
        self, epic_slug: str, slug: str, title: str, description: str | None = None
    ) -> str:
        from tausik_utils import safe_single_line

        self._require_epic(epic_slug)
        validate_slug(slug)
        validate_length("title", title)
        title = safe_single_line(title) or title
        self.be.story_add(epic_slug, slug, title, safe_single_line(description))
        return f"Story '{slug}' created in epic '{epic_slug}'."

    def story_list(self, epic_slug: str | None = None) -> list[dict[str, Any]]:
        return self.be.story_list(epic_slug)

    def story_done(self, slug: str) -> str:
        self._require_story(slug)
        self.be.story_update(slug, status="done")
        return f"Story '{slug}' marked done."

    def story_delete(self, slug: str) -> str:
        self._require_story(slug)
        self.be.story_delete(slug)
        return f"Story '{slug}' deleted."
