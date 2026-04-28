"""Regression tests for v1.3 blind-review HIGH/MED findings."""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend
from project_service import ProjectService
from tausik_utils import ServiceError


@pytest.fixture
def svc(tmp_path):
    db = tmp_path / "tausik.db"
    backend = SQLiteBackend(str(db))
    return ProjectService(backend)


def _seed_task(svc, slug="t-1"):
    svc.task_quick(f"Test task {slug}", goal="Test goal", role="developer")
    return slug


# ---------------------------------------------------------------------------
# QG-2 enforcement: task_update cannot bypass lifecycle
# ---------------------------------------------------------------------------
def test_task_update_status_done_is_refused(svc):
    """QG-2 bypass via task_update status=done must be blocked."""
    info = svc.task_quick("Bypass test", goal="g", role="developer")
    slug = info.split("'")[1] if "'" in info else "bypass-test"
    with pytest.raises(ServiceError, match="lifecycle"):
        svc.task_update(slug, status="done")


def test_task_update_status_active_is_refused(svc):
    info = svc.task_quick("Bypass2", goal="g", role="developer")
    slug = info.split("'")[1] if "'" in info else "bypass2"
    with pytest.raises(ServiceError, match="lifecycle"):
        svc.task_update(slug, status="active")


def test_task_update_status_blocked_is_refused(svc):
    info = svc.task_quick("Bypass3", goal="g", role="developer")
    slug = info.split("'")[1] if "'" in info else "bypass3"
    with pytest.raises(ServiceError, match="lifecycle"):
        svc.task_update(slug, status="blocked")


def test_task_update_status_review_is_refused(svc):
    info = svc.task_quick("Bypass4", goal="g", role="developer")
    slug = info.split("'")[1] if "'" in info else "bypass4"
    with pytest.raises(ServiceError, match="lifecycle"):
        svc.task_update(slug, status="review")


def test_task_update_other_fields_still_works(svc):
    info = svc.task_quick("Bypass5", goal="g", role="developer")
    slug = info.split("'")[1] if "'" in info else "bypass5"
    # Updating non-status fields should still succeed
    result = svc.task_update(slug, title="Updated title")
    assert "updated" in result.lower()


# ---------------------------------------------------------------------------
# QG-2: source-without-test must fail, not pass silently
# ---------------------------------------------------------------------------
def test_run_gates_with_cache_source_no_test_fails(tmp_path):
    """v1.3 blind-review: source file with no matching test must NOT pass as green."""
    from service_verification import run_gates_with_cache
    from project_backend import SQLiteBackend

    db = tmp_path / "tausik.db"
    be = SQLiteBackend(str(db))
    notes_log: list[tuple[str, str]] = []
    be.task_quick = lambda *a, **kw: None

    # Set up a task and a "source" file with no matching test
    proj = tmp_path / "proj"
    proj.mkdir()
    src = proj / "scripts"
    src.mkdir()
    (src / "newauth.py").write_text("# no test", encoding="utf-8")

    # Run with a source file that has no matching test
    cwd = os.getcwd()
    os.chdir(proj)
    try:
        passed, results, status = run_gates_with_cache(
            be._conn,
            "test-slug",
            ["scripts/newauth.py"],
            scope="standard",
            append_notes_fn=lambda s, m: notes_log.append((s, m)),
        )
    finally:
        os.chdir(cwd)

    # If everything was skipped (no tests mapped), must NOT pass
    if results and all(r.get("skipped") for r in results):
        assert passed is False, "all-skipped scoped run must NOT pass as green"
        assert status == "no-test-mapped"
        assert any("No test" in m or "no tests" in m.lower() for _, m in notes_log)


# ---------------------------------------------------------------------------
# Security: extended token list catches webhook/oauth/csrf/etc
# ---------------------------------------------------------------------------
def test_security_sensitive_recognises_extended_basenames():
    from service_verification import is_security_sensitive

    for path in [
        "scripts/webhook.py",
        "src/csrf.py",
        "auth/totp.py",
        "core/api_key.py",
        "rbac/permissions.py",
        "iam.py",
        "src/oauth_callback.py",
        "lib/xsrf.py",
    ]:
        assert is_security_sensitive([path]), f"{path} must be security-sensitive"


# ---------------------------------------------------------------------------
# Memory pretool block: case-insensitive segment match
# ---------------------------------------------------------------------------
def test_memory_block_detects_uppercase_memory_dir():
    """v1.3 blind-review: MEMORY/, Memory/, memory/ all blocked on every platform."""
    sys.path.insert(
        0, os.path.join(os.path.dirname(__file__), "..", "scripts", "hooks")
    )
    from memory_pretool_block import is_in_claude_memory

    home = os.path.expanduser("~")
    assert is_in_claude_memory(
        os.path.join(home, ".claude", "projects", "foo", "memory", "x.md")
    )
    assert is_in_claude_memory(
        os.path.join(home, ".claude", "projects", "foo", "MEMORY", "x.md")
    )
    assert is_in_claude_memory(
        os.path.join(home, ".claude", "projects", "foo", "Memory", "x.md")
    )
    assert is_in_claude_memory(
        os.path.join(home, ".claude", "agents", "test", "MeMoRy", "x.md")
    )
    # Non-memory paths still allowed
    assert not is_in_claude_memory(
        os.path.join(home, ".claude", "projects", "foo", "tasks", "x.md")
    )


# ---------------------------------------------------------------------------
# Brain plaintext leak: tags/stack/etc must be scrubbed
# ---------------------------------------------------------------------------
def test_brain_scrub_inputs_covers_tags_and_stack():
    """v1.3 blind-review: project name in tags array must be caught by scrubber."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    from brain_mcp_write import scrub_inputs

    cfg = {"project_names": ["kibertum-project"], "private_url_patterns": []}
    fields = {
        "name": "Some decision",
        "context": "OK",
        "decision": "OK",
        "rationale": "OK",
        "tags": ["architecture", "kibertum-project"],
        "stack": ["python"],
    }
    result = scrub_inputs("decisions", fields, cfg)
    assert result["ok"] is False, "project name in tags must be blocked"


def test_brain_scrub_inputs_passes_clean_data():
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    from brain_mcp_write import scrub_inputs

    cfg = {"project_names": ["secret-proj"], "private_url_patterns": []}
    fields = {
        "name": "Use urllib",
        "context": "Need stdlib HTTP",
        "decision": "Use urllib",
        "rationale": "Zero deps",
        "tags": ["architecture", "python"],
        "stack": ["python"],
    }
    result = scrub_inputs("decisions", fields, cfg)
    assert result["ok"] is True


# ---------------------------------------------------------------------------
# Stack registry: no hardcoded fallback drift
# ---------------------------------------------------------------------------
def test_default_gates_no_fallback_on_registry_failure(monkeypatch):
    """v1.3 blind-review: registry failure must return empty dict + log, not stale hardcode."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    import default_gates as dg

    # Force registry import error
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *a, **kw):
        if name == "stack_registry":
            raise ImportError("simulated")
        return real_import(name, *a, **kw)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    out = dg._build_stack_scoped_gates()
    assert out == {}, "Registry failure must yield empty dict, not hardcoded fallback"
