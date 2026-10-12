"""SENAR 1.5 §9.4 — a figure is reported with its method, a target with its basis,
and a crossing is escalated once (metrics-disclose-method-and-thresholds-carry-a-basis)."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from metric_methods import (
    DEFAULT_TARGETS,
    METHODS,
    escalate,
    figure,
    method_lines,
    open_crossings,
    set_target,
    targets,
)
from project_backend import SQLiteBackend
from render_metrics import metrics_lines


@pytest.fixture
def be(tmp_path):
    b = SQLiteBackend(str(tmp_path / "m.db"))
    yield b
    b.close()


class _Svc:
    def __init__(self, be, td):
        self.be = be
        self._td = td

    def get_metrics(self):
        return self.be.get_metrics()

    def tausik_dir(self):
        return self._td


def _seed(be, slug, *, attempts=1, defect_of=None):
    if not be.epic_get("e"):
        be.epic_add("e", "Epic")
        be.story_add("e", "s", "Story")
    be.task_add("s", slug, "T", goal="g", role="developer")
    fields = {"attempts": attempts, "status": "done", "completed_at": "2026-09-23T10:00:00Z"}
    if defect_of:
        fields["defect_of"] = defect_of
    be.task_update(slug, **fields)


def _crossings(be):
    return [
        e for e in be.events_list(entity_type="metric") if e["action"] == "metric_target_crossed"
    ]


def test_empty_population_is_reported_as_absent_not_zero(be, tmp_path):
    text = "\n".join(metrics_lines(_Svc(be, str(tmp_path))))
    assert "FPSR:          no population" in text
    assert "DER:           no population" in text
    assert "0.0%" not in text.split("--- How these")[0].split("FPSR")[1].splitlines()[0]


def test_report_discloses_method_population_period_and_self_made_records(be, tmp_path):
    _seed(be, "a")
    text = "\n".join(metrics_lines(_Svc(be, str(tmp_path))))
    assert "How these figures are computed (SENAR 1.5 §9.4)" in text
    assert "Period:" in text
    assert "fpsr: done tasks with attempts = 1 / done tasks — population: done tasks" in text
    assert "measure what was recorded, not what occurred" in text
    assert "target fpsr >= 85.0%: within (basis:" in text


def test_crossing_is_escalated_once_and_cleared_on_recovery(be):
    spec = {"max": 5.0, "basis": "b"}
    assert escalate(be, "der", 9.4, spec) is True
    assert escalate(be, "der", 9.6, spec) is False  # same crossing, not a new one
    assert len(_crossings(be)) == 1
    assert escalate(be, "der", 3.0, spec) is False  # recovered: the mark clears
    assert escalate(be, "der", 7.0, spec) is True  # a new crossing is a new event
    assert len(_crossings(be)) == 2


def test_der_above_target_prints_crossed_and_records_an_event(be, tmp_path):
    _seed(be, "origin")
    _seed(be, "fix", defect_of="origin")
    text = "\n".join(metrics_lines(_Svc(be, str(tmp_path))))
    assert "target der <= 5.0%: CROSSED" in text
    assert len(_crossings(be)) == 1


def test_override_without_basis_is_not_used_and_says_so():
    tg, notes = targets({"metric_targets": {"der": {"max": 50.0}}})
    assert tg["der"]["max"] == 5.0
    assert notes and "no basis" in notes[0]
    lines = method_lines({"der": 9.0, "fpsr": 90.0}, {"metric_targets": {"der": {"max": 50.0}}})
    assert any("no basis — not used" in ln for ln in lines)


def test_set_target_refuses_without_basis_and_records_with_one():
    cfg: dict = {}
    with pytest.raises(ValueError, match="basis"):
        set_target(cfg, "der", "max", 10.0, "  ")
    with pytest.raises(ValueError, match="unknown metric"):
        set_target(cfg, "velocity", "max", 1.0, "b")
    set_target(cfg, "der", "max", 10.0, "measured over 1500 closes")
    der = targets(cfg)[0]["der"]
    assert der["max"] == 10.0 and der["basis"] == "measured over 1500 closes"
    assert der["measured_on"] and der["measured_by"]


def test_every_registered_method_is_printed_as_registered(be, tmp_path):
    _seed(be, "a")
    text = "\n".join(metrics_lines(_Svc(be, str(tmp_path))))
    for name, meth in METHODS.items():
        assert f"  {name}: {meth['formula']} — population: {meth['population']}" in text
    for name, meth in METHODS.items():
        if meth["self_made"]:
            assert f"{name} ({meth['record']})" in text


def test_every_default_target_carries_basis_date_and_command():
    for name, spec in DEFAULT_TARGETS.items():
        assert name in METHODS
        assert str(spec.get("basis") or "").strip(), name
        assert spec.get("measured_on") and spec.get("measured_by"), name


def test_open_crossings_lists_the_recorded_and_unrecovered(be):
    assert open_crossings(be) == []
    escalate(be, "der", 9.4, {"max": 5.0, "basis": "b"})
    assert open_crossings(be) == ["der=9.4"]
    escalate(be, "der", 1.0, {"max": 5.0, "basis": "b"})
    assert open_crossings(be) == []


def test_figure_prints_value_when_population_exists():
    assert figure({"fpsr": 90.9, "populations": {"fpsr": 10}}, "fpsr") == "90.9%"
    assert figure({"fpsr": 0, "populations": {"fpsr": 0}}, "fpsr").startswith("no population")


def _view(**kw):
    base = {
        "duration_warning": None,
        "exploration": None,
        "audit_overdue": 0,
        "skill_warning": None,
    }
    return {**base, **kw}


def test_status_escalates_an_open_crossing():
    from status_view import status_warning_lines

    lines = status_warning_lines(_view(metric_crossings=["der=9.4"]))
    assert any("Metric target crossed" in ln and "der=9.4" in ln for ln in lines)
    assert not any("Metric target" in ln for ln in status_warning_lines(_view()))


def test_status_counts_the_audit_in_closures_not_sessions():
    from status_view import status_warning_lines

    (line,) = status_warning_lines(_view(audit_overdue=20))
    assert "20 task closures since last audit" in line
