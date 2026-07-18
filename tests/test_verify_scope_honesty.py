"""Tests for l26-verify-git-diff-wire — the receipt must be honest about its scope.

The divergence between declared `relevant_files` and what git says actually
changed was detected since v1.3.4 but discarded: it gated the verify cache and
nothing else, so `record_run` still signed a receipt for the narrow declared
scope. These tests pin the three properties that fix requires:

  AC #2 — divergence is persisted on the run row AND inside the signed receipt.
  AC #3 — an honest closure that edits docs/CHANGELOG beyond relevant_files is
          NOT blocked (this is ~100% of real closures — Decision #138/#139).
  AC #4 — a dishonest closure is readable from the receipt itself.
  AC #5 — no git / empty relevant_files / no task_created_at / git failure all
          degrade to "unknown", never to "complete".
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import types

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import crypto_keys  # noqa: E402
import crypto_sign  # noqa: E402
import gate_runner  # noqa: E402
import service_verification as sv  # noqa: E402
import verify_scope_honesty as vsh  # noqa: E402

# Mirrors the verification_runs baseline in backend_schema.py. Hand-rolled here
# like its sibling test modules; the drift risk that creates is tracked in
# `test-ddl-drift-verification-runs`.
_DDL = """
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
    declared_scope_status TEXT,
    undeclared_files TEXT
);
"""

_GATES = [{"name": "pytest", "passed": True, "severity": "block"}]

# The actual undeclared set from both closures of session #112. Both were
# honest: CHANGELOG/README/docs/generated-constants/IDE-mirror edits made
# beyond the declared relevant_files. Any rule that blocks on this set is a
# rule that would be disabled on first contact.
SESSION_112_UNDECLARED = [
    "CHANGELOG.md",
    "CHANGELOG.ru.md",
    "README.md",
    "README.ru.md",
    "docs/_generated/constants.json",
    "docs/en/config-trust-tiers.md",
    "docs/ru/config-trust-tiers.md",
    ".claude/scripts/session_metrics.py",
    ".cursor/scripts/session_metrics.py",
    "scripts/hooks/session_metrics.py",
    "scripts/hooks/token_metrics.py",
    "scripts/hooks/token_rows.py",
]


def _git_root(tmp_path):
    (tmp_path / ".git").mkdir()
    return str(tmp_path)


def _runner(log_files=(), diff_files=(), returncode=0):
    """Fake `subprocess.run` for git: first call is `log`, second is `diff`."""

    def run(cmd, **_kw):
        payload = log_files if "log" in cmd else diff_files
        return types.SimpleNamespace(returncode=returncode, stdout="\n".join(payload))

    return run


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(_DDL)
    yield c
    c.close()


class TestTriState:
    """`unknown` and `complete` are different claims and must never collapse."""

    def test_missing_task_created_at_is_unknown(self, tmp_path):
        d = vsh.describe_declared_scope(["a.py"], None, root=_git_root(tmp_path))
        assert d["status"] == vsh.STATUS_UNKNOWN
        assert d["undeclared"] == []

    def test_empty_declared_files_is_unknown(self, tmp_path):
        d = vsh.describe_declared_scope([], "2026-01-01T00:00:00Z", root=_git_root(tmp_path))
        assert d["status"] == vsh.STATUS_UNKNOWN

    def test_declared_list_of_blanks_is_unknown(self, tmp_path):
        d = vsh.describe_declared_scope(
            ["", "  "], "2026-01-01T00:00:00Z", root=_git_root(tmp_path)
        )
        assert d["status"] == vsh.STATUS_UNKNOWN

    def test_not_a_git_repo_is_unknown(self, tmp_path):
        # No .git directory — changed_files_since returns None.
        d = vsh.describe_declared_scope(["a.py"], "2026-01-01T00:00:00Z", root=str(tmp_path))
        assert d["status"] == vsh.STATUS_UNKNOWN
        assert d["reason"] == "git unavailable"

    def test_git_failure_is_unknown_not_complete(self, tmp_path):
        """A failing git call must not be read as 'declared scope was fine'."""
        d = vsh.describe_declared_scope(
            ["a.py"],
            "2026-01-01T00:00:00Z",
            root=_git_root(tmp_path),
            runner=_runner(["b.py"], ["c.py"], returncode=1),
        )
        assert d["status"] == vsh.STATUS_UNKNOWN

    def test_exact_match_is_complete(self, tmp_path):
        d = vsh.describe_declared_scope(
            ["a.py", "b.py"],
            "2026-01-01T00:00:00Z",
            root=_git_root(tmp_path),
            runner=_runner(["a.py"], ["b.py"]),
        )
        assert d["status"] == vsh.STATUS_COMPLETE
        assert d["undeclared_count"] == 0

    def test_over_declaration_is_complete(self, tmp_path):
        d = vsh.describe_declared_scope(
            ["a.py", "b.py", "extra.py"],
            "2026-01-01T00:00:00Z",
            root=_git_root(tmp_path),
            runner=_runner(["a.py"], ["b.py"]),
        )
        assert d["status"] == vsh.STATUS_COMPLETE

    def test_no_git_visible_changes_is_complete(self, tmp_path):
        d = vsh.describe_declared_scope(
            ["a.py"],
            "2026-01-01T00:00:00Z",
            root=_git_root(tmp_path),
            runner=_runner([], []),
        )
        assert d["status"] == vsh.STATUS_COMPLETE

    def test_under_declaration_lists_missing_files_sorted(self, tmp_path):
        d = vsh.describe_declared_scope(
            ["a.py"],
            "2026-01-01T00:00:00Z",
            root=_git_root(tmp_path),
            runner=_runner(["z.py", "m.py"], ["a.py"]),
        )
        assert d["status"] == vsh.STATUS_UNDER_DECLARED
        assert d["undeclared"] == ["m.py", "z.py"]
        assert d["undeclared_count"] == 2

    def test_backslash_declared_paths_normalize(self, tmp_path):
        """Windows-style declared paths must match git's forward slashes."""
        d = vsh.describe_declared_scope(
            [r"scripts\a.py"],
            "2026-01-01T00:00:00Z",
            root=_git_root(tmp_path),
            runner=_runner(["scripts/a.py"], []),
        )
        assert d["status"] == vsh.STATUS_COMPLETE

    def test_listing_is_capped_but_count_is_not(self, tmp_path):
        many = [f"f{i:03d}.py" for i in range(vsh.MAX_LISTED_UNDECLARED + 25)]
        d = vsh.describe_declared_scope(
            ["declared.py"],
            "2026-01-01T00:00:00Z",
            root=_git_root(tmp_path),
            runner=_runner(many, []),
        )
        assert len(d["undeclared"]) == vsh.MAX_LISTED_UNDECLARED
        assert d["undeclared_count"] == len(many)


