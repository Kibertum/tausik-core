"""r1112-hierarchy-verify-and-atomic-close — resolution, readiness, atomic close.

Gate execution is injected at the delegation seam exactly as in
test_verify_cohort; the receipt row is materialized directly so the handle
validation and the transaction run against the real schema.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import verify_cohort as vc
import verify_hierarchy as vh
from project_backend import SQLiteBackend
from project_service import ProjectService

GREEN = {"passed": True}


@pytest.fixture
def svc(tmp_path):
    # The DB lives under <root>/.tausik the way production places it, so
    # root_from_service(svc) resolves to tmp_path itself — the git state the
    # identity hashes is then the repo this test controls.
    tausik_dir = tmp_path / ".tausik"
    tausik_dir.mkdir(exist_ok=True)
    be = SQLiteBackend(str(tausik_dir / "tausik.db"))
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


def _mint_identity(svc, members):
    """The identity the PRODUCTION mint computes — same root source as
    `run_cohort_verify` (root_from_service), never a bare None. Fabricating
    receipts with root=None is how the always-stale close bug stayed green
    through its own tests."""
    from project_root import root_from_service

    return vc.canonical_identity(
        vc.collect_identity_inputs(
            svc.be, members, vc.gate_signature(svc.be), root_from_service(svc)
        )
    )


def _green_receipt(svc, members, nonce="ab" * 16, ran_at=None, ttl_s=3600):
    """Materialize the green run row a real delegated pass would record."""
    from verify_handle import compute_expires_at

    # Default to now, evaluated at call time: the TTL check is live, and a
    # frozen literal here goes stale one TTL after it is written.
    if ran_at is None:
        ran_at = datetime.now(timezone.utc).isoformat()

    identity = _mint_identity(svc, members)
    svc.be._conn.execute(
        "INSERT INTO verification_runs(task_slug, scope, command, exit_code, "
        "files_hash, ran_at, cohort_identity, handle_nonce, handle_expires_at) "
        "VALUES('h-a','manual','verify',0,'h',?,?,?,?)",
        (ran_at, identity, nonce, compute_expires_at(ran_at, ttl_s)),
    )
    svc.be._conn.commit()
    run_id = svc.be._q1("SELECT MAX(id) AS m FROM verification_runs")["m"]
    return f"{run_id}.{nonce}", identity


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
            return dict(GREEN)

        out = vh.run_hierarchy_verify(svc, "st", "story", prepare=False, _runner=runner)
        assert out["passed"] and len(calls) == 1
        assert calls[0] == ("f0.py", "f1.py", "f2.py")  # union, one pass


class TestAtomicClose:
    def test_closes_everything_on_the_exact_receipt(self, svc):
        out = vh.run_hierarchy_verify(
            svc, "st", "story", prepare=False, _runner=lambda *a, **k: dict(GREEN)
        )
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
        out = vh.run_hierarchy_verify(
            svc, "st", "story", prepare=False, _runner=lambda *a, **k: dict(GREEN)
        )
        handle, _ = _green_receipt(svc, out["members"])
        svc.task_update("h-b", goal="changed after verify")
        msg = vh.hierarchy_done_with_handle(svc, "st", "story", handle)
        assert msg.startswith("REFUSED: handle is stale")
        assert svc.be._q1("SELECT status FROM stories WHERE slug='st'")["status"] != "done"

    def test_membership_change_makes_handle_stale(self, svc):
        out = vh.run_hierarchy_verify(
            svc, "st", "story", prepare=False, _runner=lambda *a, **k: dict(GREEN)
        )
        handle, _ = _green_receipt(svc, out["members"])
        _raw_status(svc, "h-c", "blocked")  # reopen/block after verify
        msg = vh.hierarchy_done_with_handle(svc, "st", "story", handle)
        assert msg.startswith("REFUSED: handle is stale")

    def test_double_spend_refused(self, svc):
        out = vh.run_hierarchy_verify(
            svc, "st", "story", prepare=False, _runner=lambda *a, **k: dict(GREEN)
        )
        handle, _ = _green_receipt(svc, out["members"])
        vh.hierarchy_done_with_handle(svc, "st", "story", handle)
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


class TestProductionCloseParity:
    """The regression class for the always-stale close bug: mint and redeem
    must resolve the repo root through the SAME source, and redemption must
    reuse the single-task lane's handle machinery rather than a weaker copy."""

    def test_identity_minted_by_the_real_driver_closes_end_to_end(self, svc, tmp_path):
        import subprocess

        # A real git root, because production always resolves one. .tausik is
        # ignored the way production ignores it: the DB lives inside the work
        # tree, and an unignored DB would change the dirty digest between
        # mint and redeem on every write.
        (tmp_path / ".gitignore").write_text(".tausik/\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=str(tmp_path), check=True, timeout=30)
        subprocess.run(
            ["git", "-C", str(tmp_path), "config", "user.email", "t@example.com"],
            check=True,
            timeout=30,
        )
        subprocess.run(
            ["git", "-C", str(tmp_path), "config", "user.name", "t"],
            check=True,
            timeout=30,
        )
        (tmp_path / "f0.py").write_text("x = 1\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True, timeout=30)
        subprocess.run(
            ["git", "-C", str(tmp_path), "commit", "-qm", "seed"], check=True, timeout=30
        )

        # Mint through the REAL driver (identity path untampered), then stamp
        # the receipt row exactly the way the delegated-run stamp does.
        out = vc.run_cohort_verify(
            svc, ["h-a", "h-b"], prepare=False, _runner=lambda *a, **k: dict(GREEN)
        )
        assert out["passed"]
        handle, minted = _green_receipt(svc, ["h-a", "h-b"])
        assert minted == out["identity"]  # the row carries the driver's identity

        # The root actually participated: a None-root identity is a different
        # universe, and the close must not live in it.
        none_root = vc.canonical_identity(
            vc.collect_identity_inputs(svc.be, ["h-a", "h-b"], vc.gate_signature(svc.be), None)
        )
        assert none_root != out["identity"]

        svc.story_add("e", "st2", "Second")
        for slug in ("h-a", "h-b"):
            svc.be._conn.execute(
                "UPDATE tasks SET story_id=(SELECT id FROM stories WHERE slug='st2') WHERE slug=?",
                (slug,),
            )
        svc.be._conn.execute(
            "UPDATE tasks SET story_id=(SELECT id FROM stories WHERE slug='st') WHERE slug='h-c'"
        )
        svc.be._conn.commit()
        msg = vh.hierarchy_done_with_handle(svc, "st2", "story", handle)
        assert "Closed atomically: 2 task(s) + story 'st2'" in msg

    def test_dotless_handle_is_refused_not_a_crash(self, svc):
        # A user pasting only the run id used to reach handle.split(".", 1)[1]
        # and die with IndexError on a supported CLI/MCP path.
        msg = vh.hierarchy_done_with_handle(svc, "st", "story", "3589")
        assert msg.startswith("REFUSED: unknown or malformed handle")

    def test_wrong_nonce_is_refused_constant_time(self, svc):
        handle, _ = _green_receipt(svc, ["h-a", "h-b"], nonce="ab" * 16)
        run_id = handle.split(".", 1)[0]
        forged = f"{run_id}.{'cd' * 16}"
        msg = vh.hierarchy_done_with_handle(svc, "st", "story", forged)
        assert "nonce does not match" in msg

    def test_expired_handle_is_refused(self, svc):
        handle, _ = _green_receipt(svc, ["h-a", "h-b"], ran_at="2020-01-01T00:00:00Z")
        msg = vh.hierarchy_done_with_handle(svc, "st", "story", handle)
        assert "expired" in msg

    def test_epic_close_closes_its_stories_too(self, svc):
        handle, _ = _green_receipt(svc, ["h-a", "h-b", "h-c"])
        msg = vh.hierarchy_done_with_handle(svc, "e", "epic", handle)
        assert "Closed atomically: 3 task(s) + epic 'e'" in msg
        # Stories go with their epic: leaving them open under a done epic is
        # the inverse of the doctor's open-epic check.
        assert svc.be._q1("SELECT status FROM stories WHERE slug='st'")["status"] == "done"

    def test_close_projects_the_git_native_state_files(self, svc, tmp_path):
        # Auto-export is opt-in per project: without the switch the flush is a
        # no-op by design, so the test switches it on the way a real project
        # does, in the config of THIS project's .tausik.
        (tmp_path / ".tausik" / "config.json").write_text(
            json.dumps({"state": {"auto_export": True}}), encoding="utf-8"
        )
        handle, _ = _green_receipt(svc, ["h-a", "h-b", "h-c"])
        vh.hierarchy_done_with_handle(svc, "st", "story", handle)
        # The tree root is <project>/tausik — a sibling of .tausik, the way
        # _tree_root resolves it; a bare <project>/tasks would be a layout
        # production never writes.
        task_file = tmp_path / "tausik" / "tasks" / "h-a.md"
        story_file = tmp_path / "tausik" / "stories" / "st.md"
        assert "status: done" in task_file.read_text(encoding="utf-8"), (
            "DB says done but the projected state file does not — the two "
            "sources of truth diverged on the feature's own advertised action"
        )
        assert "status: done" in story_file.read_text(encoding="utf-8")
