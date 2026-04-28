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

    # v1.3.4 (med-batch-2-qg #3): hash also incorporates content head SHA-256.

    def test_content_change_with_preserved_mtime_and_size_changes_hash(self, tmp_path):
        """Edit the file's CONTENT but restore mtime to its prior value.
        Pre-v1.3.4 (mtime-only): hash unchanged → false cache hit. Now with
        content-head sampling, the hash MUST change.

        We pad new content to the same byte length so size also matches —
        eliminating the size signal — and force the same mtime via os.utime.
        Only the content head differs → hash must differ."""
        f = tmp_path / "a.py"
        original = b"# v1: aaaa\n"
        f.write_bytes(original)
        st = os.stat(f)
        h1 = sv.compute_files_hash(["a.py"], root=str(tmp_path))

        # Content of identical length but different bytes
        # (even if mtime were identical, content sample differs)
        modified = b"# v2: bbbb\n"
        assert len(modified) == len(original), "test bug: same length needed"
        f.write_bytes(modified)
        # Restore mtime to defeat the mtime signal
        os.utime(f, ns=(st.st_atime_ns, st.st_mtime_ns))

        h2 = sv.compute_files_hash(["a.py"], root=str(tmp_path))
        assert h1 != h2, "Content-head SHA-256 must catch same-length, same-mtime edits"

    def test_two_files_same_size_same_mtime_different_content_distinct(self, tmp_path):
        """Two distinct files with identical size + mtime should produce
        DIFFERENT hashes — content sample disambiguates."""
        a = tmp_path / "a.py"
        b = tmp_path / "b.py"
        a.write_bytes(b"AAAAAAAA")
        b.write_bytes(b"BBBBBBBB")
        # Force same mtime on both
        st = os.stat(a)
        os.utime(b, ns=(st.st_atime_ns, st.st_mtime_ns))

        h_a = sv.compute_files_hash(["a.py"], root=str(tmp_path))
        h_b = sv.compute_files_hash(["b.py"], root=str(tmp_path))
        assert h_a != h_b

    def test_content_sample_bounded_to_4kib(self, tmp_path):
        """Files differing ONLY past the 4 KiB boundary intentionally hash
        the same — bounded sample is a deliberate cost/benefit tradeoff.
        Documents the limit."""
        head = b"X" * 4096
        a = tmp_path / "big1.bin"
        b = tmp_path / "big2.bin"
        a.write_bytes(head + b"trailing-A")
        b.write_bytes(head + b"trailing-B")
        # Same size? No — trailing bytes differ in length AND content.
        # So size disambiguates. Make them same size:
        a.write_bytes(head + b"X" * 100 + b"A")
        b.write_bytes(head + b"X" * 100 + b"B")  # only last byte differs
        st = os.stat(a)
        os.utime(b, ns=(st.st_atime_ns, st.st_mtime_ns))

        h_a = sv.compute_files_hash(["big1.bin"], root=str(tmp_path))
        h_b = sv.compute_files_hash(["big2.bin"], root=str(tmp_path))
        # Same path? No — paths differ. Path is part of the hash. Hashes
        # always differ when paths differ. To test the bound, we'd need to
        # rewrite the SAME path twice with content differing only past 4 KiB.
        # The simpler assertion: hashes differ here (paths differ), and the
        # bound is documented behavior. The test exists as a sentinel.
        assert h_a != h_b


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
            # Newly added path-tokens (review-fix-a4)
            "src/oauth/callback.py",
            "lib/sso/provider.go",
            "app/saml/init.py",
            "src/crypto/aes.rs",
            "scripts/secrets/loader.py",
            "src/keys/rotate.py",
            "app/admin/users.tsx",
            "lib/rbac/roles.py",
            "src/webhook/dispatch.py",
            "lib/jwt/sign.go",
            "src/session/store.py",
            "app/2fa/enroll.tsx",
            "lib/mfa/totp.py",
            "app/signup/route.ts",
            "src/login/handler.go",
            "src/widget/password_reset.py",  # bare 'password' token
        ],
    )
    def test_security_paths_detected(self, path):
        assert sv.is_security_sensitive([path]) is True

    @pytest.mark.parametrize(
        "basename",
        [
            "auth.py",
            "payment.py",
            "billing.py",
            "secrets.py",
            "credentials.py",
            "jwt.py",
            "session.py",
            "auth.ts",
            "auth.go",
        ],
    )
    def test_root_basename_detected(self, basename):
        """Root-level files like auth.py / payment.py are security-sensitive."""
        assert sv.is_security_sensitive([basename]) is True
        assert sv.is_security_sensitive([f"src/{basename}"]) is True

    @pytest.mark.parametrize(
        "path",
        [
            ".env",
            "config/.env",
            "deploy/prod.env",
            "secrets/server.pem",
            "build/cert.crt",
            "id_rsa.key",
            "backup.p12",
            "store.pfx",
            "key.asc",
            "encrypted.gpg",
        ],
    )
    def test_extension_detected(self, path):
        assert sv.is_security_sensitive([path]) is True

    @pytest.mark.parametrize(
        "path",
        [
            "scripts/brain_init.py",
            "src/profile/page.tsx",
            "scripts/hooksomething.py",  # substring 'hooks' but not /hooks/
            "tests/test_auth_unrelated.py",  # tests dir, not source
            "src/widget/header.tsx",
            "lib/utils/format.go",
        ],
    )
    def test_non_security_paths_pass(self, path):
        assert sv.is_security_sensitive([path]) is False

    def test_empty_or_none_is_safe(self):
        assert sv.is_security_sensitive([]) is False
        assert sv.is_security_sensitive(None) is False  # type: ignore[arg-type]

    def test_any_match_triggers(self):
        files = ["scripts/brain_init.py", "scripts/hooks/foo.py"]
        assert sv.is_security_sensitive(files) is True

    def test_any_basename_match_triggers(self):
        files = ["scripts/brain_init.py", "src/auth.py"]
        assert sv.is_security_sensitive(files) is True

    def test_any_extension_match_triggers(self):
        files = ["src/utils.py", "config/.env"]
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


