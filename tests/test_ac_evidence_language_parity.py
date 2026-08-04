"""Language parity of the AC-evidence detectors.

task-done-evidence-written-after-the-gate-that-reads-it. Closure printed
  NOTE: high/critical task should exercise the AC's negative scenario —
        no `Negative:` evidence found in notes
  NOTE: domain challenge — ... Add a `Domain:` evidence line
on three real closures of session #134 whose negative scenarios WERE exercised
and pinned — because the evidence was written in Russian, the language of the
project, and only DOMAIN_RE spoke it.

The filed hypothesis (evidence written to notes AFTER the check that reads it)
is refuted here too: `service_task_done` re-reads the task between the two, so
the verdict depends on the TEXT and not on the path it arrived by.
"""

from __future__ import annotations

import os
import sys

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import ac_evidence_detectors as det  # noqa: E402
import service_ac_evidence  # noqa: E402
from gate_ac_check import check_verification_checklist  # noqa: E402
from service_ac_evidence import build_report  # noqa: E402

# Verbatim from the evidence of push-gate-ors-two-dialects-and-false-blocks and
# pwsh-here-string-body-parsed-as-commands (session #134). Both closures printed
# both NOTEs; both had exercised the negative scenario.
_REAL_RU_EVIDENCE = (
    "AC-1 разбор here-string не рвётся: tests/test_powershell_channel.py::test_a.\n"
    "AC-2 негативные пины на ложный блок: "
    "tests/test_powershell_channel.py::test_a_mention_is_not_a_push.\n"
    "AC-3 результат имеет смысл вне тестов: прогнаны реальные хук-процессы."
)
_REAL_AC = "1. разбор не рвётся\n2. ложный блок не возникает\n3. смысл вне тестов"


class TestProducerDerivedParity:
    """The parity expectation is COMPUTED from what the parser actually uses.

    Session #134 warning: a test that enumerates the set it guards cannot
    notice the set growing. So the detector names come from the bytecode of
    `_evidence_lines_for_unit`, not from a list written here — a new detector
    added English-only fails this test instead of silently reopening the gap.
    """

    def _applied_detector_names(self) -> set[str]:
        used = set(service_ac_evidence._evidence_lines_for_unit.__code__.co_names)
        return {n for n in used if n.endswith("_RE")}

    def test_every_applied_detector_is_declared_in_exactly_one_bucket(self):
        applied = self._applied_detector_names()
        assert applied, "bytecode scan found no detectors — the scan itself broke"
        prose = set(det.PROSE_DETECTORS)
        structural = set(det.STRUCTURAL_DETECTORS)
        assert not (prose & structural), "a detector cannot be both prose and structural"
        undeclared = applied - prose - structural
        assert not undeclared, (
            f"detector(s) {sorted(undeclared)} are applied to evidence text but "
            "declared in neither PROSE_DETECTORS nor STRUCTURAL_DETECTORS"
        )

    def test_every_prose_detector_matches_russian(self):
        # One Russian sample per prose detector: the language the evidence of
        # this project is written in. Keys are checked against the registry by
        # the test below, so a new prose detector cannot skip this table.
        samples = {
            "NEGATIVE_RE": "негативные сценарии прогнаны",
            "MANUAL_RE": "проверено вручную на реальном событии",
            "REVIEW_RE": "ревью проведено",
            "DOMAIN_RE": "результат имеет смысл вне тестов",
        }
        for name, pattern in det.PROSE_DETECTORS.items():
            assert name in samples, f"no Russian sample for prose detector {name}"
            assert pattern.search(samples[name]), f"{name} does not match Russian prose"

    def test_every_prose_detector_still_matches_english(self):
        samples = {
            "NEGATIVE_RE": "Negative: bad creds return 401",
            "MANUAL_RE": "verified manually on staging",
            "REVIEW_RE": "adversarial review record attached",
            "DOMAIN_RE": "Domain: output is valid for real inputs",
        }
        for name, pattern in det.PROSE_DETECTORS.items():
            assert pattern.search(samples[name]), f"{name} lost its English coverage"


