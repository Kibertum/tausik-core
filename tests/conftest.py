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
def _opt_out_verify_first(request, monkeypatch):
    """v1.4 Verify-First Contract: by default `task_done` refuses to close
    until a `tausik verify` run is cached. That breaks every existing test
    that exercises `task_done` directly without setting up a verify run.

    Backward-compat shim: replace `_enforce_verify_first` with a no-op so
    legacy tests aren't blocked. Tests that WANT to exercise verify-first
    behavior carry ``@pytest.mark.verify_first`` and the shim is skipped.

    We patch the method (not load_config) because tests rightfully read and
    write to the real config.json for unrelated knobs (verify_cache_ttl_seconds,
    session_idle_threshold_minutes, etc.). A global load_config mock would
    break those.
    """
    if request.node.get_closest_marker("verify_first"):
        yield
        return

    try:
        from service_gates import GatesMixin

        def _noop(self, report, slug, relevant_files):
            return None

        monkeypatch.setattr(GatesMixin, "_enforce_verify_first", _noop)
    except Exception:
        pass
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
