"""verify -> handle -> task done, through the real service stack.

v2-verify-receipt-as-argument. `test_verify_handle.py` exercises the validator
against a hand-built row; this file proves the two ENDS meet: that
`run_verify_for_task` actually hands a usable handle to its caller, and that
`_task_done_report(verify_handle=...)` actually closes on it. A validator that
is correct in isolation while nothing ever mints or presents a handle would
pass every test in the other file.

Discharges AC2 (the handle reaches the agent), AC3 (age stops deciding), AC8
(no handle -> the previous behaviour, unchanged) and AC9 (the durability policy
is published where a model can see it).
"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import crypto_keys  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402

_SCOPE = ["scripts/verify_handle.py"]


@pytest.fixture
def svc(tmp_path, monkeypatch):
    """A real project with a real signing key, cwd'd into it.

    The key matters: without one the handle path is the explicit keyless
    refusal (AC7), which is a correct answer but not the one under test here.
    """
    monkeypatch.chdir(tmp_path)
    crypto_keys.init_keys(str(tmp_path))
    for rel in _SCOPE:
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# scoped file\n", encoding="utf-8")
    be = SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db"))
    return ProjectService(be)


@pytest.fixture
def task_ready(svc):
    svc.epic_add("e", "E")
    svc.story_add("e", "s", "S")
    svc.task_add("s", "t", "Implement X", goal="Implement X", role="developer")
    svc.task_update(
        "t",
        acceptance_criteria="1. X works\n2. Returns error on invalid input",
        relevant_files=json.dumps(_SCOPE),
    )
    svc.task_start("t")
    svc.task_log("t", "AC verified: 1. X works ✓ 2. Returns error on invalid input ✓")
    return svc


def _verify_gate_only(monkeypatch):
    """One verify-trigger gate (pytest), auto_verify off — the default shape."""
    from project_config import get_gates_for_trigger as real_for_trigger

    def fake_for_trigger(trigger, cfg=None):
        if trigger == "verify":
            return [
                {
                    "name": "pytest",
                    "enabled": True,
                    "trigger": ["verify"],
                    "command": "pytest",
                    "severity": "block",
                }
            ]
        return real_for_trigger(trigger, cfg)

    monkeypatch.setattr(
        "project_config.load_config", lambda *a, **k: {"task_done": {"auto_verify": False}}
    )
    monkeypatch.setattr("project_config.get_gates_for_trigger", fake_for_trigger)


def _green_gates(monkeypatch):
    """A gate that RAN and passed — a skipped one is not a verification."""
    monkeypatch.setattr(
        "gate_runner.run_gates",
        lambda *a, **k: (
            True,
            [
                {
                    "name": "pytest",
                    "passed": True,
                    "skipped": False,
                    "severity": "block",
                    "output": "1 passed",
                    "duration_ms": 1,
                }
            ],
        ),
    )


@pytest.mark.verify_first
class TestMintedHandleClosesTheTask:
    def test_verify_returns_a_handle_and_task_done_accepts_it(self, task_ready, monkeypatch):
        _verify_gate_only(monkeypatch)
        _green_gates(monkeypatch)
        report = task_ready.run_verify_for_task("t", scope="standard", trigger="verify")
        assert report["passed"], report
        handle = report.get("verify_handle")
        assert handle, f"verify must hand the agent a handle: {report}"
        assert report.get("handle_expires_at"), "the durability policy travels with the handle"

        done = task_ready._task_done_report(
            "t",
            relevant_files=_SCOPE,
            ac_verified=True,
            no_knowledge=True,
            evidence=None,
            verify_handle=handle,
        )
        assert done["ok"], done.get("blocking_failures")

    def test_the_same_handle_cannot_close_twice(self, task_ready, monkeypatch):
        _verify_gate_only(monkeypatch)
        _green_gates(monkeypatch)
        handle = task_ready.run_verify_for_task("t", trigger="verify")["verify_handle"]
        first = task_ready._task_done_report(
            "t",
            relevant_files=_SCOPE,
            ac_verified=True,
            no_knowledge=True,
            evidence=None,
            verify_handle=handle,
        )
        assert first["ok"], first.get("blocking_failures")
        # Re-open and present the spent handle again. Straight to the row on
        # purpose: `task_start` refuses a done task and `task_update` refuses a
        # lifecycle status (both correctly — they guard QG-2). Re-opening is not
        # what is under test; presenting a SPENT handle is, and the second close
        # must be stopped by the handle, not by the status guard.
        task_ready.be._conn.execute("UPDATE tasks SET status='active' WHERE slug='t'")
        task_ready.be._conn.commit()
        second = task_ready._task_done_report(
            "t",
            relevant_files=_SCOPE,
            ac_verified=True,
            no_knowledge=True,
            evidence=None,
            verify_handle=handle,
        )
        assert not second["ok"]
        assert any("already spent" in str(f) for f in second["blocking_failures"]), second

    def test_a_close_blocked_after_the_gate_does_not_burn_the_handle(self, task_ready, monkeypatch):
        """REGRESSION, found by dogfooding. The handle used to be spent by the
        Verify-First gate itself. A close that passed that gate and was then
        blocked by a LATER check burnt a ninety-second verify run for a task
        that never closed — and since nothing was certified, the spend bought no
        safety at all. Redeem-once binds to CLOSING, so the spend now lives in
        the status='done' transaction."""
        _verify_gate_only(monkeypatch)
        _green_gates(monkeypatch)
        handle = task_ready.run_verify_for_task("t", trigger="verify")["verify_handle"]

        # Block AFTER the Verify-First gate has already validated the handle.
        # A toggle rather than `monkeypatch.undo()`: undo would also revert the
        # `svc` fixture's chdir into tmp_path, and the second close would then
        # hash the REPOSITORY's copies of the scoped files — failing on a
        # changed files_hash and telling us nothing about the handle.
        import service_gates

        blocking = {"on": True}
        original = service_gates.GatesMixin._check_verification_checklist

        def _maybe_block(self, slug, task, run_ids):
            if blocking["on"]:
                raise RuntimeError("a later check says no")
            return original(self, slug, task, run_ids)

        monkeypatch.setattr(
            service_gates.GatesMixin, "_check_verification_checklist", _maybe_block
        )
        with pytest.raises(RuntimeError):
            task_ready._task_done_report(
                "t",
                relevant_files=_SCOPE,
                ac_verified=True,
                no_knowledge=True,
                evidence=None,
                verify_handle=handle,
            )
        blocking["on"] = False
        done = task_ready._task_done_report(
            "t",
            relevant_files=_SCOPE,
            ac_verified=True,
            no_knowledge=True,
            evidence=None,
            verify_handle=handle,
        )
        assert done["ok"], (
            f"the handle was consumed by a close that never happened: "
            f"{done.get('blocking_failures')}"
        )

    def test_a_bad_handle_blocks_rather_than_falling_back(self, task_ready, monkeypatch):
        """A presented handle is terminal in BOTH directions. Falling through to
        the freshness lookup would make every refusal recoverable by having
        verified recently — the substitution of 'recent' for 'correct' that
        decision #218 removed."""
        _verify_gate_only(monkeypatch)
        _green_gates(monkeypatch)
        # A perfectly good fresh verify run EXISTS; the lookup would say yes.
        task_ready.run_verify_for_task("t", trigger="verify")
        done = task_ready._task_done_report(
            "t",
            relevant_files=_SCOPE,
            ac_verified=True,
            no_knowledge=True,
            evidence=None,
            verify_handle="999." + "a" * 32,
        )
        assert not done["ok"], "an unknown handle must block even when a fresh run exists"
        assert any("no verify run #999" in str(f) for f in done["blocking_failures"])


