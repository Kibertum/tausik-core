"""Tests for the SENAR Rule 4 domain challenge (v15s-rule4-domain-challenge).

The QG-2 checklist asks "does the result make sense OUTSIDE the tests?" for all
tiers except planning-tier trivial. Covers the parser recognition, the
evidence-json domain tag, and the checklist warning gating.
"""

from __future__ import annotations

import os
import sys

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from gate_ac_check import check_verification_checklist  # noqa: E402
from service_ac_evidence import build_report, evidence_json_to_prose  # noqa: E402


class TestParserRecognition:
    def test_domain_line_recognized(self):
        rep = build_report("1. a", "AC-1: ✓ tests/t.py. Domain: output valid for real inputs")
        assert rep.has_domain_evidence is True

    def test_phrasings_recognized(self):
        for note in (
            "Sanity: makes sense",
            "результат имеет смысл вне тестов",
            "доменный вопрос пройден",
            "real-world plausible",
        ):
            assert build_report("1. a", note).has_domain_evidence is True

    def test_absent_domain_is_false(self):
        rep = build_report("1. a", "AC-1: ✓ tests/t.py::test_a")
        assert rep.has_domain_evidence is False

    def test_empty_notes_no_crash(self):
        assert build_report("", "").has_domain_evidence is False


class TestEvidenceJsonDomainTag:
    def test_domain_tag_emitted(self):
        prose = evidence_json_to_prose(
            '{"ac_evidence":[{"n":1,"status":"pass","evidence":"sum >= 0 for real orders","domain":true}]}'
        )
        assert "domain" in prose
        # Round-trips through the parser as domain evidence.
        assert build_report("1. a", prose).has_domain_evidence is True


class TestChecklistGating:
    def test_warns_when_domain_missing_non_trivial(self):
        task = {
            "tier": "moderate",
            "notes": "AC-1: ✓ tests/t.py::test_a",
            "acceptance_criteria": "1. does a thing\n2. errors on bad input",
            "relevant_files": "[]",
        }
        out = check_verification_checklist(task)
        assert "domain challenge" in out

    def test_skipped_for_trivial_tier(self):
        task = {
            "tier": "trivial",
            "notes": "AC-1: ✓ tests/t.py::test_a",
            "acceptance_criteria": "1. does a thing\n2. errors on bad input",
            "relevant_files": "[]",
        }
        out = check_verification_checklist(task)
        assert "domain challenge" not in out

    def test_satisfied_when_domain_present(self):
        task = {
            "tier": "moderate",
            "notes": "AC-1: ✓ tests/t.py::test_a. Domain: result valid for real inputs",
            "acceptance_criteria": "1. does a thing\n2. errors on bad input",
            "relevant_files": "[]",
        }
        out = check_verification_checklist(task)
        assert "domain challenge" not in out
