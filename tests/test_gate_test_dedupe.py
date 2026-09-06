"""The duplicate-shape detector is a gate now, and the ratchet only turns down.

`audit_pytest_dedupe` had a `--check` flag and was documented as review-only, so
nothing ran it and the number grew unwatched — 294 groups / 683 tests in session
#178, 322 / 753 when the gate landed. This module holds the gate to the two
properties that make it worth having: it reddens on GROWTH, and it can never be
satisfied by deleting tests, because it does not measure how many there are.
"""

from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from gate_test_dedupe import (  # noqa: E402
    load_baseline,
    measure,
    run_test_dedupe_gate,
)

# Reads the committed baseline and every test file — no import edge selects it.
CROSSCUTTING_SCOPE = ["tests/", "tausik/gates.json", "scripts/gate_test_dedupe.py"]


def _committed_baseline() -> dict:
    with open(os.path.join(_ROOT, "tausik", "gates.json"), encoding="utf-8") as fh:
        return json.load(fh)["test_dedupe"]["baseline"]


def test_the_gate_is_green_on_the_repo_it_landed_on():
    """A gate that reddens on everything the day it lands gets switched off."""
    ok, message = run_test_dedupe_gate({}, [])
    assert ok, message


def test_the_baseline_only_ratchets_down():
    """A line nobody lowers is a list, not a ratchet.

    Measured BELOW the baseline is not a pass to enjoy quietly — it is the
    moment the baseline is meant to move, and this is what makes it move.
    """
    groups_n, tests_n, _ = measure(_ROOT)
    baseline = _committed_baseline()
    assert baseline["groups"] <= groups_n and baseline["tests"] <= tests_n, (
        "duplicate-shape debt is below the committed baseline "
        f"(measured {groups_n} groups / {tests_n} tests, baseline "
        f"{baseline['groups']} / {baseline['tests']}) — lower it in "
        "tausik/gates.json to what was achieved"
    )


def test_growth_is_red_and_says_where(monkeypatch):
    """Negative: the whole point. One more copy of an existing shape blocks."""
    import gate_test_dedupe

    groups_n, tests_n, groups = measure(_ROOT)
    monkeypatch.setattr(
        gate_test_dedupe,
        "measure",
        lambda *a, **k: (groups_n + 1, tests_n + 2, groups),
    )
    ok, message = run_test_dedupe_gate({}, [])
    assert not ok
    assert "GREW" in message
    assert f"{groups_n + 1} > baseline {groups_n}" in message
    assert ".py:" in message, "a count with no address is not actionable"


def test_deleting_tests_can_never_satisfy_the_gate(monkeypatch):
    """Negative: the subject is distinguishability, not volume.

    Fewer tests than the baseline is a PASS, and the message asks for the
    baseline to come down — nothing here rewards removing tests that are
    already distinguishable, because their number is never measured.
    """
    import gate_test_dedupe

    _, _, groups = measure(_ROOT)
    monkeypatch.setattr(gate_test_dedupe, "measure", lambda *a, **k: (1, 2, groups))
    ok, message = run_test_dedupe_gate({}, [])
    assert ok
    assert "BELOW the baseline" in message


def test_an_unreadable_baseline_refuses_instead_of_passing(monkeypatch):
    """Negative: missing is not clean.

    Reporting "no duplicates recorded" for an unreadable file would turn the
    loss of the baseline into a green verdict about the tests.
    """
    import gate_test_dedupe

    monkeypatch.setattr(gate_test_dedupe, "load_baseline", lambda *a, **k: None)
    ok, message = run_test_dedupe_gate({}, [])
    assert not ok
    assert "could not be read" in message


def test_the_baseline_is_committed_and_typed():
    """The ratchet lives in git, next to the other gate baselines."""
    baseline = load_baseline(_ROOT)
    assert baseline is not None, "tausik/gates.json carries no test_dedupe baseline"
    assert set(baseline) == {"groups", "tests"}
    assert all(isinstance(v, int) for v in baseline.values())


def test_the_gate_is_registered_on_the_blocking_triggers():
    """A detector nobody runs is what this task existed to end."""
    from gate_registry import PHASE_SCOPED, specs_for_phase

    spec = next(s for s in specs_for_phase(PHASE_SCOPED) if s.name == "test_dedupe")
    assert spec.default_config["enabled"] is True
    assert spec.default_config["severity"] == "block"
    assert set(spec.default_config["trigger"]) == {"task-done", "commit"}
