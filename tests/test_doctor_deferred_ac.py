"""A criterion parked at closure must not outlive the epic silently.

`v14b-followup-subagent-remeasure-quant` AC4. The mechanism that failed:
`v14b-baseline-token-metrics` closed on 2026-05-06 with two acceptance criteria
marked DEFERRED ("accumulates naturally as the user runs sessions"), and nobody
looked again. Two and a half months later the follow-up that depended on them
could not be satisfied at all — the data those criteria were meant to produce
had never been captured.

Two properties matter as much as the detection itself, and both were learned by
getting them wrong first:

  * PRECISION — a first cut allowed 60 characters between the criterion and the
    word, and matched four tasks of which three were false: "deferred loading"
    is a feature name here, and "G8+G18 deferred ... then closed" is already
    resolved. A check wrong three times out of four is worse than none.
  * CLEARABILITY — the deferral text lives in a CLOSED task and can never stop
    matching, so without an escape the warning would stand forever whatever
    anyone did. That is the defect `doctor-claudemd-drift-warn-never-actionable`
    exists to prevent, and reproducing it here would trade one real finding for
    the credibility of every other check.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from service_doctor_backlog import (  # noqa: E402
    check_deferred_acs,
    find_deferred_acs_in_live_work,
)

CROSSCUTTING_SCOPE = ["scripts/"]


class _Fake:
    """Minimal stand-in for the backlog service."""

    def __init__(self, tasks, epics):
        self._tasks, self._epics = tasks, epics

    def task_list(self, status=None):
        if status is None:
            return list(self._tasks)
        wanted = set(status.split(","))
        return [t for t in self._tasks if t.get("status") in wanted]

    def epic_list(self):
        return list(self._epics)


def _svc(notes: str, *, epic_status: str = "active", epic: str = "e1"):
    return _Fake(
        tasks=[{"slug": "t1", "status": "done", "epic_slug": epic, "notes": notes}],
        epics=[{"slug": "e1", "status": epic_status}],
    )


# ---------- detection ----------


def test_criterion_parked_at_closure_is_found():
    svc = _svc("AC-3: DEFERRED — baseline requires future runs")
    assert find_deferred_acs_in_live_work(svc) == ["t1"]


def test_parenthetical_between_criterion_and_marker_still_counts():
    svc = _svc("AC 8 (replay benchmark) deferred: needs a before/after session")
    assert find_deferred_acs_in_live_work(svc) == ["t1"]


# ---------- precision: the three false positives that shipped in the first cut ----------


def test_deferred_loading_is_a_feature_name_not_a_parked_criterion():
    svc = _svc("AC2 (deferred loading covers TAUSIK): empirically confirmed this session")
    assert find_deferred_acs_in_live_work(svc) == []


def test_marker_far_from_the_criterion_does_not_count():
    svc = _svc("AC6: list_tools filter is orthogonal to deferred-loading; boundary documented")
    assert find_deferred_acs_in_live_work(svc) == []


def test_deferred_then_resolved_in_the_same_note_does_not_count():
    svc = _svc("AC-5 negative scenario: G8+G18 deferred per rollback policy then closed")
    assert find_deferred_acs_in_live_work(svc) == []


def test_criterion_about_deferred_loading_is_not_flagged():
    svc = _svc("AC-6: DEFERRED loading of tools verified")
    assert find_deferred_acs_in_live_work(svc) == []


# ---------- clearability ----------


def test_handing_the_criterion_to_an_owner_clears_the_finding():
    """The escape that keeps this warning honest — and it must be recorded, not assumed."""
    svc = _svc("AC-3: DEFERRED — needs two sessions\nAC-3 CARRIED BY some-owning-task")
    assert find_deferred_acs_in_live_work(svc) == []


def test_the_same_note_without_the_hand_off_still_reports():
    svc = _svc("AC-3: DEFERRED — needs two sessions")
    assert find_deferred_acs_in_live_work(svc) == ["t1"]


# ---------- scoping ----------


def test_closed_epic_is_archaeology_not_a_warning():
    """Six of this project's ten parked criteria sit in epics that shipped long ago."""
    svc = _svc("AC-3: DEFERRED — old work", epic_status="done")
    assert find_deferred_acs_in_live_work(svc) == []


def test_missing_epic_list_degrades_quietly_rather_than_crashing_doctor():
    class _Broken(_Fake):
        def epic_list(self):
            raise RuntimeError("db unavailable")

    svc = _Broken(tasks=[{"slug": "t1", "status": "done", "notes": "AC-1: DEFERRED"}], epics=[])
    assert find_deferred_acs_in_live_work(svc) == []


# ---------- doctor finding shape ----------


def test_finding_names_the_task_and_the_clearing_action():
    severity, label, detail = check_deferred_acs(_svc("AC-3: DEFERRED — x"))[0]
    assert severity == "warn"
    assert "t1" in detail
    assert "CARRIED BY" in detail, "the reader must be told how to clear it legitimately"


def test_clean_state_reports_ok():
    severity, _label, detail = check_deferred_acs(_svc("AC-1: verified"))[0]
    assert severity == "ok"
    assert "no closed task" in detail
