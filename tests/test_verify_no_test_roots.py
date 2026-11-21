"""Early NoTestRoots diagnosis before the expensive verify lane."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from verify_no_test_roots import no_test_roots_refusal, python_sources_without_suite

# Scoped pytest selects by subject import; this file guards the verify cache
# path that lives under scripts/, so declare the cross-cutting scope.
CROSSCUTTING_SCOPE = ["scripts/"]


def test_docs_only_scope_is_not_a_no_test_roots_refusal(tmp_path: Path):
    assert python_sources_without_suite(["docs/en/readme.md", "CHANGELOG.md"]) == []
    assert no_test_roots_refusal(["docs/en/readme.md"], base=str(tmp_path)) is None


def test_explicit_test_file_without_roots_is_allowed(tmp_path: Path):
    probe = tmp_path / "test_probe.py"
    probe.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    assert no_test_roots_refusal(["test_probe.py"], base=str(tmp_path)) is None


def test_python_source_without_roots_refuses_before_lane(tmp_path: Path):
    src = tmp_path / "app.py"
    src.write_text("VALUE = 1\n", encoding="utf-8")
    message = no_test_roots_refusal(["app.py"], base=str(tmp_path))
    assert message is not None
    assert "NoTestRoots" in message
    assert "app.py" in message
    assert "--no-tests-expected" in message
    assert "COULD_NOT_RUN" in message


def test_configured_or_discovered_roots_clear_the_refusal(tmp_path: Path):
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_app.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    assert no_test_roots_refusal(["app.py"], base=str(tmp_path)) is None


@pytest.fixture
def conn(tmp_path: Path):
    from conftest import VERIFICATION_RUNS_DDL

    db = tmp_path / "tausik.db"
    connection = sqlite3.connect(db)
    connection.executescript(VERIFICATION_RUNS_DDL)
    yield connection
    connection.close()


def test_cached_run_refuses_python_scope_without_calling_gates(conn, tmp_path, monkeypatch):
    import gate_runner
    import verify_cached_run
    from verify_cache import resolve_gate_signature

    (tmp_path / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    gate_signature = resolve_gate_signature("verify")
    monkeypatch.setattr(verify_cached_run, "compute_files_hash", lambda _f: "hash")
    monkeypatch.setattr(verify_cached_run, "is_cache_allowed", lambda _f: True)
    monkeypatch.setattr(verify_cached_run, "resolve_gate_signature", lambda _t: gate_signature)
    monkeypatch.setattr(verify_cached_run, "_build_cache_command", lambda *_a, **_k: "cmd")
    monkeypatch.setattr(
        verify_cached_run, "describe_declared_scope", lambda *_a, **_k: {"status": "declared"}
    )
    ran = {"n": 0}

    def _boom(*_a, **_kw):
        ran["n"] += 1
        raise AssertionError("run_gates must not run after NoTestRoots")

    monkeypatch.setattr(gate_runner, "run_gates", _boom)
    passed, results, status = verify_cached_run.run_gates_with_cache(
        conn, "no-roots-task", ["app.py"], trigger="verify"
    )
    assert passed is False
    assert status == "no-test-roots"
    assert ran["n"] == 0
    assert any("NoTestRoots" in (row.get("output") or "") for row in results)
