"""Refuse to sign a worktree whose bytes differ from the repository's.

A signature covers raw file bytes (decision #129 — no normalisation). git may
hand the worktree different bytes than it stores, most commonly via
`core.autocrlf`, and then a manifest signed here reproduces nowhere else: the
consumer clones, gets the repository's bytes, recomputes different hashes and
refuses the skill with "modified: SKILL.md" though nobody touched the file.

`git status` cannot detect this — with `core.autocrlf=true` it normalises before
comparing and reports the tree clean. `git ls-files --eol` reports `i/lf w/crlf`,
which is indicative but only covers end-of-line filters. Comparing the worktree
bytes against `git cat-file blob :<path>` is exact and also catches ident
expansion, LFS smudge, and any other clean/smudge filter.
"""

from __future__ import annotations

import os
import subprocess

_GIT_TIMEOUT = 30


class WorktreeDriftError(Exception):
    """Worktree bytes differ from the bytes the repository stores."""


def _git(cwd: str, *args: str, binary: bool = False):
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=not binary,
        timeout=_GIT_TIMEOUT,
        stdin=subprocess.DEVNULL,
    )


def is_git_worktree(path: str) -> bool:
    """True when `path` sits inside a git worktree."""
    try:
        result = _git(path, "rev-parse", "--is-inside-work-tree")
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False
    return result.returncode == 0 and result.stdout.strip() == "true"


def _index_prefix(artifact_dir: str) -> str | None:
    """`artifact_dir` as git names it, relative to the repo root, '/'-separated.

    Deliberately asks git instead of doing `os.path.relpath` against
    `--show-toplevel`: on Windows the toplevel comes back as a long path
    (`C:/Users/ayumashev/...`) while `artifact_dir` may be the 8.3 short form
    (`AYUMAS~1`), and relpath between the two produces nonsense.
    """
    try:
        result = _git(artifact_dir, "rev-parse", "--show-prefix")
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _tracked_files(artifact_dir: str) -> set[str] | None:
    """Repo-root-relative paths git tracks under `artifact_dir`."""
    try:
        result = _git(artifact_dir, "ls-files", "-z", "--full-name", "--", ".")
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    if result.returncode != 0:
        return None
    return {p for p in result.stdout.split("\0") if p}


def drifted_files(artifact_dir: str, rel_paths: list[str]) -> list[str]:
    """Paths (relative to artifact_dir) whose worktree bytes != repository bytes.

    Untracked files have no blob to compare against and are skipped: they are new
    content, not converted content. Outside a git repo, returns [] — signing an
    unpacked tarball is legitimate and there is nothing to compare with.
    """
    if not is_git_worktree(artifact_dir):
        return []
    prefix = _index_prefix(artifact_dir)
    tracked = _tracked_files(artifact_dir)
    if prefix is None or tracked is None:
        return []

    drifted: list[str] = []
    for rel in rel_paths:
        full = prefix + rel
        if full not in tracked:
            continue  # untracked: new content, not converted content
        try:
            result = _git(artifact_dir, "cat-file", "blob", f":{full}", binary=True)
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            raise WorktreeDriftError(f"cannot read blob for {rel}: {e}") from e
        if result.returncode != 0:
            # The file is tracked, so a failure here is a real error, not an
            # "untracked" signal. Never swallow it — that is how a guard becomes
            # decorative.
            raise WorktreeDriftError(f"git cat-file failed for {rel}: rc={result.returncode}")
        try:
            with open(os.path.join(artifact_dir, rel), "rb") as f:
                on_disk = f.read()
        except OSError as e:
            raise WorktreeDriftError(f"cannot read {rel}: {e}") from e
        if on_disk != result.stdout:
            drifted.append(rel)
    return sorted(drifted)


def assert_worktree_matches_repo(artifact_dir: str, rel_paths: list[str]) -> None:
    """Raise WorktreeDriftError when the bytes about to be signed are not the
    bytes another clone will receive."""
    drifted = drifted_files(artifact_dir, rel_paths)
    if not drifted:
        return
    shown = ", ".join(drifted[:5])
    more = f" (+{len(drifted) - 5} more)" if len(drifted) > 5 else ""
    raise WorktreeDriftError(
        f"refusing to sign: worktree bytes differ from the repository's for {shown}{more}. "
        "git converted them on checkout, so this signature would verify only on "
        "this machine. Add a .gitattributes with '* -text' to the skill repo, "
        "re-checkout (git rm --cached -r . && git reset --hard), then sign again. "
        "Inspect with: git ls-files --eol. "
        "To sign the converted bytes anyway, pass --allow-eol-drift."
    )
