"""The 1.9 notes exist, and every breaking change reaches them.

release-19-notes-page-does-not-exist-yet. In 1.8 the breaking change to trust
tiers stayed in the CHANGELOG and never reached the tag's notes — and a published
tag cannot be re-cut, so that one is permanent. This file exists so 1.9 cannot
repeat it while it is still cheap to fix.

THE PAGE IS NOT A RETELLING OF THE CHANGELOG. The Unreleased section held 163
entries when these notes were written (the page now states the live count and
this file recounts it), two of them marked BREAKING. A page carrying them all
would be as unread as the file it stands in for, so what is
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
# The sentence on each page that states the 1.9 section's entry count.
_ENTRY_FIGURE = {
    "ru": re.compile(r"в разделе 1\.9 CHANGELOG больше (\d+) записей"),
    "en": re.compile(r"the 1\.9 section of the CHANGELOG holds more than (\d+) entries"),
}
_RELEASE_HEADING = "## [1.9.0]"
_UNRELEASED_HEADING = "## [Unreleased]"


def _section(lines: list[str], heading: str) -> list[str] | None:
    """The `### ` headings under `heading`, or None when the section is absent."""
    start = next((i for i, ln in enumerate(lines) if ln.startswith(heading)), None)
    if start is None:
        return None
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].startswith("## [")),
        len(lines),
    )
    return [ln for ln in lines[start:end] if ln.startswith("### ")]


def _section_for_1_9(lines: list[str]) -> list[str]:
    """The 1.9 entries: `## [1.9.0]` once the CHANGELOG is cut, `## [Unreleased]` before.

    The 1.8.0 cut (aa10f3b4) left `## [Unreleased]` with "Nothing yet." above
    `## [1.8.0]`; the same cut for 1.9 empties the section these tests read,
    and a reader of Unreleased alone goes red on the release commit itself
    (task the-1-9-notes-tests-read-only-unreleased-so-the-re).
    """
    released = _section(lines, _RELEASE_HEADING)
    if released is not None:
        return released
    unreleased = _section(lines, _UNRELEASED_HEADING)
    assert unreleased is not None, "neither [1.9.0] nor [Unreleased] is in the CHANGELOG"
    return unreleased


def _unreleased(lang: str) -> list[str]:
    """The `### ` headings of the 1.9 section, in order (name kept for the callers)."""
    return _section_for_1_9(_CHANGELOGS[lang].read_text(encoding="utf-8").splitlines())


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
    def test_the_entry_figure_on_the_page_is_a_bound_the_changelog_clears(self, lang):
        """The page states a LOWER BOUND on the entries the 1.9 section holds.

        It used to state the exact count, and the exact count was re-asserted
        here — so every CHANGELOG entry turned this test red until someone
        retyped a number on two pages (three times in session #263 alone). A
        figure nothing counts rots (convention #673); a figure that must be
        retyped per entry is a chore wearing a test's clothes. A bound rots in
        neither direction: entries are never removed, so it stays true, and it
        is raised by hand only when someone wants the page to say more."""
        page = _PAGES[lang].read_text(encoding="utf-8")
        stated = re.search(_ENTRY_FIGURE[lang], page)
        assert stated, f"{_PAGES[lang].name} no longer states its entry bound"
        assert len(_unreleased(lang)) >= int(stated.group(1)), (
            f"{_PAGES[lang].name} says more than {stated.group(1)} entries, the CHANGELOG "
            f"holds {len(_unreleased(lang))} — the bound overstates the section"
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


class TestTheUnmeasuredPromiseSaysSo:
    """Условие выпуска 1: обещание экономии не публикуется, пока нет числа.

    ЗАМЕР (смена #239): из 57 251 строки телеметрии входные токены несут 233
    (0%), базы сравнения «без TAUSIK» нет ни одной. Числа нет, а обещание на
    странице названо — значит рядом обязана стоять оговорка, и стоять ЗАМЕТНО.

    ЧИСЛО ПОЯВИЛОСЬ (смена #263): парный replay протокола
    docs/ru/research/rag-nudge-replay-protocol.md §7 дал один отсчёт на одном
    корпусе — с подсказками дороже, search_code не вызван ни разу. Оговорка
    поменяла смысл, но не место: теперь рядом с обещанием стоит «ИЗМЕРЕНО ОДИН
    РАЗ», и страница обязана говорить «на этой паре», а не «экономии нет»
    вообще — это держит класс ниже. Телеметрия числа по-прежнему не производит,
    и фраза об ОТСУТСТВИИ величины остаётся о ней.

    ПОЧЕМУ РЯДОМ, А НЕ НИЖЕ. В этой же смене матрица соответствия чинилась ровно
    от этого: закрывающий абзац говорил «величину вычислить нельзя», а таблица
    прямо над ним печатала 100%. Читатель забирает утверждение, а не сноску под
    ним, поэтому проверяется РАССТОЯНИЕ между обещанием и оговоркой.
    """

    # The same shape guards the Codex claim (session #251): decision #360 made
    # codex-first-class-19 a release story and tied it to a live acceptance run,
    # and the run found the boundary — the native refusal happened only under a
    # hook profile the user had TRUSTED; the untrusted generated profile let the
    # write through. Naming the host without that sentence would promise more
    # than the run proved, so the boundary must sit next to the claim too.
    @pytest.mark.parametrize(
        "lang,promise,caveat,near",
        [
            pytest.param("ru", "экономия токенов", "ИЗМЕРЕНО ОДИН РАЗ", 1200, id="ru-saving"),
            pytest.param("en", "token saving", "MEASURED ONCE", 1200, id="en-saving"),
            pytest.param(
                "ru", "Codex — шестой хост", "недоверенный профиль не", 2500, id="ru-codex"
            ),
            pytest.param(
                "en",
                "Codex is a sixth host",
                "untrusted profile enforces nothing",
                2500,
                id="en-codex",
            ),
        ],
    )
    def test_the_caveat_sits_next_to_the_promise(self, lang, promise, caveat, near):
        text = _PAGES[lang].read_text(encoding="utf-8")
        assert promise in text, "обещание исчезло со страницы — предпосылка теста"
        assert caveat in text, (
            "обещание названо, а его оговорка (нет числа / нужны доверенные хуки) не названа"
        )
        assert 0 < text.index(caveat) - text.index(promise) < near, (
            "оговорка оторвана от обещания — читатель заберёт обещание"
        )

    @pytest.mark.parametrize("lang", ["ru", "en"])
    def test_the_numbers_are_there_and_sourced(self, lang):
        """AC-4: числа измерены сейчас, а не перенесены из смены #225."""
        text = (
            _PAGES[lang].read_text(encoding="utf-8").replace("\u00a0", " ").replace("\u202f", " ")
        )
        assert "233" in text
        assert "57 251" in text or "57,251" in text

    @pytest.mark.parametrize("lang", ["ru", "en"])
    def test_absence_is_not_reported_as_a_refutation(self, lang):
        """Решение #334: невычислимая величина ОТСУТСТВУЕТ. Телеметрия числа не
        производит и после парного replay — та фраза остаётся о ней, а не
        превращается в «экономии нет» вообще."""
        text = _PAGES[lang].read_text(encoding="utf-8")
        needle = "ОТСУТСТВИЕ величины" if lang == "ru" else "ABSENCE of a quantity"
        assert needle in text


_PROTOCOL = _REPO / "docs" / "ru" / "research" / "rag-nudge-replay-protocol.md"
_OUTWARD_PAGES = {
    "readme-en": _REPO / "README.md",
    "readme-ru": _REPO / "README.ru.md",
    "notes-en": _PAGES["en"],
    "notes-ru": _PAGES["ru"],
}
# The §7 rows every outward page quotes: the primary metric, the exploration
# bytes and the search_code count — B, A and the percentage of B.
_QUOTED_ROWS = {
    "primary": "| основная: Σ cache_creation + Σ output |",
    "bytes": "| байты результатов исследования |",
    "search_code": "| — `search_code` |",
}
_SEP = r"[\s  ,]?"


def _protocol_figures() -> dict[str, tuple[str, str, str]]:
    """(B, A, % of B) per quoted row, digits only, read from the §7 table."""
    text = _PROTOCOL.read_text(encoding="utf-8")
    section = text[text.index("## 7.") :]
    out = {}
    for key, prefix in _QUOTED_ROWS.items():
        row = next(ln for ln in section.splitlines() if ln.startswith(prefix))
        cells = [c.strip() for c in row.strip("|").split("|")]
        b, a, pct = cells[1], cells[2], cells[4]
        out[key] = (re.sub(r"\D", "", b), re.sub(r"\D", "", a), pct.replace(" ", ""))
    return out


def _number_pattern(digits: str) -> re.Pattern:
    """195055 -> 195 055 / 195,055 / 195 055 — any thousands separator, or none."""
    groups = []
    while len(digits) > 3:
        groups.insert(0, digits[-3:])
        digits = digits[:-3]
    groups.insert(0, digits)
    return re.compile(_SEP.join(re.escape(g) for g in groups))


class TestTheMeasuredFigureIsCountedFromTheProtocol:
    """Convention #673: a number in a document is counted by something. The
    four outward pages quote the paired replay (protocol §7); the figures they
    carry are read from that table here, not compared with a retyped copy —
    so a page cannot keep an old number after the protocol's table moves."""

    @pytest.mark.parametrize("page", sorted(_OUTWARD_PAGES))
    def test_the_page_carries_the_protocol_figures(self, page):
        text = _OUTWARD_PAGES[page].read_text(encoding="utf-8")
        figures = _protocol_figures()
        for key in ("primary", "bytes"):
            b, a, pct = figures[key]
            for digits in (b, a):
                assert _number_pattern(digits).search(text), (
                    f"{page}: §7 {key} figure {digits} is not on the page"
                )
            wanted = pct.replace(",", ".").replace("%", "")
            assert re.search(re.escape(wanted) + r"\s?%", text.replace(",", ".")), (
                f"{page}: §7 {key} percentage {pct} is not on the page"
            )
        b, a, _ = figures["search_code"]
        assert (b, a) == ("0", "0"), "the protocol's search_code row moved — re-read the pages"
        assert "search_code" in text

    @pytest.mark.parametrize("page", sorted(_OUTWARD_PAGES))
    def test_no_saving_is_said_only_about_this_pair(self, page):
        """Protocol §6: one pair is one reading, no generalisation. Every
        «экономии нет» / "there is no saving" on a page must sit within 120
        characters of «на этой паре» / "on this pair"."""
        text = _OUTWARD_PAGES[page].read_text(encoding="utf-8")
        claim, scope = (
            ("экономии нет", "на этой паре")
            if page.endswith("ru")
            else ("no saving", "on this pair")
        )
        hits = [m.start() for m in re.finditer(re.escape(claim), text)]
        assert hits, f"{page}: the measured outcome is not stated at all"
        for pos in hits:
            window = text[max(0, pos - 120) : pos + len(claim) + 120]
            assert scope in window, (
                f"{page}: «{claim}» at {pos} is not scoped to this pair — that is a generalisation"
            )


class TestTheCodexHostIsNamedWithItsBoundary:
    """The boundary sentence is guarded next to the claim above (the caveat
    test); this holds the count — the page measured five hosts in session #225
    and must say Codex made it six, not leave the five standing alone."""

    @pytest.mark.parametrize("lang", ["ru", "en"])
    def test_the_host_count_is_not_left_at_five(self, lang):
        text = _PAGES[lang].read_text(encoding="utf-8")
        needle = "шестым хостом" if lang == "ru" else "sixth host"
        assert needle in text


class TestTheSchemaFigureIsCounted:
    """The page said "44 → 58, fourteen migrations" while the tree carried
    SCHEMA_VERSION = 61 (session #251): three migrations landed after the
    paragraph was written and nothing recounted it — convention #673, a number
    in a document is counted by something or it rots. 44 is a literal on
    purpose: it is what tag v1.8.0 shipped, a property of a published artifact
    that cannot drift, and a CI clone may not carry the tag to read it from."""

    _SHIPPED_IN_1_8 = 44
    _FIGURE = {
        "ru": re.compile(r"### Схема БД: (\d+) → (\d+)"),
        "en": re.compile(r"### Database schema: (\d+) → (\d+)"),
    }
    _WORDS = {
        "ru": {17: "Семнадцать", 18: "Восемнадцать", 19: "Девятнадцать", 20: "Двадцать"},
        "en": {17: "Seventeen", 18: "Eighteen", 19: "Nineteen", 20: "Twenty"},
    }

    @staticmethod
    def _schema_version() -> int:
        src = (_REPO / "scripts" / "backend_schema.py").read_text(encoding="utf-8")
        return int(re.search(r"^SCHEMA_VERSION = (\d+)", src, re.M).group(1))

    @pytest.mark.parametrize("lang", ["ru", "en"])
    def test_the_heading_ends_at_the_live_schema_version(self, lang):
        m = self._FIGURE[lang].search(_PAGES[lang].read_text(encoding="utf-8"))
        assert m, "the schema heading is gone — the figure this test reads"
        assert int(m.group(1)) == self._SHIPPED_IN_1_8
        assert int(m.group(2)) == self._schema_version(), (
            f"{lang}: the page says the schema ends at {m.group(2)}, the tree says "
            f"{self._schema_version()} — a migration landed and the notes did not move"
        )

    @pytest.mark.parametrize("lang", ["ru", "en"])
    def test_the_migration_count_in_words_matches(self, lang):
        n = self._schema_version() - self._SHIPPED_IN_1_8
        word = self._WORDS[lang].get(n)
        assert word, f"add the word for {n} to _WORDS — the count moved past the table"
        text = _PAGES[lang].read_text(encoding="utf-8")
        assert word in text, f"{lang}: {n} migrations, but the page does not say {word!r}"


class TestTheReaderSurvivesTheReleaseCut:
    """The cut `[Unreleased]` -> `[1.9.0]` is the release commit; the tests must not go red on it."""

    _BEFORE = [
        "# Changelog",
        "## [Unreleased]",
        "### Fixed — one",
        "### Added — two",
        "## [1.8.0] — 2026-08-03",
        "### Fixed — old",
    ]
    _AFTER = [
        "# Changelog",
        "## [Unreleased]",
        "Nothing yet.",
        "## [1.9.0] — 2026-09-14",
        "### Fixed — one",
        "### Added — two",
        "## [1.8.0] — 2026-08-03",
        "### Fixed — old",
    ]

    @pytest.mark.parametrize("shape", ["before", "after"])
    def test_the_same_entries_are_read_on_both_sides_of_the_cut(self, shape):
        lines = self._BEFORE if shape == "before" else self._AFTER
        assert _section_for_1_9(lines) == ["### Fixed — one", "### Added — two"]

    def test_the_old_unreleased_only_reader_would_have_read_zero_after_the_cut(self):
        """NEGATIVE: what the release commit would have produced under the old reader."""
        assert _section(self._AFTER, _UNRELEASED_HEADING) == []
        assert _section(self._BEFORE, _RELEASE_HEADING) is None

    def test_the_live_changelogs_are_on_one_side_of_the_cut_in_both_languages(self):
        sides = {
            lang: _section(
                _CHANGELOGS[lang].read_text(encoding="utf-8").splitlines(), _RELEASE_HEADING
            )
            is not None
            for lang in _CHANGELOGS
        }
        assert len(set(sides.values())) == 1, f"one language is cut and the other is not: {sides}"
