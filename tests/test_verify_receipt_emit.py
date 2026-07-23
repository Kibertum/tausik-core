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
from backend_schema_gate_runs import GATE_RUNS_SQL  # noqa: E402
import crypto_sign  # noqa: E402
import service_verification as sv  # noqa: E402
import verify_receipt_emit as vre  # noqa: E402
import verify_run_record as vrr  # noqa: E402

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
);;
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
    c.executescript(GATE_RUNS_SQL)  # canonical DDL — record_run also writes gate_runs
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


# --- s129-review-fixes: signing must resolve the project root, not the CWD ----


def _file_db(root_dir):
    """A file-based connection whose DB sits at <root>/.tausik/tausik.db — the
    real production layout, so `_project_dir_from_conn` can derive <root>."""
    tausik = os.path.join(str(root_dir), ".tausik")
    os.makedirs(tausik, exist_ok=True)
    c = sqlite3.connect(os.path.join(tausik, "tausik.db"))
    c.row_factory = sqlite3.Row
    c.executescript(_DDL)
    c.executescript(GATE_RUNS_SQL)
    return c


class TestProjectDirDerivedFromConn:
    """The HIGH from this session's adversarial review: `_project_has_key`
    looked at the DB-derived root while emission looked at CWD, so a `verify`
    run from a subdirectory produced a false 'signing failed' warning. Signing
    must resolve the same root the key check does — from the DB file."""

    def test_derives_root_from_db_file(self, tmp_path):
        c = _file_db(tmp_path)
        try:
            assert vrr._project_dir_from_conn(c) == str(tmp_path)
        finally:
            c.close()

    def test_inmemory_conn_falls_back_to_dot(self, conn):
        # AC4: an in-memory / pathless DB cannot name a root → best-effort '.'.
        assert vrr._project_dir_from_conn(conn) == "."

    def test_record_run_without_project_dir_uses_derived_root(self, tmp_path, monkeypatch):
        # AC1/AC2 wiring: with no explicit project_dir, record_run must hand
        # emit_signed_receipt the DB-derived ROOT — not '.' (the old CWD default
        # that caused the false warning from a subdirectory).
        captured = {}

        def fake_emit(conn, run_id, **kwargs):
            captured["project_dir"] = kwargs.get("project_dir")
            return (vre.STATUS_NO_KEY, None)

        monkeypatch.setattr(vre, "emit_signed_receipt", fake_emit)
        c = _file_db(tmp_path)
        try:
            sv.record_run(
                c,
                task_slug="task-a",
                scope="standard",
                command="c",
                exit_code=0,
                summary="ok",
                files_hash="h" * 64,
                gate_results=_GATES,
                # project_dir intentionally omitted → derivation must kick in
            )
        finally:
            c.close()
        assert captured["project_dir"] == str(tmp_path)

    def test_signs_against_db_root_end_to_end(self, tmp_path):
        # The observable win: keys live at the DB's root; a record_run with NO
        # project_dir signs a receipt that verifies against that root — proving
        # signing no longer depends on the process CWD.
        crypto_keys.init_keys(str(tmp_path))
        c = _file_db(tmp_path)
        try:
            run_id = sv.record_run(
                c,
                task_slug="task-a",
                scope="standard",
                command="c",
                exit_code=0,
                summary="ok",
                files_hash="h" * 64,
                gate_results=_GATES,
            )
            row = c.execute(
                "SELECT receipt_json FROM verification_runs WHERE id = ?", (run_id,)
            ).fetchone()
            assert row["receipt_json"], "signing must produce a receipt against the DB root"
            env = json.loads(row["receipt_json"])
            assert crypto_sign.verify_receipt(env, project_dir=str(tmp_path))
        finally:
            c.close()