@pytest.mark.verify_first
class TestBackwardCompatibility:
    def test_closing_without_a_handle_still_uses_the_freshness_lookup(
        self, task_ready, monkeypatch
    ):
        """AC8. The old path must stay alive: a silent tightening would strand
        every existing caller."""
        _verify_gate_only(monkeypatch)
        _green_gates(monkeypatch)
        task_ready.run_verify_for_task("t", trigger="verify")
        done = task_ready._task_done_report(
            "t",
            relevant_files=_SCOPE,
            ac_verified=True,
            no_knowledge=True,
            evidence=None,
        )
        assert done["ok"], done.get("blocking_failures")

    def test_no_handle_and_no_verify_run_still_blocks(self, task_ready, monkeypatch):
        _verify_gate_only(monkeypatch)
        _green_gates(monkeypatch)
        done = task_ready._task_done_report(
            "t",
            relevant_files=_SCOPE,
            ac_verified=True,
            no_knowledge=True,
            evidence=None,
        )
        assert not done["ok"]


@pytest.mark.verify_first
class TestUnpresentableRunsEarnNoHandle:
    def test_all_skipped_gates_yield_no_handle(self, task_ready, monkeypatch):
        """A SKIP is not a verification, so it cannot become a handle."""
        _verify_gate_only(monkeypatch)
        monkeypatch.setattr(
            "gate_runner.run_gates",
            lambda *a, **k: (
                True,
                [{"name": "pytest", "passed": True, "skipped": True, "severity": "block"}],
            ),
        )
        report = task_ready.run_verify_for_task("t", trigger="verify")
        assert not report.get("verify_handle")


class TestDurabilityPolicyIsPublished:
    """AC9 / SEP-2567: 'A policy only in server documentation is not visible to
    the model.' The number has to appear where the model actually reads."""

    def test_tool_description_states_the_handle_lifetime(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, os.path.join(root, "harness", "claude", "mcp", "project"))
        from tools_extra import TOOLS_EXTRA

        verify = next(t for t in TOOLS_EXTRA if t["name"] == "tausik_verify")
        desc = verify["description"]
        assert "verify_handle" in desc
        assert "1 hour" in desc, "the durability window must be stated to the model"
        assert "SINGLE-USE" in desc

    def test_docs_state_the_same_lifetime_as_the_constant(self):
        from verify_constants import DEFAULT_HANDLE_TTL_S

        assert DEFAULT_HANDLE_TTL_S == 3600, (
            "changing the handle TTL means changing every place it is published: "
            "the tausik_verify tool description, docs/ru/receipts.md and the "
            "receipt's own expires_at"
        )
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "docs", "ru", "receipts.md"), encoding="utf-8") as fh:
            text = fh.read()
        assert "verify-handle" in text or "хендл" in text.lower()
        assert "3600" in text or "1 час" in text
