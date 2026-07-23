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


def _is_repo_root(base: str) -> bool:
    """True when *base* holds a git repository.

    `.git` is a DIRECTORY in an ordinary clone but a FILE (a gitdir pointer) in
    a linked worktree or a submodule. Testing only for a directory declared
    both of those "not a repo" — and since every consumer here treats "not a
    repo" as unverifiable and then fails closed, an agent working in a git
    worktree (the standard isolation for parallel agents, and something this
    harness ships tooling for) could close no fileless task and pass no
    changelog check at all. Existence is the right question.
    """
    return os.path.exists(os.path.join(base, ".git"))


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
    if not _is_repo_root(base):
        return None
    run = runner or subprocess.run
    changed: set[str] = set()
    try:
        # stdin=DEVNULL is critical: when these git calls run inside the MCP
        # project server's worker thread, they would otherwise inherit the
        # MCP server's stdin (a JSON-RPC pipe to the IDE). On Windows git can
        # block trying to read that stdin (paginator probe / credential prompt
        # detection / something else), making every `task done` look like a
        # silent 10s hang per call. See defect v14b-defect-mcp-task-done-stdin-hang.
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
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
            stdin=subprocess.DEVNULL,
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
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
            stdin=subprocess.DEVNULL,
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


def uncommitted_changes(
    paths: list[str] | None = None,
    *,
    root: str | None = None,
    runner: Callable[..., subprocess.CompletedProcess] | None = None,
) -> list[str] | None:
    """Return paths with uncommitted changes (`git status --porcelain`).

    Restricted to `paths` (a git pathspec) when given, else the whole tree.
    An EMPTY list is a positive fact: the scope is provably clean. Untracked
    files count (they appear as ``??``); gitignored paths do not (so `.tausik/`
    decisions and the DB never register as changes) — which is exactly right
    for qg2-cannot-close-fileless-task: a task that only wrote to the framework
    DB leaves the git scope clean.

    Returns None when the answer cannot be computed:
      - git executable not found on PATH
      - `root` has no .git (not a repo)
      - the git call returns non-zero or raises

    None means "unverifiable" and MUST NOT be read as clean. The fileless-close
    path fails closed on None — a declaration that git cannot back does not
    close a task (verify_scope_honesty tri-state, memory #221).

    Why `git status --porcelain` and not `changed_files_since`: the latter
    unions `git log --since=<task start>`, which sweeps in commits made by
    OTHER tasks after this one started (the release-accumulation workflow). A
    fileless task's global change-set is then never empty and it could never
    close. Porcelain judges only what is uncommitted here and now — the scope
    the closing agent is actually responsible for. `runner` is injectable for
    tests (defaults to `subprocess.run`).
    """
    base = root or os.getcwd()
    if runner is None and shutil.which("git") is None:
        return None
    if not _is_repo_root(base):
        return None
    run = runner or subprocess.run
    pathspec = [_normalize_repo_path(p) for p in (paths or []) if p and p.strip()]
    cmd = ["git", "status", "--porcelain"]
    if pathspec:
        cmd += ["--", *pathspec]
    try:
        # stdin=DEVNULL for the same MCP-worker-thread reason as
        # changed_files_since — inheriting the JSON-RPC pipe can hang git.
        out = run(
            cmd,
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
    if out.returncode != 0:
        return None
    dirty: set[str] = set()
    for line in (out.stdout or "").splitlines():
        if not line.strip():
            continue
        # Porcelain v1 line: "XY <path>" (XY = 2 status chars + a space).
        # Renames/copies render as "old -> new"; record the new path (what the
        # working tree now holds) so the message names a real file.
        payload = line[3:] if len(line) > 3 else line.strip()
        if " -> " in payload:
            payload = payload.split(" -> ", 1)[1]
        norm = _normalize_repo_path(payload)
        if norm:
            dirty.add(norm)
    return sorted(dirty)


def _added_nonblank_paths(diff_text: str) -> set[str]:
    """Paths in a unified diff that gain at least one NON-BLANK added line."""
    found: set[str] = set()
    current: str | None = None
    for line in (diff_text or "").splitlines():
        if line.startswith("+++ "):
            target = line[4:].strip()
            if target == "/dev/null":
                current = None
            else:
                if target.startswith(("a/", "b/")):
                    target = target[2:]
                current = _normalize_repo_path(target) or None
            continue
        if line.startswith(("--- ", "@@", "diff ", "index ", "new file", "deleted file")):
            continue
        # A real added line: "+" followed by content that is not just spaces.
        if current and line.startswith("+") and line[1:].strip():
            found.add(current)
    return found


def files_with_substantive_additions(
    paths: list[str],
    *,
    root: str | None = None,
    since: str | None = None,
    runner: Callable[..., subprocess.CompletedProcess] | None = None,
) -> set[str] | None:
    """Subset of *paths* whose uncommitted diff ADDS at least one non-blank line.

    `uncommitted_changes` answers "did these bytes change", which is not the
    question a content policy asks. Appending a blank line to a file makes it
    dirty without adding anything — enough to satisfy a byte-level check and
    nothing else. This helper judges the diff CONTENT: a path qualifies only
    when the patch introduces a line with actual characters on it.

    Covers both tracked edits (`git diff HEAD`, so staged and unstaged alike)
    and brand-new untracked files (`git ls-files --others`), whose whole
    content is an addition and which `git diff` therefore never reports.

    `since` (an ISO timestamp, normally the task's `started_at`) additionally
    counts additions already COMMITTED during the task. Without it, a caller
    that commits before closing — which is exactly what the `/ship` skill does,
    commit at step 7 and close at step 8 — sees an empty working tree and reads
    it as "nothing was written", blocking the canonical path and teaching the
    escape flag as the normal way to close. Scoped by time rather than by
    author, so in a release-accumulation workflow another task's commit inside
    the same window can satisfy the check; that is a deliberately weaker
    guarantee than "this task wrote it", and far better than a rule whose only
    passable route is its own bypass.

    Returns None on the same "cannot compute" conditions as `uncommitted_changes`
    (no git, no repo, non-zero exit, subprocess error). None means UNVERIFIABLE
    and must not be read as "nothing substantive" — callers fail closed.
    """
    base = root or os.getcwd()
    if runner is None and shutil.which("git") is None:
        return None
    if not _is_repo_root(base):
        return None
    run = runner or subprocess.run
    pathspec = [_normalize_repo_path(p) for p in (paths or []) if p and p.strip()]
    if not pathspec:
        return set()

    def _git(cmd: list[str]) -> str | None:
        try:
            # stdin=DEVNULL for the MCP-worker-thread reason documented on
            # changed_files_since — an inherited JSON-RPC pipe can hang git.
            out = run(
                cmd,
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
        return out.stdout or "" if out.returncode == 0 else None

    diff_text = _git(["git", "diff", "--unified=0", "--no-color", "HEAD", "--", *pathspec])
    if diff_text is None:
        # An unborn HEAD (a repo with no commit yet) makes `git diff HEAD` fail
        # while the staged diff is perfectly readable. Anything else that fails
        # both ways stays unverifiable.
        diff_text = _git(["git", "diff", "--unified=0", "--no-color", "--cached", "--", *pathspec])
        if diff_text is None:
            return None
    substantive = _added_nonblank_paths(diff_text)

    if since:
        log_text = _git(
            [
                "git",
                "log",
                f"--since={since}",
                "--unified=0",
                "--no-color",
                "--patch",
                "--format=",
                "--",
                *pathspec,
            ]
        )
        if log_text is None:
            return None
        substantive |= _added_nonblank_paths(log_text)

    others = _git(["git", "ls-files", "--others", "--exclude-standard", "--", *pathspec])
    if others is None:
        return None
    for line in others.splitlines():
        rel = _normalize_repo_path(line)
        if not rel:
            continue
        try:
            with open(os.path.join(base, rel), encoding="utf-8", errors="replace") as fh:
                if any(chunk.strip() for chunk in fh):
                    substantive.add(rel)
        except OSError:
            # Listed by git but unreadable now — unverifiable, not "empty".
            return None
    return substantive


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
