"""A recorded decision always reaches the project; it reaches the outside only on proof.

Two guarantees, and everything in this module exists to hold one of them.

FIRST — the project's own copy is unconditional. Every path through `record`,
including the ones that publish and the ones that fail to, funnels through
`write_local`, which writes the DB row AND its `tausik/` file. Three of the four
call sites once wrote the row directly and skipped the projection, so a decision
recorded WITH a task_slug — the common case — reached the database and never the
tree. Funnelling beats remembering: a new branch inherits the projection by
construction rather than by review. A decision the project cannot read back is
not recorded, however well it was published, which is why the brain is a MIRROR
and never a destination.

SECOND — the external write happens only when this service is provably speaking
for the project. Publishing to the brain is an effect on a shared store outside
the repository, and it used to fire from whatever database the service happened
to hold: `decide` on a throwaway temp DB created a live page in the user's
Notion, a side effect escaping into production from a context whose whole premise
is that nothing outside it changes. `is_working_project_db` answers that question
FAIL-CLOSED — a false negative costs a decision kept local, a false positive
costs an irreversible write to someone's shared workspace.

Extracted from service_knowledge.py, which stood one line under the file-size
gate; the boundary is these two guarantees, not a line count.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, cast

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
    `~/.tausik/knowledge.db` and NOWHERE else: no local row, no brain mirror.
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

    from brain_classifier import classify
    from brain_config import load_brain
    from brain_runtime import decision_publish_fields

    cfg = load_brain()
    # Classify what would be PUBLISHED, not the headline alone. Judging by
    # `text` only was unsound by construction: the rationale ships too, and it
    # is where the project detail lives. Observed live — a release-scope
    # decision whose headline held only two-segment slugs
    # (`shared-knowledge`, `doc-swarm`) scored "no project-specific markers"
    # and went out, while the rationale carried the three-segment slugs
    # (`redoc-1-8-final`, `l26-memory-decay`) that corroborate them. The
    # marker rule was right; it was fed the smaller half.
    blob = "\n".join(str(v) for v in decision_publish_fields(text, rationale).values())
    decision = classify(blob, "decision", cfg=cfg)

    if decision.target == "brain" and cfg.get("enabled") and is_working_project_db(svc.be):
        return _record_with_mirror(svc, text, rationale, cfg, decision)

    did = write_local(svc, text, task_slug, rationale)
    return f"Decision #{did} recorded — saved to local (reason: {local_reason(decision, cfg)})."


def _record_with_mirror(
    svc: ProjectService, text: str, rationale: str | None, cfg: dict[str, Any], decision: Any
) -> str:
    """The publish path: validate the brain config loudly, write local either way."""
    from brain_config import validate_brain

    # Defect v14b-defect-brain-decisions-empty: when brain.enabled=true but
    # database_ids/token are empty, store_record silently returns
    # status=config_error and the local-fallback path runs with a quiet "brain
    # write failed" reason. Pre-validate so the user sees a loud, actionable
    # message instead of accumulating local-only decisions that should have
    # been mirrored to Notion.
    cfg_errors = validate_brain()
    if cfg_errors:
        did = write_local(svc, text, None, rationale)
        error_lines = "\n".join(f"  - {e}" for e in cfg_errors)
        return (
            f"⚠ Decision #{did} saved LOCALLY ONLY — brain mirror BLOCKED.\n\n"
            f"Brain is enabled in .tausik/config.json but misconfigured:\n"
            f"{error_lines}\n\n"
            f"Fix one of:\n"
            f"  1. Run `.tausik/tausik brain init` to complete setup, OR\n"
            f"  2. Set `brain.enabled = false` in .tausik/config.json to disable.\n\n"
            f"After fixing, migrate local-only decisions with "
            f"`tausik brain move --to-brain`."
        )
    from brain_runtime import try_brain_write_decision

    ok, detail = try_brain_write_decision(text, rationale, cfg)
    # The local write happens EITHER WAY. This used to return on a successful
    # brain write BEFORE the local one, which made Notion the only carrier: no
    # DB row, no tausik/ file, invisible to `tausik decisions` and to the memory
    # block injected at session start.
    did = write_local(svc, text, None, rationale)
    if ok:
        return (
            f"Decision #{did} recorded — saved to local and mirrored to brain "
            f"(reason: {decision.reason}). Page: {detail}"
        )
    return f"Decision #{did} recorded — saved to local (reason: brain write failed: {detail})."


def local_reason(decision: Any, cfg: dict[str, Any]) -> str:
    """Why this decision stayed local — the actual cause, not a stand-in.

    This used to collapse every non-local-classified case to "brain not
    enabled", which became a false statement the moment a second reason
    existed: a decision skipped because the service is bound to a throwaway
    DB would report the brain as disabled when it is enabled and fine.
    """
    if decision.target == "local":
        return str(decision.reason)
    if not cfg.get("enabled"):
        return "brain not enabled"
    return (
        "brain skipped — this service is not bound to the project DB, "
        "so an external publish would escape from a throwaway context"
    )


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


__all__ = ["is_working_project_db", "local_reason", "record", "write_local"]
