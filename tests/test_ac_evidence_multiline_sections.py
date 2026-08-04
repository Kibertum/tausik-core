"""Evidence may sit BELOW its heading, and the gate has to read it there.

The Rule 5 checklist gate reported "no acceptance criterion names a test" over
checklists that named several, four closes running. Matching required `AC-N` on
the SAME line as the citation, so the fuller form — a heading, then one line per
test beneath it — parsed as a heading with no evidence plus citations belonging
to nothing.

That is worse than a missing feature. A gate that denies evidence it was handed
teaches its reader to skip its output, and it is then equally ignored on the
closes where the checklist really IS absent. The signal is what was lost, not
the convenience. The form is not a matter of taste either: one criterion covered
by four tests does not fit on one line.

So this file is written in two halves that have to hold TOGETHER. The first says
the fuller form is read. The second says widening recognition did not turn into
accepting anything — because a gate that accepts everything has failed in the
other direction, and that failure is quieter.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from gate_ac_check import checklist_hard_block, checklist_missing  # noqa: E402
from service_ac_evidence import build_report  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/service_ac_evidence.py", "scripts/gate_ac_check.py"]

AC = "1. Первое. 2. Второе. 3. НЕГАТИВ: третье."

# A real test that exists on disk, so `_test_ref_exists` resolves it. Using a
# made-up path would make every assertion here pass for the wrong reason.
REAL = "tests/test_ac_evidence_multiline_sections.py::test_the_fuller_form_is_recognised"


def _task(notes: str, tier: str = "substantial") -> dict:
    return {"acceptance_criteria": AC, "notes": notes, "tier": tier}


def test_the_fuller_form_is_recognised():
    """The exact shape the gate's own message asks for, spread over lines."""
    notes = (
        "[2026-08-03T10:00:00Z] AC-1 (что проверяется): первое свойство.\n"
        f"✓ {REAL}\n"
        f"✓ {REAL}\n"
        "AC-2 (что проверяется): второе свойство.\n"
        f"✓ {REAL}\n"
    )
    report = build_report(AC, notes)
    assert report.covered == 2, f"gaps={report.gaps()}"
    assert not report.unmatched_evidence
    assert checklist_missing(_task(notes)) is False


def test_a_heading_covered_by_four_tests_is_the_point():
    """One criterion, four citations — the case that cannot fit on one line."""
    notes = "[2026-08-03T10:00:00Z] AC-1 (что проверяется): свойство.\n" + "".join(
        f"✓ {REAL}\n" for _ in range(4)
    )
    report = build_report(AC, notes)
    assert report.covered == 1
    assert len(report.items[0].evidence) >= 4


def test_the_single_line_form_still_works():
    """The fix adds a form; it must not cost the one that already worked."""
    notes = f"[2026-08-03T10:00:00Z] AC-1: ✓ {REAL}"
    assert build_report(AC, notes).covered == 1
    assert checklist_missing(_task(notes)) is False


