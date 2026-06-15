"""Pytest test count via ``pytest --collect-only``.

Single source of truth for test-count drift checks. Spawns pytest in a
subprocess (collection-only, no actual test runs) with the project's
``addopts`` overridden so the result is the FULL suite size — independent of
the fast-lane ``-m 'not slow'`` filter currently active in pyproject.

The trailing ``N tests collected`` summary line is parsed; on collection
errors a ``ValueError`` is raised so the consumer fails loudly rather than
silently writing a wrong number into ``constants.json``.

Note (gotcha #88): subprocess.run() inside the MCP project server's worker
thread MUST pass ``stdin=DEVNULL`` — otherwise it can hang silently on stdin
inheritance. We pass it everywhere, not only inside MCP, for symmetry.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

_COLLECT_SUMMARY_RE = re.compile(r"^(\d+)\s+tests?\s+collected\b", re.MULTILINE)
_COLLECT_TIMEOUT_S = 60


def count_tests(repo_root: Path) -> int:
    """Return total pytest test count (no marker filter).

    Spawns ``pytest --collect-only -q --override-ini="addopts="`` from
    ``repo_root`` and parses the trailing ``N tests collected`` line. Raises
    ``ValueError`` if the summary cannot be located or pytest exits non-zero.
    """
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "--override-ini=addopts=",
        ],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=_COLLECT_TIMEOUT_S,
        stdin=subprocess.DEVNULL,
        check=False,
    )
    if proc.returncode != 0:
        raise ValueError(
            f"pytest --collect-only exited with {proc.returncode}; "
            f"stderr tail: {proc.stderr.strip()[-500:]}"
        )
    text = proc.stdout
    matches = _COLLECT_SUMMARY_RE.findall(text)
    if not matches:
        raise ValueError(
            "Could not locate 'N tests collected' summary in pytest output. "
            f"Tail: {text.strip()[-500:]}"
        )
    return int(matches[-1])
