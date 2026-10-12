"""Cross-cutting claims say the same thing on every page that says them.

A sentence that appears on more than one page is a promise made several times, and several
copies of a promise drift. This project has the receipts: a hand-written registry excused a
missing English contract with a reason that was false, and a root document called itself the
map of the project's direction while asserting a state two releases old.

So the claims are DECLARED in `scripts/doc_map.py::CROSS_CLAIMS`, rendered into the generated
map, and each one names the test that holds it. The last test in this file refuses a claim
whose checker does not exist — a list of promises with nobody checking them is the same rot in
a tidier format.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

#: Both language trees carry the claims, so a change to either must select this file.
CROSSCUTTING_SCOPE = ["docs/en/", "docs/ru/"]


def _pages() -> list[Path]:
    return sorted(p for lang in ("en", "ru") for p in (_REPO / "docs" / lang).glob("*.md"))


#: A mention of the departed transport is legitimate when the same sentence marks it as gone
#: or offers it as an example of an external store. The English word "notion" is not the
#: product; excluding it is not a loophole but the difference between a detector and a grep —
#: `en/cli.md` says "the notion of an example path" and the first draft of this check flagged it.
_HISTORICAL = re.compile(
    r"(retired|departed|left the framework|left behind|went in 1\.|no longer|used to|"
    r"отставленн|ушёл|ушел|оставш|больше не|раньше)",
    re.I,
)
_AS_EXAMPLE = re.compile(r"\((?:Notion|Ноушн)\s*/|external store|Внешний стор", re.I)
_THE_WORD = re.compile(r"\bthe notion of\b|\bnotion of an?\b", re.I)


def _notion_lines(text: str) -> list[str]:
    """Lines naming the transport as something TAUSIK has, rather than had."""
    out = []
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if "notion" not in line.lower():
            continue
        if _THE_WORD.search(line) or _AS_EXAMPLE.search(line):
            continue
        # The retirement may sit on the next line — prose wraps, and a check that reads one line
        # at a time would demand the marker be repeated on every line of a paragraph.
        window = " ".join(lines[i : i + 2])
        if _HISTORICAL.search(window):
            continue
        out.append(line.strip())
    return out


_THIRD_STORE = re.compile(r"(three|3|три)\s+(stores|хранилищ)", re.I)


def _third_store_lines(text: str) -> list[str]:
    hit = _THIRD_STORE.search(text)
    return [hit.group(0)] if hit else []


#: One row per prose claim: its key in `CROSS_CLAIMS`, the scan, and what a hit means. A
#: table rather than a test per claim — the two scans are the same shape doing the same job
#: on different wording, which is what parametrisation is for; two copies of it would be
#: duplicate-shape debt and the dedupe ratchet says so.
PROSE_CLAIMS = (
    (
        "no-notion",
        _notion_lines,
        "presents Notion as a current capability (it left in 1.9; history and examples are fine)",
    ),
    (
        "two-stores",
        _third_store_lines,
        "counts a third knowledge store — the host's auto-memory is an ADDRESS, not a store, "
        "and an agent that reads otherwise writes project knowledge into it",
    ),
)


@pytest.mark.parametrize(
    "claim,scan,complaint", PROSE_CLAIMS, ids=lambda v: getattr(v, "__name__", v)
)
@pytest.mark.parametrize("page", _pages(), ids=lambda p: f"{p.parent.name}/{p.name}")
def test_a_prose_claim_holds_on_every_page(page, claim, scan, complaint):
    """MEASURED when this was written: 13 pages mentioned the departed transport, and every
    mention was ALREADY historical or an example — the premise that they needed cleaning was
    wrong. The value is keeping it that way instead of re-auditing 13 pages each release."""
    if page.name.startswith("whats-new"):
        pytest.skip("release notes are history by definition")
    hits = scan(page.read_text(encoding="utf-8"))
    assert not hits, f"{page.parent.name}/{page.name} {complaint}:\n  " + "\n  ".join(hits)


def test_every_declared_claim_names_a_checker_that_exists():
    """A claim with no test is a promise; this is what keeps the list from becoming one."""
    from doc_map import CROSS_CLAIMS

    assert CROSS_CLAIMS, "the claim list is empty — then the map promises nothing"
    for key, statement, held_by in CROSS_CLAIMS:
        assert len(statement) > 40, f"{key}: the statement is too short to be checkable"
        path = _REPO / held_by.split("::", 1)[0]
        assert path.is_file(), f"{key} names a missing checker: {held_by}"
        if "::" in held_by:
            name = held_by.split("::", 1)[1]
            assert name in path.read_text(encoding="utf-8"), f"{key}: {name} not in {path.name}"


def test_the_claim_detector_can_still_see():
    """NEGATIVE: the two scans above pass trivially if their patterns stopped matching."""
    assert _notion_lines("The Notion transport mirrors the store outward.")
    assert not _notion_lines("The Notion transport was retired in 1.9.")
    assert not _notion_lines("An external store (Notion/server) is unfit for this.")
    assert not _notion_lines("the notion of an example path is shared")
    assert _THIRD_STORE.search("there are three stores")
