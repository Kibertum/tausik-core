"""A recorded decision reaches the project, and nothing else decides where else.

THE GUARANTEE. The project's own copy is unconditional: every path through
`record` funnels through `write_local`, which writes the DB row AND its
`tausik/` file. Three of the four call sites once wrote the row directly and
skipped the projection, so a decision recorded WITH a task_slug — the common
case — reached the database and never the tree. Funnelling beats remembering: a
new branch inherits the projection by construction rather than by review.

WHAT THIS MODULE NO LONGER DOES. It used to mirror decisions to Notion by
itself, choosing which ones by running the text through a classifier that looked
for project-specific markers. That is gone. Visibility is a judgement about
intent, and the words cannot carry it — the same sentence is a private note in
one project and a lesson worth sharing in another. The rule failed in the
direction that costs something: six of this project's internal decisions reached
the owner's wiki, including the one cancelling the 2.0 plan, each labelled "no
project-specific markers detected" because a well-written decision usually reads
generally.

So there are two destinations and both are chosen: this project by default,
the shared local store with `--global`. The outward path to a wiki left the
framework with the Notion transport (decision #358); nothing here publishes.

Extracted from service_knowledge.py, which stood one line under the file-size
gate; the boundary is the guarantee above, not a line count.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from tausik_utils import MAX_DECISION, validate_length

if TYPE_CHECKING:
    from project_service import ProjectService


def record(
    svc: ProjectService,
    text: str,
    task_slug: str | None = None,
    rationale: str | None = None,
    to_global: bool = False,
) -> str:
    """Record a decision: locally by default, or in the shared store on request.

    Two destinations, both chosen. Without `to_global` the project keeps its
    own copy unconditionally — the guarantee this module exists for. WITH
    `to_global` the decision goes to `~/.tausik-knowledge/knowledge.db` and
    NOWHERE else: no local row.
    Saying "locally" here without that caveat is how a reader concludes the
    project always keeps a copy, which stopped being true when the flag landed.
    """
    # decision + rationale get the wider MAX_DECISION symbol limit (not the
    # task-title MAX_TITLE=512) — a decision headline is legitimately longer,
    # and the limit is in CHARACTERS so Cyrillic is not penalised (#324).
    validate_length("decision", text, MAX_DECISION)
    if rationale is not None:
        validate_length("rationale", rationale, MAX_DECISION)

    # A decision routed to the shared store leaves BOTH guarantees of this
    # module behind, and that is the point rather than an oversight. The first
    # guarantee — the project always keeps its own copy — does not apply,
    # because the person asked for the opposite; honouring it would write two
    # rows for one decision and make "where does this live" unanswerable. The
    # second — publish outward only on proof — does not apply either: the
    # shared store is a file in this user's home, not a shared workspace, so
    # there is no outward boundary to prove anything about. `write_decision`
    # raises rather than falling back, so a failed shared write never becomes a
    # quiet local one.
    if to_global:
        from knowledge_write import write_decision

        return write_decision(text, rationale, task_slug)

    # Task-linked decisions are inherently project-specific — never shared.
    if task_slug is not None:
        did = write_local(svc, text, task_slug, rationale)
        return f"Decision #{did} recorded — saved to local (reason: linked to task {task_slug})."

    # A decision is recorded HERE and nowhere else. There is no outward
    # publication left in the framework (decision #358).
    #
    # This used to route through `brain_classifier.classify`, which read the
    # text for project-specific markers and mirrored anything that looked
    # general enough to Notion. The rule was not badly written — it was the
    # wrong kind of rule. Visibility is a judgement about INTENT, and no reader
    # of the words can recover it: the same sentence is a private note in one
    # project and a lesson worth sharing in another, and only the author knows
    # which.
    #
    # It failed in the direction that costs something. Six of this project's
    # own internal decisions reached the owner's Notion, among them the one
    # cancelling the 2.0 plan and the one about the release date — each with the
    # cheerful reason "no project-specific markers detected", each phrased
    # generally because a well-written decision usually is.
    #
    # The flag `--global` now exists, so the author has a way to say "this is
    # for every project of mine" without also saying "publish it to a wiki".
    # Two destinations, both chosen rather than inferred: this project by
    # default, the shared local store with `--global`.
    did = write_local(svc, text, task_slug, rationale)
    return f"Decision #{did} recorded — saved to local."


def write_local(
    svc: ProjectService, text: str, task_slug: str | None, rationale: str | None
) -> int:
    """The ONE local write for a decision: DB row + git projection. Returns the id."""
    did = svc.be.decision_add(text, task_slug, rationale)
    from state_triggers import auto_export_by_id  # state-git-triggers (fail-open)

    auto_export_by_id(cast("ProjectService", svc), "decisions", did)
    return did


__all__ = ["record", "write_local"]
