"""Team-related task helpers split from service_task.py for filesize compliance.

Provides a mixin with task_quick / task_next / task_claim / task_unclaim.
Mixed into TaskMixin via multiple inheritance — same `self.be`,
`self._require_task`, `self.task_*` are available on the host class.
"""

from __future__ import annotations

import os
from typing import Any

from tausik_utils import ServiceError, utcnow_iso


class TaskTeamMixin:
    """task_quick + task_next + task_claim + task_unclaim."""

    def task_quick(
        self,
        title: str,
        goal: str | None = None,
        role: str | None = None,
        stack: str | None = None,
    ) -> str:
        """Quick-create a task from minimal input (auto-slug, no story required)."""
        from tausik_utils import slugify

        slug = slugify(title)
        if self.be.task_get(slug):  # type: ignore[attr-defined]
            suffix = os.urandom(3).hex()
            slug = f"{slug[:44]}-{suffix}"
        msg: str = self.task_add(  # type: ignore[attr-defined]
            None, slug, title, stack=stack, goal=goal, role=role
        )
        return msg

    def task_next(self, agent_id: str | None = None) -> dict[str, Any] | None:
        """Pick next available task; auto-start if agent_id given (QG-0 enforced)."""
        task: dict[str, Any] | None = self.be.task_next_candidate()  # type: ignore[attr-defined]
        if not task:
            return None
        if agent_id:
            self.task_claim(task["slug"], agent_id)
            try:
                self.task_start(task["slug"])  # type: ignore[attr-defined]
            except ServiceError:
                task["_qg0_failed"] = True
            refreshed: dict[str, Any] | None = self.be.task_get(task["slug"])  # type: ignore[attr-defined]
            task = refreshed or task
        return task

    def task_claim(self, slug: str, agent_id: str) -> str:
        """Claim a task for an agent. Atomic UPDATE prevents race conditions."""
        self._require_task(slug)  # type: ignore[attr-defined]
        self.be.task_claim(slug, agent_id, utcnow_iso())  # type: ignore[attr-defined]
        return f"Task '{slug}' claimed by '{agent_id}'."

    def task_unclaim(self, slug: str) -> str:
        self._require_task(slug)  # type: ignore[attr-defined]
        self.be.task_update(slug, claimed_by=None)  # type: ignore[attr-defined]
        return f"Task '{slug}' unclaimed."