class TestSecurityBlock:
    """Divergence never blocks; undeclared security-sensitive files do."""

    def test_complete_scope_does_not_block(self):
        assert vsh.security_block_reason({"status": "complete", "security_undeclared": []}) is None

    def test_none_description_does_not_block(self):
        assert vsh.security_block_reason(None) is None

    def test_session_112_honest_closure_does_not_block(self, tmp_path):
        """AC #3 — the measured real-world case. This must stay non-blocking."""
        d = vsh.describe_declared_scope(
            ["scripts/config_trust.py", "tests/test_config_trust.py"],
            "2026-01-01T00:00:00Z",
            root=_git_root(tmp_path),
            runner=_runner(SESSION_112_UNDECLARED, []),
        )
        assert d["status"] == vsh.STATUS_UNDER_DECLARED  # divergence IS detected
        assert d["security_undeclared"] == []  # ...and does NOT block
        assert vsh.security_block_reason(d) is None

    def test_undeclared_auth_file_blocks(self, tmp_path):
        """AC #4/(в) — the one case where the scoped gates would verify nothing."""
        d = vsh.describe_declared_scope(
            ["README.md"],
            "2026-01-01T00:00:00Z",
            root=_git_root(tmp_path),
            runner=_runner(["src/auth.py", "README.md"], []),
        )
        reason = vsh.security_block_reason(d)
        assert reason is not None
        assert "src/auth.py" in reason
        assert "relevant_files" in reason

    def test_undeclared_credential_extension_blocks(self, tmp_path):
        d = vsh.describe_declared_scope(
            ["README.md"],
            "2026-01-01T00:00:00Z",
            root=_git_root(tmp_path),
            runner=_runner([".env"], []),
        )
        assert vsh.security_block_reason(d) is not None

    def test_declared_security_file_does_not_block(self, tmp_path):
        """Declaring the auth file is the whole point — that must pass."""
        d = vsh.describe_declared_scope(
            ["src/auth.py"],
            "2026-01-01T00:00:00Z",
            root=_git_root(tmp_path),
            runner=_runner(["src/auth.py"], []),
        )
        assert vsh.security_block_reason(d) is None


