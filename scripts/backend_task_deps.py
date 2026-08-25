"""TAUSIK BackendTaskDepsMixin -- the ordering edge between two tasks.

`task next` used to be one line: highest complexity score among unclaimed
planning tasks. Complexity is not order. The order in this project is stated in
decisions and in the release plan -- "this one first", "that one only after it"
-- and none of it reached the query, so an agent trusting the command started in
the middle of a sequence whose every step assumes the previous one landed.

This module owns both halves of the correction, deliberately in one place:

  * the EDGE ("b comes after a"), and
  * the QUERY that has to respect it.

`task_next_candidate` moved here from `project_backend` for that reason. A
selection rule stated in one module and constrained in another is two statements
about one behaviour, and the drift between them would surface as a task quietly
offered too early -- an outcome nobody reads as a defect, because a plausible
answer is exactly what the old query already produced.

KEYED BY SLUG, NOT BY `id`. The first version referenced `tasks(id)` and was
wrong twice over. Every sibling child table (`task_logs`, `reasoning_steps`)
references `tasks(slug)`, and `docs/*/team-state-in-git.md` lists `id` among the
fields that do NOT travel: it is a local autoincrement, meaningless in another
clone. An edge that gets serialised into the git projection has to be keyed by
the identity that survives the trip. The migration tests caught it as a
`foreign key mismatch`, because their minimal stand-in for `tasks` carries the
column the rest of the schema actually points at -- `slug`.

WHAT COUNTS AS SATISFIED: the predecessor is `done`. Not started, not claimed,
not in review -- done. "After" is a statement about completed work, and treating
`active` as good enough would hand out the successor while the schema it depends
on is still being written.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

# A predecessor holds its dependent back until it reaches this status.
_SATISFIED_STATUS = "done"

# Shared by the ready-query and the blocked-query so the two can never disagree
# about what "waiting" means. Spelled once; both sides substitute it.
_HAS_UNFINISHED_PREDECESSOR = (
    "EXISTS (SELECT 1 FROM task_deps d "
    "JOIN tasks p ON p.slug = d.depends_on_slug "
    f"WHERE d.task_slug = t.slug AND p.status <> '{_SATISFIED_STATUS}')"
)

_OFFERABLE = "t.status='planning' AND t.claimed_by IS NULL"

# Planning work that exists but belongs to somebody already. Deliberately a
# THIRD count rather than folded into "nothing available": a saturated team and
# an empty backlog call for opposite responses from a fresh agent.
_CLAIMED = "t.status='planning' AND t.claimed_by IS NOT NULL"


class BackendTaskDepsMixin:
    """Declare, read and honour the order between tasks."""

    # Type stubs for mixin
    if TYPE_CHECKING:

        def _q(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]: ...
        def _q1(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None: ...
        def _ex(self, sql: str, params: tuple[Any, ...] = ()) -> int: ...

    def _task_dep_add(self, task_slug: str, depends_on_slug: str, now: str) -> bool:
        """Record "task_slug comes after depends_on_slug".

        Returns False when the edge was already there. The caller reports that
        as a no-op rather than an error: replaying a plan script must converge
        on the same graph, not fail halfway through on statements that are
        already true.
        """
        changed = self._ex(
            "INSERT OR IGNORE INTO task_deps(task_slug, depends_on_slug, created_at) "
            "VALUES(?, ?, ?)",
            (task_slug, depends_on_slug, now),
        )
        return bool(changed)

    def _task_dep_remove(self, task_slug: str, depends_on_slug: str) -> bool:
        """Withdraw the edge. Returns False when there was nothing to withdraw."""
        changed = self._ex(
            "DELETE FROM task_deps WHERE task_slug=? AND depends_on_slug=?",
            (task_slug, depends_on_slug),
        )
        return bool(changed)

    def _task_deps_of(self, task_slug: str) -> list[str]:
        """The slugs this task waits for, sorted.

        Sorted, not insertion-ordered: this list is serialised into the git
        projection, and an order that depends on when each edge was typed would
        make the exported file differ between two databases holding the same
        graph -- a false round-trip failure.
        """
        rows = self._q(
            "SELECT depends_on_slug AS slug FROM task_deps "
            "WHERE task_slug=? ORDER BY depends_on_slug",
            (task_slug,),
        )
        return [r["slug"] for r in rows]

    def _task_deps_all(self) -> dict[str, list[str]]:
        """Every edge in one query, for the exporter.

        `build_tree` serialises every task; asking per task would make the
        export cost one query per row, which is the N+1 this codebase has
        already paid down twice.
        """
        rows = self._q(
            "SELECT task_slug, depends_on_slug FROM task_deps ORDER BY task_slug, depends_on_slug"
        )
        out: dict[str, list[str]] = {}
        for row in rows:
            out.setdefault(row["task_slug"], []).append(row["depends_on_slug"])
        return out

    def _task_dep_cycle_path(self, task_slug: str, depends_on_slug: str) -> list[str]:
        """The path proving `depends_on_slug` already comes after `task_slug`.

        Empty when adding the edge is safe. A non-empty result names the route,
        because "cycle detected" tells an author that they were wrong without
        telling them WHICH of their earlier statements the new one contradicts.

        Walked here rather than left for the reader to trip over: an edge that
        closes a cycle makes every later traversal responsible for surviving it,
        and `task next` would then have to choose between looping and silently
        dropping a task. Refusing at declaration keeps the graph acyclic by
        construction.
        """
        if task_slug == depends_on_slug:
            return [task_slug, task_slug]

        # Depth-first from the proposed predecessor along ITS predecessors.
        # Reaching task_slug means it is already upstream, so the new edge would
        # close the loop.
        stack: list[tuple[str, list[str]]] = [(depends_on_slug, [depends_on_slug])]
        seen: set[str] = set()
        while stack:
            current, path = stack.pop()
            if current == task_slug:
                # `path` already runs from the proposed predecessor up to
                # `task_slug`, so it only needs `task_slug` in front to close the
                # loop: A -> (new edge) -> B -> ... -> A. Reversing it, or
                # prepending to a reversed copy, prints the first node twice and
                # makes the loop unreadable -- caught by running the command, not
                # by the test, which only looked for the word "cycle".
                return [task_slug, *path]
            if current in seen:
                continue
            seen.add(current)
            for parent in self._task_deps_of(current):
                stack.append((parent, [*path, parent]))
        return []

    def task_next_candidate(self) -> dict[str, Any] | None:
        """Highest-score offerable task whose predecessors are all done.

        Score still breaks ties, and deliberately so: the defect was that order
        could not be EXPRESSED, not that complexity was the wrong tie-break.
        Changing both at once would have left neither measured.
        """
        row: dict[str, Any] | None = self._q1(
            f"SELECT t.* FROM tasks t WHERE {_OFFERABLE} "
            f"AND NOT {_HAS_UNFINISHED_PREDECESSOR} "
            "ORDER BY t.score DESC LIMIT 1"
        )
        return row

    def _task_slugs_blocked_by_deps(self) -> list[str]:
        """Offerable tasks held back only by an unfinished predecessor.

        Exists so a caller can tell "there is no work" from "all remaining work
        is waiting" -- two states the old `None` merged into one, which reports
        a stalled plan as a finished one.
        """
        rows = self._q(
            f"SELECT t.slug AS slug FROM tasks t WHERE {_OFFERABLE} "
            f"AND {_HAS_UNFINISHED_PREDECESSOR} "
            "ORDER BY t.slug"
        )
        return [r["slug"] for r in rows]

    def _task_slugs_claimed(self) -> list[str]:
        """Planning tasks that already belong to an agent.

        Separates "the team is saturated" from "there is no work". The old
        `None` covered both, and so did the first version of the replacement --
        the same conflation, one size smaller, inside the change filed against
        it.
        """
        rows = self._q(f"SELECT t.slug AS slug FROM tasks t WHERE {_CLAIMED} ORDER BY t.slug")
        return [r["slug"] for r in rows]