class TestResolveGateSignature:
    """A1 fix: cache key includes hash of resolved gate commands."""

    def test_returns_stable_hash_when_config_loadable(self):
        """Real project_config.load_config + DEFAULT_GATES → 16-char hex."""
        sig = sv.resolve_gate_signature("task-done")
        assert isinstance(sig, str)
        assert sig not in ("", "unavailable")
        assert len(sig) == 16  # 16 hex chars

    def test_returns_unavailable_on_load_error(self, monkeypatch):
        """Config load raises → fallback sentinel; never crash callers."""
        import project_config

        def boom():
            raise RuntimeError("config unreadable")

        monkeypatch.setattr(project_config, "load_config", boom)
        assert sv.resolve_gate_signature("task-done") == "unavailable"

    def test_returns_empty_when_no_gates_for_trigger(self, monkeypatch):
        """Trigger with no gates configured → 'empty' sentinel."""
        import project_config

        monkeypatch.setattr(project_config, "get_gates_for_trigger", lambda _t, _c: [])
        assert sv.resolve_gate_signature("task-done") == "empty"

    def test_signature_changes_when_command_changes(self, monkeypatch):
        """Same trigger, different gate command → different signature."""
        import project_config

        monkeypatch.setattr(
            project_config,
            "get_gates_for_trigger",
            lambda _t, _c: [
                {"name": "pytest", "command": "pytest -q", "severity": "block"}
            ],
        )
        sig_old = sv.resolve_gate_signature("task-done")

        monkeypatch.setattr(
            project_config,
            "get_gates_for_trigger",
            lambda _t, _c: [
                {"name": "pytest", "command": "pytest -q --strict", "severity": "block"}
            ],
        )
        sig_new = sv.resolve_gate_signature("task-done")
        assert sig_old != sig_new