class TestRecordRunPersistsScope:
    """AC #2 — the divergence stops being transient."""

    def _record(self, conn, project_dir, desc):
        return sv.record_run(
            conn,
            task_slug="task-a",
            scope="standard",
            command="trigger=verify|sig=x|files=README.md",
            exit_code=0,
            summary="ok",
            files_hash="h" * 64,
            gate_results=_GATES,
            project_dir=project_dir,
            scope_description=desc,
        )

    def test_status_and_undeclared_persisted_on_row(self, conn, tmp_path):
        desc = {
            "status": vsh.STATUS_UNDER_DECLARED,
            "undeclared": ["scripts/x.py"],
            "undeclared_count": 1,
        }
        rid = self._record(conn, str(tmp_path), desc)
        row = conn.execute(
            "SELECT declared_scope_status, undeclared_files FROM verification_runs WHERE id=?",
            (rid,),
        ).fetchone()
        assert row["declared_scope_status"] == vsh.STATUS_UNDER_DECLARED
        assert json.loads(row["undeclared_files"]) == ["scripts/x.py"]

    def test_omitted_description_records_unknown_not_complete(self, conn, tmp_path):
        """AC #5 — saying nothing must not buy a clean bill of health."""
        rid = self._record(conn, str(tmp_path), None)
        row = conn.execute(
            "SELECT declared_scope_status FROM verification_runs WHERE id=?", (rid,)
        ).fetchone()
        assert row["declared_scope_status"] == vsh.STATUS_UNKNOWN

    def test_receipt_carries_divergence_and_stays_verifiable(self, conn, tmp_path):
        """AC #2 + AC #4 — read the divergence back out of the SIGNED receipt."""
        crypto_keys.init_keys(str(tmp_path))
        desc = {
            "status": vsh.STATUS_UNDER_DECLARED,
            "undeclared": ["scripts/service_gates.py"],
            "undeclared_count": 1,
        }
        rid = self._record(conn, str(tmp_path), desc)
        raw = conn.execute(
            "SELECT receipt_json FROM verification_runs WHERE id=?", (rid,)
        ).fetchone()["receipt_json"]
        envelope = json.loads(raw)
        receipt = envelope["receipt"]

        # The proof itself now says its coverage was narrower than the change.
        assert receipt["declared_scope_status"] == vsh.STATUS_UNDER_DECLARED
        assert receipt["undeclared_files"] == ["scripts/service_gates.py"]
        assert receipt["undeclared_count"] == 1
        # ...and adding those fields did not break the signature.
        assert crypto_sign.verify_receipt(envelope, project_dir=str(tmp_path)) is True

    def test_receipt_states_unknown_when_not_measured(self, conn, tmp_path):
        crypto_keys.init_keys(str(tmp_path))
        rid = self._record(conn, str(tmp_path), None)
        raw = conn.execute(
            "SELECT receipt_json FROM verification_runs WHERE id=?", (rid,)
        ).fetchone()["receipt_json"]
        receipt = json.loads(raw)["receipt"]
        assert receipt["declared_scope_status"] == vsh.STATUS_UNKNOWN
        assert receipt["undeclared_files"] == []


