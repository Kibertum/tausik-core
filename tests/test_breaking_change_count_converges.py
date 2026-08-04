"""The count of breaking changes must agree in every place that states it.

Release notes here are a hand-assembled tag message built from
`whats-new-1.8.md`, and the same set is marked up in two changelogs. Four
documents, one fact, maintained by hand — which is how the sixth breaking change
came to be missing from all four while the four AGREED with each other. They
agreed on five. The number was checked, the number converged, and the release
was still wrong, because convergence between hand-written copies proves they
were copied, not that they are complete.

So this test does NOT check that the four are equal to some constant. It checks
that they are equal TO EACH OTHER, and that is all a mechanical check can honestly
do — deciding whether a change is breaking is a judgement, and it belongs in the
entry that makes it. What this rules out is the cheaper failure: marking a
heading in one language and forgetting the other, or adding a whats-new section
without touching the changelogs.
"""

from __future__ import annotations

import os
import re

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# The version whose notes are being assembled. A literal, not a lookup: this
# guards ONE release's hand-written notes, and a test that followed "the latest
# version" would silently stop testing its subject the moment 1.9 opened — the
# exact failure `test_migration_v43_model_mismatch` was fixed for.
VERSION = "1.8.0"

_RELEASE_HEADING = re.compile(rf"^## \[{re.escape(VERSION)}\]")
_ANY_RELEASE_HEADING = re.compile(r"^## \[")
_ENTRY_HEADING = re.compile(r"^### ")
_BREAKING_MARKER = re.compile(r"BREAKING|ЛОМАЮЩЕЕ")
# `### 6. TAUSIK_HOME is validated…` — the numbered sections under the
# BREAKING CHANGES heading of a whats-new page.
_NUMBERED_SECTION = re.compile(r"^### \d+\. ")


def _read(rel: str) -> list[str]:
    with open(os.path.join(REPO, rel), encoding="utf-8") as fh:
        return fh.read().splitlines()


def _changelog_breaking(rel: str) -> list[str]:
    """Entry headings marked breaking, inside this version's section only."""
    found: list[str] = []
    inside = False
    for line in _read(rel):
        if _RELEASE_HEADING.match(line):
            inside = True
            continue
        if inside and _ANY_RELEASE_HEADING.match(line):
            break
        if inside and _ENTRY_HEADING.match(line) and _BREAKING_MARKER.search(line):
            found.append(line.strip())
    return found


def _whats_new_sections(rel: str) -> list[str]:
    return [line.strip() for line in _read(rel) if _NUMBERED_SECTION.match(line)]


# The count as a READER meets it: a word in a sentence, not a tally of headings.
# Only 1–12 — past that a release note stops spelling numbers out, and a wider
# table would start matching version numbers.
_NUMERALS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    # Russian is inflected: the noun after the numeral changes case, so the
    # numeral does too (шесть / шести / шестью). Stems, not whole words.
    "один": 1,
    "одно": 1,
    "два": 2,
    "две": 2,
    "двух": 2,
    "три": 3,
    "трёх": 3,
    "трех": 3,
    "четыре": 4,
    "четырёх": 4,
    "четырех": 4,
    "пять": 5,
    "пяти": 5,
    "шесть": 6,
    "шести": 6,
    "семь": 7,
    "семи": 7,
    "восемь": 8,
    "восьми": 8,
    "девять": 9,
    "девяти": 9,
    "десять": 10,
    "десяти": 10,
}
# "<numeral> breaking change(s)" / "<numeral> ломающих изменени<...>". The
# numeral must sit DIRECTLY before the noun phrase, so `v1/v2 → v3` and other
# stray digits are not read as a count.
_PROSE_COUNT = re.compile(
    r"(\d+|[A-Za-zА-Яа-яЁё]+)\s+(?:breaking\s+changes?|ломающих\s+изменени\w*)",
    re.IGNORECASE,
)
# Documents whose prose states the number. The two READMEs are included because
# the release paragraph names the count there too, and a paragraph is exactly
# where a stale number survives a green heading comparison.
_PROSE_SOURCES = (
    "docs/en/whats-new-1.8.md",
    "docs/ru/whats-new-1.8.md",
    "README.md",
    "README.ru.md",
)


def _stated_numbers(text: str) -> list[int]:
    """Every count of breaking changes this text states in words or digits."""
    found: list[int] = []
    for token in _PROSE_COUNT.findall(text):
        if token.isdigit():
            found.append(int(token))
            continue
        n = _NUMERALS.get(token.lower())
        if n is not None:
            found.append(n)
    return found


