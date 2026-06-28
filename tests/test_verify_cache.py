"""Tests for verify_cache.has_fresh_verify_run — Verify-First Contract.

Pins the strict-vs-relaxed lookup symmetry between `has_fresh_verify_run`
(used by `task_done`) and `run_gates_with_cache.run_gates_with_cache`
(used by inline gates). Both must accept the same Sharp edge #2 case where
`tausik verify` was invoked without `--task` (manual scope, files=[])
and a follow-up `task_done` arrives with explicit `relevant_files`.

Earlier asymmetry: `run_gates_with_cache` accepted manual→explicit, but
`has_fresh_verify_run` returned strict-miss → `task_done` failed with
cache_status='git-mismatch' even though heavy gates had just passed.
That's gotcha #111 — surfaced in three sessions before the structural fix.
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
        CREATE TABLE verification_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_slug TEXT,
            scope TEXT NOT NULL,
            command TEXT NOT NULL,
            exit_code INTEGER NOT NULL,
            summary TEXT,
            files_hash TEXT NOT NULL,
            ran_at TEXT NOT NULL,
            duration_ms INTEGER
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


class TestRelaxedAcceptManualToExplicit:
    """AC #1: manual-scope verify (files=[]) satisfies explicit task_done."""

    def test_relaxed_hit_when_strict_misses(self, conn):
        _record_manual_verify(conn, "t-relaxed")
        # Strict lookup misses (files_hash differs), relaxed accepts.
        fresh, hit = has_fresh_verify_run(conn, "t-relaxed", ["scripts/foo.py"])
        assert fresh is True
        assert hit is not None
        assert hit["scope"] == "manual"

    def test_relaxed_hit_with_multiple_explicit_files(self, conn):
        _record_manual_verify(conn, "t-multi")
        fresh, hit = has_fresh_verify_run(
            conn, "t-multi", ["scripts/a.py", "scripts/b.py", "scripts/c.py"]
        )
        assert fresh is True
        assert hit is not None


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


class TestBucketSeparationInterleaved:
    """Regression: a task-done row recorded BETWEEN the agent's `tausik verify`
    and the follow-up `task done` must NOT shadow the verify row by being
    more recent. The relaxed lookup filters by `command LIKE 'trigger=verify|%'`
    in SQL, so the verify row is selected even when interleaved task-done
    rows have higher ids."""

    def test_verify_row_still_found_with_interleaved_task_done_rows(self, conn):
        files = ["scripts/foo.py"]
        # 1. Agent runs `tausik verify --task slug` (manual scope, files=[]).
        manual_id = _record_manual_verify(conn, "t-interleaved")
        # 2. Bootstrap / pre-commit / earlier task_done attempt records a
        #    task-done bucket row with the explicit files. exit_code=0,
        #    higher id, would shadow verify in a naive ORDER BY id DESC LIMIT 1.
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
        # 3. `task done <slug> --relevant-files scripts/foo.py` — strict
        #    lookup misses (verify hash is hash([]), task_done hash differs),
        #    relaxed must skip the task-done rows and find the verify row.
        fresh, hit = has_fresh_verify_run(conn, "t-interleaved", files)
        assert fresh is True
        assert hit is not None
        assert hit["id"] == manual_id, (
            "relaxed lookup must filter by trigger=verify| in SQL — "
            "interleaved task-done rows must not shadow the manual verify"
        )
        assert hit["scope"] == "manual"


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
