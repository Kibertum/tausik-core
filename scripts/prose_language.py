"""Prose inside code is English; this counts what is not yet, and holds the number down.

THE RULE IS THE OWNER'S (decision #404) and it supersedes half of an earlier convention. That
one settled that IDENTIFIERS must be ASCII and said, in as many words, that "docstrings,
comments and test descriptions take any language". The shipped template said the same. So the
rule the owner had asked for repeatedly existed nowhere, and the file a new project is handed
argued against it.

TWO NUMBERS, NOT ONE, because they carry different prices:

* PROSE — comments, docstrings, string literals. Rewriting a comment costs nothing but the
  rewrite. Measured at 5,348 lines across 287 files.
* IDENTIFIERS — 269 of them, all in `tests/`. These stay, and the exemption is not taste: 83
  evidence citations in 21 closed tasks point at Cyrillic pytest node ids, journals are
  append-only, and renaming would turn live evidence into unresolvable references. The price
  was measured before the exemption was declared, and this module keeps the two apart so the
  exemption cannot quietly grow into the prose count.

NO MASS TRANSLATION HERE. Rewriting 5,348 lines in one pass is exactly the size of edit this
project refuses to make without a task per unit of meaning. The ratchet lets the number fall
whenever a file is touched for its own reasons, and refuses to let it rise.
"""

from __future__ import annotations

import ast
import json
import os
import re
from typing import Final, NamedTuple

#: Cyrillic is the only non-ASCII prose this repository has ever carried, and naming the range
#: keeps the check honest about what it can see: a Greek or Arabic comment would pass. That is
#: a real limit, stated rather than papered over with a catch-all "non-ASCII" that would also
#: flag an em dash, a degree sign and every arrow in the existing docstrings.
#: Built with `chr()` rather than written out: `ruff format` collapses the escape form into
#: the literal characters, and the detector then counts its own pattern line as a finding —
#: which it did on the first run.
CYRILLIC: Final[re.Pattern[str]] = re.compile("[" + chr(0x0400) + "-" + chr(0x04FF) + "]")

#: Trees whose Python this rule governs. Everything shipped or run; nothing generated.
ROOTS: Final[tuple[str, ...]] = ("scripts", "harness", "bootstrap", "tests")

GATES_KEY: Final[str] = "prose_language"


class Count(NamedTuple):
    prose_lines: int
    files: int
    identifiers: int

    def as_dict(self) -> dict[str, int]:
        return {
            "prose_lines": self.prose_lines,
            "files": self.files,
            "identifiers": self.identifiers,
        }


def _identifier_lines(tree: ast.AST) -> set[int]:
    """Lines whose DEFINED NAME is Cyrillic — the declared exemption, counted apart."""
    out: set[int] = set()
    for node in ast.walk(tree):
        name = getattr(node, "name", None)
        if isinstance(name, str) and CYRILLIC.search(name):
            line = getattr(node, "lineno", 0)
            if line:
                out.add(line)
    return out


def count_file(path: str) -> tuple[int, int]:
    """``(prose_lines, identifier_lines)`` for one file. Unreadable or unparseable → (0, 0).

    A file that will not parse is not a finding of THIS check: something else in the tree
    fails on it first, and reporting it here would send the reader to the wrong place.
    """
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            src = fh.read()
    except OSError:
        return 0, 0
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return 0, 0
    ident = _identifier_lines(tree)
    prose = sum(
        1 for n, line in enumerate(src.splitlines(), 1) if CYRILLIC.search(line) and n not in ident
    )
    return prose, len(ident)


def count(repo_root: str = ".", roots: tuple[str, ...] = ROOTS) -> Count:
    """Walk the governed trees. `__pycache__` and deployed profiles are not source."""
    prose = files = idents = 0
    for root in roots:
        base = os.path.join(repo_root, root)
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for name in filenames:
                if not name.endswith(".py"):
                    continue
                p, i = count_file(os.path.join(dirpath, name))
                idents += i
                if p:
                    prose += p
                    files += 1
    return Count(prose, files, idents)


def baseline(repo_root: str = ".") -> dict[str, int]:
    try:
        with open(os.path.join(repo_root, "tausik", "gates.json"), encoding="utf-8") as fh:
            node = json.load(fh).get(GATES_KEY)
    except (OSError, ValueError):
        return {}
    return node if isinstance(node, dict) else {}


def check(repo_root: str = ".") -> tuple[str, str, Count]:
    """``(level, detail, measured)``. ``warn`` only on GROWTH; shrinking asks to be recorded."""
    got = count(repo_root)
    base = baseline(repo_root)
    if not base:
        return (
            "absent",
            f"no baseline in tausik/gates.json[{GATES_KEY}] — record prose_lines "
            f"{got.prose_lines}, files {got.files}, identifiers {got.identifiers}",
            got,
        )
    grew = [
        f"{name} {have} > {want}"
        for name, have, want in (
            ("prose lines", got.prose_lines, base.get("prose_lines", got.prose_lines)),
            ("identifiers", got.identifiers, base.get("identifiers", got.identifiers)),
        )
        if have > want
    ]
    if grew:
        return (
            "warn",
            "non-English prose in code GREW: "
            + "; ".join(grew)
            + ". New comments and docstrings are written in English (decision #404).",
            got,
        )
    if got.prose_lines < base.get("prose_lines", got.prose_lines) or got.identifiers < base.get(
        "identifiers", got.identifiers
    ):
        return (
            "ok",
            f"non-English prose shrank to {got.prose_lines} line(s) in {got.files} file(s), "
            f"{got.identifiers} identifier(s) — record the lower numbers in "
            f"tausik/gates.json[{GATES_KEY}]",
            got,
        )
    return (
        "ok",
        f"{got.prose_lines} line(s) of non-English prose in {got.files} file(s) at the "
        f"baseline; {got.identifiers} Cyrillic identifier(s) exempt by measured price",
        got,
    )


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    p = argparse.ArgumentParser(description="Non-English prose inside Python sources")
    p.add_argument("--repo-root", default=".")
    p.add_argument("--json", action="store_true", dest="as_json")
    p.add_argument("--check", action="store_true", help="Exit 1 when the number has grown")
    args = p.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    level, detail, got = check(args.repo_root)
    print(json.dumps({"level": level, **got.as_dict()}) if args.as_json else f"[{level}] {detail}")
    return 1 if (args.check and level == "warn") else 0


if __name__ == "__main__":
    raise SystemExit(main())
