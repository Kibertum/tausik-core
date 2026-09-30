"""`tausik demo` and the project-root rule it forced on three gates.

The demo runs the real CLI against a sandbox on the temp drive. Running it exposed
three gates that located "the project" from their own file: `ruff_format` refused a
sandbox on another drive, `test_dedupe` measured the framework's tests inside a
consumer's close, and `cross_model_parity` crashed from the deployed copy.
"""

from __future__ import annotations

import glob
import os
import sys
import tempfile

import pytest

# Runs a sandbox of its own and reads no source tree for coverage.
CROSSCUTTING_SCOPE: list[str] = []

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import gate_cross_model_parity  # noqa: E402
import gate_project_root  # noqa: E402
import gate_ruff_format  # noqa: E402
import gate_test_dedupe  # noqa: E402
import project_cli_demo  # noqa: E402


@pytest.mark.slow
def test_the_demo_behaves_as_it_says_and_leaves_nothing_behind(capsys):
    before = set(glob.glob(os.path.join(tempfile.gettempdir(), "tausik-demo-*")))
    assert project_cli_demo.run_demo() == 0
    out = capsys.readouterr().out
    # Each step's verdict is the REAL CLI's words, not a caption.
    assert "verify-first" in out
    assert "FAILED tests/test_calc.py::test_add" in out
    assert "Task 'fix-add' completed" in out
    assert "as described" in out
    after = set(glob.glob(os.path.join(tempfile.gettempdir(), "tausik-demo-*")))
    assert after <= before, f"sandbox left behind: {after - before}"


@pytest.fixture
def consumer(tmp_path, monkeypatch):
    """A project that is NOT the framework: its own .tausik, no tests/, no bootstrap/."""
    (tmp_path / ".tausik").mkdir()
    monkeypatch.setenv("TAUSIK_DIR", str(tmp_path / ".tausik"))
    return tmp_path


def test_the_project_root_is_where_its_tausik_dir_is(consumer):
    assert os.path.samefile(gate_project_root.project_root(), consumer)


def test_ruff_format_and_dedupe_measure_the_consumer_not_the_framework(consumer):
    assert os.path.samefile(gate_ruff_format._repo_root(), consumer)
    assert os.path.samefile(gate_test_dedupe._repo_root(), consumer)


def test_ruff_format_takes_a_file_of_the_consumer_without_a_drive_error(consumer):
    (consumer / "calc.py").write_text("x = 1\n", encoding="utf-8")
    ok, message = gate_ruff_format.run_ruff_format_gate({}, [str(consumer / "calc.py")])
    assert "mount" not in message


def test_cross_model_parity_does_not_apply_where_there_is_no_bootstrap_source(consumer):
    ok, message = gate_cross_model_parity.run_cross_model_parity_gate({}, [])
    assert ok, message
    assert "not applicable" in message


def test_cross_model_parity_still_runs_on_the_framework_itself(monkeypatch):
    """NEGATIVE: the fix must not switch the gate off where it has a subject."""
    monkeypatch.setenv("TAUSIK_DIR", os.path.join(_ROOT, ".tausik"))
    if not os.path.isdir(os.path.join(_ROOT, ".tausik")):
        pytest.skip("framework checkout without a .tausik project")
    ok, message = gate_cross_model_parity.run_cross_model_parity_gate({}, [])
    assert "not applicable" not in message
    assert "raised" not in message, message


def test_dedupe_in_a_consumer_measures_the_consumer_whatever_the_framework_owes(consumer):
    """It measured the framework's 280+ groups here and refused a consumer's close for them."""
    ok, message = gate_test_dedupe.run_test_dedupe_gate({}, ["calc.py"])
    assert ok, message
    assert "NOT ADOPTED" in message and "measured 0 group(s)" in message
