"""A record number on a page written for the user is an address they cannot open.

THE MEASUREMENT. 123 references of the form `decision #404` across the pages marked
`reader=user`. Each addresses a row in THIS project's database; a reader running TAUSIK on
their own project has no such row. The number resolves to nothing for them, and the sentence
around it asks them to take it on faith.

WHO IS NOT TOUCHED. On `reader=maintainer` and `reader=agent` pages the number is an address
the reader can follow — they have the database and `decisions_list` answers. Stripping it
there would remove the traceability the project exists to keep, so the count is per-reader and
only the user's is held down.

WHAT REPLACED A NUMBER IS THE STATEMENT IT HUNG OFF. "...left the framework in 1.9 (decision
#358)" became "...left the framework in 1.9". The reader loses an address they could not use;
the fact stays.

WHY 52 REMAIN. They sit in prose — behind a preposition, or opening a sentence — where no
bracket marks their boundary. A regex over prose broke a sentence twice in one day
left a preposition dangling with nothing after it — dead end #784. Those are
rewritten by hand as pages are touched, and the ratchet is what makes that happen.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import doc_internal_refs as dir_  # noqa: E402

CROSSCUTTING_SCOPE = ["docs/ru/", "docs/en/"]


def _baseline() -> dict:
    node = json.loads((_REPO / "tausik" / "gates.json").read_text(encoding="utf-8"))
    return node["doc_internal_refs"]


class TestTheCountOnlyGoesDown:
    def test_the_live_tree_is_at_or_below_the_baseline(self):
        got = dir_.count(str(_REPO))
        want = _baseline()
        assert got.references <= want["references"], (
            f"{got.references} references on user pages, baseline {want['references']}. "
            "A number a reader cannot open belongs on a maintainer page, or the sentence "
            "should say what it meant."
        )

    def test_the_baseline_states_what_it_measured_and_why_a_remainder_exists(self):
        note = _baseline().get("_comment", "")
        assert "123" in note and "52" in note, "before and after are both recorded"
        assert "only shrink" in note
        assert "prose" in note, "the reason the remainder is not zero is named"


class TestOnlyTheUsersPagesAreCounted:
    @pytest.mark.parametrize("reader", ["maintainer", "agent"])
    def test_another_reader_is_not_counted(self, reader, tmp_path):
        """NEGATIVE, AC-4: there the number is an address the reader can follow."""
        page = tmp_path / "x.md"
        page.write_text(
            f"<!-- doc-map: reader={reader}; zone=reference -->\nSee decision #404.\n",
            encoding="utf-8",
        )
        assert dir_.count_page(str(page)) == 0

    @pytest.mark.parametrize(
        ("marker", "expected"),
        [
            pytest.param("<!-- doc-map: reader=user; zone=reference -->" + chr(10), 1, id="user"),
            pytest.param("", 0, id="no_marker_is_not_guessed_at"),
        ],
    )
    def test_the_marker_decides_and_its_absence_is_not_a_guess(self, marker, expected, tmp_path):
        """A page that declares no reader is not assumed to be the user's: guessing would
        count the pages nobody classified and make the number describe the backlog."""
        page = tmp_path / "x.md"
        page.write_text(marker + "See decision #404." + chr(10), encoding="utf-8")
        assert dir_.count_page(str(page)) == expected


class TestWhatCountsAsAReference:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            pytest.param("decision #404", 1, id="en_decision"),
            pytest.param("memory #746", 1, id="en_memory"),
            pytest.param("convention #275", 1, id="en_convention"),
            pytest.param("github#51", 0, id="external_tracker_is_not_ours"),
            pytest.param("v1.9.0", 0, id="a_version_is_not_a_record"),
            pytest.param("#404 on its own", 0, id="a_bare_number_is_not_addressed"),
        ],
    )
    def test_the_pattern_names_the_kind_before_the_number(self, text, expected, tmp_path):
        """A bare `#404` could be an issue, a heading level or a column. The kind word is
        what makes it OUR record, and counting without it would flag half the documentation."""
        page = tmp_path / "x.md"
        page.write_text(
            f"<!-- doc-map: reader=user; zone=reference -->\n{text}\n", encoding="utf-8"
        )
        assert dir_.count_page(str(page)) == expected

    def test_an_external_tracker_reference_survives_the_cleanup(self):
        """`github#51` addresses something a reader CAN open. It is not ours to strip."""
        text = (_REPO / "docs" / "ru" / "cli.md").read_text(encoding="utf-8")
        assert "github#" in text


class TestTheWorstPagesAreNamed:
    def test_the_report_ranks_them(self):
        rows = dir_.worst(str(_REPO), top=5)
        assert rows, "the remainder is not zero, so the report has something to say"
        assert rows == sorted(rows, key=lambda r: -r[1])
