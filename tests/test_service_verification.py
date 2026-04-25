"""Tests for scripts/service_verification.py — verify-cache primitives."""

from __future__ import annotations

import os
import sqlite3
import sys
import time

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import service_verification as sv  # noqa: E402

# --- Schema fixture --------------------------------------------------------


_VERIFICATION_RUNS_DDL = """
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
    duration_ms INTEGER
);
"""


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(_VERIFICATION_RUNS_DDL)
    yield c
    c.close()


# --- compute_files_hash ----------------------------------------------------


class TestComputeFilesHash:
    def test_empty_returns_stable_marker(self):
        h = sv.compute_files_hash([])
        assert isinstance(h, str) and len(h) == 64
        # Same on repeat
        assert sv.compute_files_hash([]) == h

    def test_none_treated_as_empty(self):
        assert sv.compute_files_hash(None) == sv.compute_files_hash([])  # type: ignore[arg-type]

    def test_changes_when_file_modified(self, tmp_path):
        f = tmp_path / "a.py"
        f.write_text("# v1")
        h1 = sv.compute_files_hash(["a.py"], root=str(tmp_path))
        # Force mtime change
        time.sleep(0.05)
        f.write_text("# v2")
        os.utime(f, None)
        h2 = sv.compute_files_hash(["a.py"], root=str(tmp_path))
        assert h1 != h2

    def test_order_independent(self, tmp_path):
        (tmp_path / "a.py").write_text("a")
        (tmp_path / "b.py").write_text("b")
        h1 = sv.compute_files_hash(["a.py", "b.py"], root=str(tmp_path))
        h2 = sv.compute_files_hash(["b.py", "a.py"], root=str(tmp_path))
        assert h1 == h2

    def test_missing_file_contributes_sentinel(self, tmp_path):
        """Missing file → still hashes (sentinel 0). Hash differs from empty."""
        h_missing = sv.compute_files_hash(["nope.py"], root=str(tmp_path))
        h_empty = sv.compute_files_hash([], root=str(tmp_path))
        assert h_missing != h_empty

    def test_file_appearance_changes_hash(self, tmp_path):
        h_before = sv.compute_files_hash(["new.py"], root=str(tmp_path))
        (tmp_path / "new.py").write_text("hi")
        h_after = sv.compute_files_hash(["new.py"], root=str(tmp_path))
        assert h_before != h_after

    def test_skips_empty_or_non_string(self, tmp_path):
        (tmp_path / "a.py").write_text("a")
        h = sv.compute_files_hash(
            ["", None, 123, "a.py"],
            root=str(tmp_path),  # type: ignore[list-item]
        )
        # Should equal hash of just ["a.py"]
        assert h == sv.compute_files_hash(["a.py"], root=str(tmp_path))


# --- is_security_sensitive -------------------------------------------------


class TestIsSecuritySensitive:
    @pytest.mark.parametrize(
        "path",
        [
            "scripts/hooks/memory_pretool_block.py",
            "src/auth/login.ts",
            "app/payment/handlers.py",
            "lib/payments/refund.go",
            "billing/invoice.rs",
        ],
    )
    def test_security_paths_detected(self, path):
        assert sv.is_security_sensitive([path]) is True

    @pytest.mark.parametrize(
        "path",
        [
            "scripts/brain_init.py",
            "src/profile/page.tsx",
            "scripts/hooksomething.py",  # substring 'hooks' but not /hooks/
            "tests/test_auth_unrelated.py",  # tests dir, not source
        ],
    )
    def test_non_security_paths_pass(self, path):
        # tests/test_auth_unrelated has 'auth' substring but NOT under /auth/
        # — reasonable false negative; cache stays enabled
        assert sv.is_security_sensitive([path]) is False

    def test_empty_or_none_is_safe(self):
        assert sv.is_security_sensitive([]) is False
        assert sv.is_security_sensitive(None) is False  # type: ignore[arg-type]

    def test_any_match_triggers(self):
        files = ["scripts/brain_init.py", "scripts/hooks/foo.py"]
        assert sv.is_security_sensitive(files) is True


