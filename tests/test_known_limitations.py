"""The gap register is checkable, not declarative — otherwise it rots the way TODO.md did.

WHAT THIS FILE IS FOR. Three things looked identical before the page existed: "we decided
not to do this", "we have not finished this" and "this is broken". A guard whose blind spot
is undocumented reads as total, so the gaps were collected from the places they were
already declared — a gate docstring, a memory record, a skill section — into one page.

WHY IT NEEDS A TEST AT ALL. A page of prose with no owner goes stale silently, and this
project has the receipt: a root document calling itself the map of the project's direction
sat two releases behind with a link to a file that no longer existed. So the shape that
makes the page worth reading is asserted:

  * every gap NAMES what is not guaranteed and WHY living with it is cheaper — a gap with
    no reason is a defect, and the section must not become a bin for those;
  * every gap cites something that holds the boundary, so the claim can be checked;
  * the pointer from CLAUDE.md and AGENTS.md exists and is a POINTER, never a copy: the
    same class of two-documents-two-answers drift already cost this project a defect;
  * the two language versions carry the same set of gaps.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_RU = _REPO / "docs" / "ru" / "known-limitations.md"
_EN = _REPO / "docs" / "en" / "known-limitations.md"

#: Both language trees, because the register is a pair of pages and a change to either
#: one has to select this file; the boundary claims also cite paths under `scripts/`.
CROSSCUTTING_SCOPE = ["docs/ru/", "docs/en/", "scripts/"]

#: What a gap entry must answer, per language. The heading is the gap; these three lines
#: are the contract on its body.
_REQUIRED = {
    "ru": ("**Не гарантировано:**", "**Почему живём:**", "**Держит границу:**"),
    "en": ("**Not guaranteed:**", "**Why we live with it:**", "**Holds the boundary:**"),
}


def _sections(path: Path) -> list[tuple[str, str]]:
    """``(heading, body)`` for every `###` gap entry on the page."""
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"^### ", text, flags=re.M)[1:]
    out = []
    for part in parts:
        head, _, body = part.partition("\n")
        out.append((head.strip(), body))
    return out


@pytest.mark.parametrize("lang,path", [("ru", _RU), ("en", _EN)])
def test_every_gap_says_what_is_not_guaranteed_and_why_we_live_with_it(lang, path):
    """AC3 and AC4 together: the answer and the reason are both required.

    AC4 is the sharp one — without a stated reason the register turns into a list of
    defects nobody wants to fix, which is worse than no register, because it launders
    them as decisions.
    """
    gaps = _sections(path)
    assert len(gaps) >= 8, f"{path.name}: only {len(gaps)} gaps — the collection is thin"
    for head, body in gaps:
        for marker in _REQUIRED[lang]:
            assert marker in body, f"{path.name}: gap '{head}' is missing {marker}"


@pytest.mark.parametrize("lang,path", [("ru", _RU), ("en", _EN)])
def test_every_gap_cites_something_that_exists(lang, path):
    """AC5: a boundary held by a file nobody can open is held by nothing.

    Only paths are checked, and only those that look repo-relative: a citation may also
    name a symbol or a docstring, and demanding a path everywhere would push the page
    towards weaker references rather than stronger ones. A `tests/test_doctor_*.py`
    glob counts when it matches at least one file.
    """
    boundary = _REQUIRED[lang][2]
    checked = 0
    for head, body in _sections(path):
        claim = body.split(boundary, 1)[1].split("\n\n", 1)[0]
        for token in re.findall(r"`([\w./*-]+\.(?:py|md))`", claim):
            if "*" in token:
                assert list(_REPO.glob(token)), f"{path.name}: '{head}' cites {token}, no match"
            else:
                assert (_REPO / token).exists(), f"{path.name}: '{head}' cites a missing {token}"
            checked += 1
    assert checked >= 8, f"{path.name}: only {checked} citations resolved to paths"


def test_both_languages_carry_the_same_gaps():
    """AC6's first half: a page that drifts between languages tells two stories."""
    assert len(_sections(_RU)) == len(_sections(_EN))


@pytest.mark.parametrize(
    "doc,link",
    [("CLAUDE.md", "docs/ru/known-limitations.md"), ("AGENTS.md", "docs/en/known-limitations.md")],
)
def test_the_entry_points_point_at_the_page(doc, link):
    """Both onboarding documents carry the pointer and not a drifting copy.

    A pointer cannot disagree with the page; a copied gap can, and then the reader has
    two answers and no way to tell which is current. So the gap MARKERS may appear on the
    page and nowhere else.
    """
    text = (_REPO / doc).read_text(encoding="utf-8")
    assert link in text, f"{doc} does not name {link}"
    for marker in (*_REQUIRED["ru"], *_REQUIRED["en"]):
        assert marker not in text, (
            f"{doc} carries '{marker}' — that is a copy of the register, not a pointer to "
            "it. Keep the content in docs/{ru,en}/known-limitations.md and link to it."
        )


@pytest.mark.parametrize("path", [_RU, _EN])
def test_open_defects_are_not_a_hand_written_list(path):
    """The register must send the reader to the live source, not to a frozen list.

    A hand-maintained defect list is the failure this project measured: it falls behind
    without saying so. The section earns its place by naming the command instead.
    """
    text = path.read_text(encoding="utf-8")
    assert "tausik task list --status planning" in text
    assert "tausik roadmap" in text
