"""A task's OWN export file, subtracted from the coverage a receipt claims.

THE DEFECT THIS EXISTS FOR (verify-handle-dies-on-a-tasks-own-export-file,
reproduced twice in session #191). A task that named its own export
`tausik/tasks/<slug>.md` in `--relevant-files` could never be closed. The verify
run writes into the task — the declared scope, the run number, the receipt — the
exporter re-serializes the task from that write, and the handle presented a
moment later covers a file the act of verifying had already moved. The refusal
was accurate and unfixable: 870e9d910c7c -> edd0acd46e7b -> e8d9e08ecc20, each
run pushing the hash further. Hashing that file asks whether the measurement
changed what it measured. It always did.

WHY SUBTRACTION AND NOT THE OTHER TWO REPAIRS. Snapshotting the hash BEFORE the
run does not converge either — the receipt is written into the task after the
gates, so `task done` still reads a moved file. Forbidding the path outright is
honest but teaches an exception instead of behaving sensibly: a task whose
product IS records naturally declares its own export. Convention #409 already
names this illness in the neighbouring check (`--no-file-changes`): a check
whose subject is "what did the AGENT change" must subtract what the framework
itself wrote. A task's export is not the task's product; it is a render of the
task's own bookkeeping.

ONLY THIS TASK'S OWN EXPORT, NEVER THE WHOLE PROJECTION. Somebody else's export
is a legitimate subject: a planning task that re-parented ten tasks really does
produce those files, and the current verify run does not touch them, so their
hash means exactly what it says. Subtracting all of `tausik/` would zero such a
receipt's coverage and lie about what was checked. Measured in the same session:
`nine-open-tasks-are-invisible-to-release-scope` closed by declaring nine
FOREIGN exports and not its own.

THE ADDRESS IS DERIVED, NEVER LISTED (obligation 1 of #409). The directory comes
from `state_triggers.projection_dirs` — the resolver the exporter itself uses to
decide where a row lands — and the suffix from `state_serialize.MANAGED_SUFFIX`.
The one literal here, `TASK_KIND`, is an entity KIND, not a layout: it is matched
against the directories the exporter reports, so a projection that stopped
holding tasks yields no path rather than a stale guess. A literal
`"tausik/tasks/"` would be a second declaration of the layout, free to drift from
the first (#249).

THE BOUNDARY, SAID OUT LOUD (obligation 2 of #409). Subtraction removes the file
from COVERAGE, so a HAND edit to that same export, made between verify and the
close, stops being noticed. That is the identical honest limit
`gate_verify_first._projection_prefixes` already declares for
`--no-file-changes`, and for the same reason: an uncommitted change carries no
author, so a hand edit inside the projection is byte-for-byte what the exporter
writes. Everything else stays covered — the subtraction reaches exactly one path
and cannot touch source.

FAIL-OPEN IS THE STRICT DIRECTION HERE, WHICH IS WHY IT IS ALLOWED. When the
projection root cannot be resolved these functions subtract NOTHING, and the
callers behave exactly as they did before this module existed: the circular
refusal comes back. An unresolvable layout therefore costs convenience, never
coverage — the opposite of the usual fail-open, where a check that could not run
would sign a pass.

WHAT A CALLER STILL OWES. Subtraction can empty the coverage entirely (a task
that declared its own export and nothing else). `compute_files_hash([])` is a
stable empty-marker that no edit ever moves, so a green recorded against it would
stay valid for its whole TTL across arbitrary tree changes — the exact
stale-green class `verify_cache` and `verify_cached_run` guard with `bool(files)`
on the DECLARED list. That guard stops firing once coverage and declaration can
differ, so every caller of `coverage_files` must re-ask the emptiness question
about the COVERAGE. `declares_own_export` is here so the resulting refusal can
name the one thing the reader needs to know instead of reporting changed files in
general.

THE PARENT STORY, ADDED LATER AND ON PURPOSE (Decision #286,
parent-story-projection-counts-as-undeclared-work). `task start` writes one more
file than the task's own export: it flips `status: open -> active` in
`tausik/stories/<story>.md`. Measured, session #196 — verify #1898 reported
exactly one undeclared file and `git diff` showed exactly that one line. Nobody
wrote it but the lifecycle.

Why this does NOT reopen the "only your own" boundary above. That boundary
protects a foreign entity's projection, which is a real product of a task that
produces records. The parent story of THIS task is not foreign and is not a
product: it changed because this task was activated, and it would change
identically if the agent did nothing else at all. So the subtraction still
reaches only what this task's own lifecycle wrote — the set simply has two
members instead of one.

WHERE THE STORY SLUG COMES FROM, AND WHY NOT THE DATABASE. From the task's own
export, parsed with `state_parse` — the framework's own reader for the
framework's own format. The alternative was a query, and it would have dragged a
connection into a function whose whole job is comparing paths; neither caller of
the scope description holds one. The projection can in principle be stale, and
the two ways it can be are both safe: with auto-export off nothing rewrote the
story file either, so the subtraction finds nothing to remove; and a task moved
between stories has its export rewritten by the move, so a stale `story:` is not
reachable while the projection is live. Under-subtracting leaves a line in the
report; over-subtracting would hide a change, and no path here can do that.

THE EPIC IS NOT SUBTRACTED, AND THAT IS MEASURED RATHER THAN ASSUMED. Across
session #196 — two `task start`, one `task done`, one `task add`, one
`task move` — no epic projection was ever reported changed by git. An epic file
lists its stories, not its tasks, so a task's lifecycle does not touch it. If
that ever changes, it changes here, next to this sentence.
"""

