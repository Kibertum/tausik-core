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
    cohort_summary,
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


# Production shape: `run_verify_for_task` reports carry NO `files_hash` key
# (surfacing it is tracked separately) — a stub that invents one would keep the
# tests greener than the code they guard.
GREEN_REPORT = {"passed": True}


class TestIdentity:
    def test_membership_order_never_participates(self, svc):
        a = _identity(svc.be, ["t-a", "t-b"])
        b = _identity(svc.be, ["t-b", "t-a"])
        assert canonical_identity(a) == canonical_identity(b)

    def test_membership_drift_changes_identity(self, svc):
        assert canonical_identity(_identity(svc.be, ["t-a", "t-b"])) != (
            canonical_identity(_identity(svc.be, ["t-a"]))
        )

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
        re_statused = _identity(svc.be, ["t-a", "t-b"])
        re_statused["task_statuses"]["t-a"] = "blocked"
        assert invalidation_reason(cur, re_statused) == "member-status-drift"
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
        assert cur["repository_state"]["head"] in ("unknown-root", "unavailable")
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
            return dict(GREEN_REPORT)

        out = run_cohort_verify(svc, ["t-b", "t-a"], prepare=False, _runner=fake_runner)
        assert out["passed"] and out["state"] == "green"
        assert len(calls) == 1  # ONE pass, not one per member
        assert calls[0][1] == ("m0.py", "m1.py")  # the union, sorted
        row = svc.be._q1("SELECT state FROM verification_cohorts WHERE id=?", (out["cohort_pk"],))
        assert row["state"] == "green"

    def test_refuses_single_task_pool(self, svc):
        out = run_cohort_verify(svc, ["t-a"], _runner=lambda *a, **k: {})
        assert "at least two" in out["refused"]

    def test_refuses_unscoped_pool_and_leaves_no_residue(self, svc):
        svc.task_add("st", "t-c", "T", goal="g", role="developer")
        svc.task_add("st", "t-d", "T", goal="g", role="developer")
        out = run_cohort_verify(svc, ["t-c", "t-d"], _runner=lambda *a, **k: {"passed": True})
        assert "unscoped" in out["refused"]
        # The refusal must not leave a permanent 'open' cohort row behind:
        assert svc.be._q1("SELECT COUNT(*) AS n FROM verification_cohorts")["n"] == 0

    def test_refuses_security_sensitive_union_on_a_fresh_cohort(self, svc):
        # Contract §4 is about the CURRENT union, not only about drift from a
        # predecessor: a fresh cohort over hooks/auth/billing paths is never
        # pooled silently.
        svc.task_update("t-a", relevant_files='["scripts/hooks/task_gate.py"]')
        out = run_cohort_verify(svc, ["t-a", "t-b"], _runner=lambda *a, **k: {"passed": True})
        assert "security-sensitive-scope" in out["refused"]
        assert svc.be._q1("SELECT COUNT(*) AS n FROM verification_cohorts")["n"] == 0

    def test_green_then_identity_drift_on_edit(self, svc):
        def green(slug, relevant_files=None, **k):
            return dict(GREEN_REPORT)

        out = run_cohort_verify(svc, ["t-a", "t-b"], prepare=False, _runner=green)
        assert out["state"] == "green"
        # A member edit after a GREEN run invalidates carry-forward: the next
        # cohort verify must refuse reuse and name the reason. (After a RED
        # run a changed identity is just the next attempt — fixes change the
        # tree, and blocking them would make a red cohort unfixable; live
        # runs #3587/#3588 -> #3589.)
        svc.task_update("t-a", goal="changed")
        out2 = run_cohort_verify(
            svc, ["t-a", "t-b"], prepare=False, _runner=lambda *a, **k: {"passed": True}
        )
        assert out2.get("refused", "").startswith("reuse refused: task-edits")


class TestPreparation:
    """The pooled lane pays preparation INSIDE the shared run path — one
    place, so CLI and MCP cannot diverge on whether it ran."""

    def test_preparation_runs_over_the_union_scope(self, svc, monkeypatch):
        import verify_prepare

        seen = []
        monkeypatch.setattr(
            verify_prepare, "run", lambda root, files: seen.append(tuple(files)) or []
        )
        out = run_cohort_verify(
            svc, ["t-a", "t-b"], prepare=True, _runner=lambda *a, **k: dict(GREEN_REPORT)
        )
        assert out["passed"]
        assert seen == [("m0.py", "m1.py")]

    def test_prepare_false_skips_it(self, svc, monkeypatch):
        import verify_prepare

        seen = []
        monkeypatch.setattr(
            verify_prepare, "run", lambda root, files: seen.append(tuple(files)) or []
        )
        run_cohort_verify(
            svc, ["t-a", "t-b"], prepare=False, _runner=lambda *a, **k: dict(GREEN_REPORT)
        )
        assert seen == []

    def test_preparation_failure_refuses_without_judging(self, svc, monkeypatch):
        import verify_prepare

        def boom(root, files):
            raise verify_prepare.PreparationFailed("ruff format refused")

        monkeypatch.setattr(verify_prepare, "run", boom)
        out = run_cohort_verify(svc, ["t-a", "t-b"], _runner=lambda *a, **k: dict(GREEN_REPORT))
        assert "preparation failed" in out["refused"]
        assert svc.be._q1("SELECT COUNT(*) AS n FROM verification_cohorts")["n"] == 0


class TestSummarySurfacesTheHandle:
    def test_green_summary_names_the_handle_and_its_redeemer(self, svc):
        out = {
            "passed": True,
            "identity": "i" * 64,
            "members": ["t-a", "t-b"],
            "union_scope": ["m0.py"],
            "report": {
                "verify_handle": "3599." + "ab" * 16,
                "handle_expires_at": "2026-10-07T10:00:00Z",
            },
        }
        text = cohort_summary(out)
        assert "Verify handle: 3599." + "ab" * 16 in text
        assert "story done|epic done <parent-slug> --verify-handle" in text

    def test_handleless_report_says_so_instead_of_staying_silent(self, svc):
        out = {
            "passed": True,
            "identity": "i" * 64,
            "members": ["t-a", "t-b"],
            "union_scope": ["m0.py"],
            "report": {},
        }
        assert "Verify handle: none" in cohort_summary(out)


class TestBackwardCompat:
    def test_single_task_still_works_untouched(self, svc):
        # The single-task lane is run_verify_for_task with a task and its own
        # scope; the cohort tables must not be in that path.
        report = svc.run_verify_for_task("t-a", scope="manual")
        assert "passed" in report  # same shape as before cohorts existed
        row = svc.be._q1("SELECT cohort_identity FROM verification_runs ORDER BY id DESC LIMIT 1")
        assert row is None or row["cohort_identity"] is None  # never stamped

    def test_gate_signature_tracks_the_live_gate_config(self, svc):
        # Behavior, not determinism-of-a-pure-function: flipping a gate:% meta
        # key must move the signature, because cohort identity rests on it.
        before = gate_signature(svc.be)
        svc.be._conn.execute("INSERT INTO meta(key, value) VALUES('gate:pytest', 'enabled')")
        svc.be._conn.commit()
        assert gate_signature(svc.be) != before