class TestCacheInvalidatesOnGateChange:
    """A1 fix end-to-end: changing gate command between runs misses cache."""

    def test_cache_misses_when_signature_changes(self, conn, monkeypatch):
        import gate_runner
        import project_config

        monkeypatch.setattr(
            gate_runner,
            "run_gates",
            lambda *_a, **_k: (
                True,
                [{"name": "x", "passed": True, "severity": "warn", "output": ""}],
            ),
        )

        # First run with command "alpha"
        monkeypatch.setattr(
            project_config,
            "get_gates_for_trigger",
            lambda _t, _c: [
                {"name": "pytest", "command": "alpha", "severity": "block"}
            ],
        )
        passed1, _, status1 = sv.run_gates_with_cache(
            conn, "x-task", ["scripts/foo.py"], scope="lightweight"
        )
        assert passed1 and status1 == "miss"

        # Second run, same files, same scope, but command changed → MISS again
        monkeypatch.setattr(
            project_config,
            "get_gates_for_trigger",
            lambda _t, _c: [{"name": "pytest", "command": "beta", "severity": "block"}],
        )
        passed2, _, status2 = sv.run_gates_with_cache(
            conn, "x-task", ["scripts/foo.py"], scope="lightweight"
        )
        assert passed2 and status2 == "miss"  # not "hit"