from __future__ import annotations

import os
from typing import Any

# The single entity kind this module speaks about. Not a layout declaration: it
# is looked up among the directories `projection_dirs` reports, so it names a
# kind the exporter agrees exists or it names nothing at all.
TASK_KIND = "tasks"

# The parent story's projection directory, looked up the same way and for the
# same reason: matched against what the exporter reports, never spelled as a
# path (#249).
STORY_KIND = "stories"

# The frontmatter key under which a task's export names its parent story.
_STORY_KEY = "story"


def _projection_path(kind: str, slug: str | None, svc: Any) -> str | None:
    """Absolute, normcased path of `slug`'s file in the `kind` projection dir.

    None whenever the layout does not resolve — the exporter reports no such
    directory, or the resolver raised. None means "subtract nothing".
    """
    if not slug or not isinstance(slug, str):
        return None
    try:
        from state_serialize import MANAGED_SUFFIX
        from state_triggers import projection_dirs

        for directory in projection_dirs(svc):
            if os.path.basename(directory) == kind:
                return os.path.normcase(
                    os.path.abspath(os.path.join(directory, slug + MANAGED_SUFFIX))
                )
    except Exception:  # noqa: BLE001 — an unresolvable layout subtracts nothing
        return None
    return None


def parent_story_slug(task_slug: str, *, svc: Any = None) -> str | None:
    """The story `task_slug` belongs to, read from the task's own export.

    None on every doubt: no export on disk, an unreadable or unparsable file, no
    `story:` key (a task with no parent is the ordinary case). The file is read
    through `state_parse`, the reader the importer uses, so this cannot come to
    disagree with the format the exporter writes.
    """
    path = own_export_abspath(task_slug, svc=svc)
    if not path:
        return None
    try:
        from state_parse import parse_frontmatter, split_file

        with open(path, encoding="utf-8", newline="") as fh:
            fm_text, _body = split_file(fh.read())
        story = parse_frontmatter(fm_text).get(_STORY_KEY)
    except Exception:  # noqa: BLE001 — unreadable projection subtracts nothing
        return None
    return story if isinstance(story, str) and story.strip() else None


def parent_story_abspath(task_slug: str, *, svc: Any = None) -> str | None:
    """Absolute, normcased path of the projection of `task_slug`'s story."""
    return _projection_path(STORY_KIND, parent_story_slug(task_slug, svc=svc), svc)


def own_export_abspath(task_slug: str, *, svc: Any = None) -> str | None:
    """Absolute, normcased path of `task_slug`'s export file, or None.

    None on every doubt — no slug, no resolvable projection root, no directory
    for `TASK_KIND` among the ones the exporter reports, any import failure.
    None means "subtract nothing", which is the pre-existing behaviour.

    `svc` is passed through to `projection_dirs`. The verify path has no
    ProjectService in hand at two of its three call sites, and None is the right
    answer there rather than a defect: with `svc=None` the resolver falls back to
    the ambient `find_tausik_dir()`, which is the SAME base `compute_files_hash`
    resolves the declared relative paths against (`os.getcwd()`). Deriving the
    export path from a different project than the one the coverage paths are read
    from would compare two trees.
    """
    return _projection_path(TASK_KIND, task_slug, svc)


