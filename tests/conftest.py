"""TAUSIK test configuration."""

import pytest
from unittest.mock import patch

from verify_first_compat_predicate import should_apply_verify_first_autouse_compat_shim


@pytest.fixture(autouse=True)
def _mock_run_gates():
    """Mock gate_runner.run_gates to prevent pytest-in-pytest recursion.

    Tests that need to test gate behavior should use their own
    patch.dict("sys.modules", ...) to override this.
    """
    with patch("gate_runner.run_gates", return_value=(True, [])):
        yield


@pytest.fixture(autouse=True)
def _verify_first_autouse_compat_shim(request, monkeypatch):
    """Bridge legacy tests into v1.4 Verify-First without rewriting the suite.

    **Product contract.** With ``task_done.auto_verify`` left at default
    ``false``, ``task_done`` requires a fresh green from ``tausik verify`` in
    ``verification_runs``. Most unit tests call ``task_done`` without seeding
    that cache.

    **Shim (this fixture).** When `should_apply_verify_first_autouse_compat_shim`
    is true for ``request.node``, patch ``GatesMixin._enforce_verify_first`` to
    a no-op so those tests keep passing.

    **Opt-in to real enforcement.** Declare ``@pytest.mark.verify_first`` on a
    test (or class). The shim is then skipped; see `verify_first_compat_predicate`
    and `docs/en/verify-glossary.md` (test shim).

    **Why patch the method, not config.** Tests legitimately tweak
    ``load_config()`` for unrelated keys (TTL, idle thresholds); mocking the
    whole config globally would regress them.
    """
    if not should_apply_verify_first_autouse_compat_shim(request.node):
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
