"""Tests for scripts/verify_receipt_check.py — QG-2 receipt validation.

Covers AC of v15-receipt-check-on-done: valid receipt passes, tampered
payload/signature blocks, slug/ran_at binding mismatch blocks, NULL
receipt and missing key degrade gracefully (close allowed).
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import crypto_keys  # noqa: E402
import crypto_sign  # noqa: E402
import service_verification as sv  # noqa: E402
from verify_receipt_check import check_receipt_for_hit  # noqa: E402

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
    declared_scope_status TEXT, undeclared_files TEXT
);
"""

_GATES = [{"name": "pytest", "passed": True, "severity": "block"}]


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(_DDL)
    yield c
    c.close()


@pytest.fixture
def keyed_project(tmp_path):
    crypto_keys.init_keys(str(tmp_path))
    return str(tmp_path)


def _record(conn, project_dir, slug="task-a"):
    return sv.record_run(
        conn,
        task_slug=slug,
        scope="standard",
        command="trigger=verify|sig=x|files=",
        exit_code=0,
        summary="ok",
        files_hash="h" * 64,
        gate_results=_GATES,
        project_dir=project_dir,
    )


def _rewrite_envelope(conn, run_id, mutate):
    row = conn.execute(
        "SELECT receipt_json FROM verification_runs WHERE id = ?", (run_id,)
    ).fetchone()
    env = json.loads(row["receipt_json"])
    mutate(env)
    conn.execute(
        "UPDATE verification_runs SET receipt_json = ? WHERE id = ?",
        (json.dumps(env), run_id),
    )
    conn.commit()


class TestValid:
    def test_valid_receipt_allows_close(self, conn, keyed_project):
        run_id = _record(conn, keyed_project)
        ok, note = check_receipt_for_hit(conn, run_id, "task-a", keyed_project)
        assert ok is True
        assert "VALID" in note

    def test_git_sha_drift_warns_but_allows(self, conn, keyed_project, monkeypatch):
        run_id = _record(conn, keyed_project)

        def resign_with_sha(env):
            env["receipt"]["git_sha"] = "f" * 40
            env.update(crypto_sign.sign_receipt(keyed_project, env["receipt"]))

        _rewrite_envelope(conn, run_id, resign_with_sha)
        import verify_receipt_emit as vre

        monkeypatch.setattr(vre, "current_git_sha", lambda *_a, **_k: "a" * 40)
        ok, note = check_receipt_for_hit(conn, run_id, "task-a", keyed_project)
        assert ok is True
        assert "drift" in note


class TestTamperBlocks:
    def test_tampered_payload_blocks(self, conn, keyed_project):
        run_id = _record(conn, keyed_project)
        _rewrite_envelope(conn, run_id, lambda e: e["receipt"].update(passed=False))
        ok, note = check_receipt_for_hit(conn, run_id, "task-a", keyed_project)
        assert ok is False
        assert "INVALID" in note

    def test_corrupt_json_blocks(self, conn, keyed_project):
        run_id = _record(conn, keyed_project)
        conn.execute("UPDATE verification_runs SET receipt_json = '{nope' WHERE id = ?", (run_id,))
        conn.commit()
        ok, note = check_receipt_for_hit(conn, run_id, "task-a", keyed_project)
        assert ok is False
        assert "corrupt" in note

    def test_slug_mismatch_blocks(self, conn, keyed_project):
        run_id = _record(conn, keyed_project, slug="task-a")
        ok, note = check_receipt_for_hit(conn, run_id, "task-other", keyed_project)
        assert ok is False
        assert "substituted" in note

    def test_ran_at_mismatch_blocks(self, conn, keyed_project):
        run_id = _record(conn, keyed_project)

        def resign_with_ran_at(env):
            env["receipt"]["ran_at"] = "1999-01-01T00:00:00Z"
            env.update(crypto_sign.sign_receipt(keyed_project, env["receipt"]))

        _rewrite_envelope(conn, run_id, resign_with_ran_at)
        ok, note = check_receipt_for_hit(conn, run_id, "task-a", keyed_project)
        assert ok is False
        assert "substituted" in note


class TestGracefulDegradation:
    def test_null_receipt_allows_close(self, conn, tmp_path):
        run_id = _record(conn, str(tmp_path / "keyless"))  # no key -> no receipt
        ok, note = check_receipt_for_hit(conn, run_id, "task-a", str(tmp_path / "keyless"))
        assert ok is True
        assert "none" in note

    def test_receipt_without_public_key_allows_close(self, conn, keyed_project, tmp_path):
        run_id = _record(conn, keyed_project)
        bare = tmp_path / "bare"
        bare.mkdir()
        ok, note = check_receipt_for_hit(conn, run_id, "task-a", str(bare))
        assert ok is True
        assert "no public key" in note

    def test_missing_run_row_allows_close(self, conn, keyed_project):
        ok, note = check_receipt_for_hit(conn, 424242, "task-a", keyed_project)
        assert ok is True
        assert "skipped" in note
