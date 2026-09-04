"""Memory hygiene operations (archive + dedupe).

Extracted from service_knowledge.py to keep that file under the 400-line gate.
Mirrors the service_knowledge_aggregates.py split pattern: thin delegators
in KnowledgeMixin, real logic here.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Callable

from tausik_utils import ServiceError

if TYPE_CHECKING:
    from project_backend import SQLiteBackend


def archive_memory(be: SQLiteBackend, before: str, confirm: bool = False) -> dict[str, Any]:
    """Soft-archive memory rows whose ``created_at`` is older than ``before``.

    ``before`` is a duration string like ``"90d"`` / ``"12w"`` / ``"2m"`` /
    ``"1y"``. Without ``confirm=True`` returns a dry-run preview; with
    ``confirm=True`` the matching rows get a ``archived_at`` timestamp
    (idempotent — already-archived rows are skipped).
    """
    from memory_cleanup import parse_duration_to_days

    try:
        days = parse_duration_to_days(before)
    except ValueError as e:
        raise ServiceError(str(e)) from e
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    if confirm:
        # Ids are read BEFORE applying: afterwards the rows carry archived_at and
        # the candidate query no longer returns them. The caller needs them to drop
        # those files from the git projection, which excludes archived rows. Ids,
        # not slugs — the candidate projection does not select a slug column, and
        # the id still resolves to one after the row is archived.
        doomed = [r["id"] for r in be.memory_archive_candidates(cutoff) if r.get("id")]
        archived = be.memory_archive_apply(cutoff)
        return {
            "archived": archived,
            "archived_ids": doomed,
            "before_days": days,
            "cutoff": cutoff,
            "applied": True,
        }
    candidates = be.memory_archive_candidates(cutoff)
    return {
        "archived": 0,
        "candidates": candidates,
        "before_days": days,
        "cutoff": cutoff,
        "applied": False,
    }


def dedupe_memory(be: SQLiteBackend, threshold: float = 0.85, n: int = 200) -> list[dict[str, Any]]:
    """Suggest memory pairs with similarity ≥ ``threshold`` (0 < t ≤ 1).

    Compares unarchived rows in pairs (same ``type`` only) using
    SequenceMatcher over ``title || content``. Returns suggestions sorted
    by descending ratio. Read-only — does not delete or merge.
    """
    from memory_cleanup import find_dedupe_candidates

    if not (0.0 < threshold <= 1.0):
        raise ServiceError(f"threshold must be in (0, 1], got {threshold!r}")
    rows = be.memory_list(n=n, include_archived=False)
    return find_dedupe_candidates(rows, threshold)


def git_ignore_probe(repo_root: str) -> Callable[[str], bool]:
    """A cached `git check-ignore` for one repository.

    FAILS OPEN. When git cannot be reached or refuses to answer, the path is
    reported as NOT ignored, so the finding survives. The opposite default
    would let a broken git turn the whole stale_file detector off silently,
    which is the failure this module's half of the fix exists to prevent.
    """
    import subprocess

    cache: dict[str, bool] = {}

    def probe(path: str) -> bool:
        if path not in cache:
            try:
                proc = subprocess.run(  # noqa: S603 - fixed argv, shell=False
                    ["git", "check-ignore", "-q", "--", path],
                    cwd=repo_root,
                    capture_output=True,
                    stdin=subprocess.DEVNULL,
                    timeout=10,
                    check=False,
                )
                cache[path] = proc.returncode == 0
            except (OSError, subprocess.SubprocessError):
                cache[path] = False
        return cache[path]

    return probe


def lint_memory(
    be: SQLiteBackend,
    apply: bool = False,
    n: int = 500,
    file_exists: Callable[[str], bool] | None = None,
) -> dict[str, Any]:
    """Lint the active memory set for contradictions / superseded / stale files.

    Dry-run by default: returns ``{findings, applied:False, archived:0}``. With
    ``apply=True`` the unambiguous ``superseded`` findings are archived (the
    superseding entry already replaces them); contradictions and stale-file
    hits are advisory-only — they need human judgement, so ``apply`` never
    auto-archives them. ``file_exists`` defaults to repo-relative existence.

    A git-IGNORED path is absent by design, so it is not reported as stale; the
    probe is skipped when ``file_exists`` is injected, because a caller that
    supplied its own filesystem is not describing this repository.
    """
    from memory_cleanup import find_lint_candidates

    rows = be.memory_list(n=n, include_archived=False)
    edges = be.edge_list(relation="contradicts", n=n) + be.edge_list(relation="supersedes", n=n)
    check = file_exists if file_exists is not None else os.path.exists
    ignored = git_ignore_probe(os.getcwd()) if file_exists is None else None
    findings = find_lint_candidates(rows, edges, check, ignored)

    archived = 0
    if apply:
        superseded_ids = sorted({f["id"] for f in findings if f["kind"] == "superseded"})
        archived = be.memory_archive_ids(superseded_ids)
    return {"findings": findings, "applied": apply, "archived": archived, "count": len(findings)}