# --- record_run + lookup_recent_for_task -----------------------------------


class TestRecordAndLookup:
    def test_record_returns_id(self, conn):
        rid = sv.record_run(
            conn,
            task_slug="t1",
            scope="lightweight",
            command="cmd-x",
            exit_code=0,
            summary="ok",
            files_hash="abc",
            duration_ms=42,
        )
        assert rid >= 1

    def test_lookup_recent_hits_when_fresh_and_matches(self, conn):
        sv.record_run(
            conn,
            task_slug="t1",
            scope="lightweight",
            command="cmd-x",
            exit_code=0,
            summary="ok",
            files_hash="hash-abc",
        )
        hit = sv.lookup_recent_for_task(
            conn, "t1", files_hash="hash-abc", command="cmd-x"
        )
        assert hit is not None
        assert hit["scope"] == "lightweight"

    def test_lookup_misses_on_no_runs(self, conn):
        assert (
            sv.lookup_recent_for_task(conn, "never", files_hash="x", command="y")
            is None
        )

    def test_lookup_misses_on_files_hash_mismatch(self, conn):
        sv.record_run(
            conn,
            task_slug="t1",
            scope="standard",
            command="cmd-x",
            exit_code=0,
            summary="ok",
            files_hash="hash-OLD",
        )
        miss = sv.lookup_recent_for_task(
            conn, "t1", files_hash="hash-NEW", command="cmd-x"
        )
        assert miss is None

    def test_lookup_misses_on_command_mismatch(self, conn):
        sv.record_run(
            conn,
            task_slug="t1",
            scope="standard",
            command="cmd-OLD",
            exit_code=0,
            summary="ok",
            files_hash="h",
        )
        miss = sv.lookup_recent_for_task(conn, "t1", files_hash="h", command="cmd-NEW")
        assert miss is None

    def test_lookup_misses_on_red_run(self, conn):
        """Most recent run failed → no cache hit even if files match."""
        sv.record_run(
            conn,
            task_slug="t1",
            scope="standard",
            command="cmd",
            exit_code=1,
            summary="FAIL",
            files_hash="h",
        )
        miss = sv.lookup_recent_for_task(conn, "t1", files_hash="h", command="cmd")
        assert miss is None

    def test_lookup_misses_when_stale(self, conn):
        """Run with old ran_at timestamp → cache miss."""
        sv.record_run(
            conn,
            task_slug="t1",
            scope="standard",
            command="cmd",
            exit_code=0,
            summary="ok",
            files_hash="h",
        )
        # Backdate the run by 1 hour
        conn.execute(
            "UPDATE verification_runs SET ran_at = ? WHERE task_slug = ?",
            ("2020-01-01T00:00:00Z", "t1"),
        )
        conn.commit()
        miss = sv.lookup_recent_for_task(
            conn, "t1", files_hash="h", command="cmd", max_age_s=600
        )
        assert miss is None

    def test_lookup_takes_most_recent(self, conn):
        """When there are multiple runs, the latest wins."""
        sv.record_run(
            conn,
            task_slug="t1",
            scope="standard",
            command="cmd",
            exit_code=1,  # red older
            summary="x",
            files_hash="h",
        )
        sv.record_run(
            conn,
            task_slug="t1",
            scope="standard",
            command="cmd",
            exit_code=0,  # green newer
            summary="ok",
            files_hash="h",
        )
        hit = sv.lookup_recent_for_task(conn, "t1", files_hash="h", command="cmd")
        assert hit is not None
        assert hit["exit_code"] == 0

    def test_lookup_empty_slug_returns_none(self, conn):
        assert sv.lookup_recent_for_task(conn, "", files_hash="h", command="c") is None


# --- is_cache_allowed ------------------------------------------------------


class TestIsCacheAllowed:
    def test_safe_files_allow_cache(self):
        assert sv.is_cache_allowed(["scripts/brain_init.py"]) is True

    def test_security_files_disallow_cache(self):
        assert sv.is_cache_allowed(["scripts/hooks/anything.py"]) is False

    def test_empty_files_allow(self):
        assert sv.is_cache_allowed([]) is True