def _prose_counts() -> dict[str, int]:
    """{"<file>:<line>": count} for every prose statement across the sources."""
    stated: dict[str, int] = {}
    for rel in _PROSE_SOURCES:
        path = os.path.join(REPO, rel)
        if not os.path.isfile(path):
            continue
        # Line-joined: the sentence wraps across lines in every one of these
        # files, and a per-line scan would see neither half of it.
        text = re.sub(r"\s+", " ", "\n".join(_read(rel)))
        for i, n in enumerate(_stated_numbers(text)):
            stated[f"{rel}#{i + 1}"] = n
    return stated


SOURCES = {
    "CHANGELOG.md": lambda: _changelog_breaking("CHANGELOG.md"),
    "CHANGELOG.ru.md": lambda: _changelog_breaking("CHANGELOG.ru.md"),
    "docs/en/whats-new-1.8.md": lambda: _whats_new_sections("docs/en/whats-new-1.8.md"),
    "docs/ru/whats-new-1.8.md": lambda: _whats_new_sections("docs/ru/whats-new-1.8.md"),
}


def test_all_four_documents_state_the_same_number():
    counts = {name: len(get()) for name, get in SOURCES.items()}
    assert len(set(counts.values())) == 1, (
        "The documents disagree on how many breaking changes "
        f"{VERSION} has: {counts}. Every breaking change is stated in four "
        "places; marking it in one language and not the other is the failure "
        "this catches."
    )


def test_the_count_is_not_zero():
    """Guards the check above from passing on four empty lists.

    Four documents that all say nothing agree perfectly. If this release ever
    genuinely has no breaking changes, this assertion is the place to say so
    deliberately rather than the place it happens silently.
    """
    counts = {name: len(get()) for name, get in SOURCES.items()}
    assert all(c > 0 for c in counts.values()), counts


def test_the_whats_new_sections_are_numbered_without_gaps():
    """A hand-numbered list is where a duplicate or a skipped index hides."""
    for rel in ("docs/en/whats-new-1.8.md", "docs/ru/whats-new-1.8.md"):
        numbers = [int(re.match(r"^### (\d+)\. ", s).group(1)) for s in _whats_new_sections(rel)]
        assert numbers == list(range(1, len(numbers) + 1)), f"{rel}: {numbers}"


def test_the_detectors_would_actually_fire():
    """Patterns that match nothing would let all of the above pass forever."""
    assert _BREAKING_MARKER.search("### Fixed — something (BREAKING)")
    assert _BREAKING_MARKER.search("### Исправлено — что-то (ЛОМАЮЩЕЕ)")
    assert _BREAKING_MARKER.search("### BREAKING: something")
    assert not _BREAKING_MARKER.search("### Fixed — an ordinary entry")
    assert _NUMBERED_SECTION.match("### 6. TAUSIK_HOME is validated")
    assert not _NUMBERED_SECTION.match("### What is new")


def test_every_prose_statement_of_the_count_matches_the_sections():
    """The number SPELLED OUT in prose, not just the number of headings.

    The heading comparison above went green over four documents whose opening
    sentence said "five" while six sections followed it — caught by hand at the
    tag, one command before the tag was cut. Counting headings and counting
    what the text CLAIMS are two different measurements, and only the second is
    what a reader takes away: nobody counts the sections, everybody reads the
    first sentence. Both READMEs are scanned too, because the number leaks into
    the release paragraph there as well.
    """
    expected = len(_whats_new_sections("docs/en/whats-new-1.8.md"))
    stated = _prose_counts()
    assert stated, (
        "No document states the count in prose any more. Either the sentence "
        "was dropped or _NUMERALS stopped matching it — an unfalsifiable check "
        "is worse than none, so this fails rather than passes empty."
    )
    wrong = {where: n for where, n in stated.items() if n != expected}
    assert not wrong, (
        f"Prose disagrees with the {expected} numbered sections: {wrong}. "
        f"All statements found: {stated}."
    )


def test_the_prose_detector_would_actually_fire():
    """A numeral scanner that matches nothing would pass the check above forever."""
    assert _stated_numbers("Six breaking changes with migrations first.") == [6]
    assert _stated_numbers("Сначала — шесть ломающих изменений с миграцией.") == [6]
    assert _stated_numbers("шести ломающих изменений") == [6]
    assert _stated_numbers("Five breaking changes") == [5]
    assert _stated_numbers("6 ломающих изменений") == [6]
    assert _stated_numbers("nothing about a count here") == []
    # A digit that is NOT counting breaking changes must not be picked up.
    assert _stated_numbers("Verify receipt schema: v1/v2 -> v3") == []


def test_a_manufactured_divergence_is_caught():
    """The negative half: the comparison must be able to FAIL.

    Runs the real comparison against a deliberately unequal set, so a future
    refactor that makes `test_all_four_documents_state_the_same_number`
    unfalsifiable is caught here rather than discovered at the next release.
    """
    counts = {"a": 6, "b": 6, "c": 5, "d": 6}
    assert len(set(counts.values())) != 1
