"""Answer length is measured; this is the thing that goes red when it grows.

WHY IT EXISTS. `tausik metrics answers` produced a number from 1.10 and nothing compared it
to anything. Story J closed as delivered while the median final answer went from 396 words to
522 against a budget of 200. A number nobody compares only records the drift it was built to
stop.

WHY IT DOES NOT BLOCK A BUILD. Host transcripts live on the machine that wrote them and never
travel — the property `red_history` already declares about which tests have been seen red. So
the live check below SKIPS with a named reason where there is nothing to read, rather than
reading absence as zero (decision #334) or as a failure. A check that fails on missing data is
a check people learn to pass a flag to.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import answer_budget_ratchet as abr  # noqa: E402


@pytest.fixture
def gates(tmp_path):
    """A repo root carrying only the baseline this module reads."""
    (tmp_path / "tausik").mkdir()

    def write(node):
        (tmp_path / "tausik" / "gates.json").write_text(
            json.dumps({abr.GATES_KEY: node} if node is not None else {}), encoding="utf-8"
        )
        return str(tmp_path)

    return write


def _measured(monkeypatch, **kw):
    base = {"transcripts": 3, "answers": 40, "final_words_median": 300, "final_words_p90": 600}
    base.update(kw)
    monkeypatch.setattr(abr, "measure_local", lambda *_a, **_k: base)
    return base


class TestGrowthIsTheSignal:
    @pytest.mark.parametrize(
        ("median", "p90", "named"),
        [
            pytest.param(301, 600, "median", id="median_grew"),
            pytest.param(300, 601, "p90", id="p90_grew"),
            pytest.param(400, 900, "median", id="both_grew"),
        ],
    )
    def test_a_number_above_the_baseline_warns_and_says_which(
        self, gates, monkeypatch, median, p90, named
    ):
        root = gates({"final_words_median": 300, "final_words_p90": 600})
        _measured(monkeypatch, final_words_median=median, final_words_p90=p90)
        v = abr.check(root, repo_root=root)
        assert v.level == "warn"
        assert named in v.detail and "GREW" in v.detail

    def test_the_warning_points_at_the_rule_rather_than_at_the_number(self, gates, monkeypatch):
        """A ratchet that only says "bigger" invites raising the baseline. This one names
        where the rule lives, because the fix is to follow it."""
        root = gates({"final_words_median": 300, "final_words_p90": 600})
        _measured(monkeypatch, final_words_median=500)
        assert "rules file" in abr.check(root, repo_root=root).detail


class TestShrinkingIsNotAFailure:
    def test_an_improvement_passes_and_asks_to_be_recorded(self, gates, monkeypatch):
        """AC-4: a ratchet only holds what it was told, so the lower number has to be
        written down or the next regression is measured against the old slack."""
        root = gates({"final_words_median": 300, "final_words_p90": 600})
        _measured(monkeypatch, final_words_median=210, final_words_p90=400)
        v = abr.check(root, repo_root=root)
        assert v.level == "ok"
        assert "shrank" in v.detail and "gates.json" in v.detail

    def test_sitting_exactly_on_the_baseline_is_ok_and_quiet(self, gates, monkeypatch):
        root = gates({"final_words_median": 300, "final_words_p90": 600})
        _measured(monkeypatch)
        v = abr.check(root, repo_root=root)
        assert v.level == "ok" and "at the baseline" in v.detail


class TestAbsenceIsReportedAsAbsence:
    """Three different facts, three different answers, none of them a failure."""

    def test_no_transcripts_at_all(self, gates, monkeypatch):
        root = gates({"final_words_median": 300})
        monkeypatch.setattr(abr, "measure_local", lambda *_a, **_k: {})
        v = abr.check(root, repo_root=root)
        assert v.level == "absent" and "no host transcripts" in v.detail

    def test_too_few_answers_to_make_a_median_mean_anything(self, gates, monkeypatch):
        root = gates({"final_words_median": 300})
        _measured(monkeypatch, answers=abr.MIN_ANSWERS - 1)
        v = abr.check(root, repo_root=root)
        assert v.level == "absent" and "describe the sample" in v.detail

    def test_no_baseline_recorded_yet_prints_the_numbers_to_record(self, gates, monkeypatch):
        root = gates(None)
        _measured(monkeypatch, final_words_median=333, final_words_p90=777)
        v = abr.check(root, repo_root=root)
        assert v.level == "absent"
        assert "333" in v.detail and "777" in v.detail

    def test_an_unreadable_gates_file_is_no_baseline_not_a_crash(self, tmp_path, monkeypatch):
        (tmp_path / "tausik").mkdir()
        (tmp_path / "tausik" / "gates.json").write_text("{not json", encoding="utf-8")
        _measured(monkeypatch)
        assert abr.check(str(tmp_path), repo_root=str(tmp_path)).level == "absent"


class TestTheDoctorRowNeverTakesTheDashboardDown:
    def test_a_failing_measurement_is_an_ok_row_saying_it_did_not_measure(self, monkeypatch):
        def boom(*_a, **_k):
            raise RuntimeError("transcript directory vanished")

        monkeypatch.setattr(abr, "check", boom)
        level, detail = abr.doctor_line(".", repo_root=".")
        assert level == "ok" and "not measured" in detail

    def test_growth_reaches_the_dashboard_as_a_warning(self, gates, monkeypatch):
        root = gates({"final_words_median": 300, "final_words_p90": 600})
        _measured(monkeypatch, final_words_median=900)
        level, detail = abr.doctor_line(root, repo_root=root)
        assert level == "warn" and "GREW" in detail


class TestTheBaselineIsAMeasurementNotAWish:
    def test_it_is_not_the_budget(self):
        """200 is what the agent is told to aim at. A ratchet set there would be crossed on
        day one, and a threshold ordinary work crosses is one somebody switches off — the
        lesson this project already paid for with a telemetry window."""
        from answer_shape import DEFAULT_BUDGET_WORDS

        recorded = abr.baseline(str(_REPO))
        assert recorded, "the live repository must carry a recorded baseline"
        assert recorded["final_words_median"] > DEFAULT_BUDGET_WORDS

    def test_the_recorded_baseline_says_when_and_over_what_it_was_measured(self):
        note = abr.baseline(str(_REPO)).get("_comment", "")
        assert "2026-09-29" in note and "transcripts" in note
        assert "only shrink" in note

    def test_the_live_machine_is_not_above_its_own_baseline(self):
        """The ratchet itself, on this checkout. Skips where there is nothing to read —
        the number does not travel between machines."""
        v = abr.check(str(_REPO), repo_root=str(_REPO))
        if v.level == "absent":
            pytest.skip(v.detail)
        assert v.level == "ok", v.detail
