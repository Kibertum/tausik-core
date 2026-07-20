"""Tests for verify_cache.has_fresh_verify_run — Verify-First Contract.

The lookup is strict-only: a green counts for a `task_done` iff it was
recorded for the same slug, the same file set (by hash), and the same gate
signature, within the TTL.

Historical note — this file used to pin the OPPOSITE contract. A relaxed
fallback accepted any fresh green whose recorded command named no files
("manual scope", Sharp edge #2 / gotcha #111) as a certificate for an
arbitrary explicit file set, so that `tausik verify` without `--task` could
satisfy a follow-up `task_done`. verify-cache-empty-scope-hit removed it: with
no declared files `gate_runner` SKIPS the scoped gates, so such a run proved
nothing about the files it was certifying, and `compute_files_hash([])` is a
stable empty-marker that no edit moves — the green stayed valid for the whole
TTL across arbitrary tree changes. The convenience was real; what it was
built on was not.

The empty-scope contract itself is pinned in test_verify_cache_empty_scope.py.
"""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from verify_cache import (  # noqa: E402
    _build_cache_command,
    has_fresh_verify_run,
)
from verify_files_hash import compute_files_hash  # noqa: E402
from service_verification import record_run  # noqa: E402


@pytest.fixture
def conn(tmp_path):
    db = tmp_path / "verify.db"
    c = sqlite3.connect(str(db))
    c.row_factory = sqlite3.Row
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS verification_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_slug TEXT,
    scope TEXT NOT NULL CHECK(scope IN
        ('lightweight', 'standard', 'high', 'critical', 'manual')),
    command TEXT NOT NULL,
    exit_code INTEGER NOT NULL,
    summary TEXT,
    files_hash TEXT NOT NULL,
    ran_at TEXT NOT NULL,
    duration_ms INTEGER,
    receipt_json TEXT,
    -- l26-verify-git-diff-wire: how the declared scope related to git at run
    -- time. 'complete' | 'under-declared' | 'unknown'; NULL on rows written
    -- before v38 and read as 'unknown' (never as 'complete').
    declared_scope_status TEXT,
    -- JSON array of files git saw change but relevant_files omitted (capped).
    undeclared_files TEXT,
    -- verify-no-test-mapped-dead-end: 1 when the caller declared, for this run,
    -- that its files map to no test on purpose (docs, config, migrations). Such
    -- a run passes with NO gate executed, so it must stay countable:
    --   SELECT * FROM verification_runs WHERE no_tests_declared = 1;
    -- A dedicated column, not a `scope` value — `scope` is a CHECK-constrained
    -- SENAR tier, and overloading it would have required rebuilding the table
    -- to widen the constraint.
    no_tests_declared INTEGER NOT NULL DEFAULT 0
)
        """
    )
    return c


def _record_manual_verify(conn: sqlite3.Connection, slug: str) -> int:
    """Record what `tausik verify` (no --task) writes: empty files,
    manual scope, files=[] in the command payload."""
    return record_run(
        conn,
        task_slug=slug,
        scope="manual",
        command=_build_cache_command("verify", []),
        exit_code=0,
        summary="pytest pass",
        files_hash=compute_files_hash([]),
        duration_ms=42,
    )


def _record_explicit_verify(conn: sqlite3.Connection, slug: str, files: list[str]) -> int:
    """Record what `tausik verify --task <slug>` writes: explicit files,
    standard scope, files=foo,bar in the command payload."""
    return record_run(
        conn,
        task_slug=slug,
        scope="standard",
        command=_build_cache_command("verify", files),
        exit_code=0,
        summary="pytest pass",
        files_hash=compute_files_hash(files),
        duration_ms=42,
    )


class TestManualScopeCertifiesNothing:
    """Inverted by verify-cache-empty-scope-hit — see module docstring.

    A manual-scope verify run (files=[]) ran with the scoped gates skipped,
    so it cannot stand in for a file set it never looked at.
    """

    def test_manual_row_does_not_satisfy_explicit_task_done(self, conn):
        _record_manual_verify(conn, "t-relaxed")
        fresh, hit = has_fresh_verify_run(conn, "t-relaxed", ["scripts/foo.py"])
        assert fresh is False
        assert hit is None

    def test_manual_row_does_not_satisfy_multiple_explicit_files(self, conn):
        _record_manual_verify(conn, "t-multi")
        fresh, hit = has_fresh_verify_run(
            conn, "t-multi", ["scripts/a.py", "scripts/b.py", "scripts/c.py"]
        )
        assert fresh is False
        assert hit is None

    def test_manual_row_does_not_satisfy_empty_task_done(self, conn):
        """Nor does it match itself: empty scope is refused on the read side
        too, independently of the `noncacheable|` stamp the writer applies."""
        _record_manual_verify(conn, "t-empty")
        fresh, hit = has_fresh_verify_run(conn, "t-empty", [])
        assert fresh is False
        assert hit is None


class TestStrictPriorityOverRelaxed:
    """AC #3: strict hit returns first; relaxed not reached if strict matches."""

    def test_strict_hit_returns_strict_row_not_manual(self, conn, tmp_path):
        # Both rows present: a strict-match for explicit files, AND a manual
        # row. Strict must win — its scope/id should be returned, not manual.
        f = tmp_path / "scripts" / "x.py"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("# x", encoding="utf-8")
        os.chdir(tmp_path)
        files = ["scripts/x.py"]
        manual_id = _record_manual_verify(conn, "t-strict-priority")
        strict_id = _record_explicit_verify(conn, "t-strict-priority", files)
        assert strict_id != manual_id
        fresh, hit = has_fresh_verify_run(conn, "t-strict-priority", files)
        assert fresh is True
        assert hit is not None
        assert hit["id"] == strict_id, (
            "strict path must take precedence — relaxed branch should not "
            "execute when lookup_recent_for_task has an exact match"
        )
        assert hit["scope"] == "standard"


