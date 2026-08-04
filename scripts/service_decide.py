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

So there are three destinations and all of them are chosen: this project by
default, the shared local store with `--global`, and the outside world only via
`tausik brain move --to-brain`, by name.

WHERE THE THROWAWAY GUARD WENT. `is_working_project_db` still lives here — it is
about THIS module's notion of "am I really the project's service" — but its
caller is now `brain_move`, which owns the only outward path. It answers
FAIL-CLOSED: a false negative costs a manual re-run, a false positive costs an
irreversible write to someone's shared workspace.

Extracted from service_knowledge.py, which stood one line under the file-size
gate; the boundary is the guarantee above, not a line count.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, cast

from tausik_utils import MAX_DECISION, validate_length

if TYPE_CHECKING:
    from project_backend import SQLiteBackend
    from project_service import ProjectService


def record(
    svc: ProjectService,
    text: str,
    task_slug: str | None = None,
    rationale: str | None = None,
    to_global: bool = False,
) -> str:
    """Record a decision: locally by default, or in the shared store on request.

    Three destinations, not two. Without `to_global` the project keeps its own
    copy unconditionally and the brain sees it only on proof — the two
    guarantees this module exists for. WITH `to_global` the decision goes to
    `~/.tausik-knowledge/knowledge.db` and NOWHERE else: no local row, no brain
    mirror.
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

    # Task-linked decisions are inherently project-specific — never route to brain.
    if task_slug is not None:
        did = write_local(svc, text, task_slug, rationale)
        return f"Decision #{did} recorded — saved to local (reason: linked to task {task_slug})."

    # A decision is recorded HERE and nowhere else. Publishing outward is a
    # separate act, performed on purpose, with `tausik brain publish`.
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
    # Three destinations, all chosen rather than inferred: this project by
    # default, the shared local store with `--global`, the outside world only
    # when asked by name.
    did = write_local(svc, text, task_slug, rationale)
    return f"Decision #{did} recorded — saved to local."


def _same_file(a: str, b: str) -> bool:
    r"""Do these two paths name the same file? Asked of the filesystem first.

    The question is identity of a FILE, and a string comparison answers a
    different one. When both paths exist, the filesystem itself answers:
    `(st_dev, st_ino)` is what "the same file" MEANS, so symlinks, junctions,
    hard links and drive-letter casing all collapse without any normalization
    having to be correct about them.

    That order matters, because the string route carried a claim that is false.
    It read "two genuinely distinct files cannot share a realpath", and folding
    case after resolving makes that untrue exactly where it costs most: NTFS
    supports per-directory case sensitivity (`fsutil setCaseSensitiveInfo`, the
    documented path for WSL2), so `Data.db` and `data.db` can exist SEPARATELY,
    realpath returns two names, and `normcase` then declares them one. A
    fail-closed guard becomes fail-OPEN for precisely the class it was written
    to catch. `st_ino` does not have that failure mode.

    The string route remains as a FALLBACK, for the case the stat route cannot
    serve: one of the paths does not exist yet (an uninitialised project), or
    the filesystem reports no usable inode — some Windows network shares return
    zero. There the residual risk above is accepted, and named rather than
    denied: it is the narrow case of a non-existent file on a case-sensitive
    volume, where nothing better is available.

    Both normalizations in that fallback are still there for their own reasons:

      * `realpath` — a symlinked or junctioned `.tausik/` makes the resolver
        return one spelling and the backend hold the other. Decided rather than
        left implicit: a symlink to the project's database IS the project's
        database, and refusing it would be the same over-refusal as the casing
        bug, one indirection further out.
      * `normcase` — on Windows and macOS `d:\...` and `D:\...` are one file and
        two strings. `state_serialize.assert_export_target` already folds case
        before comparing for exactly this reason (and memory #83 records the
        rule for this project); this guard was written later and did not follow
        it. The consequence was worse than a missed publish: the guard is
        fail-closed, so a drive-letter difference silently disabled publishing
        AND made `local_reason` tell a user working in their own project that
        their context was a throwaway.
    """
    try:
        sa, sb = os.stat(a), os.stat(b)
        if sa.st_ino and sb.st_ino:
            return (sa.st_dev, sa.st_ino) == (sb.st_dev, sb.st_ino)
    except OSError:
        pass  # not both present, or unstattable — fall through to the string route
    return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))


def is_working_project_db(be: SQLiteBackend) -> bool:
    """True iff this backend is bound to the project's real DB. Fail-CLOSED.

    Any error answering the question means no publish: the cost of a false
    negative is a decision kept local, the cost of a false positive is an
    irreversible write to someone's shared workspace.
    """
    try:
        from project_config import find_tausik_dir

        return _same_file(be.db_path, os.path.join(find_tausik_dir(), "tausik.db"))
    except Exception:  # noqa: BLE001 — unknown provenance is not permission
        return False


def write_local(
    svc: ProjectService, text: str, task_slug: str | None, rationale: str | None
) -> int:
    """The ONE local write for a decision: DB row + git projection. Returns the id."""
    did = svc.be.decision_add(text, task_slug, rationale)
    from state_triggers import auto_export_by_id  # state-git-triggers (fail-open)

    auto_export_by_id(cast("ProjectService", svc), "decisions", did)
    return did


__all__ = ["is_working_project_db", "record", "write_local"]