def _resolve(raw: str, base: str) -> str:
    """Normalize one declared path the way `compute_files_hash` reads it.

    Same two steps in the same order — backslashes folded to `/`, then joined
    onto `base` when relative — because a path this module failed to recognize
    would be hashed by the other and the subtraction would silently not happen.
    """
    rel = raw.replace("\\", "/")
    abs_p = rel if os.path.isabs(rel) else os.path.join(base, rel)
    return os.path.normcase(os.path.abspath(abs_p))


def coverage_files(
    file_paths: list[str] | None,
    task_slug: str,
    *,
    svc: Any = None,
    root: str | None = None,
) -> list[str]:
    """`file_paths` minus `task_slug`'s own export. Order preserved.

    `root` mirrors `compute_files_hash(..., root=)`: the base relative declared
    paths are resolved against. Both must be given the same base or one will
    subtract a file the other still hashes.
    """
    files = [f for f in (file_paths or []) if f and isinstance(f, str)]
    own = own_export_abspath(task_slug, svc=svc)
    if not own:
        return files
    base = root or os.getcwd()
    return [f for f in files if _resolve(f, base) != own]


def subtract_own_bookkeeping(
    file_paths: list[str] | None,
    task_slug: str,
    *,
    svc: Any = None,
    root: str | None = None,
) -> tuple[list[str], list[str]]:
    """`file_paths` minus what THIS task's own lifecycle wrote. Order preserved.

    Returns `(kept, removed)`. `removed` carries the paths AS THE CALLER SPELLED
    THEM, not a re-derived form: the caller is reporting on its own list, and a
    message that renames the file it is talking about makes the reader look for
    a second one.

    Two members today — the task's own export and the projection of its parent
    story — and the docstring above says why each is this task's bookkeeping and
    why nothing else is. `coverage_files` deliberately does NOT grow the same
    second member: it feeds the receipt's HASH, where the question is what was
    verified, and the parent story is not something a gate would have run over.
    Here the question is what the AGENT changed, and the answer differs.
    """
    files = [f for f in (file_paths or []) if f and isinstance(f, str)]
    bookkeeping = {
        p
        for p in (
            own_export_abspath(task_slug, svc=svc),
            parent_story_abspath(task_slug, svc=svc),
        )
        if p
    }
    if not bookkeeping:
        return files, []
    base = root or os.getcwd()
    kept: list[str] = []
    removed: list[str] = []
    for raw in files:
        (removed if _resolve(raw, base) in bookkeeping else kept).append(raw)
    return kept, removed


def own_export_display(
    task_slug: str,
    *,
    svc: Any = None,
    root: str | None = None,
) -> str | None:
    """How to SPELL that export in a message, relative to `root`/cwd, or None.

    Refusals name the file, and naming it with a literal `"tausik/tasks/…"` would
    put a third declaration of the layout in prose that no resolver would ever
    correct (#249) — a message is exactly the place a stale path survives longest,
    because nothing executes it. Falls back to the absolute path when the file
    lies outside `root`, which is still true rather than merely tidy.
    """
    own = own_export_abspath(task_slug, svc=svc)
    if not own:
        return None
    base = os.path.abspath(root or os.getcwd())
    try:
        rel = os.path.relpath(own, os.path.normcase(base))
    except ValueError:  # different drive on Windows — no relative form exists
        return own.replace(os.sep, "/")
    if rel.startswith(".."):
        return own.replace(os.sep, "/")
    return rel.replace(os.sep, "/")


def declares_own_export(
    file_paths: list[str] | None,
    task_slug: str,
    *,
    svc: Any = None,
    root: str | None = None,
) -> bool:
    """True iff `file_paths` names `task_slug`'s own export.

    Asked by the refusals, not by the hashes: a coverage that came out empty
    reads very differently to an agent depending on whether its own export was
    the reason, and "your declared files changed" was the message that sent
    session #191 hunting the cache for a defect that was never there.
    """
    files = [f for f in (file_paths or []) if f and isinstance(f, str)]
    return len(coverage_files(files, task_slug, svc=svc, root=root)) != len(files)
