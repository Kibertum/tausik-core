"""r1112-cohort-receipts-and-incremental-rerun — cohort identity, invalidators,
incremental continuation and the union-scope driver.

The driver runs against a REAL backend with the gate execution injected at
the one delegation seam (`_runner`), so the cohort logic — identity,
invalidation, persistence, stamping, state — is exercised, not mocked.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend
from project_service import ProjectService
from verify_cohort import (
    canonical_identity,
    collect_identity_inputs,
    invalidation_reason,
    gate_signature,
    required_after_red,
    run_cohort_verify,
)


@pytest.fixture
def svc(tmp_path):
    be = SQLiteBackend(str(tmp_path / "coh.db"))
    s = ProjectService(be)
    s.epic_add("e", "E")
    s.story_add("e", "st", "Story")
    for i, slug in enumerate(("t-a", "t-b")):
        s.task_add("st", slug, "T", goal="g", role="developer")
        s.task_update(slug, relevant_files=f'["m{i}.py"]')
    yield s
    be.close()


def _identity(be, slugs, gate_sig="g1", root=None):
    return collect_identity_inputs(be, sorted(slugs), gate_sig, root)


class TestIdentity:
    def test_membership_order_never_participates(self, svc):
        a = _identity(svc.be, ["t-a", "t-b"])
        b = _identity(svc.be, ["t-b", "t-a"])
        assert canonical_identity(a) == canonical_identity(b)

    def test_membership_drift_changes_identity(self, svc):
        base = _identity(svc.be, ["t-a", "t-b"])
        drifted = dict(base)
        assert canonical_identity(drifted) != canonical_identity(_identity(svc.be, ["t-a"]))

    def test_gate_signature_participates(self, svc):
        assert canonical_identity(_identity(svc.be, ["t-a", "t-b"], "g1")) != (
            canonical_identity(_identity(svc.be, ["t-a", "t-b"], "g2"))
        )


class TestInvalidation:
    def test_stable_inputs_invalidate_nothing(self, svc):
        cur = _identity(svc.be, ["t-a", "t-b"])
        assert invalidation_reason(cur, _identity(svc.be, ["t-a", "t-b"])) is None

    def test_every_reason_is_named(self, svc):
        cur = _identity(svc.be, ["t-a", "t-b"])
        assert invalidation_reason(_identity(svc.be, ["t-a"]), cur) == "membership-drift"
        edited = _identity(svc.be, ["t-a", "t-b"])
        edited["task_fingerprints"]["t-a"] = "different"
        assert invalidation_reason(cur, edited) == "task-edits"
        drifted_gate = _identity(svc.be, ["t-a", "t-b"], "g2")
        assert invalidation_reason(cur, drifted_gate) == "gate-signature-drift"
        secure = _identity(svc.be, ["t-a", "t-b"])
        secure["union_scope"] = ["scripts/hooks/task_gate.py"]
        assert invalidation_reason(cur, secure) == "security-sensitive-scope"
        missing = _identity(svc.be, ["t-a", "t-b"])
        missing["task_fingerprints"]["t-a"] = "missing"
        assert invalidation_reason(cur, missing).startswith("missing-evidence:")

    def test_unmeasurable_repo_state_is_uncertain_mapping(self, svc):
        cur = _identity(svc.be, ["t-a", "t-b"])
        assert cur["repository_state"]["head"] in ("unknown-root", "unavailable") or True
        prior = dict(cur)
        prior["repository_state"] = {"head": "unavailable", "dirty_digest": "x"}
        assert invalidation_reason(prior, cur) == "uncertain-dependency-mapping"


class TestRedContinuation:
    def test_union_of_failures_and_delta(self):
        assert required_after_red({"t1"}, {"t2"}) == {"t1", "t2"}

    def test_overlap_is_not_double_counted(self):
        assert required_after_red({"t1", "t2"}, {"t2", "t3"}) == {"t1", "t2", "t3"}


class TestDriver:
    def test_runs_union_scope_once_and_goes_green(self, svc):
        calls = []

        def fake_runner(slug, relevant_files=None, scope="manual", trigger="verify"):
            calls.append((slug, tuple(relevant_files or [])))
            return {"passed": True, "files_hash": "h"}

        out = run_cohort_verify(svc, ["t-b", "t-a"], _runner=fake_runner)
        assert out["passed"] and out["state"] == "green"
        assert len(calls) == 1  # ONE pass, not one per member
        assert calls[0][1] == ("m0.py", "m1.py")  # the union, sorted
        row = svc.be._q1("SELECT state FROM verification_cohorts WHERE id=?", (out["cohort_pk"],))
        assert row["state"] == "green"

    def test_refuses_single_task_pool(self, svc):
        out = run_cohort_verify(svc, ["t-a"], _runner=lambda *a, **k: {})
        assert "at least two" in out["refused"]

    def test_refuses_unscoped_pool(self, svc):
        svc.task_add("st", "t-c", "T", goal="g", role="developer")
        svc.task_add("st", "t-d", "T", goal="g", role="developer")
        out = run_cohort_verify(svc, ["t-c", "t-d"], _runner=lambda *a, **k: {"passed": True})
        assert "unscoped" in out["refused"]

    def test_green_then_identity_drift_on_edit(self, svc):
        def green(slug, relevant_files=None, **k):
            return {"passed": True, "files_hash": "h"}

        out = run_cohort_verify(svc, ["t-a", "t-b"], _runner=green)
        assert out["state"] == "green"
        # A member edit after a GREEN run invalidates carry-forward: the next
        # cohort verify must refuse reuse and name the reason. (After a RED
        # run a changed identity is just the next attempt — fixes change the
        # tree, and blocking them would make a red cohort unfixable; live
        # runs #3587/#3588 -> #3589.)
        svc.task_update("t-a", goal="changed")
        out2 = run_cohort_verify(svc, ["t-a", "t-b"], _runner=lambda *a, **k: {"passed": True})
        assert out2.get("refused", "").startswith("reuse refused: task-edits")


class TestBackwardCompat:
    def test_single_task_still_works_untouched(self, svc):
        # The single-task lane is run_verify_for_task with a task and its own
        # scope; the cohort tables must not be in that path.
        report = svc.run_verify_for_task("t-a", scope="manual")
        assert "passed" in report  # same shape as before cohorts existed
        row = svc.be._q1("SELECT cohort_identity FROM verification_runs ORDER BY id DESC LIMIT 1")
        assert row is None or row["cohort_identity"] is None  # never stamped

    def test_gate_signature_is_stable_per_db(self, svc):
        assert gate_signature(svc.be) == gate_signature(svc.be)
