"""The verification descriptor, not command text, controls both proof doors."""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import crypto_keys
from backend_schema_gate_runs import GATE_RUNS_SQL
from conftest import canonical_ddl
from verify_cache import _build_cache_command, resolve_gate_signature
from verify_files_hash import compute_files_hash
from verify_handle_check import check_handle
from verify_recent_lookup import lookup_recent_for_task
from verify_run_descriptor import (
    NON_REPLAYABLE,
    NOT_PRESENTABLE,
    VerificationRunDescriptor,
)
from verify_run_record import record_run


@pytest.fixture
def proof(tmp_path, monkeypatch):
    crypto_keys.init_keys(str(tmp_path))
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "scripts" / "demo.py"
    source.parent.mkdir()
    source.write_text("x = 1\n", encoding="utf-8")
    files = ["scripts/demo.py"]
    descriptor = VerificationRunDescriptor.create(
        trigger="verify",
        files=files,
        gate_signature=resolve_gate_signature("verify"),
        replayable=True,
        presentable_once=True,
    )
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(canonical_ddl("verification_runs"))
    conn.executescript(GATE_RUNS_SQL)
    handle_out: dict = {}
    run_id = record_run(
        conn,
        task_slug="demo",
        scope="standard",
        command=_build_cache_command("verify", files),
        exit_code=0,
        summary="pytest=PASS",
        files_hash=compute_files_hash(files),
        gate_results=[{"name": "pytest", "passed": True, "skipped": False, "severity": "block"}],
        trigger="verify",
        descriptor=descriptor,
        handle_out=handle_out,
        project_dir=str(tmp_path),
    )
    yield conn, run_id, handle_out["handle"], descriptor, compute_files_hash(files), str(tmp_path)
    conn.close()


def _doors(proof):
    conn, _run_id, handle, descriptor, files_hash, root = proof
    cache = lookup_recent_for_task(conn, "demo", files_hash=files_hash, descriptor=descriptor)
    presentation = check_handle(conn, handle, task_slug="demo", project_dir=root)
    return cache is not None, presentation.ok


@pytest.mark.parametrize(
    ("column", "value", "cache_ok", "presentation_ok"),
    [
        ("replay_policy", NON_REPLAYABLE, False, True),
        ("presentation_policy", NOT_PRESENTABLE, True, False),
    ],
)
def test_policy_fields_open_only_their_own_door(proof, column, value, cache_ok, presentation_ok):
    conn, run_id, *_ = proof
    conn.execute(f"UPDATE verification_runs SET {column}=? WHERE id=?", (value, run_id))
    conn.commit()
    assert _doors(proof) == (cache_ok, presentation_ok)


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("run_trigger", "task-done"),
        ("run_files_json", '["scripts/other.py"]'),
        ("gate_signature", "0" * 16),
    ],
)
def test_identity_mutations_close_both_doors(proof, column, value):
    conn, run_id, *_ = proof
    conn.execute(f"UPDATE verification_runs SET {column}=? WHERE id=?", (value, run_id))
    conn.commit()
    assert _doors(proof) == (False, False)


@pytest.mark.parametrize(
    ("column", "value", "expected"),
    [
        ("command", "arbitrary audit text", (True, True)),
        ("scope", "critical", (True, False)),
    ],
)
def test_display_text_and_signed_scope_have_separate_authority(proof, column, value, expected):
    conn, run_id, *_ = proof
    conn.execute(f"UPDATE verification_runs SET {column}=? WHERE id=?", (value, run_id))
    conn.commit()
    assert _doors(proof) == expected


def test_command_only_legacy_row_gets_no_rights(proof):
    conn, run_id, handle, descriptor, files_hash, root = proof
    conn.execute(
        "UPDATE verification_runs SET run_trigger=NULL, run_files_json=NULL, "
        "gate_signature=NULL, replay_policy=NULL, presentation_policy=NULL WHERE id=?",
        (run_id,),
    )
    conn.commit()
    assert (
        lookup_recent_for_task(conn, "demo", files_hash=files_hash, descriptor=descriptor) is None
    )
    verdict = check_handle(conn, handle, task_slug="demo", project_dir=root)
    assert not verdict.ok and "legacy or corrupt row" in verdict.reason


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("run_trigger", None),
        ("run_files_json", "not-json"),
        ("gate_signature", None),
        ("replay_policy", None),
        ("presentation_policy", None),
    ],
)
def test_incomplete_descriptor_closes_both_doors(proof, column, value):
    conn, run_id, *_ = proof
    conn.execute(f"UPDATE verification_runs SET {column}=? WHERE id=?", (value, run_id))
    conn.commit()
    assert _doors(proof) == (False, False)
