"""The checklist warning reads the same evidence the parser finds
(checklist-warning-contradicts-the-evidence-it-reads).

Measured in session #267: the warning comes from `gate_ac_check.checklist_missing`,
which counts criteria whose evidence names an activity. Acceptance criteria
written inline as 'AC-1 text AC-2 text' — no '.' after the number — parsed as
ONE item, so the journal's 'AC-2: ✓ tests/…::test_…' had no item to bind to and
the note said no criterion named a test while the evidence was there.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from gate_ac_check import checklist_missing
from service_ac_evidence import parse_ac_text

AC = "AC-1 Связь хранится как данные. AC-2 Ссылка проверяется на трекер. AC-3 Голый номер отвергается."
REF = "tests/test_tracker_ref.py::TestГолыйНомерОтвергнут::test_номер_без_трекера_отказ"


def test_inline_ac_prefixed_items_are_three_items():
    assert len(parse_ac_text(AC)) == 3


def test_the_evidence_is_bound_and_the_warning_stays_quiet():
    task = {"acceptance_criteria": AC, "notes": f"[2026-09-01T00:00:00Z] AC-3: ✓ {REF}\n"}
    assert checklist_missing(task, set()) is False


def test_a_task_with_no_evidence_is_still_warned():
    task = {"acceptance_criteria": AC, "notes": "[2026-09-01T00:00:00Z] AC-1: ✓ done\n"}
    assert checklist_missing(task, set()) is True


def test_prose_numbers_without_the_prefix_do_not_split():
    text = "Handles Python 3.11 and returns 2 values within 5 seconds"
    assert len(parse_ac_text(text)) == 1
