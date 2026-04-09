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
