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
    # Genuinely keyword-free: no negative/manual/review/domain marker, no AC tag,
    # no test ref. ("Reviewed" would now match REVIEW_RE's bare stem — the point
    # of this case is the marker-LESS line, so it must not contain one.)
    notes = "Refactored the parser, no specific AC tag"
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


# --- ac-evidence-parser-format-strict --------------------------------------
# The parser must tolerate the two project-authored prefixes in front of an AC
# number — the task_log `[timestamp]` and an `AC verified:` / `AC:` header —
# WITHOUT loosening the "criterion number + resolvable ref" requirement.

import pytest  # noqa: E402


@pytest.mark.parametrize(
    "line",
    [
        "[2026-04-23T04:28:29Z] AC verified: 1. ✓ tests/test_x.py::test_a",
        "[2026-04-27T12:11:41Z] AC: 1.✓ tests/test_x.py stuff",
        "[2026-04-23T04:28:29Z] 1. ✓ tests/test_x.py",
        "AC-1: ✓ tests/test_x.py",
        "AC1 ✓ tests/test_x.py",
    ],
)
def test_timestamp_and_header_prefix_bind_to_ac(line):
    """AC1/AC2: each project-authored form binds the test ref to AC 1."""
    ac = "1. do the thing"
    rep = build_report(ac, line)
    item1 = next(i for i in rep.items if i.ac_index == 1)
    assert item1.has_test_ref is True, f"failed to bind: {line!r}"
    assert rep.covered_with_tests == 1


@pytest.mark.parametrize(
    "line",
    [
        # A test path but NO criterion number → must NOT be credited.
        "[2026-04-24T09:46:34Z] - pytest tests/test_x.py: 15/15 pass",
        "[2026-05-01T01:08:24Z] Tests: tests/test_x.py (7 cases)",
        # A stray number inside prose is not a criterion marker.
        "[2026-04-23T04:28:29Z] see section 3. tests/test_x.py in passing",
        # A decision reference with a '#' number is not an AC marker.
        "[2026-04-23T04:28:29Z] Decision #138 touches tests/test_x.py",
        # An em-dash 'AC verified —' header with no following number.
        "[2026-04-28T08:53:50Z] AC verified — see prior notes; pytest tests/test_x.py",
    ],
)
def test_numberless_test_mentions_not_credited(line):
    """AC3 (fail-closed): a test path without a criterion number earns no AC
    credit — the prefix strip must not loosen this."""
    ac = "1. do the thing"
    rep = build_report(ac, line)
    assert rep.covered_with_tests == 0, f"wrongly credited: {line!r}"
    # The evidence line still exists (it carries a test ref) but is unmatched.
    assert all(e.ac_index is None for e in rep.unmatched_evidence if e.test_refs)


def test_header_strip_does_not_eat_ac_number_token():
    """The colon-anchored header strip must not consume the number in `AC-1:`
    (that number IS the criterion) — `AC-1:` still binds to AC 1."""
    from service_ac_evidence import _strip_log_prefixes

    assert _strip_log_prefixes("AC-1: ✓ tests/test_x.py").startswith("AC-1")
    # And the multi-word colon header IS stripped.
    assert _strip_log_prefixes("[t] AC verified: 1. ✓ x").strip().startswith("1.")


def test_prefix_strip_preserves_raw_evidence_text():
    """The strip is index-detection only — the stored `raw` keeps the original
    line (timestamp included) so evidence remains auditable."""
    line = "[2026-04-23T04:28:29Z] AC verified: 1. ✓ tests/test_x.py"
    lines = parse_evidence_lines(line)
    assert any("2026-04-23" in e.raw for e in lines)


# --- ac-evidence-parser-cannot-see-a-measurement ---------------------------
# The strongest evidence in the project (a real gate run) must be READABLE.


def test_verification_run_is_a_measurement_with_captured_id():
    """AC1: `verification_run #NNNN` is recognised as a measurement and its run
    id is captured for the gate layer to fact-check."""
    lines = parse_evidence_lines("AC-1: verification_run #1450 scoped pytest PASS")
    e = next(x for x in lines if x.ac_index == 1)
    assert e.is_measurement is True
    assert e.measurement_run_id == 1450
    assert e.evidence_type == "measurement"


def test_pytest_summary_is_a_measurement_by_number_form():
    """AC1: a pytest summary is a measurement recognised by the passed-count
    shape (number, not a keyword) — but carries no run id to fact-check."""
    lines = parse_evidence_lines("AC-2: 5778 passed, 23 skipped in 564.12s")
    e = next(x for x in lines if x.ac_index == 2)
    assert e.is_measurement is True
    assert e.measurement_run_id is None
    assert e.evidence_type == "measurement"


def test_measurement_counts_toward_covered_by_form():
    """AC1: report.covered credits a measurement by form (parity with test_ref),
    so a criterion proven by a run is no longer 'no evidence'."""
    rep = build_report(
        "1. a\n2. b",
        "AC-1: verification_run #1450\nAC-2: 6000 passed in 300s",
    )
    assert rep.covered == 2


def test_prose_number_is_not_a_measurement():
    """NEGATIVE: an ordinary number in prose is not a pytest summary — only the
    `N passed` shape and `verification_run #N` are measurements."""
    lines = parse_evidence_lines("AC-1: refactored 3 modules and 5 helpers")
    e = next(x for x in lines if x.ac_index == 1)
    assert e.is_measurement is False
