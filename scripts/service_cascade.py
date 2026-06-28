"""TAUSIK CascadeMixin -- auto-start/auto-close parent story/epic on task transitions."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from project_backend import SQLiteBackend


class CascadeMixin:
    """Auto-cascade task status changes to parent story/epic."""

    be: SQLiteBackend

    def _cascade_start(self, task_slug: str) -> None:
        """Auto-start parent story and epic when first task starts."""
        task = self.be.task_get_full(task_slug)
        if not task:
            return
        if task.get("story_slug"):
            story = self.be.story_get(task["story_slug"])
            if story and story["status"] == "open":
                self.be.story_update(story["slug"], status="active")
            if task.get("epic_slug"):
                epic = self.be.epic_get(task["epic_slug"])
                if epic and epic["status"] not in ("active", "done"):
                    self.be.epic_update(task["epic_slug"], status="active")

    def _cascade_done(self, task_slug: str) -> list[str]:
        """Auto-close parent story/epic if all tasks done."""
        msgs: list[str] = []
        task = self.be.task_get_full(task_slug)
        if not task or not task.get("story_slug"):
            return msgs
        remaining = self.be.story_active_task_count(task["story_slug"])
        if remaining == 0:
            self.be.story_update(task["story_slug"], status="done")
            msgs.append(f"Story '{task['story_slug']}' auto-closed.")
            if task.get("epic_slug"):
                undone = self.be.epic_undone_story_count(task["epic_slug"])
                if undone == 0:
                    self.be.epic_update(task["epic_slug"], status="done")
                    msgs.append(f"Epic '{task['epic_slug']}' auto-closed.")
        return msgs
