"""Conservative task ownership recovered from committed task exports.

Git timestamps answer *when* a path changed, never *which task* changed it.
For a release branch that commits several independently planned tasks while a
long-running task remains active, treating every later commit as that task's
work makes a narrow verification receipt permanently under-declared.

This module removes only paths whose ownership is proved by the same commit:
it must change a ``tausik/tasks/<slug>.md`` export, and the committed export
must declare the path in ``relevant_files``.  Task lifecycle state is not file
ownership: requiring ``done`` creates a QG-2 cycle for independently committed
tasks that need the verifier in order to close.
Unknown, malformed, ambiguous and uncommitted changes deliberately remain.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from collections import defaultdict
from typing import Callable

import git_exec
from state_parse import ParseError, parse_frontmatter, split_file
from verify_git_diff import _is_repo_root, _normalize_repo_path

_TASK_PREFIX = "tausik/tasks/"
_TASK_SUFFIX = ".md"
_DYNAMIC_FILES = frozenset({"AGENTS.md", "CLAUDE.md"})
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
    commits = _git_text(
        ["git", "log", f"--since={task_started_at}", "--format=%H"], base=base, run=run
    )
    if commits is None:
        return set()

    claimants: dict[str, set[str]] = defaultdict(set)
    for commit in (line.strip() for line in commits.splitlines()):
        if not commit:
            continue
        names = _git_text(
            ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit],
            base=base,
            run=run,
        )
        if names is None:
            continue
        changed = {_normalize_repo_path(line) for line in names.splitlines() if line.strip()}
        for path in changed & _DYNAMIC_FILES:
            previous_blob = _git_text(["git", "show", f"{commit}^:{path}"], base=base, run=run)
            current_blob = _git_text(["git", "show", f"{commit}:{path}"], base=base, run=run)
            if _is_dynamic_only_change(previous_blob, current_blob):
                claimants[path].add("__dynamic_projection__")
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
            declared = current.get("relevant_files")
            if not isinstance(declared, list):
                continue
            owned = {_normalize_repo_path(str(path)) for path in declared}
            # These projections are framework output of the commit-local
            # ownership proof, not undeclared work by the task being verified.
            owned.add(export_path)
            story = current.get("story")
            if isinstance(story, str) and story:
                owned.add(f"tausik/stories/{story}.md")
            for path in owned & changed_paths & changed:
                claimants[path].add(slug)
    return {path for path, owners in claimants.items() if len(owners) == 1}
