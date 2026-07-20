"""Git-index file listing shared by the static audit scripts.

The static audits (``audit_stale_docs``, ``audit_orphan_files``,
``audit_unused_python``) all claim to report on *tracked* files, but each
walked the filesystem with ``rglob`` and therefore also picked up
gitignored paths. That produced permanent false positives — a gitignored
file is by definition referenced by nothing and cannot be "fixed" — and,
worse, printed the names of intentionally-local research files into
reports (convention #176 keeps those names out of shared output).

This module is the single place that answers "what does git track here?".

Degradation contract (deliberate): :func:`tracked_files` returns ``None``
— never an empty set — whenever git cannot answer (git missing, not a
repository, non-zero exit, empty listing). ``None`` means *unknown*, and
callers fall back to their filesystem walk. Returning an empty set would
make every audit report the whole tree as unreferenced the moment git
hiccups; ``None`` keeps that failure loud but harmless.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# git ls-files can be slow on huge trees; audits run manually, so one call
# per process is cheap enough that no caching layer is warranted here.
_GIT_TIMEOUT_SECONDS = 30


def tracked_files(repo_root: Path, *, warn: bool = True) -> frozenset[str] | None:
    """Relative forward-slashed paths tracked by git under ``repo_root``.

    Returns ``None`` when git cannot answer — see the module docstring for
    why that is distinct from an empty set. When ``warn`` is true, the
    reason is written to stderr so a degraded audit run is visible rather
    than silently wider than advertised.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "ls-files", "-z", "--full-name", "--", "."],
            capture_output=True,
            # MCP-reachable code must never inherit stdin — a subprocess that
            # blocks on it hangs the server (see tests/test_risk_compute_stdin).
            stdin=subprocess.DEVNULL,
            timeout=_GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        _warn(warn, f"git ls-files failed ({exc.__class__.__name__}: {exc})")
        return None

    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", errors="replace").strip().splitlines()
        _warn(
            warn, f"git ls-files exited {proc.returncode}: {detail[0] if detail else 'no output'}"
        )
        return None

    paths = {
        chunk.replace("\\", "/")
        for chunk in proc.stdout.decode("utf-8", errors="replace").split("\0")
        if chunk
    }
    if not paths:
        _warn(warn, "git ls-files returned nothing")
        return None
    return frozenset(paths)


def is_tracked(rel: str, tracked: frozenset[str] | None) -> bool:
    """True when ``rel`` should be audited.

    An unknown index (``tracked is None``) admits everything — that is the
    filesystem-walk fallback, not a filter that silently drops files.
    """
    return True if tracked is None else rel in tracked


def _warn(enabled: bool, message: str) -> None:
    if enabled:
        print(
            f"[audit] git file listing unavailable, falling back to filesystem walk: {message}",
            file=sys.stderr,
        )
