"""The documentation map: one record per page, derived FROM THE PAGE.

WHY A MAP AT ALL. Measured before this module existed: 64 EN pages and 63 RU pages,
~21k lines; 17 EN and 23 RU of them were reachable from no navigation section at all,
and nothing anywhere said who a page is for. A reader of the framework, an agent
working through it and someone maintaining the core were served the same undifferentiated
list, and the reading order existed only in `docs/README.md`.

WHY THE RECORD LIVES IN THE PAGE. The obvious alternative — one registry file listing
every page with its reader and zone — was tried in this project twice and failed the same
way both times: a registry kept away from its subject carries an excuse nobody re-reads.
The hand-written singleton list said the English reader of the agent contract "is served
by AGENTS.md", which was false for years, and `docs/README.md` still groups four pages
under "Internal agent specs (EN only)" that have had RU halves for a while. A marker in
the page is read by whoever opens the page, and one source cannot disagree with itself.

So each page carries

    <!-- doc-map: reader=<user|agent|maintainer>; zone=<zone> -->

and this module only collects those, pairs them up, and renders the map. A page with no
marker is a FINDING, not a default: guessing a reader would produce a map that looks
complete and answers the wrong question.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import TypedDict

EN_DIR = "docs/en"
RU_DIR = "docs/ru"

#: The three readers, closed on purpose. A fourth one is a decision, not a typo: the
#: point of the axis is that a page written for everybody is written for nobody.
READERS = ("user", "agent", "maintainer")

#: Zones follow the navigation sections that `docs/README.md` already uses, so the map
#: and the hub cannot tell two different stories about where a page belongs.
ZONES = (
    "getting-started",
    "core-surface",
    "quality",
    "configuration",
    "ide-and-skills",
    "memory-and-store",
    "sessions",
    "security",
    "reference",
    "release-notes",
    "internal-spec",
)

#: CROSS-CUTTING CLAIMS: sentences that appear on more than one page and must say the same
#: thing everywhere. Each one names the test that holds it, and a claim whose test does not
#: exist is refused by `tests/test_doc_cross_claims.py` — a list of promises with no checker
#: is the shape of rot this map was built against.
CROSS_CLAIMS: tuple[tuple[str, str, str], ...] = (
    (
        "two-stores",
        "There are two knowledge stores and no third: the project database and the shared "
        "store. The host's own auto-memory is an ADDRESS in the routing table, not a store.",
        "tests/test_doc_cross_claims.py::test_a_prose_claim_holds_on_every_page",
    ),
    (
        "no-notion",
        "The Notion transport left the framework in 1.9 (decision #358). A page may name it "
        "as history or as an example of an external store, never as a current capability.",
        "tests/test_doc_cross_claims.py::test_a_prose_claim_holds_on_every_page",
    ),
    (
        "senar-edition",
        "TAUSIK claims SENAR v1.5 Core and no other edition; every place naming the edition "
        "is checked against one constant.",
        "tests/test_senar_version_claim.py",
    ),
    (
        "counted-numbers",
        "A number in a documentation table that code can compute comes from "
        "docs/_generated/constants.json, never typed by hand.",
        "tests/test_doc_table_count_subjects.py",
    ),
)

_MARKER_RE = re.compile(r"<!--\s*doc-map:\s*reader\s*=\s*([a-z]+)\s*;\s*zone\s*=\s*([a-z-]+)\s*-->")


def marker(text: str) -> tuple[str, str] | None:
    """``(reader, zone)`` declared by the page, or None when it declares nothing."""
    m = _MARKER_RE.search(text)
    if not m:
        return None
    reader, zone = m.group(1), m.group(2)
    return (reader, zone) if reader in READERS and zone in ZONES else None


class Record(TypedDict):
    """One page in both languages. Typed rather than a bag of `object`.

    A loose `dict[str, object]` here cost two mypy suppressions on its first day, and a
    suppression is where the next reader stops asking what a field holds.
    """

    reader: str | None
    zone: str | None
    langs: list[str]
    undeclared: list[str]
    conflict: list[str]


def collect(repo_root: Path) -> dict[str, Record]:
    """``{basename: Record}`` over both language trees.

    Keyed by BASENAME because a pair is one page in two languages: a reader and a zone
    that differed between the halves would mean the two halves are different documents,
    and that is what the parity detector is for.
    """
    out: dict[str, Record] = {}
    for lang, sub in (("en", EN_DIR), ("ru", RU_DIR)):
        folder = repo_root / sub
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.md")):
            rec = out.setdefault(
                path.name,
                Record(reader=None, zone=None, langs=[], undeclared=[], conflict=[]),
            )
            rec["langs"].append(lang)
            got = marker(path.read_text(encoding="utf-8"))
            if got is None:
                rec["undeclared"].append(lang)
                continue
            reader, zone = got
            # The FIRST declaration wins and a disagreeing second one is reported, rather
            # than silently overwritten: two halves claiming different readers is a finding.
            if rec["reader"] is None:
                rec["reader"], rec["zone"] = reader, zone
            elif (rec["reader"], rec["zone"]) != (reader, zone):
                rec["conflict"].append(f"{lang}: {reader}/{zone}")
    return out


def findings(records: dict[str, Record]) -> dict[str, list[str]]:
    """The three ways the map can be wrong, each as a list of page names."""
    undeclared = sorted(n for n, r in records.items() if r["undeclared"])
    conflicting = sorted(n for n, r in records.items() if r["conflict"])
    unpaired = sorted(n for n, r in records.items() if len(r["langs"]) < 2)
    return {"undeclared": undeclared, "conflicting": conflicting, "unpaired": unpaired}


def render_markdown(records: dict[str, Record]) -> str:
    """The map itself — generated, so it cannot drift from the pages it describes."""
    lines = [
        "<!-- GENERATED by scripts/doc_map.py. Do not edit by hand: the reader and the",
        "     zone are declared in each PAGE, and this file is their projection.",
        "     Reissue: `python scripts/doc_map.py --write`. Check: `--check`. -->",
        "",
        "# Documentation map",
        "",
        "One record per page: who it is for, where it belongs, and which languages carry it.",
        "The record lives in the page (`<!-- doc-map: reader=…; zone=… -->`); this file is",
        "generated from those declarations.",
        "",
    ]
    by_zone: dict[str, list[tuple[str, Record]]] = {}
    for name, rec in sorted(records.items()):
        by_zone.setdefault(str(rec["zone"]), []).append((name, rec))
    for zone in ZONES:
        rows = by_zone.get(zone)
        if not rows:
            continue
        lines.append(f"## {zone}")
        lines.append("")
        lines.append("| Page | Reader | Languages |")
        lines.append("|---|---|---|")
        for name, rec in rows:
            langs = ", ".join(sorted(rec["langs"]))
            lines.append(f"| `{name}` | {rec['reader']} | {langs} |")
        lines.append("")
    lines.append("## Cross-cutting claims")
    lines.append("")
    lines.append("| Claim | It says | Held by |")
    lines.append("|---|---|---|")
    for key, statement, held_by in CROSS_CLAIMS:
        lines.append(f"| `{key}` | {statement} | `{held_by}` |")
    lines.append("")
    found = findings(records)
    if any(found.values()):
        lines.append("## Findings")
        lines.append("")
        for kind, names in found.items():
            if names:
                lines.append(f"- **{kind}** ({len(names)}): " + ", ".join(f"`{n}`" for n in names))
        lines.append("")
    total = len(records)
    paired = sum(1 for r in records.values() if len(r["langs"]) == 2)
    lines.append(f"{total} page(s), {paired} carried by both languages.")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Documentation map (generated from page markers)")
    p.add_argument("--write", action="store_true", help="Write docs/_generated/doc-map.md")
    p.add_argument("--check", action="store_true", help="Exit 1 on a finding or a stale file")
    p.add_argument("--json", action="store_true", help="Machine-readable output")
    p.add_argument("--repo-root", type=Path, default=None)
    args = p.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    root = Path(args.repo_root).resolve() if args.repo_root else Path.cwd().resolve()
    records = collect(root)
    target = root / "docs" / "_generated" / "doc-map.md"
    rendered = render_markdown(records)

    if args.write:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8", newline="\n")
        print(f"Wrote {target.relative_to(root).as_posix()}")
        return 0

    print(json.dumps(findings(records), indent=2, ensure_ascii=False) if args.json else rendered)

    if args.check:
        found = findings(records)
        stale = not target.is_file() or target.read_text(encoding="utf-8") != rendered
        if found["undeclared"] or found["conflicting"] or stale:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