class TestReverseDirectionRejected:
    """AC #2: explicit verify run does NOT auto-satisfy a different file set
    via relaxed fallback. Reverse direction must stay strict so mtime /
    gate-signature invalidation keeps working."""

    def test_explicit_verify_does_not_match_different_explicit_files(self, conn, tmp_path):
        # Verify recorded against ["scripts/a.py"], task_done arrives with
        # ["scripts/b.py"]. Strict misses (different files_hash + command),
        # relaxed sees a row but with files=['scripts/a.py'] in command —
        # NOT empty — so must reject (reverse direction).
        a = tmp_path / "scripts" / "a.py"
        b = tmp_path / "scripts" / "b.py"
        a.parent.mkdir(parents=True, exist_ok=True)
        a.write_text("# a", encoding="utf-8")
        b.write_text("# b", encoding="utf-8")
        os.chdir(tmp_path)
        _record_explicit_verify(conn, "t-reverse", ["scripts/a.py"])
        fresh, hit = has_fresh_verify_run(conn, "t-reverse", ["scripts/b.py"])
        assert fresh is False
        assert hit is None


class TestBucketSeparation:
    """A task-done row must never satisfy the Verify-First lookup.

    Bucket separation used to need an explicit SQL filter because the relaxed
    lookup ignored `command`. With the strict-only lookup it falls out of the
    exact `command` match — the trigger is part of the key — but the property
    is what matters, so it stays asserted directly.
    """

    def test_task_done_row_does_not_satisfy_verify_first(self, conn, tmp_path):
        f = tmp_path / "scripts" / "foo.py"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("# foo", encoding="utf-8")
        os.chdir(tmp_path)
        files = ["scripts/foo.py"]
        # Bootstrap / pre-commit / an earlier task_done attempt records a
        # task-done bucket row for exactly these files: exit_code=0, same
        # files_hash. Only the trigger differs.
        record_run(
            conn,
            task_slug="t-bucket",
            scope="lightweight",
            command=_build_cache_command("task-done", files),
            exit_code=0,
            summary="filesize=PASS",
            files_hash=compute_files_hash(files),
            duration_ms=0,
        )
        fresh, hit = has_fresh_verify_run(conn, "t-bucket", files)
        assert fresh is False, "task-done bucket row must not close QG-2"
        assert hit is None

    def test_verify_row_found_despite_newer_task_done_rows(self, conn, tmp_path):
        """The verify row still wins when task-done rows are interleaved after
        it — a newer row in the other bucket must not shadow it."""
        f = tmp_path / "scripts" / "foo.py"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("# foo", encoding="utf-8")
        os.chdir(tmp_path)
        files = ["scripts/foo.py"]
        verify_id = _record_explicit_verify(conn, "t-interleaved", files)
        for _ in range(2):
            record_run(
                conn,
                task_slug="t-interleaved",
                scope="lightweight",
                command=_build_cache_command("task-done", files),
                exit_code=0,
                summary="filesize=PASS",
                files_hash=compute_files_hash(files),
                duration_ms=0,
            )
        fresh, hit = has_fresh_verify_run(conn, "t-interleaved", files)
        assert fresh is True
        assert hit is not None
        assert hit["id"] == verify_id
        assert hit["scope"] == "standard"


class TestSecurityShortCircuit:
    """AC #4: security-sensitive files never reach the relaxed branch.
    is_cache_allowed=False at the top short-circuits before any DB hit."""

    def test_security_sensitive_rejects_even_with_manual_row(self, conn):
        # Manual verify row exists for the slug, but the task_done call
        # names an auth file. Must return (False, None) without using cache.
        _record_manual_verify(conn, "t-security")
        fresh, hit = has_fresh_verify_run(conn, "t-security", ["src/auth/login.py"])
        assert fresh is False
        assert hit is None

    def test_security_sensitive_rejects_even_with_strict_row(self, conn, tmp_path):
        f = tmp_path / "src" / "auth" / "login.py"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("# auth", encoding="utf-8")
        os.chdir(tmp_path)
        files = ["src/auth/login.py"]
        _record_explicit_verify(conn, "t-security-strict", files)
        fresh, hit = has_fresh_verify_run(conn, "t-security-strict", files)
        assert fresh is False
        assert hit is None


class TestEmptyAndMissingCases:
    """No row at all → False; preserved across the relaxed-fallback rewrite."""

    def test_no_row_for_slug_returns_false(self, conn):
        fresh, hit = has_fresh_verify_run(conn, "nonexistent", ["scripts/x.py"])
        assert fresh is False
        assert hit is None

    def test_red_row_does_not_satisfy_relaxed(self, conn):
        # Manually insert a red verify run (exit_code != 0). Neither strict
        # nor relaxed lookup should accept it. Use direct SQL to bypass
        # record_run's no-red-write convention used in production paths.
        record_run(
            conn,
            task_slug="t-red",
            scope="manual",
            command=_build_cache_command("verify", []),
            exit_code=1,
            summary="pytest fail",
            files_hash=compute_files_hash([]),
        )
        fresh, hit = has_fresh_verify_run(conn, "t-red", ["scripts/x.py"])
        assert fresh is False
        assert hit is None
