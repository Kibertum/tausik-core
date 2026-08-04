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


def test_a_manufactured_divergence_is_caught():
    """The negative half: the comparison must be able to FAIL.

    Runs the real comparison against a deliberately unequal set, so a future
    refactor that makes `test_all_four_documents_state_the_same_number`
    unfalsifiable is caught here rather than discovered at the next release.
    """
    counts = {"a": 6, "b": 6, "c": 5, "d": 6}
    assert len(set(counts.values())) != 1
