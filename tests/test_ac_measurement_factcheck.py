"""ac-evidence-parser-cannot-see-a-measurement — the gate reads the FACT.

A `verification_run #NNNN` line counts as verification activity only when the
run actually exists, belongs to THIS task, and is green. The parser reads the
form; these tests pin that the gate reads the fact — a decorative
`verification_run #1` (nonexistent / foreign / red) must NOT clear the gate.
"""

from __future__ import annotations

import os
import sys

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import pytest  # noqa: E402

from gate_ac_check import (  # noqa: E402
    _evidence_strength,
    check_verification_checklist,
    checklist_missing,
)

_AC = "1. thing one\n2. thing two"
_MEASUREMENT_ONLY = "AC-1: verification_run #1450\nAC-2: verification_run #1450"


# --- Gate layer (pure, driven by an explicit verified_run_ids set) ---------


def test_verified_run_clears_activity_gate():
    """AC4: a task proven ONLY by a green run (no test/manual/review/checkmark)
    clears checklist_missing — the check mark is no longer the shortest path."""
    task = {"acceptance_criteria": _AC, "notes": _MEASUREMENT_ONLY, "tier": "moderate"}
    assert checklist_missing(task, {1450}) is False
    _real, activity, total = _evidence_strength(task, {1450})
    assert activity == total == 2


@pytest.mark.parametrize("verified", [set(), {999}, {1451}])
def test_unverified_run_does_not_clear_gate(verified):
    """AC3: a run id that is NOT a green run for this task (nonexistent, foreign
    slug, or red — all absent from verified_run_ids) does NOT clear the gate."""
    task = {"acceptance_criteria": _AC, "notes": _MEASUREMENT_ONLY, "tier": "moderate"}
    assert checklist_missing(task, verified) is True


def test_bare_pytest_summary_is_not_activity_without_a_run():
    """A pytest summary carries no run id, so it cannot be fact-checked and does
    not clear the activity gate on its own (it still counts toward covered)."""
    task = {
        "acceptance_criteria": _AC,
        "notes": "AC-1: 5778 passed in 564s\nAC-2: 5778 passed in 564s",
        "tier": "moderate",
    }
    # No verified run ids at all → activity stays 0 even though covered==2.
    assert checklist_missing(task, set()) is True


def test_checklist_note_gone_when_measurement_verified():
    """AC4: the 'no criterion names a test/manual/review' NOTE disappears once a
    green run backs the criteria."""
    task = {
        "acceptance_criteria": _AC,
        "complexity": "simple",
        "notes": _MEASUREMENT_ONLY,
        "relevant_files": "[]",
        "tier": "moderate",
    }
    out = check_verification_checklist(task, {1450})
    assert "no acceptance criterion names" not in out


# --- Service layer: green-run id set is built from the DB, filtered on exit ---


def test_green_run_ids_filter_exit_code_and_slug(tmp_path):
    """AC2/AC3 end-to-end: _green_verification_run_ids returns only green
    (exit_code==0) runs for THIS slug — a red run and a foreign-slug run are
    excluded, which is exactly what stops a decorative citation."""
    from project_backend import SQLiteBackend
    from project_service import ProjectService

    be = SQLiteBackend(str(tmp_path / "t.db"))
    svc = ProjectService(be)
    try:
        rows = [
            ("mine", 0, "green-mine"),  # green, this task -> included
            ("mine", 1, "red-mine"),  # red, this task -> excluded
            ("other", 0, "green-other"),  # green, foreign task -> excluded
        ]
        ids = {}
        for slug, exit_code, tag in rows:
            cur = be._conn.execute(
                "INSERT INTO verification_runs "
                "(task_slug, scope, command, exit_code, summary, files_hash, ran_at) "
                "VALUES (?, 'standard', 'pytest', ?, ?, 'h', '2026-07-27T00:00:00Z')",
                (slug, exit_code, tag),
            )
            ids[tag] = int(cur.lastrowid)
        be._conn.commit()

        green = svc._green_verification_run_ids("mine")
        assert ids["green-mine"] in green
        assert ids["red-mine"] not in green
        assert ids["green-other"] not in green
    finally:
        be.close()
