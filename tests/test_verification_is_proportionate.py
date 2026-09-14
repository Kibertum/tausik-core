"""Verification is proportionate to the change (owner, session #263).

The close of a docs/measurement task printed six notes asking for test refs, a
`Negative:` line and a `Domain:` line — each an invitation to write a test that
asserts a sentence. A task whose every relevant file is prose has no behaviour
a test could exercise, so those notes are not printed for it; a task with code
in scope keeps every one of them (the anti-gutting half of the same claim).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
)

from gate_ac_check import check_verification_checklist  # noqa: E402

_AC = "AC-1: the page says X. AC-2: the page says Y. AC-3 (negative): the page never says Z."
# Evidence lines with check marks but no test refs, no Negative:, no Domain:.
_NOTES = "AC-1: ✓ the page says X.\nAC-2: ✓ the page says Y.\nAC-3: ✓ the page never says Z."
_TEST_SHAPED = (
    "Verification checklist",
    "test-ref evidence",
    "negative scenario",
    "domain challenge",
)


def _task(relevant_files: str) -> dict:
    return {
        "tier": "moderate",
        "complexity": "complex",  # -> checklist tier high, where every note is asked
        "notes": _NOTES,
        "acceptance_criteria": _AC,
        "relevant_files": relevant_files,
    }


def test_a_prose_only_task_is_not_asked_for_test_shaped_evidence():
    out = check_verification_checklist(
        _task('["README.md", "docs/en/whats-new-1.9.md", "CHANGELOG.ru.md", "ROADMAP.md"]')
    )
    for note in _TEST_SHAPED:
        assert note not in out, f"a prose-only task was asked for: {note}\n{out}"


def test_a_task_with_code_in_scope_keeps_every_note():
    out = check_verification_checklist(_task('["README.md", "scripts/gate_ac_check.py"]'))
    for note in _TEST_SHAPED:
        assert note in out, f"a code-bearing task lost the note: {note}\n{out}"


def test_an_undeclared_scope_is_not_treated_as_prose():
    """Nothing is known about an empty scope, so the notes keep asking."""
    out = check_verification_checklist(_task("[]"))
    assert "negative scenario" in out and "domain challenge" in out
