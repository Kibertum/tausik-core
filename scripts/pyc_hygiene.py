"""Stale bytecode: `.pyc` files that remember a path the tree no longer has.

Session #187 read a traceback naming
`C:\\Projects\\Personal\\claude\\tests\\test_bootstrap_skills_coverage.py` — a path
that does not exist. The repository once lived there; the tree moved; the
caches under `__pycache__/` stayed. CPython validates a `.pyc` against the
SOURCE's mtime and size, never its path, so the cache is accepted and the
code object it carries brings its old `co_filename` along. Every traceback
through such a module then points the reader at an address where nothing is.

Measured in #207 before anything was written: 2561 `.pyc` under the tree
(vendors/, research/ and .tausik/ excluded), 543 whose recorded directory is
not the directory next to their `__pycache__`, 527 of those under the
nonexistent old tree — tests 432, scripts 69, bootstrap 16, hooks 6, harness 4
— spread over cpython-311/313/314 and pytest 8/9 tags. The cache had been
accumulating for months; a one-off purge would have cured that day and held
nothing. So the check lives in `tausik doctor`, and the purge behind a flag.

WHAT COUNTS AS STALE is the DIRECTORY, compared after `normpath`/`normcase`:
a `.pyc` whose `co_filename` sits in the directory that owns its `__pycache__`
is honest, whatever spelling it uses (`tests\\..\\scripts` is the same place;
a relative `scripts\\hooks\\x.py` from an interpreter run at the root is not a
lie about location). Only a recorded directory that is NOT the owning one is
reported — those are the 527.

THE PURGE DELETES ONLY WHAT WAS LISTED, and nothing else: the interpreter
recreates a cache on the next import, so there is nothing to lose, and a
purge wider than the list would be a second, unreviewed policy about what is
disposable. The skip list is fixed here rather than configurable: vendors/,
research/ and .tausik/ are never touched (they are read-only by decision, and
their caches are not ours to reason about).
"""

from __future__ import annotations

import marshal
import os
from collections.abc import Callable, Iterator

#: Never walked. vendors/ and research/ are read-only by decision; .tausik/
#: is the runtime; .git is not a tree of ours.
SKIP_DIRS = frozenset({"vendors", "research", ".tausik", ".git", "node_modules"})

#: Bytes of header before the marshalled code object (PEP 552 layout: magic,
#: flags, and either mtime+size or a source hash — 16 bytes in all).
_PYC_HEADER = 16


def _norm(path: str) -> str:
    return os.path.normcase(os.path.normpath(os.path.abspath(path)))


def recorded_source(pyc_path: str) -> str | None:
    """The `co_filename` a `.pyc` carries, or None when it cannot be read.

    Unreadable means truncated, foreign-magic (another interpreter's format)
    or otherwise not a code object; such a file is not evidence either way
    and is not reported as stale.
    """
    try:
        with open(pyc_path, "rb") as fh:
            fh.read(_PYC_HEADER)
            code = marshal.load(fh)
    except (OSError, ValueError, EOFError, TypeError):
        return None
    name = getattr(code, "co_filename", None)
    return name if isinstance(name, str) else None


def _pyc_files(root: str) -> Iterator[str]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        if os.path.basename(dirpath) != "__pycache__":
            continue
        for name in sorted(filenames):
            if name.endswith(".pyc"):
                yield os.path.join(dirpath, name)


def stale_bytecode(root: str) -> list[tuple[str, str]]:
    """`(pyc path, recorded source path)` for every cache whose recorded
    directory is not the directory that owns its `__pycache__`."""
    out: list[tuple[str, str]] = []
    for pyc in _pyc_files(root):
        recorded = recorded_source(pyc)
        if recorded is None:
            continue
        owner = _norm(os.path.dirname(os.path.dirname(pyc)))
        # A relative `co_filename` was recorded by an interpreter run from
        # some cwd; resolved against the owning directory's own root it is
        # the same place, and against nothing it is not a claim about a
        # location at all. Only an ABSOLUTE recorded path can lie.
        if not os.path.isabs(recorded):
            continue
        if _norm(os.path.dirname(recorded)) != owner:
            out.append((pyc, recorded))
    return out


def purge(entries: list[tuple[str, str]]) -> int:
    """Delete exactly the listed `.pyc` files. Returns how many were removed."""
    removed = 0
    for pyc, _recorded in entries:
        try:
            os.remove(pyc)
            removed += 1
        except FileNotFoundError:
            continue
    return removed


def doctor_section(
    project_dir: str,
    fix: bool,
    print_ok: Callable[[str, str], None],
    print_warn: Callable[[str, str], None],
) -> int:
    """One `tausik doctor` row. Returns the number of warnings it added (0/1).

    Reports, and on `fix` purges and reports what it purged — never purges
    silently, because a doctor that deletes without saying so is one whose
    output cannot be trusted about anything else either.
    """
    stale = stale_bytecode(project_dir)
    if not stale:
        print_ok("Stale bytecode", "none — every .pyc names the tree it lives in")
        return 0
    roots = sorted({os.path.dirname(rec) for _p, rec in stale})
    shown = ", ".join(roots[:3]) + (f" (+{len(roots) - 3} more)" if len(roots) > 3 else "")
    if fix:
        removed = purge(stale)
        print_warn(
            "Stale bytecode",
            f"purged {removed} of {len(stale)} .pyc that named another tree ({shown}); "
            "the interpreter recreates them on the next import",
        )
        return 1
    print_warn(
        "Stale bytecode",
        f"{len(stale)} .pyc name a directory that is not theirs ({shown}) — tracebacks "
        "through them point at a path that does not exist; run "
        "`tausik doctor --fix-bytecode` to purge exactly these",
    )
    return 1
