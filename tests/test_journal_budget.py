"""The journal has a budget, and only the RETELLING half of it does.

MEASURED, session #277: 292 entries across 25 closed tasks, 99,335 characters (~24,800
tokens). Evidence of closure — an AC with a tick, a structured root cause, a domain or
negative line — is 158 entries and 48,400 characters. The other 134 entries and 50,935
characters, 51% of the journal, retell the work. Median entry 319, p90 520, longest 1,355.

Those numbers set the limits rather than taste: 520 is the p90, above every ordinary
entry and below the handful that narrate a session; 2,037 is the measured mean of
retelling per task, a declared remainder that may only shrink.

THE NEGATIVE HALF IS THE POINT, and it is most of this file. A budget that squeezed
evidence would trade the expensive thing for the cheap one — the journal exists so a
closure can be checked, and a release about token economy has no business making proof
shorter. So evidence is exempt at ANY length, and the cap is a signal: a refusal here
would teach agents to close tasks in silence, which is the failure the project was built
against.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import journal_budget as jb  # noqa: E402

LONG = "и" * 900
SHORT = "переписал склейку частей"


class TestEvidenceIsNeverCapped:
    @pytest.mark.parametrize(
        "text",
        [
            pytest.param(f"AC-1: ✓ tests/test_x.py::test_y {LONG}", id="ac_tick"),
            pytest.param(f"AC-2: tested via tests/test_x.py::test_y {LONG}", id="tested_via"),
            pytest.param(f"Root cause (edge-case): {LONG}", id="root_cause"),
            pytest.param(f"Domain: {LONG}", id="domain"),
            pytest.param(f"Negative: {LONG}", id="negative"),
            pytest.param(f"NO-DEAD-END: {LONG}", id="no_dead_end"),
            pytest.param(f"EVIDENCE-RETIRED: tests/x.py::y — {LONG}", id="evidence_amendment"),
        ],
    )
    def test_a_long_proof_gets_no_advisory(self, text):
        """Nine hundred characters of proof is fine. That is what the journal is for."""
        assert jb.is_evidence(text)
        assert jb.entry_advisory(text) == ""

    def test_lowercase_markers_still_count_as_evidence(self):
        """A false negative nags about the very line the close gate demands.

        The check errs generous on purpose: a false positive costs one uncapped entry, a
        false negative pushes the author to shorten proof.
        """
        assert jb.is_evidence(f"ac-3: ✓ tests/x.py::y {LONG}")
        assert jb.is_evidence(f"domain: {LONG}")


class TestRetellingIsCapped:
    def test_a_long_retelling_gets_an_advisory_with_the_number(self):
        line = jb.entry_advisory(f"переписал склейку и прогнал ленту. {LONG}")
        assert line
        assert str(len(f"переписал склейку и прогнал ленту. {LONG}")) in line
        assert "520" in line

    def test_the_advisory_says_what_to_do_instead(self):
        """A cap that does not name the alternative is read as "write less proof"."""
        line = jb.entry_advisory(LONG)
        assert "память" in line or "CHANGELOG" in line
        assert "не ограничено" in line

    @pytest.mark.parametrize("length", [1, 100, 319, 519, 520])
    def test_an_ordinary_entry_is_silent(self, length):
        """The measured median is 319 against a limit of 520, so most entries say nothing."""
        assert jb.entry_advisory("и" * length) == ""

    def test_one_character_over_speaks(self):
        """The boundary is checked, not assumed."""
        assert jb.entry_advisory("и" * 521)

    def test_the_limit_is_a_parameter_not_a_constant_in_the_message(self):
        line = jb.entry_advisory("и" * 200, limit=100)
        assert "100" in line and "520" not in line


class TestThePerTaskSum:
    def test_only_retelling_counts_toward_the_task_total(self):
        entries = [f"AC-1: ✓ tests/x.py::y {LONG}", "короткий пересказ"]
        evidence, retelling = jb.journal_chars(entries)
        assert evidence > 900
        assert retelling == len("короткий пересказ")

    def test_a_task_over_the_sum_gets_one_line(self):
        entries = ["и" * 300] * 10
        line = jb.closing_advisory(entries, limit=2037)
        assert line and "3000" in line
        assert "доказательство закрытия не считается" in line

    def test_a_task_under_the_sum_is_silent(self):
        assert jb.closing_advisory(["и" * 300] * 3, limit=2037) == ""

    def test_a_task_of_pure_evidence_is_silent_at_any_size(self):
        """Ten long proofs are not a budget problem. This is the rule, not an exception."""
        entries = [f"AC-{i}: ✓ tests/x.py::y {LONG}" for i in range(10)]
        assert jb.closing_advisory(entries, limit=2037) == ""


class TestTheLimitsComeFromTheRatchet:
    def test_the_committed_node_carries_both_numbers(self):
        node = json.loads((_REPO / "tausik" / "gates.json").read_text(encoding="utf-8"))
        budget = node["journal_budget"]
        assert budget["entry_chars"] == 520
        assert isinstance(budget["retelling_chars_per_task"], int)

    def test_the_baseline_states_the_measurement_it_came_from(self):
        """A number without the measurement beside it cannot be argued with."""
        node = json.loads((_REPO / "tausik" / "gates.json").read_text(encoding="utf-8"))
        comment = node["journal_budget"]["_baseline_comment"]
        for fact in ("292", "99 335", "50 935", "51%", "319", "520"):
            assert fact in comment, fact
        assert "только уменьшаться" in comment

    def test_limits_are_read_from_the_project(self):
        entry, per_task = jb.limits(str(_REPO))
        assert entry == 520
        assert per_task > 0

    def test_a_project_without_the_node_falls_back_to_the_measured_defaults(self, tmp_path):
        """A project that never adopted the ratchet keeps working.

        The fallback is the figure the measurement produced, not a round number — a
        default nobody measured is how a budget becomes decoration.
        """
        (tmp_path / "tausik").mkdir()
        (tmp_path / "tausik" / "gates.json").write_text("{}", encoding="utf-8")
        assert jb.limits(str(tmp_path)) == (jb.ENTRY_CHARS, jb.TASK_RETELLING_CHARS)

    def test_an_unreadable_ratchet_does_not_raise(self, tmp_path):
        assert jb.limits(str(tmp_path)) == (jb.ENTRY_CHARS, jb.TASK_RETELLING_CHARS)


class TestNothingHereCanBreakAClose:
    def test_close_lines_swallow_a_broken_service(self):
        class Broken:
            def task_logs(self, _slug):
                raise RuntimeError("db gone")

        assert jb.close_lines_for(Broken(), "x") == []

    def test_close_lines_read_the_message_field(self):
        class Fake:
            def task_logs(self, _slug):
                return [{"message": "и" * 3000}]

        lines = jb.close_lines_for(Fake(), "x")
        assert len(lines) == 1 and "3000" in lines[0]

    def test_log_suffix_is_prefixed_only_when_there_is_something_to_say(self):
        assert jb.log_suffix(SHORT) == ""
        assert jb.log_suffix("и" * 900).startswith("\nℹ")
