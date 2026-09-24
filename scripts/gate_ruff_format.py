"""`ruff format --check` over the task's files, with the inherited debt frozen.

Found in session #155: `ruff format --check` said 86 files would be
reformatted, and no gate, verify, close or CI script ever asked — the formatter
was configured (`[tool.ruff] line-length = 100`) and its verdict was wired to
nothing. By 1.10 the number was 117: silence let it grow.

Decision #386 chose a RATCHET over one mass-formatting commit. The files that
diverged when the gate landed are listed in `tausik/gates.json` →
`ruff_format.legacy_unformatted` and are skipped; every other Python file the
task touches must be formatted. The list may only shrink:
tests/test_gate_ruff_format.py refuses a listed file that is now formatted
(remove it) and an unformatted file that is not listed (format it).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys


def _repo_root(here: str | None = None) -> str:
    """The .git-anchored project root, NOT this file's parent's parent.

    Gates run from the DEPLOYED copy (`.claude/scripts/`), where dirname-twice
    lands on `.claude/`: the frozen list was never found there and every task
    path came out as `../scripts/x.py`, so a listed legacy file was refused as
    unformatted (session #269). Same lesson as gate_test_dedupe._repo_root.
    """
    start = here or os.path.dirname(os.path.abspath(__file__))
    d = start
    for _ in range(12):
        if os.path.exists(os.path.join(d, ".git")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return os.path.dirname(start)


def legacy_unformatted(repo_root: str | None = None) -> set[str] | None:
    """The frozen list, or None when the project has not adopted it."""
    path = os.path.join(repo_root or _repo_root(), "tausik", "gates.json")
    try:
        with open(path, encoding="utf-8") as f:
            node = (json.load(f).get("ruff_format") or {}).get("legacy_unformatted")
    except (OSError, ValueError):
        return None
    return {str(p).replace("\\", "/") for p in node} if isinstance(node, list) else None


#: Two output shapes: `Would reformat: PATH` (ruff <= 0.15) and a diagnostic
#: whose location line is ` --> PATH:L:C` (0.16+). Both are read.
_REFORMAT = re.compile(r"^(?:Would reformat: (?P<a>.+?)|\s*--> (?P<b>.+?):\d+:\d+)\s*$")


def ruff_command() -> list[str]:
    """The SAME ruff the `ruff` lint gate runs (`ruff` on PATH), else the module.

    Two versions disagree about formatting — 0.15 and 0.16 on this machine did —
    so the formatter gate must not pick a different binary than the linter.
    """
    exe = shutil.which("ruff")
    return [exe] if exe else [sys.executable, "-m", "ruff"]


def unformatted(files: list[str], cwd: str | None = None) -> list[str] | None:
    """Files `ruff format --check` would change; None when ruff cannot run."""
    if not files:
        return []
    try:
        proc = subprocess.run(
            [*ruff_command(), "format", "--check", *files],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=cwd or _repo_root(),
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode not in (0, 1):
        return None
    root = cwd or _repo_root()
    found = set()
    for ln in proc.stdout.splitlines():
        m = _REFORMAT.match(ln)
        if m:
            path = (m.group("a") or m.group("b")).strip()
            if os.path.isabs(path):
                path = os.path.relpath(path, root)
            found.add(path.replace("\\", "/"))
    return sorted(found)


def run_ruff_format_gate(gate: dict, files: list[str]) -> tuple[bool, str]:
    """Formatting of the task's Python files, the frozen legacy list excepted."""
    legacy = legacy_unformatted() or set()
    root = _repo_root()
    py = []
    for f in files or []:
        rel = os.path.relpath(os.path.abspath(f), root).replace("\\", "/")
        if rel.endswith(".py") and os.path.isfile(os.path.join(root, rel)) and rel not in legacy:
            py.append(rel)
    if not py:
        return True, "ruff format: no task file to check (none, or all on the frozen legacy list)"
    bad = unformatted(py, root)
    if bad is None:
        return False, "ruff format could not run (is ruff installed in this interpreter?)"
    if bad:
        return False, (
            f"ruff format: {len(bad)} task file(s) are not formatted: {', '.join(bad)}. "
            f"Fix: python -m ruff format {' '.join(bad)}"
        )
    return True, f"ruff format: {len(py)} task file(s) formatted"
