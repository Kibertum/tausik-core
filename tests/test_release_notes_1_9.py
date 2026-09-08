"""The 1.9 notes exist, and every breaking change reaches them.

release-19-notes-page-does-not-exist-yet. In 1.8 the breaking change to trust
tiers stayed in the CHANGELOG and never reached the tag's notes — and a published
tag cannot be re-cut, so that one is permanent. This file exists so 1.9 cannot
repeat it while it is still cheap to fix.

THE PAGE IS NOT A RETELLING OF THE CHANGELOG. The Unreleased section held 163
entries when these notes were written, exactly one of them marked BREAKING. A
page carrying all 163 would be as unread as the file it stands in for, so what is
checked is the part that must not be lost: every entry the CHANGELOG itself calls
breaking has to appear in the notes.

Marked-up entries are the subject, not a judgement of what "counts" as breaking —
that judgement belongs to whoever writes the entry, and second-guessing it here
would make the check an opinion.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]

CROSSCUTTING_SCOPE = ["docs/", "CHANGELOG.md", "CHANGELOG.ru.md"]

_PAGES = {
    "ru": _REPO / "docs" / "ru" / "whats-new-1.9.md",
    "en": _REPO / "docs" / "en" / "whats-new-1.9.md",
}
_CHANGELOGS = {
    "ru": _REPO / "CHANGELOG.ru.md",
    "en": _REPO / "CHANGELOG.md",
}
_BREAKING_HEADING = {"ru": "## ЛОМАЮЩИЕ ИЗМЕНЕНИЯ", "en": "## BREAKING CHANGES"}
_BREAKING_ENTRY = {"ru": re.compile(r"^### ЛОМАЮЩЕЕ\b"), "en": re.compile(r"^### BREAKING\b")}


def _unreleased(lang: str) -> list[str]:
    """The `### ` headings of the Unreleased section, in order."""
    lines = _CHANGELOGS[lang].read_text(encoding="utf-8").splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("## [Unreleased]"))
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].startswith("## [")),
        len(lines),
    )
    return [ln for ln in lines[start:end] if ln.startswith("### ")]


class TestThePagesExistInBothLanguagesAtOnce:
    """1.8 shipped in one language and the second never came."""

    @pytest.mark.parametrize("lang", sorted(_PAGES))
    def test_the_page_is_there(self, lang):
        assert _PAGES[lang].is_file(), (
            f"{_PAGES[lang].relative_to(_REPO)} is missing — the release has no notes, "
            "so the tag has no source of text but the CHANGELOG nobody opens"
        )

    @pytest.mark.parametrize("lang", sorted(_PAGES))
    def test_it_has_a_breaking_section(self, lang):
        text = _PAGES[lang].read_text(encoding="utf-8")
        assert _BREAKING_HEADING[lang] in text, (
            f"{_PAGES[lang].name} has no breaking-changes section. That section is the "
            "single source of the tag's text; without it the tag and the repository "
            "can say different things, which is what happened to 1.8."
        )

    @pytest.mark.parametrize("lang", sorted(_PAGES))
    def test_it_says_the_section_is_the_source_of_the_tag_text(self, lang):
        text = _PAGES[lang].read_text(encoding="utf-8").lower()
        needle = "источник текста" if lang == "ru" else "source of the future tag"
        assert needle in text, (
            f"{_PAGES[lang].name} does not state that the breaking section IS the tag "
            "text. An unstated convention is one the next release will not follow."
        )


class TestEveryBreakingEntryReachesTheNotes:
    """The defect this page exists against, checked rather than promised."""

    @pytest.mark.parametrize("lang", sorted(_PAGES))
    def test_the_changelog_marks_at_least_one(self, lang):
        """PREMISE. With no marked entry the assertion below is vacuous."""
        marked = [h for h in _unreleased(lang) if _BREAKING_ENTRY[lang].match(h)]
        assert marked, (
            "no Unreleased entry is marked breaking in "
            f"{_CHANGELOGS[lang].name} — either the markup was dropped or the "
            "release genuinely has none; both change what this file can assert"
        )

    @pytest.mark.parametrize("lang", sorted(_PAGES))
    def test_each_one_is_named_on_the_page(self, lang):
        page = _PAGES[lang].read_text(encoding="utf-8").lower()
        missing = []
        for heading in _unreleased(lang):
            if not _BREAKING_ENTRY[lang].match(heading):
                continue
            # Match on the distinctive words of the entry, not the whole line: the
            # notes rephrase for a reader, and demanding the exact sentence would
            # force the page to be a copy of the CHANGELOG.
            body = heading.split("—", 1)[-1].strip().lower()
            keywords = [w for w in re.findall(r"[\w`.]{5,}", body) if not w.isdigit()][:4]
            if not any(k.strip("`.") in page for k in keywords):
                missing.append((heading, keywords))
        assert not missing, (
            f"these BREAKING entries are in {_CHANGELOGS[lang].name} and nowhere in "
            f"{_PAGES[lang].name}: {missing}. That is precisely how 1.8's trust-tier "
            "change ended up in a file nobody opens on upgrade."
        )


class TestThePageIsNotTheChangelog:
    """AC5. A page carrying everything is as unread as the file it replaces."""

    @pytest.mark.parametrize("lang", sorted(_PAGES))
    def test_it_carries_far_fewer_entries_than_the_changelog(self, lang):
        page_sections = [
            ln
            for ln in _PAGES[lang].read_text(encoding="utf-8").splitlines()
            if ln.startswith("### ")
        ]
        changelog_entries = _unreleased(lang)
        assert len(changelog_entries) > 50, "the Unreleased section shrank unexpectedly"
        assert len(page_sections) < len(changelog_entries) / 4, (
            f"{_PAGES[lang].name} has {len(page_sections)} sections against "
            f"{len(changelog_entries)} changelog entries — it is turning into a copy "
            "of the changelog, and a copy is read exactly as often as the original"
        )

    @pytest.mark.parametrize("lang", sorted(_PAGES))
    def test_it_points_at_the_changelog_for_the_rest(self, lang):
        text = _PAGES[lang].read_text(encoding="utf-8")
        assert "CHANGELOG" in text, (
            f"{_PAGES[lang].name} selects a subset and does not say where the rest is"
        )


class TestTheBreakingSectionIsNotPadded:
    """AC6. Calling something breaking that the changelog does not is inflation,
    and inflation makes the section unreadable in exactly the way that loses the
    one entry that mattered."""

    @pytest.mark.parametrize("lang", sorted(_PAGES))
    def test_it_holds_no_more_items_than_the_changelog_marks(self, lang):
        text = _PAGES[lang].read_text(encoding="utf-8")
        after = text.split(_BREAKING_HEADING[lang], 1)[1]
        section = after.split("\n---", 1)[0]
        numbered = re.findall(r"^### \d+\.", section, re.MULTILINE)
        marked = [h for h in _unreleased(lang) if _BREAKING_ENTRY[lang].match(h)]
        assert len(numbered) <= len(marked), (
            f"{_PAGES[lang].name} lists {len(numbered)} breaking changes while the "
            f"changelog marks {len(marked)}. Either the changelog markup is missing "
            "one, or the section is being padded."
        )
