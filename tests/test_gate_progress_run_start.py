"""r14-mcp-streaming-progress: gate_runner emits run_start with ETA."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


@pytest.fixture(autouse=True)
def _disable_global_run_gates_mock(monkeypatch):
    """conftest.py autouses a `gate_runner.run_gates` mock to prevent
    pytest-in-pytest recursion. We need the real `run_gates` to assert on
    its emitted progress events. Reload the module so the patched binding
    is replaced by the real callable for the duration of the test.
    """
    import importlib

    import gate_runner

    importlib.reload(gate_runner)
    yield


def test_run_start_event_has_max_seconds():
    """Direct stub of gate_runner attrs — we only care about payload shape."""
    import gate_runner

    fake_gates = [
        {"name": "alpha", "timeout": 30, "severity": "warn", "trigger": ["x"]},
        {"name": "beta", "timeout": 60, "severity": "block", "trigger": ["x"]},
    ]
    orig_get = gate_runner.get_gates_for_trigger
    orig_applies = gate_runner.gate_applies_to
    gate_runner.get_gates_for_trigger = lambda *a, **k: fake_gates
    gate_runner.gate_applies_to = lambda gate, files: False
    try:
        events: list[dict] = []
        gate_runner.run_gates("x", files=[], progress_callback=events.append)
    finally:
        gate_runner.get_gates_for_trigger = orig_get
        gate_runner.gate_applies_to = orig_applies
    starts = [e for e in events if e.get("event") == "run_start"]
    assert len(starts) == 1
    s = starts[0]
    assert s["total"] == 2
    assert s["max_seconds"] == 90
    assert s["gates"] == ["alpha", "beta"]
    assert s["trigger"] == "x"


def test_run_start_skipped_when_no_gates():
    import gate_runner

    orig = gate_runner.get_gates_for_trigger
    gate_runner.get_gates_for_trigger = lambda *a, **k: []
    try:
        events: list[dict] = []
        gate_runner.run_gates(
            "nonexistent-trigger", files=[], progress_callback=events.append
        )
    finally:
        gate_runner.get_gates_for_trigger = orig
    assert all(e.get("event") != "run_start" for e in events)