class TestRunGatesWithCacheIntegration:
    """End-to-end through the path `task done` actually takes."""

    @pytest.fixture(autouse=True)
    def _stub_gates(self, monkeypatch):
        monkeypatch.setattr(
            gate_runner,
            "run_gates",
            lambda *a, **k: (True, [{"name": "pytest", "passed": True, "skipped": False}]),
        )

    def test_honest_under_declaration_is_not_blocked(self, conn, monkeypatch):
        """AC #3 — reproduces both session #112 closures end-to-end."""
        monkeypatch.setattr(
            sv,
            "describe_declared_scope",
            lambda files, created_at, **kw: {
                "status": vsh.STATUS_UNDER_DECLARED,
                "reason": "test",
                "undeclared": SESSION_112_UNDECLARED,
                "undeclared_count": len(SESSION_112_UNDECLARED),
                "security_undeclared": [],
            },
        )
        notes: list[str] = []
        passed, results, status = sv.run_gates_with_cache(
            conn,
            "task-a",
            ["scripts/config_trust.py"],
            append_notes_fn=lambda _s, m: notes.append(m),
            task_created_at="2026-01-01T00:00:00Z",
        )
        assert passed is True
        assert status == "git-mismatch"  # detected...
        assert any("WARN" in n for n in notes)  # ...reported...
        # ...and the recorded row tells the truth about its own coverage.
        row = conn.execute(
            "SELECT declared_scope_status, undeclared_files FROM verification_runs "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert row["declared_scope_status"] == vsh.STATUS_UNDER_DECLARED
        assert "CHANGELOG.md" in json.loads(row["undeclared_files"])

    def test_undeclared_security_file_blocks_before_gates_run(self, conn, monkeypatch):
        """AC #4 — the half of the v1.3.4 hole that refusing the cache left open."""
        monkeypatch.setattr(
            sv,
            "describe_declared_scope",
            lambda files, created_at, **kw: {
                "status": vsh.STATUS_UNDER_DECLARED,
                "reason": "test",
                "undeclared": ["src/auth.py"],
                "undeclared_count": 1,
                "security_undeclared": ["src/auth.py"],
            },
        )
        ran: list[bool] = []
        monkeypatch.setattr(
            gate_runner, "run_gates", lambda *a, **k: (ran.append(True), (True, []))[1]
        )
        notes: list[str] = []
        passed, results, status = sv.run_gates_with_cache(
            conn,
            "task-a",
            ["README.md"],
            append_notes_fn=lambda _s, m: notes.append(m),
            task_created_at="2026-01-01T00:00:00Z",
        )
        assert passed is False
        assert status == "scope-security-mismatch"
        assert results[0]["name"] == "scope-declaration"
        assert results[0]["severity"] == "block"
        assert ran == []  # fail fast: no point running gates on a scope we reject
        assert any("src/auth.py" in n for n in notes)

    def test_unknown_scope_still_records_a_row(self, conn, monkeypatch):
        """AC #5 — degradation is explicit, not a missing row or a silent 'complete'."""
        monkeypatch.setattr(
            sv,
            "describe_declared_scope",
            lambda files, created_at, **kw: {
                "status": vsh.STATUS_UNKNOWN,
                "reason": "git unavailable",
                "undeclared": [],
                "undeclared_count": 0,
                "security_undeclared": [],
            },
        )
        passed, _results, status = sv.run_gates_with_cache(
            conn, "task-a", ["a.py"], task_created_at="2026-01-01T00:00:00Z"
        )
        assert passed is True
        assert status in {"miss", "hit"}
        row = conn.execute(
            "SELECT declared_scope_status FROM verification_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert row["declared_scope_status"] == vsh.STATUS_UNKNOWN