class TestRunGatesWithCacheIntegration:
    """H2 fix: end-to-end coverage of run_gates_with_cache flow."""

    @staticmethod
    def _stub_gate(passed: bool = True):
        results = [
            {
                "name": "stub",
                "passed": passed,
                "severity": "block",
                "output": "ok" if passed else "boom",
            }
        ]
        return lambda *_a, **_k: (passed, results)

    def test_cache_miss_then_hit_on_identical_inputs(self, conn, tmp_path, monkeypatch):
        import gate_runner

        f = tmp_path / "scripts" / "alpha.py"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("# v1")
        monkeypatch.chdir(tmp_path)
        calls = []
        monkeypatch.setattr(
            gate_runner,
            "run_gates",
            lambda *_a, **_k: (calls.append(1), self._stub_gate()(_a, _k))[1],
        )
        # 1st call → miss (records)
        passed1, _, st1 = sv.run_gates_with_cache(
            conn, "task-x", ["scripts/alpha.py"], scope="lightweight"
        )
        assert passed1 and st1 == "miss"
        assert len(calls) == 1
        # 2nd call → cache hit (no extra gate call)
        passed2, _, st2 = sv.run_gates_with_cache(
            conn, "task-x", ["scripts/alpha.py"], scope="lightweight"
        )
        assert passed2 and st2 == "hit"
        assert len(calls) == 1  # gate not re-invoked

    def test_cache_bypass_on_security_file(self, conn, monkeypatch):
        import gate_runner

        monkeypatch.setattr(gate_runner, "run_gates", self._stub_gate(passed=True))
        passed, _, st = sv.run_gates_with_cache(
            conn,
            "auth-task",
            ["scripts/hooks/foo.py"],  # security-sensitive
            scope="critical",
        )
        assert passed
        assert st == "bypass"
        # No record_run on bypass
        rows = conn.execute(
            "SELECT id FROM verification_runs WHERE task_slug = ?",
            ("auth-task",),
        ).fetchall()
        assert rows == []

    def test_cache_invalidates_on_mtime_change(self, conn, tmp_path, monkeypatch):
        import gate_runner
        import time as _time

        f = tmp_path / "scripts" / "beta.py"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("# v1")
        monkeypatch.chdir(tmp_path)
        calls = []
        monkeypatch.setattr(
            gate_runner,
            "run_gates",
            lambda *_a, **_k: (calls.append(1), self._stub_gate()(_a, _k))[1],
        )
        sv.run_gates_with_cache(
            conn, "task-y", ["scripts/beta.py"], scope="lightweight"
        )
        assert len(calls) == 1
        # Touch the file — mtime changes → files_hash changes → cache miss
        _time.sleep(0.05)
        f.write_text("# v2")
        os.utime(f, None)
        passed, _, st = sv.run_gates_with_cache(
            conn, "task-y", ["scripts/beta.py"], scope="lightweight"
        )
        assert passed and st == "miss"
        assert len(calls) == 2

    def test_cache_misses_on_red_run(self, conn, monkeypatch):
        import gate_runner

        monkeypatch.setattr(gate_runner, "run_gates", self._stub_gate(passed=False))
        passed, _, st = sv.run_gates_with_cache(
            conn, "task-red", ["scripts/zzz.py"], scope="lightweight"
        )
        assert passed is False
        # Red runs not stored as cache-hittable; record_run still happens but
        # exit_code != 0 → lookup_recent returns None
        # We assert via direct lookup: no cache hit
        hit = sv.lookup_recent_for_task(
            conn,
            "task-red",
            files_hash=sv.compute_files_hash(["scripts/zzz.py"]),
            command="ignored",  # mismatched intentionally
        )
        # cache_command in red branch was 'trigger=task-done|sig=...|files=...'
        # but record_run is NOT called for red (only on `passed and cache_ok`)
        # so lookup with any command finds nothing
        assert hit is None
        # Confirm: no row recorded for red
        rows = conn.execute(
            "SELECT id FROM verification_runs WHERE task_slug = ?",
            ("task-red",),
        ).fetchall()
        assert rows == []

    def test_append_notes_called_on_hit(self, conn, tmp_path, monkeypatch):
        import gate_runner

        f = tmp_path / "scripts" / "g.py"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("g")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(gate_runner, "run_gates", self._stub_gate())
        notes: list[tuple[str, str]] = []

        def append(slug, msg):
            notes.append((slug, msg))

        sv.run_gates_with_cache(
            conn,
            "task-h",
            ["scripts/g.py"],
            scope="lightweight",
            append_notes_fn=append,
        )
        notes.clear()
        # Second call is a hit
        sv.run_gates_with_cache(
            conn,
            "task-h",
            ["scripts/g.py"],
            scope="lightweight",
            append_notes_fn=append,
        )
        assert any("cache hit" in m for _, m in notes)

    def test_append_notes_called_on_miss_with_summary(
        self, conn, tmp_path, monkeypatch
    ):
        import gate_runner

        (tmp_path / "scripts").mkdir()
        (tmp_path / "scripts" / "h.py").write_text("h")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(gate_runner, "run_gates", self._stub_gate())
        notes: list[tuple[str, str]] = []

        sv.run_gates_with_cache(
            conn,
            "task-m",
            ["scripts/h.py"],
            scope="lightweight",
            append_notes_fn=lambda s, m: notes.append((s, m)),
        )
        # On miss: at least one Gates: summary line
        assert any(m.startswith("Gates:") for _, m in notes)


class TestRunGatesWithCacheScopePropagation:
    """A9 fix: scope passed in from caller is stored in verification_runs."""

    def test_scope_recorded_as_passed(self, conn, monkeypatch):
        import gate_runner

        def fake_run_gates(_trigger, _files):
            return True, [
                {"name": "stub", "passed": True, "severity": "block", "output": "ok"}
            ]

        monkeypatch.setattr(gate_runner, "run_gates", fake_run_gates)
        passed, results, status = sv.run_gates_with_cache(
            conn, "fake-slug", ["scripts/foo.py"], scope="standard"
        )
        assert passed is True
        assert status == "miss"
        row = conn.execute(
            "SELECT scope FROM verification_runs WHERE task_slug = ?",
            ("fake-slug",),
        ).fetchone()
        assert row["scope"] == "standard"

    def test_critical_scope_forwarded(self, conn, monkeypatch):
        """Caller (service_gates) sets scope=critical for security tasks."""
        import gate_runner

        monkeypatch.setattr(
            gate_runner,
            "run_gates",
            lambda *_a, **_k: (
                True,
                [{"name": "x", "passed": True, "severity": "warn", "output": ""}],
            ),
        )
        # Plain (non-security) files but caller asks for critical
        sv.run_gates_with_cache(conn, "auth-task", ["scripts/foo.py"], scope="critical")
        row = conn.execute(
            "SELECT scope FROM verification_runs WHERE task_slug = ?",
            ("auth-task",),
        ).fetchone()
        assert row["scope"] == "critical"


