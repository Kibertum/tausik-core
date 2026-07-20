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
    except Exception:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
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


@pytest.fixture(autouse=True)
def _isolated_config_trust_tiers(tmp_path_factory, monkeypatch):
    """Point the user/managed config tiers at throwaway paths for every test.

    `load_config` merges ~/.tausik/config.json on top of the project config, so
    without this a dev who keeps a real user-tier file would get different
    results from CI — the suite would silently measure their machine.
    """
    tier_dir = tmp_path_factory.mktemp("config_tiers")
    monkeypatch.setenv("TAUSIK_USER_CONFIG", str(tier_dir / "user.json"))
    monkeypatch.delenv("TAUSIK_MANAGED_CONFIG", raising=False)
    yield


def canonical_ddl(table: str) -> str:
    """Вырезать CREATE TABLE <table> из backend_schema.SCHEMA_SQL.

    Единственный источник DDL для тестовых фикстур. Рукописные копии схемы
    verification_runs уже дважды стоили дорого: сначала добавление двух колонок
    в v38 потребовало ручной правки девяти блоков (задача
    test-ddl-drift-verification-runs), затем в сессии #119 фикстура без
    CHECK(scope IN (...)) дала 20 зелёных тестов при фиче, которая падала
    IntegrityError на КАЖДОЙ записи в живую БД.

    Копия схемы в тесте доказывает соответствие копии, а не продакшену, и
    расходится молча — поэтому её здесь быть не должно.
    """
    import os
    import sys

    scripts = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from backend_schema import SCHEMA_SQL

    marker = f"CREATE TABLE IF NOT EXISTS {table}"
    start = SCHEMA_SQL.index(marker)
    end = SCHEMA_SQL.index("\n);", start) + len("\n);")
    return SCHEMA_SQL[start:end]


VERIFICATION_RUNS_DDL = canonical_ddl("verification_runs")
