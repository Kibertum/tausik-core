"""TAUSIK ReasoningMixin — RENAR reasoning-trace service methods.

Extracted from service_task.py to keep it under the 400-line filesize cap
(v16r-reasoning-steps-table). Mixed into TaskMixin; relies on the composed
service's ``_require_task`` plus the backend's reasoning_step CRUD.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tausik_utils import ServiceError, validate_content

if TYPE_CHECKING:
    from project_backend import SQLiteBackend

# RENAR reasoning-trace step kinds — CLOSED list (mirrors the DB CHECK on
# reasoning_steps.kind). Order is the canonical reasoning flow.
REASONING_KINDS: tuple[str, ...] = ("intent", "premise", "action", "verification")


class ReasoningMixin:
    """Record and read a task's structured reasoning trace."""

    be: SQLiteBackend

    if TYPE_CHECKING:

        def _require_task(self, slug: str) -> dict[str, Any]: ...

    def reasoning_step_add(self, slug: str, kind: str, content: str) -> str:
        """Append a RENAR reasoning step (intent|premise|action|verification).

        ``kind`` is validated against the closed list here (friendly error)
        and again by the DB CHECK constraint (hard guarantee). seq
        auto-increments per task.
        """
        self._require_task(slug)
        if kind not in REASONING_KINDS:
            raise ServiceError(
                f"Invalid reasoning kind '{kind}'. Valid: {', '.join(REASONING_KINDS)}"
            )
        validate_content("reasoning content", content)
        seq = self.be.reasoning_step_add(slug, kind, content)
        return f"Reasoning step #{seq} ({kind}) recorded for '{slug}'."

    def reasoning_steps(self, slug: str) -> list[dict]:
        """Return the ordered reasoning trace for a task."""
        self._require_task(slug)
        return self.be.reasoning_step_list(slug)
