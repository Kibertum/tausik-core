"""Git-diff cross-check helpers for verify cache.

v1.3.4 fix-verify-cache-relevant-files-bypass: prevent the bypass where an
agent declares `relevant_files=[docs/x.md]` while actually editing
`scripts/auth.py`. The verify cache (10-min TTL) hashes only the *declared*
files, so misreporting yielded a stale-green that skipped the security check.

This module supplies the cross-check: union files committed since the task
started + currently uncommitted, then refuse cache when the declared set is
a strict subset of the actual changes (i.e. agent under-declared).

Lives separately from `service_verification.py` for filesize gate compliance
and so the git/subprocess dependency is contained.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Callable


def _normalize_repo_path(raw: str) -> str:
    """Normalize a path string for set comparison against git output.

    git always emits forward slashes; declared paths may use backslashes on
    Windows. Strip leading './' that git also strips. Empty string after
    normalization is filtered by callers.
    """
    s = (raw or "").replace("\\", "/").strip()
    while s.startswith("./"):
        s = s[2:]
    return s


def changed_files_since(
    task_created_at: str,
    *,
    root: str | None = None,
    runner: Callable[..., subprocess.CompletedProcess] | None = None,
) -> set[str] | None:
    """Return set of git-tracked file paths changed since task_created_at.

    Combines two queries:
      1. `git log --since=<task_created_at> --name-only --pretty=format:`
         — files in commits since the task started.
      2. `git diff --name-only HEAD` — currently uncommitted changes.

    Paths are normalized to forward slashes (git already uses them, but the
    set is union-friendly).

    Returns None when:
      - task_created_at is empty/None (caller passed nothing)
      - git executable not found on PATH
      - root has no .git (not a git repo or any ancestor)
      - any git invocation returns non-zero exit code
      - subprocess raises (timeout, OSError, etc.)

    None signals "skip the cross-check" — defensive degradation per
    fix-verify-cache-relevant-files-bypass AC #5 (don't break non-git users).

    `runner` is injectable for tests (defaults to `subprocess.run`).
    """
    if not task_created_at:
        return None
    base = root or os.getcwd()
    # When a runner is injected (tests), skip the system-git probe: the runner
    # is responsible for simulating git output. The .git-dir check still runs
    # so the test can simulate non-git via tmp_path without .git.
    if runner is None and shutil.which("git") is None:
        return None
    if not os.path.isdir(os.path.join(base, ".git")):
        return None
    run = runner or subprocess.run
    changed: set[str] = set()
    try:
        log_out = run(
            [
                "git",
                "log",
                f"--since={task_created_at}",
                "--name-only",
                "--pretty=format:",
            ],
            cwd=base,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if log_out.returncode != 0:
            return None
        for line in (log_out.stdout or "").splitlines():
            line = line.strip()
            if line:
                changed.add(_normalize_repo_path(line))
        diff_out = run(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=base,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if diff_out.returncode != 0:
            return None
        for line in (diff_out.stdout or "").splitlines():
            line = line.strip()
            if line:
                changed.add(_normalize_repo_path(line))
    except (OSError, subprocess.SubprocessError):
        return None
    changed.discard("")
    return changed


def is_declared_consistent_with_git_diff(
    declared_files: list[str],
    task_created_at: str,
    *,
    root: str | None = None,
    runner: Callable[..., subprocess.CompletedProcess] | None = None,
) -> bool:
    """True iff declared_files covers all git-changed files since task_created_at.

    Returns True (cache may proceed) when:
      - changed_files_since returns None (not in git, or any git failure) —
        defensive fallback per AC #5
      - actual changes set is empty (nothing to compare against)
      - declared_set ⊇ actual_set (agent declared everything that changed,
        possibly more — over-declaration is fine)

    Returns False (cache must refuse) when:
      - declared_set is a strict subset of actual_set, i.e. there exists
        at least one file in actual_set that is NOT in declared_set —
        the agent under-declared. This is the bypass vector: agent claims
        relevant_files=[docs/x.md] while editing scripts/auth.py would
        otherwise produce a stale-green via the existing files_hash check.
    """
    actual = changed_files_since(task_created_at, root=root, runner=runner)
    if actual is None:
        return True
    if not actual:
        return True
    declared_set = {_normalize_repo_path(s) for s in (declared_files or []) if s}
    declared_set.discard("")
    missing = actual - declared_set
    return not missing
