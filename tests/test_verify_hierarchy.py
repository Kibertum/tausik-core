"""r1112-hierarchy-verify-and-atomic-close — resolution, readiness, atomic close.

Gate execution is injected at the delegation seam exactly as in
test_verify_cohort; the receipt row is materialized directly so the handle
validation and the transaction run against the real schema.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import verify_cohort as vc
import verify_hierarchy as vh
from project_backend import SQLiteBackend
from project_service import ProjectService

GREEN = {"passed": True, "files_hash": "h"}


@pytest.fixture
def svc(tmp_path):
    be = SQLiteBackend(str(tmp_path / "h.db"))
    s = ProjectService(be)
    s.epic_add("e", "E")
    s.story_add("e", "st", "Story")
    for i, slug in enumerate(("h-a", "h-b", "h-c")):
        s.task_add("st", slug, "T", goal="g", role="developer")
        s.task_update(
            slug,
            relevant_files=json.dumps([f"f{i}.py"]),
            plan=json.dumps([{"step": "do it", "done": True}]),
            acceptance_criteria="AC-1 works",
        )
        be._conn.execute(
            "INSERT INTO task_logs(task_slug, message, created_at) VALUES(?,?,?)",
            (slug, "AC-1: OK tested via tests/x.py::t", "2026-10-06T00:00:00Z"),
        )
    be._conn.commit()
    yield s
    be.close()


def _raw_status(svc, slug, status):
    """Lifecycle transitions are service-guarded; tests set the column the
    way a completed lifecycle would have left it."""
    svc.be._conn.execute("UPDATE tasks SET status=? WHERE slug=?", (status, slug))
    svc.be._conn.commit()


def _green_receipt(svc, members):
    """Materialize the green run row a real delegated pass would record."""
    identity = vc.canonical_identity(
        vc.collect_identity_inputs(svc.be, members, vc.gate_signature(svc.be), None)
    )
    svc.be._conn.execute(
        "INSERT INTO verification_runs(task_slug, scope, command, exit_code, "
        "files_hash, ran_at, cohort_identity, handle_nonce) "
        "VALUES('h-a','manual','verify',0,'h','2026-10-06T00:00:00Z',?, 'n1')",
        (identity,),
    )
    svc.be._conn.commit()
    run_id = svc.be._q1("SELECT MAX(id) AS m FROM verification_runs")["m"]
    return f"{run_id}.n1", identity


class TestResolution:
    def test_story_and_epic_descendants(self, svc):
        assert vh.resolve_descendants(svc.be, "st", "story") == ["h-a", "h-b", "h-c"]
        assert vh.resolve_descendants(svc.be, "e", "epic") == ["h-a", "h-b", "h-c"]

    def test_empty_pool_refused(self, svc):
        svc.story_add("e", "empty", "Empty")
        out = vh.run_hierarchy_verify(svc, "empty", "story", _runner=lambda *a, **k: GREEN)
        assert "no non-done tasks" in out["refused"]

    def test_single_task_pool_refused_as_ordinary_verify(self, svc):
        _raw_status(svc, "h-b", "done")
        _raw_status(svc, "h-c", "done")
        out = vh.run_hierarchy_verify(svc, "st", "story", _runner=lambda *a, **k: GREEN)
        assert "ordinary `verify --task h-a`" in out["refused"]


class TestReadiness:
    def test_incomplete_plan_blocks_the_cohort(self, svc):
        svc.task_update("h-b", plan=json.dumps([{"step": "x", "done": False}]))
        out = vh.run_hierarchy_verify(svc, "st", "story", _runner=lambda *a, **k: GREEN)
        assert "h-b: plan incomplete" in out["refused"]

    def test_missing_ac_evidence_blocks_the_cohort(self, svc):
        svc.be._conn.execute("DELETE FROM task_logs WHERE task_slug='h-c'")
        svc.be._conn.commit()
        out = vh.run_hierarchy_verify(svc, "st", "story", _runner=lambda *a, **k: GREEN)
        assert "h-c: no numbered AC evidence logged" in out["refused"]

    def test_ready_cohort_runs_once(self, svc):
        calls = []

        def runner(slug, relevant_files=None, **k):
            calls.append(tuple(relevant_files or []))
            return GREEN

        out = vh.run_hierarchy_verify(svc, "st", "story", _runner=runner)
        assert out["passed"] and len(calls) == 1
        assert calls[0] == ("f0.py", "f1.py", "f2.py")  # union, one pass


class TestAtomicClose:
    def test_closes_everything_on_the_exact_receipt(self, svc):
        out = vh.run_hierarchy_verify(svc, "st", "story", _runner=lambda *a, **k: GREEN)
        handle, _ = _green_receipt(svc, out["members"])
        msg = vh.hierarchy_done_with_handle(svc, "st", "story", handle)
        assert "Closed atomically: 3 task(s) + story 'st'" in msg
        assert (
            svc.be._q1(
                "SELECT COUNT(*) AS n FROM tasks WHERE status='done' "
                "AND story_id=(SELECT id FROM stories WHERE slug='st')"
            )["n"]
            == 3
        )
        assert svc.be._q1("SELECT status FROM stories WHERE slug='st'")["status"] == "done"
        assert (
            svc.be._q1("SELECT handle_redeemed_at FROM verification_runs ORDER BY id DESC LIMIT 1")[
                "handle_redeemed_at"
            ]
            is not None
        )

    def test_edited_member_makes_handle_stale(self, svc):
        out = vh.run_hierarchy_verify(svc, "st", "story", _runner=lambda *a, **k: GREEN)
        handle, _ = _green_receipt(svc, out["members"])
        svc.task_update("h-b", goal="changed after verify")
        msg = vh.hierarchy_done_with_handle(svc, "st", "story", handle)
        assert msg.startswith("REFUSED: handle is stale")
        assert svc.be._q1("SELECT status FROM stories WHERE slug='st'")["status"] != "done"

    def test_membership_change_makes_handle_stale(self, svc):
        out = vh.run_hierarchy_verify(svc, "st", "story", _runner=lambda *a, **k: GREEN)
        handle, _ = _green_receipt(svc, out["members"])
        _raw_status(svc, "h-c", "blocked")  # reopen/block after verify
        msg = vh.hierarchy_done_with_handle(svc, "st", "story", handle)
        assert msg.startswith("REFUSED: handle is stale")

    def test_double_spend_refused(self, svc):
        out = vh.run_hierarchy_verify(svc, "st", "story", _runner=lambda *a, **k: GREEN)
        handle, _ = _green_receipt(svc, out["members"])
        vh.hierarchy_done_with_handle(svc, "st", "story", handle)
        svc.story_update("st", "reopened") if hasattr(svc, "story_update") else None
        svc.be._conn.execute("UPDATE stories SET status='open' WHERE slug='st'")
        svc.be._conn.execute(
            "UPDATE tasks SET status='active' WHERE story_id="
            "(SELECT id FROM stories WHERE slug='st')"
        )
        svc.be._conn.commit()
        msg = vh.hierarchy_done_with_handle(svc, "st", "story", handle)
        assert "already redeemed" in msg

    def test_standalone_story_done_untouched(self, svc):
        # Without --verify-handle the legacy path stays: no receipt needed.
        for slug in ("h-a", "h-b", "h-c"):
            _raw_status(svc, slug, "done")
        assert (
            "done" in svc.story_done("st").lower()
            or svc.be._q1("SELECT status FROM stories WHERE slug='st'")["status"] == "done"
        )