class TestWideningIsNotAcceptingAnything:
    """The half that keeps the gate a gate."""

    def test_a_task_with_no_checklist_is_still_warned(self):
        notes = "[2026-08-03T10:00:00Z] Сделал правку, вроде работает."
        assert checklist_missing(_task(notes)) is True

    def test_prose_naming_a_path_is_not_evidence_even_inside_a_section(self):
        """The line that made the tick mandatory for inheritance.

        Taken from a real task's notes: a PLANNING note recording which tests
        constrain the change. It names paths and sits under a heading, and it is
        not a claim that anything was verified.
        """
        notes = (
            "[2026-08-03T10:00:00Z] AC-1 (что проверяется): свойство.\n"
            "ОГРАНИЧЕНИЕ, КОТОРОЕ НАДО СОБЛЮСТИ: tests/test_knowledge_write.py:62 "
            "утверждают форму выдачи.\n"
        )
        assert build_report(AC, notes).covered == 0
        assert checklist_missing(_task(notes)) is True

    def test_prose_starting_with_a_digit_does_not_open_a_section(self):
        """The regression the widening introduced, caught by pre-tag review.

        `AC_NUMBER_PREFIX_RE` makes the `AC` token optional — correctly, because
        it was written for the `acceptance_criteria` FIELD, where every line is
        numbered by construction. Applied to free-form notes it read an ordinary
        sentence as a heading, and the next citation — about something else
        entirely — was credited to that criterion.

        Not cosmetic: `_evidence_strength` counts real citations PER TASK and
        the Rule 5 hard block clears at one, so one sentence beginning with a
        digit could clear the gate for a task with no real coverage at all.
        """
        notes = (
            "Ran the full suite locally.\n"
            "3 retries were added to the flaky network client during cleanup.\n"
            f"✓ {REAL}\n"
        )
        report = build_report(AC, notes)
        assert report.covered == 0, f"prose credited AC {report.gaps()}"
        assert len(report.unmatched_evidence) == 1
        assert checklist_hard_block(_task(notes), set())[0] is True

    @pytest.mark.parametrize(
        "heading",
        [
            "5 environment variables were added to the sample config.",
            "2 of the three flaky tests were quarantined.",
            "1) this is prose that happens to be numbered.",
        ],
    )
    def test_no_digit_led_sentence_opens_a_section(self, heading):
        notes = f"[2026-08-03T10:00:00Z] {heading}\n✓ {REAL}\n"
        assert build_report(AC, notes).covered == 0

    def test_but_an_explicit_AC_token_still_does(self):
        """The control: the mechanism is genuinely reachable, so the tests above
        mean something."""
        notes = f"[2026-08-03T10:00:00Z] AC-2 (what is checked): the thing.\n✓ {REAL}\n"
        assert build_report(AC, notes).covered == 1

    def test_a_bare_tick_does_not_inherit_a_section(self):
        """A check mark is a claim that verification happened — the thing being
        verified. It must not acquire a criterion by proximity."""
        notes = "[2026-08-03T10:00:00Z] AC-1 (что проверяется): свойство.\n✓ проверено\n"
        assert build_report(AC, notes).covered == 0
        assert checklist_missing(_task(notes)) is True

    def test_a_citation_before_any_heading_belongs_to_nothing(self):
        notes = f"[2026-08-03T10:00:00Z] ✓ {REAL}\n"
        report = build_report(AC, notes)
        assert report.covered == 0
        assert len(report.unmatched_evidence) == 1

    def test_a_blank_line_ends_the_section(self):
        """Conservative boundary: a citation paragraphs below a heading was not
        obviously meant for it, and guessing wrong invents evidence."""
        notes = f"[2026-08-03T10:00:00Z] AC-1 (что проверяется): свойство.\n\n✓ {REAL}\n"
        assert build_report(AC, notes).covered == 0

    def test_a_new_log_entry_ends_the_section(self):
        """`task log` appends independently — a heading in an earlier entry says
        nothing about a citation in a later one."""
        notes = (
            "[2026-08-03T10:00:00Z] AC-1 (что проверяется): свойство.\n"
            f"[2026-08-03T11:00:00Z] ✓ {REAL}\n"
        )
        report = build_report(AC, notes)
        assert report.covered == 0
        assert len(report.unmatched_evidence) == 1

    def test_a_later_heading_takes_over_from_the_earlier_one(self):
        """Evidence must not keep flowing into the first criterion forever."""
        notes = (
            "[2026-08-03T10:00:00Z] AC-1 (что проверяется): первое.\n"
            f"✓ {REAL}\n"
            "AC-3 (что проверяется): третье.\n"
            f"✓ {REAL}\n"
        )
        report = build_report(AC, notes)
        assert report.gaps() == [2], f"covered the wrong criteria: gaps={report.gaps()}"


class TestTheMessageNamesBothForms:
    """AC5: showing one example without saying it was the ONLY recognised one is
    what made a correct checklist look absent."""

    @pytest.mark.parametrize("tier", ["substantial", "deep"])
    def test_the_hard_block_message_offers_the_multiline_form(self, tier):
        from gate_ac_check import checklist_hard_block

        blocking, message = checklist_hard_block(_task("nothing here", tier), set())
        assert blocking
        assert "AC-3: ✓ tests/test_foo.py::test_bar" in message
        assert "beneath it" in message

    def test_the_warning_offers_both_forms(self):
        from gate_ac_check import check_verification_checklist

        warning = check_verification_checklist(_task("nothing here"), set())
        assert "one line" in warning
        assert "beneath it" in warning
