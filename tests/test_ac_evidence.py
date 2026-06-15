"""SENAR Rule 5 - structured AC evidence parser (v1.4)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from service_ac_evidence import (  # noqa: E402
    build_report,
    parse_ac_text,
    parse_evidence_lines,
)


def test_parse_numbered_ac():
    ac = """
    1. Migration v21 creates table reviews
    2. backend_crud exposes review_record
    3. CLI works end-to-end
    """
    items = parse_ac_text(ac)
    assert len(items) == 3
    assert "Migration" in items[0]


def test_parse_evidence_with_test_ref():
    notes = "AC-1: ✓ tested via tests/test_foo.py::test_bar"
    lines = parse_evidence_lines(notes)
    assert len(lines) == 1
    e = lines[0]
    assert e.ac_index == 1
    assert e.has_checkmark is True
    assert "tests/test_foo.py::test_bar" in e.test_refs
    assert e.evidence_type == "test_ref"


def test_parse_evidence_manual():
    notes = "AC-2: ✓ manual run produced expected output"
    lines = parse_evidence_lines(notes)
    assert lines[0].ac_index == 2
    assert lines[0].is_manual is True
    assert lines[0].evidence_type == "test_ref" or lines[0].evidence_type == "manual"


def test_parse_evidence_negative_scenario():
    notes = "Negative: empty input returns 400 (manual curl run)"
    lines = parse_evidence_lines(notes)
    assert lines[0].is_negative is True


def test_match_evidence_full_coverage():
    ac = "1. add foo\n2. add bar\n3. add baz"
    notes = (
        "AC-1: ✓ tested via tests/test_x.py::test_a\n"
        "AC-2: ✓ tested via tests/test_x.py::test_b\n"
        "AC-3: ✓ manual smoke run\n"
        "Negative: empty payload returns 400"
    )
    rep = build_report(ac, notes)
    assert rep.total_ac == 3
    assert rep.covered == 3
    assert rep.coverage_pct == 100.0
    assert rep.has_negative_evidence is True
    assert rep.gaps() == []


def test_match_evidence_partial_coverage_finds_gaps():
    ac = "1. a\n2. b\n3. c"
    notes = "AC-1: ✓ tested via tests/test_x.py::test_a"
    rep = build_report(ac, notes)
    assert rep.covered == 1
    assert rep.gaps() == [2, 3]


def test_match_evidence_unmatched_lines_collected():
    ac = "1. a"
    notes = "Reviewed code, no specific AC tag"
    rep = build_report(ac, notes)
    assert rep.covered == 0
    assert rep.gaps() == [1]
    assert len(rep.unmatched_evidence) == 0  # plain text without keywords ignored


def test_inline_ac_reference_matches():
    ac = "1. a\n2. b"
    notes = "All good - ✓ checked AC-2 via tests/test_y.py"
    rep = build_report(ac, notes)
    item2 = next(i for i in rep.items if i.ac_index == 2)
    assert item2.has_test_ref is True


def test_parser_handles_empty_input():
    rep = build_report("", "")
    assert rep.total_ac == 0
    assert rep.covered == 0
    assert rep.coverage_pct == 0.0


def test_summary_shape():
    ac = "1. a\n2. b"
    notes = "AC-1: ✓ tested via tests/test_x.py"
    rep = build_report(ac, notes)
    s = rep.to_summary()
    assert "AC coverage" in s
    assert "gaps" in s
    assert "negative scenario" in s
