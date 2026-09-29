"""A rotted or invented closure citation is retired only by an outcome (github#150).

closure-citations-rot-is-detected-but-never-acted-on (1.10). The audit read a
reconciliation note as prose, so the same findings came back every pass and
nobody acted on them. An appended outcome line now retires a finding — only
when it is valid and only when every citing task has one.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import closure_amendments as ca
from audit_closure_evidence import (
    NEVER_EXISTED,
    RECONCILED,
    RETIRED,
    ROTTED,
    UNPROVEN,
    audit_closure_evidence,
    successor_ref,
)

OLD = "tests/test_alpha.py::test_renamed_from_that"
NEW = "tests/test_alpha.py::test_renamed_to_this"


def _repo(tmp_path: Path) -> str:
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_alpha.py").write_text(
        "def test_renamed_to_this():\n    pass\n", encoding="utf-8"
    )
    return str(tmp_path)


def _cite(ref: str) -> str:
    return f"- 2026-01-01T00:00:00Z [done] — AC-1: ✓ {ref}"


def _log(line: str) -> str:
    return f"\n[2026-09-24T00:00:00Z] {line}"


def _probe(known: set[str]):
    def probe(_root, rel, name):
        return (f"{rel}::{name}" if name else rel) in known

    return probe


def _audit(root: str, tasks: list[dict]) -> dict:
    return audit_closure_evidence(root, tasks, probe=_probe({OLD}))


def _verdict(report: dict, ref: str = OLD) -> str:
    return next(f["verdict"] for f in report["findings"] if f["ref"] == ref)


@pytest.mark.parametrize(
    "line, bucket",
    [
        (f"EVIDENCE-MOVED: {OLD} => {NEW}", RECONCILED),
        (f"EVIDENCE-RETIRED: {OLD} — feature removed in 1.8", RETIRED),
        (f"EVIDENCE-UNPROVEN: {OLD} — no test covers AC-1", UNPROVEN),
    ],
    ids=["moved", "retired", "unproven"],
)
def test_an_outcome_moves_the_finding_to_its_own_counted_bucket(tmp_path, line, bucket):
    report = _audit(_repo(tmp_path), [{"slug": "a", "notes": _cite(OLD) + _log(line)}])
    assert _verdict(report) == bucket
    assert report["counts"][bucket] == 1 and report["counts"][ROTTED] == 0


def test_moved_to_a_ref_that_does_not_resolve_retires_nothing(tmp_path):
    line = f"EVIDENCE-MOVED: {OLD} => tests/test_alpha.py::test_also_gone"
    report = _audit(_repo(tmp_path), [{"slug": "a", "notes": _cite(OLD) + _log(line)}])
    assert _verdict(report) == ROTTED


def test_an_outcome_in_one_of_two_citing_tasks_retires_nothing(tmp_path):
    line = f"EVIDENCE-MOVED: {OLD} => {NEW}"
    report = _audit(
        _repo(tmp_path),
        [
            {"slug": "a", "notes": _cite(OLD) + _log(line)},
            {"slug": "b", "notes": _cite(OLD)},
        ],
    )
    assert _verdict(report) == ROTTED


def test_an_invented_citation_can_be_answered_as_unproven(tmp_path):
    ghost = "tests/test_alpha.py::test_never_written"
    line = f"EVIDENCE-UNPROVEN: {ghost} — cited from memory; no test exists"
    report = _audit(_repo(tmp_path), [{"slug": "a", "notes": _cite(ghost) + _log(line)}])
    finding = next(f for f in report["findings"] if f["ref"] == ghost)
    assert finding["verdict"] == UNPROVEN and finding["was"] == NEVER_EXISTED


def test_the_answer_template_names_the_full_successor(tmp_path):
    report = _audit(_repo(tmp_path), [{"slug": "a", "notes": _cite(OLD)}])
    (finding,) = report["findings"]
    assert successor_ref(finding) == NEW
    assert ca.template(OLD, "a", NEW) == f'tausik task log a "EVIDENCE-MOVED: {OLD} => {NEW}"'


class TestAnAddressIsNotASentence:
    """MEASURED on the first real use: one answer, one full stop, silently not counted.

    A journal line is prose. An author who finishes the thought puts a full stop right after
    the reference, `\S+` took it into the address, the address resolved to nothing, and the
    answer did not count — with no complaint, which is the class this project calls zero
    tolerance. The register stayed red and the reason was invisible.
    """

    @pytest.mark.parametrize(
        ("line", "expected"),
        [
            pytest.param(
                "EVIDENCE-MOVED: a.py::t => tests/x.py::test_y.",
                "tests/x.py::test_y",
                id="full_stop",
            ),
            pytest.param(
                "EVIDENCE-MOVED: a.py::t => tests/x.py::test_y,",
                "tests/x.py::test_y",
                id="comma",
            ),
            pytest.param(
                "EVIDENCE-MOVED: a.py::t => tests/x.py::test_y;",
                "tests/x.py::test_y",
                id="semicolon",
            ),
            pytest.param(
                "EVIDENCE-MOVED: a.py::t => tests/x.py::test_y",
                "tests/x.py::test_y",
                id="nothing_to_trim",
            ),
        ],
    )
    def test_sentence_punctuation_after_an_address_is_not_part_of_it(self, line, expected):
        assert ca.parse(line)["a.py::t"] == ("moved", expected)

    def test_a_dot_inside_an_address_is_load_bearing(self):
        """Trimming by class rather than by position would eat the extension."""
        assert ca.parse("EVIDENCE-MOVED: a.py::t => tests/x.py")["a.py::t"] == (
            "moved",
            "tests/x.py",
        )

    def test_the_old_address_is_trimmed_too(self):
        """It is read from the same prose and ends a clause just as often.

        The separator before a reason is an em dash or a hyphen, as the format documents; a
        comma there produces no reason at all, and that is the format's answer, not a bug this
        change is allowed to paper over.
        """
        assert ca.parse("EVIDENCE-RETIRED: tests/x.py. — gone with its subject")["tests/x.py"] == (
            "retired",
            "gone with its subject",
        )
        assert ca.parse("EVIDENCE-RETIRED: tests/x.py, gone with its subject") == {}

    def test_a_reason_keeps_its_own_full_stop(self):
        """THE NEGATIVE: a reason is free text, and trimming there would edit what somebody
        wrote. Only addresses are trimmed."""
        got = ca.parse("EVIDENCE-RETIRED: tests/x.py — subject removed in 77703c4a.")
        assert got["tests/x.py"] == ("retired", "subject removed in 77703c4a.")

    def test_a_reference_that_is_only_punctuation_survives(self):
        """Reduced to an empty string it would be a ref nobody can report back, so the trim
        yields to the original rather than returning nothing."""
        got = ca.parse("EVIDENCE-RETIRED: . — nothing here")
        assert "." in got
        assert "" not in got, "an empty key is a finding nobody can name back to the author"
