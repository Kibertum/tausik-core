"""The ratchets, checked without the full lane.

MEASURED. Fifteen ratchets live in `tausik/gates.json`, each guarded by its own test, and
the only way to learn you moved one was the full lane: 12 441 tests, five minutes, plus a
call to work out which of them was yours. In the session that filed this, ratchets went red
on the author's own work about ten times. The same checks — 25 files, 549 tests — run in
21 seconds.

THE SET IS DERIVED, NEVER LISTED. A file belongs when it names the baseline in a string, or
imports a module under `scripts/` that does. The second half is not optional: the first
version stopped at the first half and missed `test_gate_ruff_format.py`, which reads the
baseline through `gate_ruff_format.legacy_unformatted()` — the very ratchet that had gone
red that morning. A hand-kept list would go blind the first time someone adds a ratchet and
forgets to register it, which is exactly how a guard in this project once stayed green while
seven labels left its view.

WHAT THE DERIVATION CANNOT TELL APART, said rather than hidden: a test that PRINTS the
baseline's path in a message looks the same as one that opens it. Such a file joins the set
and costs a few seconds. The error is in the harmless direction — the expensive mistake
would be leaving a ratchet test out and calling the run green.

WHAT THIS IS NOT. It is not the full lane and does not claim to be — a ratchet held says
nothing about the behaviour around it. The output says so, because a fast green that reads
like a complete one is worse than no fast green at all.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

#: The baseline file. A test that opens it is a test about a ratchet.
BASELINE = "gates.json"

#: How a file NAMES the baseline, as opposed to mentioning it in prose. The quotes are the
#: point: `"tausik/gates.json"` is a path in the code, while the same words inside a comment
#: are someone explaining the design.
READS_BASELINE = re.compile(r"""["'][^"']*""" + re.escape(BASELINE) + r"""["']""")

#: A module imported by a test. Only the first segment matters — `scripts/` is flat.
IMPORTS = re.compile(r"^\s*(?:import|from)\s+([\w.]+)", re.MULTILINE)


class NoRatchetTests(RuntimeError):
    """The derived set came out empty. Absence is reported, never passed off as green."""


def baseline_readers(root: str | Path) -> set[str]:
    """Modules under `scripts/` that name the baseline — the second way a test reaches it."""
    scripts_dir = Path(root) / "scripts"
    readers: set[str] = set()
    if not scripts_dir.is_dir():
        return readers
    for name in sorted(os.listdir(scripts_dir)):
        if not name.endswith(".py"):
            continue
        try:
            text = (scripts_dir / name).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if READS_BASELINE.search(text):
            readers.add(name[:-3])
    return readers


def ratchet_tests(root: str | Path) -> list[str]:
    """Test files that reach the ratchet baseline, relative to `root`, sorted."""
    tests_dir = Path(root) / "tests"
    found: list[str] = []
    if not tests_dir.is_dir():
        return found
    readers = baseline_readers(root)
    for name in sorted(os.listdir(tests_dir)):
        if not (name.startswith("test_") and name.endswith(".py")):
            continue
        try:
            text = (tests_dir / name).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        imported = {m.group(1).split(".")[0] for m in IMPORTS.finditer(text)}
        if READS_BASELINE.search(text) or (imported & readers):
            found.append(f"tests/{name}")
    return found


def run(root: str | Path = ".", *, runner=subprocess.run) -> int:
    """Run the derived set. Returns pytest's exit code.

    Raises `NoRatchetTests` when the set is empty: reporting a green over nothing is the
    shape of failure this project decided against — a quantity that cannot be obtained is
    named absent, not zero.
    """
    files = ratchet_tests(root)
    if not files:
        raise NoRatchetTests(
            "no test file under tests/ reads the ratchet baseline, so there is nothing to "
            "run and nothing to say about the ratchets. Either the tree is not a TAUSIK "
            "checkout, or the guards are gone — both are worth knowing, and neither is a "
            "green."
        )
    print(
        f"Ratchets only: {len(files)} file(s) that reach {BASELINE}. "
        "This is NOT the full lane — a ratchet held says nothing about the behaviour "
        "around it."
    )
    proc = runner([sys.executable, "-m", "pytest", "-q", *files], cwd=str(root))
    return int(proc.returncode)


if __name__ == "__main__":  # pragma: no cover - exercised via the CLI
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
