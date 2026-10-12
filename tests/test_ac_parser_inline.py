"""Inline-aware AC parsing + evidence-marker counting (dogfooding-friction fix).

acceptance_criteria is stored as a SINGLE line ('1. … 2. … N.'), which the old
line-anchored parsers collapsed to one item, and the marker regex r'\\d+[.)].*✓'
did not recognise the canonical 'AC-N: ✓' format — so a correctly-evidenced
close still warned 'N AC criteria, but only 0 markers'. These tests pin the fix.

See scripts/service_ac_evidence.py (parse_ac_text / _split_inline_numbered) and
scripts/gate_ac_check.py (verify_ac).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pytest  # noqa: E402

from gate_ac_check import verify_ac  # noqa: E402
from service_ac_evidence import build_report, parse_ac_text  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402


# --- AC-1: single-line AC splits into N items --------------------------------


def test_single_line_ac_splits_into_items():
    ac = "1. builds the schema. 2. is idempotent. 3. handles the empty case."
    items = parse_ac_text(ac)
    assert len(items) == 3
    assert items[0].startswith("builds the schema")
    assert items[2].startswith("handles the empty case")


def test_single_line_ac_with_ac_prefix():
    ac = "AC-1: first thing. AC-2: second thing."
    items = parse_ac_text(ac)
    assert len(items) == 2
    # Colon separator is consumed — body has no leading ':'.
    assert items[0].startswith("first thing")
    assert not items[0].startswith(":")


def test_multiline_ac_unchanged():
    ac = "1. add foo\n2. add bar\n3. add baz"
    items = parse_ac_text(ac)
    assert len(items) == 3


# --- AC-2: stray numbers do not inflate or mis-split -------------------------


def test_stray_high_number_ignored():
    # Decision #138 and a trailing high number must not become item 9.
    ac = (
        "1. first. 2. second (see Decision #138). 3. third. 4. fourth. "
        "5. fifth. 6. sixth. 7. seventh."
    )
    items = parse_ac_text(ac)
    assert len(items) == 7
    assert "Decision #138" in items[1]  # stays inside item 2, not a boundary


def test_leading_zero_and_decimals_ignored():
    # "0." and "Python 3.11" / "v1.4" must not create boundaries.
    ac = "1. supports Python 3.11 and v1.4. 2. returns 0 on no-op. 3. logs cleanly."
    items = parse_ac_text(ac)
    assert len(items) == 3
    assert "Python 3.11" in items[0]
    assert "returns 0" in items[1]


# --- AC-3: 'AC-N: ✓' markers credited; spurious warning gone -----------------


def test_inline_markers_full_coverage_no_warning():
    ac = "1. builds. 2. is idempotent. 3. handles empty."
    notes = (
        "AC-1: ✓ tested via tests/test_x.py::test_a. "
        "AC-2: ✓ tested via tests/test_x.py::test_b. "
        "AC-3: ✓ tested via tests/test_x.py::test_c."
    )
    rep = build_report(ac, notes)
    assert rep.total_ac == 3
    assert rep.covered == 3
    task = {"acceptance_criteria": ac, "notes": notes}
    warnings = verify_ac("t1", task, ac_verified=True)
    assert not any("evidence markers" in w for w in warnings)


def test_inline_markers_partial_coverage_warns():
    ac = "1. builds. 2. is idempotent. 3. handles empty."
    notes = "AC-1: ✓ tested via tests/test_x.py::test_a. AC-2: ✓ done."
    task = {"acceptance_criteria": ac, "notes": notes}
    warnings = verify_ac("t1", task, ac_verified=True)
    msg = next(w for w in warnings if "evidence markers" in w)
    assert "3 AC criteria, but only 2" in msg


# --- AC-4: boundary cases ----------------------------------------------------


def test_empty_ac_returns_empty():
    assert parse_ac_text("") == []
    assert parse_ac_text("   ") == []


def test_free_prose_falls_back_to_splitlines():
    ac = "Make the thing work and not crash."
    items = parse_ac_text(ac)
    assert items == ["Make the thing work and not crash."]


def test_single_genuine_criterion_stays_one_item():
    ac = "1. the only acceptance criterion here."
    items = parse_ac_text(ac)
    assert len(items) == 1
    assert items[0].startswith("the only")


def test_verify_ac_no_criteria_skips():
    # No acceptance_criteria -> no work, no warning, no raise.
    assert verify_ac("t1", {"acceptance_criteria": "", "notes": ""}, ac_verified=True) == []


# --- Segmented single-line evidence (bare 'N. ✓' + per-segment accuracy) ------


def test_bare_numbered_single_line_evidence_credited():
    ac = "1. a. 2. b. 3. c."
    notes = "AC verified: 1. ✓ tested test_a. 2. ✓ tested test_b. 3. ✓ tested test_c."
    rep = build_report(ac, notes)
    assert rep.total_ac == 3
    assert rep.covered == 3
    task = {"acceptance_criteria": ac, "notes": notes}
    assert not any("evidence markers" in w for w in verify_ac("t1", task, ac_verified=True))


def test_segment_checkmark_is_per_segment_not_line_level():
    # Only criterion 2 carries a ✓ — 1 and 3 must NOT be credited.
    ac = "1. a. 2. b. 3. c."
    notes = "1. pending. 2. ✓ done via tests/test_x.py::test_b. 3. pending."
    rep = build_report(ac, notes)
    assert rep.covered == 1
    assert rep.gaps() == [1, 3]


def test_canonical_inline_still_works_after_segmentation():
    ac = "1. a. 2. b. 3. c."
    notes = "AC-1: ✓ a. AC-2: ✓ b. AC-3: ✓ c."
    rep = build_report(ac, notes)
    assert rep.covered == 3


# --- Adversarial-review hardening --------------------------------------------


def test_prose_numbers_do_not_falsely_credit_criteria():
    # Descriptive prose with stray 'N.' tokens (non-contiguous, no AC prefix)
    # must NOT be segmented into per-criterion evidence (HIGH-2 false positive).
    ac = "1. a. 2. b. 3. c. 4. d. 5. e. 6. f. 7. g."
    notes = "see 3. tested in tests/test_x.py and section 7. confirms output"
    rep = build_report(ac, notes)
    assert rep.covered == 0
    assert 3 in rep.gaps()
    assert 7 in rep.gaps()


def test_bare_non_contiguous_evidence_not_segmented():
    # Bare '1. .. 3. ..' (skips 2, not contiguous, no AC prefix) is processed
    # whole rather than mis-segmented — only the leading prefix index is read.
    ac = "1. a. 2. b. 3. c."
    notes = "1. ✓ done 3. ✓ done"
    rep = build_report(ac, notes)
    # Not over-credited: at most criterion 1 (leading prefix) is recognised.
    assert rep.covered <= 1
    assert 2 in rep.gaps()


def test_bare_verified_word_does_not_bypass_gate():
    # An incidental 'verified' with no AC evidence must raise QG-2, not pass.
    ac = "1. a. 2. b."
    task = {"acceptance_criteria": ac, "notes": "git identity verified by CI"}
    with pytest.raises(ServiceError, match="QG-2"):
        verify_ac("t1", task, ac_verified=True)


def test_covered_evidence_satisfies_gate_without_verified_word():
    # No literal 'verified', but real per-criterion evidence -> no raise.
    ac = "1. a. 2. b."
    notes = "AC-1: ✓ tests/test_x.py::test_a. AC-2: ✓ tests/test_x.py::test_b."
    task = {"acceptance_criteria": ac, "notes": notes}
    warnings = verify_ac("t1", task, ac_verified=True)
    assert not any("evidence markers" in w for w in warnings)
