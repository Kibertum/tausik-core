"""Fileless QG-2 close — git proof for `--no-file-changes` / `--external-evidence`.

Extracted from `gate_verify_first` so the verify-first module stays under the
filesize cap while the fileless path can grow (out-of-repo evidence flag).
"""

from __future__ import annotations

import os
from typing import Any

from gate_block import _block
from tausik_utils import cli_invocation

_CLI = cli_invocation()


def _projection_prefixes(svc: Any) -> tuple[str, ...]:
    """Repo-relative prefixes that the framework's OWN state export writes into.

    Derived, never listed: `state_triggers.projection_dirs` answers where the
    exporter puts things, and this only rebases those absolute paths onto the
    repository root that porcelain output is relative to. Adding a projected kind
    therefore cannot leave this check behind.

    NAMED BOUNDARY — the honest limit of the exclusion. A file inside these
    directories that a HAND wrote is byte-for-byte the same kind of thing as one
    the auto-export wrote, and an uncommitted change carries no author, so the two
    cannot be told apart. A hand edit to `tausik/tasks/x.md` does ride through a
    `--no-file-changes` close. This is stated rather than hidden because the
    alternative — an unreachable flag — was measurably worse, and because the
    excluded tree holds the framework's bookkeeping, not the product's code.
    Everything else under `tausik/` (a hand-maintained `gates.json`, a README) is
    OUTSIDE the exclusion and still blocks.

    Returns `()` when the projection root or the repository root cannot be
    resolved: nothing is excluded and the check behaves exactly as before.
    """
    try:
        from state_triggers import projection_dirs
        from verify_git_diff import repo_root

        dirs = projection_dirs(svc)
        if not dirs:
            return ()
        base = repo_root(os.path.dirname(os.path.dirname(dirs[0])))
        if not base:
            return ()
        prefixes = []
        for d in dirs:
            rel = os.path.relpath(d, base).replace(os.sep, "/")
            if rel.startswith(".."):
                return ()
            prefixes.append(rel.rstrip("/") + "/")
        return tuple(prefixes)
    except Exception:  # noqa: BLE001 — an unresolvable layout excludes nothing
        return ()


def roadmap_is_generated(svc: Any, project_root: str) -> bool:
    """True iff ROADMAP.md is byte-equal to what the generator renders now.

    A status change reissues ROADMAP.md, and a fileless close then saw the file dirty
    and refused: the framework's own output blocked the close it had just caused. Only
    an EXACT match is the generator's; a hand edit differs and still counts as work.
    """
    try:
        path = os.path.join(project_root, "ROADMAP.md")
        with open(path, encoding="utf-8", newline="") as fh:
            current = fh.read()
        from state_triggers import _ROADMAP_MARK

        if _ROADMAP_MARK not in current[:512]:
            return False
        import release_roadmap

        return release_roadmap.render(svc.be._conn) == current
    except Exception:  # noqa: BLE001 — unknown is not "generated": the file stays dirty
        return False


def enforce_no_file_changes(
    svc: Any,
    report: dict[str, Any],
    slug: str,
    relevant_files: list[str] | None,
    *,
    external_evidence: bool = False,
) -> None:
    """Prove — via git, not the agent's word — that the declared scope has no
    uncommitted changes, for a `task done --no-file-changes` close.

    Clean scope → allowed; the countable record is left for _task_done_report
    to write in the status=done transaction. Dirty scope, unavailable git, or a
    service with no project directory → blocked, fail-closed: a declaration git
    cannot back must never close a task (verify_scope_honesty tri-state).

    ``external_evidence`` is the out-of-repo close path: evidence and file work
    live outside this git tree, so the host working tree is not the subject.
    Empty ``relevant_files`` without this flag still means the whole tree.
    """
    from verify_git_diff import uncommitted_changes

    tausik_dir = getattr(svc, "tausik_dir", None)
    if not callable(tausik_dir):
        _block(
            report,
            "verify-first",
            f"QG-2: task '{slug}' declares --no-file-changes, but this service "
            f"exposes no project directory to scope the git check to. Cannot "
            f"prove an empty scope — fail-closed.",
            f"{_CLI} task done {slug} --ac-verified --relevant-files <paths...>",
        )
        return
    if external_evidence:
        if relevant_files:
            _block(
                report,
                "verify-first",
                f"QG-2: task '{slug}' declares --external-evidence together with "
                f"--relevant-files. Out-of-repo evidence cannot also declare an "
                f"in-tree pathspec — drop one of the two.",
                f"{_CLI} task done {slug} --ac-verified --no-file-changes --external-evidence",
            )
            return
        svc.be.task_append_notes(
            slug,
            "Verify-First: --external-evidence — host-tree dirty check skipped "
            "(evidence outside this git); no gates run (nothing to gate).",
        )
        return
    root = os.path.dirname(tausik_dir())
    dirty = uncommitted_changes(relevant_files, root=root)
    if dirty:
        excluded = _projection_prefixes(svc)
        if excluded:
            dirty = [p for p in dirty if not p.startswith(excluded)]
        if dirty and "ROADMAP.md" in dirty:
            if roadmap_is_generated(svc, root):
                dirty = [p for p in dirty if p != "ROADMAP.md"]
    scope_desc = (
        "declared paths " + ", ".join(relevant_files) if relevant_files else "the working tree"
    )
    remediation = f"{_CLI} task done {slug} --ac-verified --relevant-files <paths...>"
    if dirty is None:
        _block(
            report,
            "verify-first",
            f"QG-2: task '{slug}' declares --no-file-changes, but git could not "
            f"verify it (not a repo, git missing, or the call failed). An "
            f"unprovable empty scope is 'unknown', not 'verified empty' — "
            f"fail-closed. Fix git, or declare the files this task touched.",
            remediation,
        )
        return
    if dirty:
        shown = ", ".join(dirty[:10])
        more = "" if len(dirty) <= 10 else f" (+{len(dirty) - 10} more)"
        _block(
            report,
            "verify-first",
            f"QG-2: task '{slug}' declares --no-file-changes, but git reports "
            f"uncommitted changes in {scope_desc}: {shown}{more}. Either these "
            f"files ARE this task's work — declare them and drop the flag — or "
            f"they are earlier uncommitted work: commit/stash it, then close.",
            remediation,
        )
        return
    svc.be.task_append_notes(
        slug,
        f"Verify-First: --no-file-changes verified — git scope clean "
        f"({scope_desc}), no gates run (nothing to gate).",
    )
