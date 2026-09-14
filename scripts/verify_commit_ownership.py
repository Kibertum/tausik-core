"""Conservative task ownership recovered from committed task exports.

Git timestamps answer *when* a path changed, never *which task* changed it.
For a release branch that commits several independently planned tasks while a
long-running task remains active, treating every later commit as that task's
work makes a narrow verification receipt permanently under-declared.

This module removes only paths whose ownership is proved by immutable commit
history.  The usual proof changes a ``tausik/tasks/<slug>.md`` export and that
committed export declares the path in ``relevant_files``.  A second, equally
bounded proof reads the parent tree: an already active, blocked or done task
may declare a path before its later implementation-only commit.  Task lifecycle
state is not normally file ownership: requiring ``done`` creates a QG-2 cycle
for independently committed tasks that need the verifier in order to close.
Unknown, malformed, ambiguous and uncommitted changes deliberately remain.

Claims are not all of one kind.  A task's own export and its parent story are
*projections* the framework writes for whichever task moved state; a
``relevant_files`` entry or a ``scope_paths`` ACL stored in the same commit is a
*work* claim; a declaration read from the parent tree is a weaker, earlier work
claim.  A path is resolved on the strongest tier that names anyone: one name
there owns it, two or more keep it ambiguous, and a weaker tier is never
consulted once a stronger one has spoken.  Flattening the tiers made every
export moved by a backlog commit ambiguous between itself and the task whose
ACL moved it (151 of 200 paths in one measured commit) -- two independent proofs
that the path is foreign cancelled each other.  A task never holds a work claim
on its own export, whichever field spells it: that file is its projection.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from collections import defaultdict
from fnmatch import fnmatchcase
from typing import Callable

import git_exec
from state_parse import ParseError, parse_frontmatter, split_file
from verify_git_diff import _is_repo_root, _normalize_repo_path

_TASK_PREFIX = "tausik/tasks/"
_TASK_SUFFIX = ".md"
_DYNAMIC_FILES = frozenset({"AGENTS.md", "CLAUDE.md"})
_PREDECLARED_STATUSES = frozenset({"active", "blocked", "done"})
# A generic filename can appear in hundreds of task journals.  Beyond this
# bounded candidate set the historical declaration is not cheap enough to
# inspect during a verification receipt, so it remains undeclared (safe).
_MAX_PARENT_SCOPE_CANDIDATES = 64
# One `git log --name-only` answers "which commits changed which paths" for the
# whole window.  The mark prefixes each commit header so a path can never be
# mistaken for one; a header that is not a hexadecimal hash is dropped.
_COMMIT_MARK = "\x01"
_COMMIT_HASH = re.compile(r"^[0-9a-f]{7,64}$")
_DYNAMIC_BLOCK = re.compile(
    r"<!-- DYNAMIC:START -->.*?<!-- DYNAMIC:END -->", re.DOTALL
)


def _git_text(
    args: list[str], *, base: str, run: Callable[..., subprocess.CompletedProcess]
) -> str | None:
    try:
        out = run(
            args,
            cwd=base,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return (out.stdout or "") if out.returncode == 0 else None


def _task_metadata(blob: str | None) -> dict[str, object] | None:
    if not blob:
        return None
    try:
        frontmatter, _body = split_file(blob)
        return parse_frontmatter(frontmatter)
    except ParseError:
        return None


def _is_dynamic_only_change(previous: str | None, current: str | None) -> bool:
    """True only when one well-formed DYNAMIC block is the whole change."""
    if previous is None or current is None:
        return False
    previous_blocks = _DYNAMIC_BLOCK.findall(previous)
    current_blocks = _DYNAMIC_BLOCK.findall(current)
    if len(previous_blocks) != 1 or len(current_blocks) != 1:
        return False
    return _DYNAMIC_BLOCK.sub("<dynamic>", previous) == _DYNAMIC_BLOCK.sub("<dynamic>", current)


def _commits_with_paths(history: str) -> list[tuple[str, set[str]]]:
    """Parse ``git log --format=<mark>%H --name-only`` into (commit, paths)."""
    commits: list[tuple[str, set[str]]] = []
    current: set[str] | None = None
    for raw in history.splitlines():
        line = raw.strip()
        if line.startswith(_COMMIT_MARK):
            header = line[len(_COMMIT_MARK):].strip()
            current = None
            if _COMMIT_HASH.match(header):
                current = set()
                commits.append((header, current))
        elif line and current is not None:
            current.add(_normalize_repo_path(line))
    return commits


def _scope_path_matches(path: str, scope_paths: object) -> bool:
    """Whether a commit-local task ACL explicitly covers ``path``.

    ``scope_paths`` is the immutable write ACL stored in the same commit, not
    the current worktree.  A malformed entry never matches; glob matching uses
    the repository-normalized spelling used by the rest of this verifier.
    """
    if not isinstance(scope_paths, list):
        return False
    return any(
        isinstance(pattern, str)
        and fnmatchcase(path, _normalize_repo_path(pattern))
        for pattern in scope_paths
    )


def _parent_scope_claimants(
    commit: str,
    path: str,
    *,
    task_slug: str | None,
    base: str,
    run: Callable[..., subprocess.CompletedProcess],
) -> set[str]:
    """Return active sibling slugs that declared ``path`` in ``commit``'s parent.

    ``git grep`` is only a candidate finder; the parent blob is parsed and the
    exact ``relevant_files`` entry is checked before a claimant is returned.
    Reading the parent tree, rather than today's projection, prevents a later
    declaration from retroactively claiming an earlier implementation commit.
    """
    parent = f"{commit}^"
    matches = _git_text(
        ["git", "grep", "-l", "-F", "--", path, parent, "--", "tausik/tasks"],
        base=base,
        run=run,
    )
    if matches is None:
        return set()
    claimants: set[str] = set()
    candidate_exports = matches.splitlines()
    if len(candidate_exports) > _MAX_PARENT_SCOPE_CANDIDATES:
        return set()
    for match in candidate_exports:
        _revision, separator, export_path = match.partition(":")
        if not separator or not export_path.startswith(_TASK_PREFIX) or not export_path.endswith(_TASK_SUFFIX):
            continue
        parent_metadata = _task_metadata(
            _git_text(["git", "show", f"{parent}:{export_path}"], base=base, run=run)
        )
        if not parent_metadata:
            continue
        slug = parent_metadata.get("slug")
        status = parent_metadata.get("status")
        declared = parent_metadata.get("relevant_files")
        if (
            not isinstance(slug, str)
            or slug == task_slug
            or export_path == path
            or status not in _PREDECLARED_STATUSES
            or not isinstance(declared, list)
        ):
            continue
        if path in {_normalize_repo_path(str(item)) for item in declared}:
            claimants.add(slug)
    return claimants



def foreign_completed_paths_since(
    task_started_at: str,
    task_slug: str | None,
    *,
    changed_paths: set[str],
    root: str | None = None,
    runner: Callable[..., subprocess.CompletedProcess] | None = None,
) -> set[str]:
    """Return paths conclusively owned by another task's committed export.

    An empty result means either no such proof exists or ownership could not be
    inspected.  That degradation is safe: callers retain the original strict
    git comparison.  A path claimed by two completed tasks is ambiguous and is
    retained as well.
    """
    if not task_started_at or not task_slug:
        return set()
    base = root or os.getcwd()
    if runner is None and shutil.which("git") is None:
        return set()
    if not _is_repo_root(base):
        return set()
    run = runner or git_exec.run_git
    history = _git_text(
        ["git", "log", f"--since={task_started_at}", f"--format={_COMMIT_MARK}%H", "--name-only"],
        base=base,
        run=run,
    )
    if history is None:
        return set()

    claimants: dict[str, set[str]] = defaultdict(set)
    ambiguous: set[str] = set()
    for commit, changed in _commits_with_paths(history):
        # A commit that touches nothing under inspection can claim nothing:
        # skipping it is what keeps a long-lived task from paying one `git
        # show` per export for every commit of the window (measured: 630
        # commits, 168 s, on a one-path inspection).
        inspected = changed & changed_paths
        if not inspected:
            continue
        same_commit: dict[str, set[str]] = defaultdict(set)
        projection: dict[str, set[str]] = defaultdict(set)
        for path in inspected & _DYNAMIC_FILES:
            previous_blob = _git_text(["git", "show", f"{commit}^:{path}"], base=base, run=run)
            current_blob = _git_text(["git", "show", f"{commit}:{path}"], base=base, run=run)
            if _is_dynamic_only_change(previous_blob, current_blob):
                projection[path].add("__dynamic_projection__")
        task_exports = sorted(
            path for path in changed if path.startswith(_TASK_PREFIX) and path.endswith(_TASK_SUFFIX)
        )
        for export_path in task_exports:
            current = _task_metadata(
                _git_text(["git", "show", f"{commit}:{export_path}"], base=base, run=run)
            )
            if not current:
                continue
            slug = current.get("slug")
            if (
                not isinstance(slug, str)
                or slug == task_slug
            ):
                continue
            # These projections are framework output of the commit-local
            # ownership proof, not undeclared work by the task being verified.
            if export_path in inspected:
                projection[export_path].add(slug)
            story = current.get("story")
            if isinstance(story, str) and story:
                story_path = f"tausik/stories/{story}.md"
                if story_path in inspected:
                    projection[story_path].add(slug)
            declared = current.get("relevant_files")
            owned = (
                {_normalize_repo_path(str(path)) for path in declared}
                if isinstance(declared, list)
                else set()
            )
            for path in (owned & inspected) - {export_path}:
                same_commit[path].add(slug)
            for path in inspected - {export_path}:
                if (
                    current.get("status") in _PREDECLARED_STATUSES
                    and _scope_path_matches(path, current.get("scope_paths"))
                ):
                    same_commit[path].add(slug)
        for path in inspected:
            # Strongest tier that names anyone decides; weaker tiers are not
            # consulted, so a projection cannot compete with a work claim and
            # the parent tree is only read when the commit itself is silent.
            owners = same_commit.get(path, set())
            if not owners:
                owners = _parent_scope_claimants(
                    commit, path, task_slug=task_slug, base=base, run=run
                )
            if not owners:
                owners = projection.get(path, set())
            if len(owners) == 1:
                claimants[path].update(owners)
            elif owners:
                ambiguous.add(path)
    return set(claimants).difference(ambiguous)
