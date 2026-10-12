"""Fail-closed audit of one exact public ref through an anonymous git endpoint."""

from __future__ import annotations

import os
import subprocess
import tempfile

from publication_scope import PublicationError, tree_of
from publication_snapshot import (
    history_exclusion_counts,
    leaks_in_snapshot,
    snapshot_tree,
)

_TIMEOUT = 300


def _git(cwd: str, *args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=_TIMEOUT,
        stdin=subprocess.DEVNULL,
    )


def _exact_remote_sha(repo_root: str, remote: str, ref: str) -> str:
    result = _git(repo_root, "ls-remote", "--exit-code", remote, ref)
    lines = [line.split("\t", 1) for line in result.stdout.splitlines() if "\t" in line]
    exact = [sha for sha, name in lines if name == ref]
    if result.returncode != 0 or len(exact) != 1:
        detail = result.stderr.strip() or f"expected one exact match, got {len(exact)}"
        raise PublicationError(f"cannot resolve exact remote ref {ref}: {detail}")
    return exact[0]


def audit_remote_ref(
    repo_root: str, remote: str, ref: str, source: str = "HEAD"
) -> tuple[bool, str, str]:
    """Audit the advertised ref's tree and all reachable history.

    A temporary bare repository keeps the remote objects separate from the
    development object database.  Network, ref-resolution and fetch failures
    raise ``PublicationError``; uncertainty is never returned as a green audit.
    """
    advertised = _exact_remote_sha(repo_root, remote, ref)
    with tempfile.TemporaryDirectory(prefix="tausik-public-audit-") as temp:
        init = _git(temp, "init", "--bare", "--quiet")
        if init.returncode != 0:
            raise PublicationError(f"cannot initialise remote-audit repository: {init.stderr}")
        fetched = _git(temp, "fetch", "--no-tags", "--quiet", remote, ref)
        if fetched.returncode != 0:
            raise PublicationError(f"cannot fetch exact remote ref {ref}: {fetched.stderr.strip()}")
        resolved = _git(temp, "rev-parse", "--verify", "FETCH_HEAD^{commit}")
        if resolved.returncode != 0:
            raise PublicationError(f"remote ref {ref} does not resolve to a commit")
        observed = resolved.stdout.strip()
        if advertised != observed:
            tag = _git(temp, "cat-file", "-t", advertised)
            if tag.returncode != 0 or tag.stdout.strip() != "tag":
                raise PublicationError(
                    f"remote ref {ref} changed while it was audited ({advertised} -> {observed})"
                )

        problems: list[str] = []
        expected_tree = snapshot_tree(repo_root, source)
        actual_tree = tree_of(temp, observed)
        if actual_tree != expected_tree:
            problems.append(
                f"tree differs from filtered {source}: expected {expected_tree[:12]}, "
                f"observed {actual_tree[:12]}"
            )
        exposed = {
            rule: count for rule, count in history_exclusion_counts(temp, observed).items() if count
        }
        if exposed:
            problems.append(
                "excluded history: "
                + ", ".join(f"{rule} ({count})" for rule, count in exposed.items())
            )
        leaks = {
            name: paths for name, paths in leaks_in_snapshot(repo_root, source).items() if paths
        }
        if leaks:
            problems.append(
                "source snapshot has non-zero leak classes: "
                + ", ".join(f"{name} ({len(paths)})" for name, paths in leaks.items())
            )
        if problems:
            return False, "; ".join(problems), observed
        return (
            True,
            f"{ref} is exact tree {actual_tree[:12]} with no excluded reachable history",
            observed,
        )
