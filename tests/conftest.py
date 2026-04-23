"""TAUSIK test configuration."""

import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def _mock_run_gates():
    """Mock gate_runner.run_gates to prevent pytest-in-pytest recursion.

    Tests that need to test gate behavior should use their own
    patch.dict("sys.modules", ...) to override this.
    """
    with patch("gate_runner.run_gates", return_value=(True, [])):
        yield


@pytest.fixture(autouse=True)
def _isolated_brain_registry(tmp_path_factory, monkeypatch):
    """Redirect the global brain registry to a throwaway path for every test.

    Prevents tests that go through scrub_with_config(union_with_registry=True)
    from reading or writing the dev's real ~/.tausik-brain/projects.json.
    """
    reg_dir = tmp_path_factory.mktemp("brain_registry")
    monkeypatch.setenv("TAUSIK_BRAIN_REGISTRY", str(reg_dir / "projects.json"))
    yield
