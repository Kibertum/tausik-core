"""Internal record numbers on pages written for the user: a number they cannot open.

THE MEASUREMENT. Across the 88 pages marked `reader=user` there are 196 references of the
form `decision #404` / `memory #746`, plus 60 task slugs. Every one addresses a row in THIS
project's database. A reader running TAUSIK on their own project has no such row — the number
resolves to nothing for them, and the sentence around it asks them to take it on faith.

WHO THIS DOES NOT APPLY TO. On `reader=maintainer` and `reader=agent` pages the number is an
address the reader can actually follow: they have the database, and `decisions_list` answers.
Stripping numbers there would remove the traceability the project exists to keep, so the count
is per-reader and only the user's is ratcheted.

WHAT REPLACES A NUMBER IS A STATEMENT, NOT A HOLE. "Because of decision #376" becomes what
that decision said. The reader loses an address they could not use and gains the fact it
stood for; deleting the clause instead would take the fact away too.

ONE EXCEPTION, DECLARED RATHER THAN SILENT: a historical sentence whose whole point is that
something changed at a specific recorded moment keeps its number, because without it the claim
stops being checkable. Those are listed in `DECLARED_HISTORICAL` with the reason.
"""

from __future__ import annotations

import os
import re
from typing import Final, NamedTuple

#: A record reference: the word naming the kind, then the number. Both languages, because the
#: documentation is written in both and a reader meets whichever branch they opened.
REFERENCE: Final[re.Pattern[str]] = re.compile(
    r"(?:"
    + "|".join(
        (
            "".join(chr(c) for c in (0x440, 0x435, 0x448, 0x435, 0x43D, 0x438, 0x435)),  # decision
            "".join(chr(c) for c in (0x440, 0x435, 0x448, 0x435, 0x43D, 0x438, 0x44F)),  # decisions
            "".join(chr(c) for c in (0x43F, 0x430, 0x43C, 0x44F, 0x442, 0x44C)),  # memory
            "".join(chr(c) for c in (0x441, 0x43C, 0x435, 0x43D, 0x430)),  # session
            "".join(chr(c) for c in (0x441, 0x43C, 0x435, 0x43D, 0x44B)),  # session, genitive
            "decision",
            "memory",
            "convention",
            "gotcha",
            "session",
        )
    )
    + r")\s*#\d+",
    re.IGNORECASE,
)

#: The reader a page declares. Only the first is cleaned.
USER: Final[str] = "user"

#: Pages whose number stays, with the reason. A historical claim — "X lived in the core until
#: the decision that moved it" — loses its checkability without the address, and a reader who
#: wants to verify the history is no longer the casual reader this rule protects.
DECLARED_HISTORICAL: Final[dict[str, str]] = {}


class Count(NamedTuple):
    references: int
    pages: int


def reader_of(text: str) -> str | None:
    m = re.search(r"<!--\s*doc-map:\s*reader=(\w+)", text)
    return m.group(1) if m else None


def count_page(path: str) -> int:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return 0
    if reader_of(text) != USER:
        return 0
    if os.path.basename(path) in DECLARED_HISTORICAL:
        return 0
    return len(REFERENCE.findall(text))


def count(repo_root: str = ".") -> Count:
    """References on user pages, and how many pages carry at least one."""
    total = pages = 0
    for lang in ("ru", "en"):
        base = os.path.join(repo_root, "docs", lang)
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            if not name.endswith(".md"):
                continue
            n = count_page(os.path.join(base, name))
            if n:
                total += n
                pages += 1
    return Count(total, pages)


def worst(repo_root: str = ".", top: int = 10) -> list[tuple[str, int]]:
    """The pages to fix first, most references first."""
    rows: list[tuple[str, int]] = []
    for lang in ("ru", "en"):
        base = os.path.join(repo_root, "docs", lang)
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            if name.endswith(".md"):
                n = count_page(os.path.join(base, name))
                if n:
                    rows.append((f"docs/{lang}/{name}", n))
    return sorted(rows, key=lambda r: -r[1])[:top]


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    p = argparse.ArgumentParser(description="Internal record numbers on user-facing pages")
    p.add_argument("--repo-root", default=".")
    p.add_argument("--top", type=int, default=10)
    args = p.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    got = count(args.repo_root)
    print(f"{got.references} reference(s) on {got.pages} page(s) written for the user")
    for path, n in worst(args.repo_root, args.top):
        print(f"  {n:4}  {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