class TestRealClosureRegression:
    def test_russian_evidence_now_counts_as_negative_and_domain(self):
        rep = build_report(_REAL_AC, _REAL_RU_EVIDENCE)
        assert rep.has_negative_evidence is True
        assert rep.has_domain_evidence is True

    def test_closure_with_russian_evidence_prints_neither_note(self):
        task = {
            "tier": "moderate",
            "complexity": "complex",  # -> checklist tier high, where Negative: is asked
            "notes": _REAL_RU_EVIDENCE,
            "acceptance_criteria": _REAL_AC,
            "relevant_files": "[]",
        }
        out = check_verification_checklist(task)
        assert "negative scenario" not in out
        assert "domain challenge" not in out

    def test_closure_without_any_such_evidence_still_prints_both(self):
        """Anti-gutting pin: the fix must not be 'delete the check'."""
        task = {
            "tier": "moderate",
            "complexity": "complex",
            "notes": (
                "AC-1: ✓ tests/test_powershell_channel.py::test_a\n"
                "AC-2: ✓ tests/test_powershell_channel.py::test_b\n"
                "AC-3: ✓ tests/test_powershell_channel.py::test_c"
            ),
            "acceptance_criteria": _REAL_AC,
            "relevant_files": "[]",
        }
        out = check_verification_checklist(task)
        assert "negative scenario" in out
        assert "domain challenge" in out


class TestVerdictIsTextNotPath:
    """AC-5 control for the filed (and refuted) ordering hypothesis.

    `task done --evidence X` logs X to notes and re-reads the task before the
    checks; `task log X` then `task done` produces the same notes. So the same
    text must produce the same verdict — writing it earlier is not a workaround,
    and the ordering was never the cause.
    """

    def test_same_text_same_verdict_regardless_of_how_it_arrived(self):
        via_evidence = build_report(_REAL_AC, _REAL_RU_EVIDENCE)
        via_earlier_log = build_report(_REAL_AC, f"[2026-07-24T10:00:00Z] {_REAL_RU_EVIDENCE}")
        assert via_earlier_log.has_negative_evidence == via_evidence.has_negative_evidence
        assert via_earlier_log.has_domain_evidence == via_evidence.has_domain_evidence

    def test_timestamp_prefix_does_not_hide_a_marker(self):
        """`task log` prefixes every line — the prefix must not eat the marker."""
        rep = build_report("1. a", "[2026-07-24T12:00:55Z] Negative: bad input rejected")
        assert rep.has_negative_evidence is True


class TestNoFalseCreditFromUnrelatedProse:
    def test_plain_evidence_without_markers_stays_uncredited(self):
        rep = build_report("1. a", "AC-1: ✓ tests/test_x.py::test_a")
        assert rep.has_negative_evidence is False
        assert rep.has_domain_evidence is False

    def test_russian_words_that_are_not_the_markers_do_not_credit(self):
        rep = build_report("1. a", "AC-1: ✓ переписал парсер, добавил разбор строк")
        assert rep.has_negative_evidence is False
        assert rep.has_domain_evidence is False


class TestTheTwoLanguagesAreEquallyLoose:
    """The parity table above proves each detector speaks Russian AND English; it
    does not prove they are the SAME strictness. These pin that — a detector that
    credits a bare word in one language must credit it in the other, and a false
    positive one language avoids the other must avoid too."""

    def test_review_credits_a_bare_stem_in_both_languages(self):
        # English used to demand a phrase; a plain "code review" was HARD-blocked
        # while Russian "ревью" passed. They must now agree.
        assert bool(det.REVIEW_RE.search("code review completed")) is True
        assert bool(det.REVIEW_RE.search("reviewed by a senior engineer")) is True
        assert bool(det.REVIEW_RE.search("код прошёл ревью")) is True
        # Same-boolean is the actual invariant, not "both happen to be True".
        assert bool(det.REVIEW_RE.search("code review")) == bool(
            det.REVIEW_RE.search("проведено ревью")
        )

    def test_review_keeps_its_old_english_forms_and_rejects_lookalikes(self):
        assert det.REVIEW_RE.search("adversarial review record attached")
        assert det.REVIEW_RE.search("/review skill was run")
        # A word that merely contains the letters must not credit.
        assert det.REVIEW_RE.search("previewing the data") is None

    def test_domain_rejects_a_compound_in_both_languages(self):
        # `subdomain` / `поддоменное` is not a domain-sanity challenge. English
        # never credited it; Russian used to. They must now agree.
        assert det.DOMAIN_RE.search("subdomain check passed") is None
        assert det.DOMAIN_RE.search("поддоменное имя проверено") is None
        assert bool(det.DOMAIN_RE.search("subdomain check")) == bool(
            det.DOMAIN_RE.search("поддоменное имя")
        )

    def test_domain_still_credits_a_genuine_domain_line_in_russian(self):
        assert det.DOMAIN_RE.search("доменная проверка смысла пройдена")
        assert det.DOMAIN_RE.search("результат имеет смысл вне тестов")
