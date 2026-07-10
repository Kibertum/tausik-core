"""Git-side helpers for the skill vendor cache: forced removal and EOL pinning.

Split out of ``skill_manager`` at the 400-line filesize cap. Both helpers exist
because git's behaviour on a consumer's machine is not the publisher's to choose.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys

# git converts line endings on checkout when core.autocrlf / core.eol say so.
# The signed manifest hashes raw bytes, so a converted checkout cannot reproduce
# the publisher's hashes: a skill signed on one platform gets refused on another
# with "modified: SKILL.md" though the file was never touched. `git clone` is
# OUR command, not the publisher's, so conversion is pinned off here rather than
# hoping every skill repo ships a `.gitattributes` with `* -text`. Decision #129.
EOL_PINS = ("-c", "core.autocrlf=false", "-c", "core.eol=lf")


def rmtree_force(path: str) -> None:
    """`shutil.rmtree` that survives git's read-only pack files on Windows.

    Git marks `.git/objects/pack/*.pack` and `*.idx` read-only. On Windows an
    unlink of a read-only file raises PermissionError, so a plain rmtree leaves
    the checkout half-deleted and whatever the caller meant to do afterwards
    never runs.
    """

    def _chmod_retry(func, target, _exc):
        os.chmod(target, stat.S_IWRITE)
        func(target)

    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=_chmod_retry)
    else:  # pragma: no cover - 3.11 path
        shutil.rmtree(path, onerror=_chmod_retry)


def pin_eol_config(repo_dir: str) -> None:
    """Persist the pin inside the clone — `-c` covers the clone command only.

    Without this the next `git pull --ff-only` re-reads the user's global
    core.autocrlf and converts the freshly fetched blobs. Verified, not assumed.
    """
    for key, value in (("core.autocrlf", "false"), ("core.eol", "lf")):
        subprocess.run(
            ["git", "config", key, value],
            cwd=repo_dir,
            capture_output=True,
            timeout=30,
            stdin=subprocess.DEVNULL,
        )


def eol_is_pinned(repo_dir: str) -> bool:
    """True when this checkout was made with conversion pinned off."""
    try:
        result = subprocess.run(
            ["git", "config", "--local", "--get", "core.autocrlf"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=30,
            stdin=subprocess.DEVNULL,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False
    # `git config --get` on an unset key exits 1 with no output; stdout may also
    # be None when the call is mocked. Treat both as "not pinned".
    return (result.stdout or "").strip() == "false"
