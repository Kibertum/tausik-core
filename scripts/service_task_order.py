"""Task ordering: declaring an edge, and answering `next` honestly.

MODULE-LEVEL FUNCTIONS TAKING `svc`, not methods on `ProjectService`. That is
not a style preference: `tausik/gates.json` carries a ratchet on the composed
public surface of `ProjectService` and `SQLiteBackend`, and it only turns down.
Both classes predate the gate and sit far above its cap of 60, so the gate's
whole job is to stop them growing while they come down. `redact` -- the last
feature to land here -- added its command the same way, and this follows it.

The capability is not diminished by living outside the class; what changes is
that a reader of `ProjectService` has four fewer names to scroll past before
finding out what the class is FOR.

Two responsibilities live here and nowhere else:

  * `task_depends` / `task_undepends` -- the only way an ordering statement
    enters the system, and therefore the only place a refusal can be phrased.
  * `task_next_report` -- the answer `task next` should have been giving all
    along: not just a task, but WHICH state the backlog is in and what the
    choice was based on.

Why the report exists. The old command returned a task or `None`, and `None`
meant three different things: the backlog is empty, everything is claimed,
everything is waiting on something unfinished. A caller cannot act on a merged
answer -- "there is no work" and "the plan is stalled" call for opposite
responses -- and merging them is the defect
`check-result-conflates-could-not-run-with-passed` was filed about.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tausik_utils import ServiceError, utcnow_iso

if TYPE_CHECKING:
    from project_service import ProjectService

# What `task next` actually sorts by once the ordering edges have had their say.
# Named in the report so nobody reads "suggested" as "highest priority" again --
# the wording that let a complexity sort pass for a plan for eleven releases.
ORDERING_BASIS = "declared order first, then complexity score (complex > medium > simple)"


def _require(svc: ProjectService, slug: str) -> None:
    """Refuse an unknown task BY NAME.

    A refusal that says only "invalid" leaves the author guessing which of the
    two arguments was wrong, and the two are easy to transpose.
    """
    if svc.be.task_get(slug) is None:
        raise ServiceError(f"Task '{slug}' not found.")


def task_depends(svc: ProjectService, slug: str, after: str) -> str:
    """Declare that `slug` comes after `after`."""
    if slug == after:
        raise ServiceError(f"Task '{slug}' cannot depend on itself.")
    _require(svc, slug)
    _require(svc, after)

    cycle = svc.be._task_dep_cycle_path(slug, after)
    if cycle:
        raise ServiceError(
            f"Refusing '{slug}' after '{after}': this closes a cycle "
            f"{' -> '.join(cycle)}. One of those edges has to go first."
        )

    added = svc.be._task_dep_add(slug, after, utcnow_iso())
    svc._project_task(slug)
    if not added:
        return f"Task '{slug}' already comes after '{after}'; nothing changed."
    return f"Task '{slug}' now comes after '{after}'."


def task_undepends(svc: ProjectService, slug: str, after: str) -> str:
    """Withdraw the ordering edge."""
    _require(svc, slug)
    removed = svc.be._task_dep_remove(slug, after)
    svc._project_task(slug)
    if not removed:
        return f"Task '{slug}' did not come after '{after}'; nothing changed."
    return f"Task '{slug}' no longer comes after '{after}'."


def task_deps(svc: ProjectService, slug: str) -> list[str]:
    """The slugs `slug` waits for."""
    _require(svc, slug)
    deps: list[str] = svc.be._task_deps_of(slug)
    return deps


def task_next_report(svc: ProjectService) -> dict[str, Any]:
    """What the backlog is offering, and why.

    `state` is one of:
      * ``ready``       -- a task is offerable; `task` holds it.
      * ``all-blocked`` -- open tasks exist but every one waits on an unfinished
                           predecessor; `blocked` names them.
      * ``all-claimed`` -- open tasks exist but every one already belongs to an
                           agent; `claimed` names them.
      * ``empty``       -- there is no planning work left at all.

    FOUR states, not three. The first version of this function split off
    `all-blocked` and then merged "saturated team" back into `empty` -- the same
    conflation, one size smaller, inside the change filed against it. A backlog
    where everything is claimed is not an empty one, and a fresh agent reading
    the first as the second draws the opposite conclusion.

    `blocked` and `claimed` are populated in the ``ready`` case too. A reader
    deciding whether to trust the suggestion needs to know how much of the
    backlog was withheld from the comparison -- a "next task" chosen out of one
    candidate means something different from one chosen out of twenty.
    """
    task: dict[str, Any] | None = svc.be.task_next_candidate()
    blocked: list[str] = svc.be._task_slugs_blocked_by_deps()
    claimed: list[str] = svc.be._task_slugs_claimed()

    if task is not None:
        state = "ready"
    elif blocked:
        # Blocked wins over claimed when both hold: an ordering constraint is the
        # project's own statement about what must happen first, while a claim is
        # only who got there.
        state = "all-blocked"
    elif claimed:
        state = "all-claimed"
    else:
        state = "empty"

    return {
        "state": state,
        "task": task,
        "blocked": blocked,
        "claimed": claimed,
        "basis": ORDERING_BASIS,
    }
