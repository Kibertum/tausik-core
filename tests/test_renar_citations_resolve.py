"""Every RENAR section our sources cite must exist in the live corpus.

Session #198 found fourteen citations pointing at chapter 14; session #199
measured the real shape and it was worse. Three distinct failure classes, and
the dangerous one is not the dangling reference:

* **Resolves, but to unrelated text.** `§14.4.2` read in our code as "the
  manifest schema"; in the corpus it is *ISO/IEC/IEEE 29148:2018*. A reader who
  follows it lands on a real section and believes it. A dangling reference at
  least announces itself.
* **Does not exist at all.** `§12.9` — the backbone of the level ladder — was
  cited in eight places; the corpus has no §12.9 in `standard/`.
* **Points at a document the corpus no longer carries.** `§0.2.3` cited "the
  audit"; `audit/` holds one unrelated file.

This test closes the first two classes mechanically. It cannot close the third,
and it cannot tell "resolves" from "resolves to the right subject" — that
remains a reading act, done once in the task and recorded there. What it does
guarantee is that a citation cannot rot into nothing while nobody looks.

**Skips when the corpus is not on disk** (fresh clone, CI without the sibling
checkout). That is a real limitation, stated rather than hidden: on such a
machine this control is dormant, not passing.
"""

from __future__ import annotations

import os
import re

import pytest

# This test imports no product module — it reads sources as DATA, so no import
# edge selects it and a scoped run would skip it silently while staying green.
# Declared here so a change to any citing source actually runs it. (The full
# lane caught exactly this: `verify` passed on a scoped run while the suite
# went red on TestInvisibleToEveryEdge.)
CROSSCUTTING_SCOPE = ["scripts/", "docs/", "tests/"]

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT = os.path.dirname(_HERE)
CORPUS = os.path.normpath(os.path.join(_PROJECT, "..", "..", "standards", "renar"))
STANDARD = os.path.join(CORPUS, "standard")

# Sources whose RENAR citations are load-bearing: they justify a verdict, a
# manifest field or a documented contract.
CITING_SOURCES = [
    "scripts/renar_conformance.py",
    "scripts/renar_export.py",
    "scripts/project_cli_renar.py",
    "scripts/renar_drift.py",
    "tests/test_renar_conformance.py",
    "tests/test_renar_export.py",
    "docs/en/cli.md",
    "docs/ru/cli.md",
]

# A RENAR section reference always carries at least one dot (§13.4.2, §1.5).
# A bare "§1" in our sources is a fixture's fictional ТЗ anchor
# ("TZ-2026-001 §1"), not a citation of this standard — excluded by the dot.
_CITE = re.compile(r"§(\d+(?:\.\d+)+)")
_HEADING = re.compile(r"^#{1,6}\s+(\d+(?:\.\d+)*)\s+\S")
# Closed-list tables number their rows in the first cell (§4.11.1 is a row of
# the §4.11 drift table, not a heading) — those are citable too.
_TABLE_ROW = re.compile(r"^\|\s*(\d+\.\d+(?:\.\d+)*)\s*\|")


def _corpus_sections() -> set[str]:
    found: set[str] = set()
    for name in sorted(os.listdir(STANDARD)):
        if not name.endswith(".md"):
            continue
        with open(os.path.join(STANDARD, name), encoding="utf-8", newline="") as fh:
            for line in fh:
                stripped = line.strip()
                for pattern in (_HEADING, _TABLE_ROW):
                    m = pattern.match(stripped)
                    if m:
                        found.add(m.group(1))
                        break
    return found


def _citations() -> dict[str, list[str]]:
    """section -> ["path:line", ...] over every citing source."""
    out: dict[str, list[str]] = {}
    for rel in CITING_SOURCES:
        path = os.path.join(_PROJECT, rel)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8", newline="") as fh:
            for lineno, line in enumerate(fh, 1):
                for m in _CITE.finditer(line):
                    out.setdefault(m.group(1), []).append(f"{rel}:{lineno}")
    return out


SIBLING_ROOT = os.path.normpath(os.path.join(_PROJECT, "..", "..", "standards"))

# Absence and misconfiguration must not look alike. A machine without the
# sibling checkout genuinely cannot run this control, so it skips. But once
# ../../standards exists, a missing standard/ means the path is WRONG — a typo,
# a moved corpus — and skipping there would disable the whole check while the
# suite stayed green. That is the failure this control exists to prevent, so it
# fails loudly instead. (Mutation M7: pointing CORPUS at renar-typo must go red,
# not skip.)
corpus_required = pytest.mark.skipif(
    not os.path.isdir(SIBLING_ROOT),
    reason=(
        "no ../../standards checkout on this machine — this control is DORMANT "
        "here, not passing"
    ),
)


@corpus_required
def test_corpus_path_resolves():
    assert os.path.isdir(STANDARD), (
        f"../../standards exists but {STANDARD} does not — the corpus path is "
        "wrong (typo or moved corpus). Fix the path; do not let this become a skip."
    )


@corpus_required
def test_corpus_index_is_not_empty():
    """Guards the whole file against a silent empty scan.

    A wrong CORPUS path yields zero headings, and then every citation would
    'resolve' against an empty set only because nothing was compared. Three
    hundred-odd sections is the live shape; the floor is deliberately far below
    it so a chapter split does not fail the suite.
    """
    assert len(_corpus_sections()) > 200


@corpus_required
def test_every_citation_resolves():
    sections = _corpus_sections()
    cites = _citations()
    assert cites, "no citations found — the scanner or CITING_SOURCES is broken"
    dangling = {
        sec: places for sec, places in sorted(cites.items()) if sec not in sections
    }
    assert not dangling, "citations with no such section in the corpus:\n" + "\n".join(
        f"  §{sec} — cited at {', '.join(places)}" for sec, places in dangling.items()
    )