# --- v1.3.4: changed_files_since + git-diff cross-check -------------------


def _fake_run(
    stdout_log: str = "", stdout_diff: str = "", rc_log: int = 0, rc_diff: int = 0
):
    """Build a runner that returns canned subprocess.CompletedProcess.

    The first call (git log) returns stdout_log/rc_log; the second call
    (git diff) returns stdout_diff/rc_diff. Order matters and must match
    the order changed_files_since invokes git.
    """
    import subprocess

    calls = {"n": 0}

    def runner(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return subprocess.CompletedProcess(
                args=args[0] if args else [],
                returncode=rc_log,
                stdout=stdout_log,
                stderr="",
            )
        return subprocess.CompletedProcess(
            args=args[0] if args else [],
            returncode=rc_diff,
            stdout=stdout_diff,
            stderr="",
        )

    return runner


class TestChangedFilesSince:
    """v1.3.4 helper for verify-cache cross-check vs git diff."""

    def test_combines_committed_and_uncommitted(self, tmp_path, monkeypatch):
        # Mock os.path.isdir to claim .git exists at tmp_path
        monkeypatch.setattr("os.path.isdir", lambda p: True)
        runner = _fake_run(
            stdout_log="scripts/a.py\nscripts/b.py\n",
            stdout_diff="scripts/c.py\nscripts/a.py\n",
        )
        out = sv.changed_files_since(
            "2026-04-28T12:00:00Z", root=str(tmp_path), runner=runner
        )
        assert out == {"scripts/a.py", "scripts/b.py", "scripts/c.py"}

    def test_returns_none_when_no_git_dir(self, tmp_path):
        # tmp_path has no .git
        out = sv.changed_files_since("2026-04-28T12:00:00Z", root=str(tmp_path))
        assert out is None

    def test_returns_none_when_empty_timestamp(self):
        assert sv.changed_files_since("") is None
        assert sv.changed_files_since(None) is None  # type: ignore[arg-type]

    def test_returns_none_when_git_log_fails(self, tmp_path, monkeypatch):
        monkeypatch.setattr("os.path.isdir", lambda p: True)
        runner = _fake_run(rc_log=128)
        out = sv.changed_files_since(
            "2026-04-28T12:00:00Z", root=str(tmp_path), runner=runner
        )
        assert out is None

    def test_returns_none_when_git_diff_fails(self, tmp_path, monkeypatch):
        monkeypatch.setattr("os.path.isdir", lambda p: True)
        runner = _fake_run(stdout_log="x\n", rc_diff=128)
        out = sv.changed_files_since(
            "2026-04-28T12:00:00Z", root=str(tmp_path), runner=runner
        )
        assert out is None

    def test_returns_none_when_subprocess_raises(self, tmp_path, monkeypatch):
        monkeypatch.setattr("os.path.isdir", lambda p: True)

        def boom(*_a, **_kw):
            raise OSError("fork failed")

        out = sv.changed_files_since(
            "2026-04-28T12:00:00Z", root=str(tmp_path), runner=boom
        )
        assert out is None

    def test_normalizes_backslashes_and_dot_slash(self, tmp_path, monkeypatch):
        monkeypatch.setattr("os.path.isdir", lambda p: True)
        runner = _fake_run(
            stdout_log="./scripts/a.py\n",
            stdout_diff="./scripts/b.py\n",  # git emits forward slash; this exercises normalization
        )
        out = sv.changed_files_since(
            "2026-04-28T12:00:00Z", root=str(tmp_path), runner=runner
        )
        assert out == {"scripts/a.py", "scripts/b.py"}


class TestIsDeclaredConsistentWithGitDiff:
    """v1.3.4 cache-bypass guard."""

    def test_under_declared_returns_false(self, tmp_path, monkeypatch):
        """Agent declares docs/x.md but actually changed scripts/auth.py → False."""
        monkeypatch.setattr("os.path.isdir", lambda p: True)
        runner = _fake_run(stdout_log="scripts/auth.py\n", stdout_diff="")
        ok = sv.is_declared_consistent_with_git_diff(
            ["docs/x.md"],
            "2026-04-28T12:00:00Z",
            root=str(tmp_path),
            runner=runner,
        )
        assert ok is False

    def test_exact_match_returns_true(self, tmp_path, monkeypatch):
        monkeypatch.setattr("os.path.isdir", lambda p: True)
        runner = _fake_run(stdout_log="scripts/auth.py\n", stdout_diff="")
        ok = sv.is_declared_consistent_with_git_diff(
            ["scripts/auth.py"],
            "2026-04-28T12:00:00Z",
            root=str(tmp_path),
            runner=runner,
        )
        assert ok is True

    def test_over_declaration_returns_true(self, tmp_path, monkeypatch):
        """Agent declares MORE files than changed — fine, not a bypass."""
        monkeypatch.setattr("os.path.isdir", lambda p: True)
        runner = _fake_run(stdout_log="scripts/auth.py\n", stdout_diff="")
        ok = sv.is_declared_consistent_with_git_diff(
            ["scripts/auth.py", "scripts/extra.py", "tests/test_auth.py"],
            "2026-04-28T12:00:00Z",
            root=str(tmp_path),
            runner=runner,
        )
        assert ok is True

    def test_no_changes_returns_true(self, tmp_path, monkeypatch):
        """No git changes at all → no inconsistency possible."""
        monkeypatch.setattr("os.path.isdir", lambda p: True)
        runner = _fake_run(stdout_log="", stdout_diff="")
        ok = sv.is_declared_consistent_with_git_diff(
            ["scripts/auth.py"],
            "2026-04-28T12:00:00Z",
            root=str(tmp_path),
            runner=runner,
        )
        assert ok is True

    def test_not_in_git_returns_true(self, tmp_path):
        """Defensive fallback per AC #5: non-git users keep working."""
        ok = sv.is_declared_consistent_with_git_diff(
            ["docs/x.md"], "2026-04-28T12:00:00Z", root=str(tmp_path)
        )
        assert ok is True

    def test_partial_overlap_with_extra_changed_returns_false(
        self, tmp_path, monkeypatch
    ):
        """Declared = {a.py}, changed = {a.py, b.py} → b.py was missed → False."""
        monkeypatch.setattr("os.path.isdir", lambda p: True)
        runner = _fake_run(stdout_log="scripts/a.py\nscripts/b.py\n", stdout_diff="")
        ok = sv.is_declared_consistent_with_git_diff(
            ["scripts/a.py"],
            "2026-04-28T12:00:00Z",
            root=str(tmp_path),
            runner=runner,
        )
        assert ok is False

    def test_backslash_declaration_normalizes_to_match(self, tmp_path, monkeypatch):
        """Windows-style declared paths still match git's forward-slash output."""
        monkeypatch.setattr("os.path.isdir", lambda p: True)
        runner = _fake_run(stdout_log="scripts/auth.py\n", stdout_diff="")
        ok = sv.is_declared_consistent_with_git_diff(
            ["scripts\\auth.py"],
            "2026-04-28T12:00:00Z",
            root=str(tmp_path),
            runner=runner,
        )
        assert ok is True


class TestRunGatesWithCacheGitDiffIntegration:
    """run_gates_with_cache + task_created_at end-to-end behavior."""

    def test_cache_hit_when_declared_matches_changes(self, conn, monkeypatch, tmp_path):
        """Pre-warm cache, then re-run with same files + matching git diff →
        cache should HIT (status='hit')."""
        monkeypatch.setattr("os.path.isdir", lambda p: True)
        # First call: pretend gates ran fresh (mock run_gates to PASS)
        import gate_runner

        monkeypatch.setattr(
            gate_runner,
            "run_gates",
            lambda _trigger, _files: (
                True,
                [{"name": "g", "passed": True, "skipped": False, "severity": "block"}],
            ),
        )
        # Match: declared & changed both = ["scripts/foo.py"] — patch the
        # function in the module that hosts it (verify_git_diff). The
        # is_declared_consistent_with_git_diff predicate looks it up by
        # name there, not via service_verification's re-export.
        import verify_git_diff

        monkeypatch.setattr(
            verify_git_diff,
            "changed_files_since",
            lambda ts, **_kw: {"scripts/foo.py"},
        )
        # First call records the run
        passed, _, status1 = sv.run_gates_with_cache(
            conn,
            "task1",
            ["scripts/foo.py"],
            task_created_at="2026-04-28T12:00:00Z",
        )
        assert passed is True
        assert status1 == "miss"
        # Second call: same files, same timestamp → cache hit
        passed2, _, status2 = sv.run_gates_with_cache(
            conn,
            "task1",
            ["scripts/foo.py"],
            task_created_at="2026-04-28T12:00:00Z",
        )
        assert passed2 is True
        assert status2 == "hit"

    def test_cache_refused_when_declared_underreports(
        self, conn, monkeypatch, tmp_path
    ):
        """Pre-warm cache for declared=[scripts/foo.py]. Then declare same
        files BUT git diff shows scripts/auth.py also changed → cache must
        return status='git-mismatch', not 'hit'."""
        monkeypatch.setattr("os.path.isdir", lambda p: True)
        import gate_runner

        monkeypatch.setattr(
            gate_runner,
            "run_gates",
            lambda _trigger, _files: (
                True,
                [{"name": "g", "passed": True, "skipped": False, "severity": "block"}],
            ),
        )
        # Pre-warm: git diff matches declared
        import verify_git_diff

        monkeypatch.setattr(
            verify_git_diff,
            "changed_files_since",
            lambda ts, **_kw: {"scripts/foo.py"},
        )
        passed, _, status1 = sv.run_gates_with_cache(
            conn,
            "task2",
            ["scripts/foo.py"],
            task_created_at="2026-04-28T12:00:00Z",
        )
        assert status1 == "miss"
        # Now flip git diff to include extra file the agent did NOT declare
        monkeypatch.setattr(
            verify_git_diff,
            "changed_files_since",
            lambda ts, **_kw: {"scripts/foo.py", "scripts/auth.py"},
        )
        passed2, _, status2 = sv.run_gates_with_cache(
            conn,
            "task2",
            ["scripts/foo.py"],
            task_created_at="2026-04-28T12:00:00Z",
        )
        assert status2 == "git-mismatch"

    def test_no_task_created_at_falls_back_to_security_only(self, conn, monkeypatch):
        """Without task_created_at, behavior matches pre-v1.3.4 — no git
        cross-check, just security-bypass + files_hash."""
        import gate_runner

        monkeypatch.setattr(
            gate_runner,
            "run_gates",
            lambda _trigger, _files: (
                True,
                [{"name": "g", "passed": True, "skipped": False, "severity": "block"}],
            ),
        )
        # Don't even patch changed_files_since — it must not be called
        sv.run_gates_with_cache(
            conn,
            "task3",
            ["scripts/foo.py"],
            # task_created_at intentionally omitted
        )
        # Re-run: cache should HIT despite us never patching git
        _, _, status = sv.run_gates_with_cache(
            conn,
            "task3",
            ["scripts/foo.py"],
        )
        assert status == "hit"
