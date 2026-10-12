"""The vocabulary has somewhere to be looked up, and the list cannot go stale quietly.

THE MEASUREMENT THAT FILED THIS. Across the 88 pages marked `reader=user`, `gate` appears 715
times, `slug` 467, `stack` 350, `QG-2` 74, `QG-0` 66 — and there was no `glossary.md`,
`terms.md`, `concepts.md` or `faq.md` anywhere in the tree. A reader met the words and had
nowhere to go.

WHY A TEST AND NOT JUST THE PAGE. A glossary written once is a glossary that drifts: the next
term enters the user-facing pages and nobody notices it is undefined. The check below reads
the pages, not the page — it fails when a term the reader will actually meet is missing from
the list.

THE LIST IS MEASURED, NOT IMAGINED. Every entry is a word counted on user pages; a term that
appears nowhere is not defended here, because a glossary padded with words nobody uses teaches
the reader to skim it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]

# This file walks the documentation tree, so a change under docs/ must select it.
CROSSCUTTING_SCOPE = ["docs/ru/", "docs/en/"]

#: Terms a user-facing page uses without explaining, counted over `reader=user` pages. The
#: number beside each is how often it appeared when the glossary was written — kept so the
#: next author can see which of these are load-bearing and which are marginal.
REQUIRED_TERMS: dict[str, int] = {
    "gate": 715,
    "slug": 467,
    "stack": 350,
    "QG-2": 74,
    "QG-0": 66,
    "SENAR": 119,
    "RENAR": 53,
    "harness": 90,
    "handoff": 85,
    "epic": 80,
    "story": 87,
    "tier": 128,
    "receipt": 143,
    "projection": 38,
    "Verify-First": 37,
    "snapshot": 22,
    "ratchet": 16,
    "dead end": 19,
}


def _user_pages(lang: str) -> list[Path]:
    out = []
    for path in sorted((_REPO / "docs" / lang).glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        if "reader=user" in text:
            out.append(path)
    return out


@pytest.mark.parametrize("lang", ["ru", "en"])
def test_the_glossary_exists_and_is_marked_for_the_user(lang):
    page = _REPO / "docs" / lang / "glossary.md"
    assert page.is_file()
    text = page.read_text(encoding="utf-8")
    assert "reader=user" in text
    assert "zone=getting-started" in text


@pytest.mark.parametrize("term", sorted(REQUIRED_TERMS))
def test_every_measured_term_is_defined_in_both_languages(term):
    """The pair matters: a reader on the English branch must not meet a Russian-only entry."""
    for lang in ("ru", "en"):
        text = (_REPO / "docs" / lang / "glossary.md").read_text(encoding="utf-8").lower()
        assert term.lower() in text, f"{lang}: {term!r} is used on user pages and not defined"


def test_a_new_term_on_a_user_page_is_caught():
    """THE POINT OF THE CHECK: it reads the PAGES, so the list cannot rot silently.

    If a term from the measured set starts appearing on user pages and the glossary loses it,
    this goes red — which is what "the glossary was written once" fails to do.
    """
    text = (_REPO / "docs" / "ru" / "glossary.md").read_text(encoding="utf-8").lower()
    missing = []
    for term, _count in REQUIRED_TERMS.items():
        used = any(
            term.lower() in p.read_text(encoding="utf-8", errors="replace").lower()
            for p in _user_pages("ru")
        )
        if used and term.lower() not in text:
            missing.append(term)
    assert not missing, f"used on user pages, absent from the glossary: {missing}"


@pytest.mark.parametrize("lang", ["ru", "en"])
def test_a_definition_carries_no_internal_reference_number(lang):
    """A reader who meets `decision #404` in a DEFINITION has been handed a dead end: the
    number addresses a record they cannot open. Numbers belong on maintainer pages."""
    text = (_REPO / "docs" / lang / "glossary.md").read_text(encoding="utf-8")
    # The Russian alternatives are DATA the check searches FOR, not prose written here.
    # Spelled out they would add a line to the very count `prose_language` guards — the trap
    # this project has already sprung twice — so they are built from code points.
    ru = "|".join(
        "".join(chr(c) for c in word)
        for word in (
            (0x440, 0x435, 0x448, 0x435, 0x43D, 0x438, 0x435),  # decision
            (0x43F, 0x430, 0x43C, 0x44F, 0x442, 0x44C),  # memory
        )
    )
    hits = re.findall(rf"(?:{ru}|decision|memory|convention)\s*#\d+", text, re.I)
    assert not hits, f"{lang}: internal references in the glossary: {hits}"


@pytest.mark.parametrize("lang", ["ru", "en"])
def test_start_here_points_at_it(lang):
    """AC-5: the entry page for a user must name the glossary, or nobody finds it."""
    text = (_REPO / "docs" / lang / "start-here-user.md").read_text(encoding="utf-8")
    assert "glossary.md" in text


@pytest.mark.parametrize("lang", ["ru", "en"])
def test_the_page_says_where_its_list_came_from(lang):
    """A list with no provenance is the next one somebody pads with words nobody uses."""
    text = (_REPO / "docs" / lang / "glossary.md").read_text(encoding="utf-8")
    assert "715" in text, "the measurement that produced the list is stated"
