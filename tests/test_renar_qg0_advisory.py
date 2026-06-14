"""RENAR-lite QG-0 advisory (Decision #115, rung 2) — non-blocking nudge."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from gate_qg0_check import check_qg0_start  # noqa: E402
from gate_qg0_renar import renar_qg0_advisory  # noqa: E402


class _Be:
    """Minimal backend stub for SPEC/ADAPT presence."""

    def __init__(self, specs=None, adapts=None, raise_=False):
        self._specs = specs or []
        self._adapts = adapts or []
        self._raise = raise_

    def specs_for_task(self, slug):
        if self._raise:
            raise RuntimeError("boom")
        return self._specs

    def adapts_for_target(self, target_type, slug):
        return self._adapts


def _valid_task(**over):
    task = {
        "goal": "do a thing",
        "acceptance_criteria": "AC1: works. Negative: errors on invalid input.",
        "scope": "scripts/x.py",
        "scope_exclude": "tests/",
        "rollback_plan": "git revert",
        "complexity": "medium",
        "tier": "deep",
    }
    task.update(over)
    return task


class TestRenarAdvisory:
    def test_high_stakes_without_artifacts_nudges(self):
        msg = renar_qg0_advisory(_Be(), _valid_task(), "feat-x")
        assert msg is not None
        assert "RENAR (advisory)" in msg and "feat-x" in msg

    def test_complex_fallback_when_no_tier(self):
        task = _valid_task(tier=None, complexity="complex")
        assert renar_qg0_advisory(_Be(), task, "feat-x") is not None

    def test_low_stakes_no_advisory(self):
        task = _valid_task(tier="light", complexity="simple")
        assert renar_qg0_advisory(_Be(), task, "feat-x") is None

    def test_linked_spec_suppresses(self):
        assert renar_qg0_advisory(_Be(specs=[{"slug": "s1"}]), _valid_task(), "x") is None

    def test_existing_adapt_suppresses(self):
        assert renar_qg0_advisory(_Be(adapts=[{"id": 1}]), _valid_task(), "x") is None

    def test_backend_error_swallowed(self):
        assert renar_qg0_advisory(_Be(raise_=True), _valid_task(), "x") is None

    def test_toggle_off_suppresses(self, monkeypatch):
        import project_config

        monkeypatch.setattr(
            project_config, "load_config", lambda *a, **k: {"renar": {"qg0_advisory": False}}
        )
        assert renar_qg0_advisory(_Be(), _valid_task(), "x") is None


class TestAdvisoryIsNonBlocking:
    def test_advisory_appended_not_raised(self):
        warnings = check_qg0_start(
            "x", _valid_task(), renar_advisory_fn=lambda: "RENAR (advisory): nudge"
        )
        assert any("RENAR (advisory)" in w for w in warnings)

    def test_advisory_callback_error_is_swallowed(self):
        def _boom():
            raise RuntimeError("x")

        # Must not raise — QG-0 stays alive even if the advisory errors.
        warnings = check_qg0_start("x", _valid_task(), renar_advisory_fn=_boom)
        assert isinstance(warnings, list)
