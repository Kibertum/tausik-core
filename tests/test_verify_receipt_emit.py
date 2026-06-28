"""Tests for scripts/verify_receipt_emit.py — signed receipts on verify runs.

Covers AC of v15-receipt-emit-on-verify: emission via record_run,
persistence in verification_runs.receipt_json, tamper detection on read,
and graceful no-key degradation.
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
import verify_receipt_emit as vre  # noqa: E402

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
    receipt_json TEXT
);
"""

_GATES = [
    {"name": "pytest", "passed": True, "severity": "block"},
    {"name": "ruff", "passed": True, "severity": "warn"},
]


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


def _record(conn, project_dir, *, slug="task-a", exit_code=0, gates=_GATES):
    return sv.record_run(
        conn,
        task_slug=slug,
        scope="standard",
        command="trigger=verify|sig=x|files=",
        exit_code=exit_code,
        summary="ok",
        files_hash="h" * 64,
        duration_ms=10,
        gate_results=gates,
        project_dir=project_dir,
    )


def _stored_envelope(conn, run_id):
    row = conn.execute(
        "SELECT receipt_json FROM verification_runs WHERE id = ?", (run_id,)
    ).fetchone()
    return json.loads(row["receipt_json"]) if row["receipt_json"] else None


class TestEmission:
    def test_green_run_gets_signed_receipt(self, conn, keyed_project):
        run_id = _record(conn, keyed_project)
        env = _stored_envelope(conn, run_id)
        assert env is not None
        assert env["envelope"] == "tausik-signed/v1"
        assert env["receipt"]["task_slug"] == "task-a"
        assert env["receipt"]["passed"] is True
        assert crypto_sign.verify_receipt(env, project_dir=keyed_project)

    def test_red_run_is_attested_too(self, conn, keyed_project):
        gates = [{"name": "pytest", "passed": False, "severity": "block"}]
        run_id = _record(conn, keyed_project, exit_code=1, gates=gates)
        env = _stored_envelope(conn, run_id)
        assert env is not None
        assert env["receipt"]["passed"] is False
        assert crypto_sign.verify_receipt(env, project_dir=keyed_project)

    def test_skipped_gates_stay_out_of_receipt(self, conn, keyed_project):
        gates = _GATES + [{"name": "hadolint", "passed": True, "skipped": True}]
        run_id = _record(conn, keyed_project, gates=gates)
        env = _stored_envelope(conn, run_id)
        names = [g["name"] for g in env["receipt"]["gates"]]
        assert "hadolint" not in names
        assert crypto_sign.verify_receipt(env, project_dir=keyed_project)

    def test_receipt_binds_gates_and_fingerprint(self, conn, keyed_project):
        run_id = _record(conn, keyed_project)
        env = _stored_envelope(conn, run_id)
        names = [g["name"] for g in env["receipt"]["gates"]]
        assert names == sorted(["pytest", "ruff"])
        fp = crypto_keys.fingerprint(crypto_keys.load_public(keyed_project))
        assert env["receipt"]["key_fingerprint"] == fp
        assert env["signature"]["key_fingerprint"] == fp

    def test_receipt_ran_at_matches_db_row(self, conn, keyed_project):
        run_id = _record(conn, keyed_project)
        env = _stored_envelope(conn, run_id)
        row = conn.execute(
            "SELECT ran_at FROM verification_runs WHERE id = ?", (run_id,)
        ).fetchone()
        assert env["receipt"]["ran_at"] == row["ran_at"]

    def test_no_task_slug_no_receipt(self, conn, keyed_project):
        run_id = sv.record_run(
            conn,
            task_slug=None,
            scope="manual",
            command="c",
            exit_code=0,
            summary="ok",
            files_hash="h",
            gate_results=_GATES,
            project_dir=keyed_project,
        )
        assert _stored_envelope(conn, run_id) is None

    def test_no_gate_results_back_compat(self, conn, keyed_project):
        run_id = sv.record_run(
            conn,
            task_slug="task-b",
            scope="manual",
            command="c",
            exit_code=0,
            summary="ok",
            files_hash="h",
        )
        assert _stored_envelope(conn, run_id) is None


class TestNoKeyDegradation:
    def test_record_run_survives_missing_key(self, conn, tmp_path):
        run_id = _record(conn, str(tmp_path / "keyless"))
        assert run_id > 0
        assert _stored_envelope(conn, run_id) is None

    def test_emit_reports_no_key(self, conn, tmp_path):
        run_id = _record(conn, str(tmp_path))  # no key -> row without receipt
        status, fp = vre.emit_signed_receipt(
            conn,
            run_id,
            task_slug="task-a",
            scope="standard",
            gate_results=_GATES,
            passed=True,
            files_hash="h" * 64,
            project_dir=str(tmp_path),
        )
        assert status == vre.STATUS_NO_KEY
        assert fp is None

    def test_emit_missing_run_is_error(self, conn, keyed_project):
        status, fp = vre.emit_signed_receipt(
            conn,
            999_999,
            task_slug="task-a",
            scope="standard",
            gate_results=_GATES,
            passed=True,
            files_hash="h" * 64,
            project_dir=keyed_project,
        )
        assert status == vre.STATUS_ERROR
        assert fp is not None


class TestTamperDetection:
    def test_modified_payload_fails_verification(self, conn, keyed_project):
        run_id = _record(conn, keyed_project)
        env = _stored_envelope(conn, run_id)
        env["receipt"]["passed"] = False  # flip the verdict
        assert crypto_sign.verify_receipt(env, project_dir=keyed_project) is False

    def test_modified_signature_fails_verification(self, conn, keyed_project):
        run_id = _record(conn, keyed_project)
        env = _stored_envelope(conn, run_id)
        sig = env["signature"]["value"]
        env["signature"]["value"] = ("0" if sig[0] != "0" else "1") + sig[1:]
        assert crypto_sign.verify_receipt(env, project_dir=keyed_project) is False


class TestLoadReceipt:
    def test_load_by_task_returns_latest(self, conn, keyed_project):
        _record(conn, keyed_project)
        second = _record(conn, keyed_project)
        stored = vre.load_receipt(conn, task_slug="task-a")
        assert stored is not None and stored["run_id"] == second

    def test_load_by_run_id(self, conn, keyed_project):
        run_id = _record(conn, keyed_project)
        stored = vre.load_receipt(conn, run_id=run_id)
        assert stored is not None
        assert stored["envelope"]["receipt"]["task_slug"] == "task-a"

    def test_load_missing_returns_none(self, conn):
        assert vre.load_receipt(conn, task_slug="ghost") is None
        assert vre.load_receipt(conn, run_id=42) is None

    def test_load_without_filter_returns_none(self, conn):
        assert vre.load_receipt(conn) is None

    def test_corrupt_json_returns_none(self, conn):
        conn.execute(
            "INSERT INTO verification_runs (task_slug, scope, command, exit_code, "
            "summary, files_hash, ran_at, receipt_json) "
            "VALUES ('task-x', 'manual', 'c', 0, 'ok', 'h', '2026-01-01T00:00:00Z', '{broken')"
        )
        conn.commit()
        assert vre.load_receipt(conn, task_slug="task-x") is None
