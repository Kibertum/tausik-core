"""Where a task's "what changed" is measured FROM: a git snapshot, not a clock.

scope-gate-baseline-never-moves-after-first-start (Sortula #49 / core#10,
decision #390). The scope-honesty gate measured `git log --since=<started_at>`
plus every uncommitted change in the tree. A task that lived two days measured
everybody's commits of those two days (576 files at the consumer; 2690 here for
release-18-breaking-change-notes), and in a shared dirty tree every task
measured the whole tree.

The anchor is a git object instead of a time:

* at FIRST activation, `git stash create` records the working tree as it is —
  committed and uncommitted — without touching it (HEAD when the tree is clean);
* the object is kept alive by `refs/tausik/baseline/<slug>` (not pushed by
  default, so it never leaves the machine);
* "what changed" is `git diff --name-only <anchor>`: the snapshot against the
  working tree now — work that was already dirty before the task started no
  longer counts as the task's;
* a RESUME (start of a blocked task, unblock) re-anchors, and says so in the
  journal: resetting the measure is an event, not a side effect.

Outside a git repository every function answers None and the callers keep the
old time-based measure.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any

import git_exec

_REF = "refs/tausik/baseline/"


def _git(root: str, *args: str) -> subprocess.CompletedProcess | None:
    if shutil.which("git") is None or not os.path.exists(os.path.join(root, ".git")):
        return None
    try:
        return git_exec.run_git(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            check=False,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def anchor(root: str, slug: str) -> str | None:
    """Snapshot the working tree for `slug`; return the anchor SHA or None."""
    # The snapshot is a commit object, so git wants an identity; a machine or CI
    # runner without one must not silently fall back to HEAD.
    ident = ("-c", "user.name=tausik", "-c", "user.email=tausik@localhost")
    made = _git(root, *ident, "stash", "create", f"tausik baseline {slug}")
    sha = (made.stdout or "").strip() if made is not None and made.returncode == 0 else ""
    if not sha:
        head = _git(root, "rev-parse", "HEAD")
        if head is None or head.returncode != 0:
            return None
        sha = (head.stdout or "").strip()
    if not sha:
        return None
    ref = _git(root, "update-ref", _REF + slug, sha)
    return sha if ref is not None and ref.returncode == 0 else None


def baseline_of(root: str, slug: str) -> str | None:
    """The anchor SHA recorded for `slug`, or None."""
    got = _git(root, "rev-parse", "--verify", "--quiet", _REF + slug + "^{commit}")
    if got is None or got.returncode != 0:
        return None
    return (got.stdout or "").strip() or None


def changed_since_anchor(root: str, sha: str) -> set[str] | None:
    """Tracked paths that differ between the anchor and the working tree now."""
    got = _git(root, "diff", "--name-only", sha)
    if got is None or got.returncode != 0:
        return None
    return {ln.strip().replace("\\", "/") for ln in (got.stdout or "").splitlines() if ln.strip()}


def on_activation(be: Any, tausik_dir: str, slug: str, *, first: bool) -> str | None:
    """Anchor at first activation; re-anchor on resume and journal it.

    Never raises: a missing git or a failed call leaves the old time-based
    measure in place, which is the stricter of the two.
    """
    root = os.path.dirname(os.path.abspath(tausik_dir))
    before = None if first else baseline_of(root, slug)
    sha = anchor(root, slug)
    if sha is None or first:
        return None
    note = (
        f"BASELINE re-anchored on resume: {(before or 'none')[:12]} -> {sha[:12]}. "
        "Changes made before this point no longer count as this task's scope."
    )
    try:
        be.task_append_notes(slug, note)
    except Exception:  # noqa: BLE001 — the anchor stands; only the journal line failed
        return None
    return note


def release(tausik_dir: str, slug: str) -> None:
    """Drop the anchor ref once the task is closed (the object may then be pruned)."""
    root = os.path.dirname(os.path.abspath(tausik_dir))
    _git(root, "update-ref", "-d", _REF + slug)
