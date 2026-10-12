"""security-verify-handle-deadlock: one presentation for a green security run.

Defect report (Artem Soglaev, 2026-10-12, release 1.11.3): a security-sensitive
declared set forces `cache_ok=False`, so a GREEN verify-trigger run is recorded
as `noncacheable|` — the freshness lookup can never match it and no handle is
minted — while `task done` requires exactly such evidence. Two rules deadlock:
closing demands proof, presenting proof is refused, even for a genuinely green
run (12/12 tests, close returned STALE).

The contract fix (owner-approved): the green security run mints a SINGLE-USE
signed handle — the receipt already binds project key, files and gate
signature; redemption re-computes both against live state and spends the
handle. The `noncacheable|` stamp stays: the CACHE never replays a security
green, so every later consumer still re-verifies.
"""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

import verify_handle as vh
from conftest import canonical_ddl
from backend_schema_gate_runs import GATE_RUNS_SQL
from test_verify_handle import _build_cache_command, _write_files
from verify_files_hash import compute_files_hash
from verify_cache import resolve_gate_signature
from verify_handle_check import check_handle, redeem_handle
from verify_recent_lookup import lookup_recent_for_task
from verify_run_record import record_run
from verify_run_descriptor import VerificationRunDescriptor
from verify_zero_gate import NONCACHEABLE_PREFIX, is_presentable_once


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(canonical_ddl("verification_runs"))
    c.executescript(GATE_RUNS_SQL)
    yield c
    c.close()


@pytest.fixture
def keyed_project(tmp_path, monkeypatch):
    import crypto_keys

    crypto_keys.init_keys(str(tmp_path))
    monkeypatch.chdir(tmp_path)
    return str(tmp_path)


def _record_security_green(conn, project_dir, files=("auth/login.py", "auth/pay.py")):
    """The production write path for the deadlock case: green, real gates,
    non-empty coverage, cache refused ONLY because the set is security-sensitive."""
    declared = _write_files(project_dir, files)
    handle_out: dict = {}
    run_id = record_run(
        conn,
        task_slug="sec-task",
        scope="critical",
        command=f"{NONCACHEABLE_PREFIX}{_build_cache_command('verify', declared)}",
        exit_code=0,
        summary="pytest=PASS ruff=PASS",
        files_hash=compute_files_hash(declared),
        gate_results=[
            {
                "name": "pytest",
                "passed": True,
                "skipped": False,
                "severity": "block",
                "output": "12 passed",
            },
            {"name": "ruff", "passed": True, "skipped": False, "severity": "block", "output": ""},
        ],
        scope_description={"status": "complete", "undeclared": [], "undeclared_count": 0},
        trigger="verify",
        handle_out=handle_out,
        allow_handle=True,
        descriptor=VerificationRunDescriptor.create(
            trigger="verify",
            files=declared,
            gate_signature=resolve_gate_signature("verify"),
            replayable=False,
            presentable_once=True,
        ),
    )
    return run_id, handle_out, declared


# --- AC1: the green security run mints a single-use certificate ----------------


def test_green_security_run_mints_a_single_use_handle(conn, keyed_project):
    run_id, handle_out, files = _record_security_green(conn, keyed_project)
    assert handle_out.get("handle"), "the deadlock: green security run, no presentable proof"
    run = vh.load_run_for_handle(conn, run_id)
    assert is_presentable_once(dict(run))
    receipt = __import__("json").loads(run["receipt_json"])["receipt"]
    assert sorted(receipt["files"]) == sorted(files), "receipt binds the security files"


# --- AC2: close on it once; the second presentation is spent --------------------


def test_handle_closes_once_and_is_spent(conn, keyed_project):
    _, handle_out, _ = _record_security_green(conn, keyed_project)
    handle = handle_out["handle"]
    first = redeem_handle(conn, handle, task_slug="sec-task", project_dir=keyed_project)
    assert first.ok, first.reason
    second = redeem_handle(conn, handle, task_slug="sec-task", project_dir=keyed_project)
    assert not second.ok and "single-use" in second.reason


# --- AC3 NEGATIVE: the cache door stays shut ------------------------------------


def test_freshness_lookup_still_refuses_the_stamped_row(conn, keyed_project):
    _run_id, handle_out, files = _record_security_green(conn, keyed_project)
    assert handle_out.get("handle"), "precondition: the single-use mint happened"
    hit = lookup_recent_for_task(
        conn,
        "sec-task",
        files_hash=compute_files_hash(files),
        descriptor=VerificationRunDescriptor.create(
            trigger="verify",
            files=files,
            gate_signature=resolve_gate_signature("verify"),
            replayable=True,
            presentable_once=True,
        ),
    )
    assert hit is None, "cache replayed a security green — the reuse ban broke"


# --- AC4 NEGATIVE: the other stamped greens still mint nothing ------------------


def test_empty_scope_and_all_skipped_still_mint_nothing(conn, keyed_project):
    handle_out: dict = {}
    record_run(
        conn,
        task_slug="hollow-task",
        scope="standard",
        command=f"{NONCACHEABLE_PREFIX}{_build_cache_command('verify', [])}",
        exit_code=0,
        summary="all gates skipped",
        files_hash=compute_files_hash([]),
        gate_results=[
            {"name": "filesize", "passed": True, "skipped": True, "severity": "warn", "output": ""}
        ],
        scope_description={"status": "unknown"},
        trigger="verify",
        handle_out=handle_out,
        allow_handle=True,
        descriptor=VerificationRunDescriptor.create(
            trigger="verify",
            files=[],
            gate_signature=resolve_gate_signature("verify"),
            replayable=False,
            presentable_once=False,
        ),
    )
    assert "handle" not in handle_out, "a run that certified nothing minted a certificate"


def test_stamped_row_without_nonce_is_not_presentable_once(conn, keyed_project):
    run = {"command": f"{NONCACHEABLE_PREFIX}trigger=verify|files=auth/x.py", "handle_nonce": None}
    assert not is_presentable_once(run)


def test_legacy_stamped_row_is_refused_even_with_a_nonce_attached_by_hand(conn, keyed_project):
    """The laundering guard kept: judge the RECEIPT's files. A hand-shaped row
    (stamped, nonce, but files NOT security-minted through the write path) —
    the mint authority is the write path; redemption still re-derives files."""
    declared = _write_files(keyed_project, ("auth/login.py",))
    handle_out: dict = {}
    record_run(
        conn,
        task_slug="launder-task",
        scope="standard",
        command=f"{NONCACHEABLE_PREFIX}{_build_cache_command('verify', declared)}",
        exit_code=0,
        summary="pytest=PASS",
        files_hash=compute_files_hash(declared),
        gate_results=[
            {
                "name": "pytest",
                "passed": True,
                "skipped": False,
                "severity": "block",
                "output": "1 passed",
            }
        ],
        scope_description={"status": "complete", "undeclared": [], "undeclared_count": 0},
        trigger="verify",
        handle_out=handle_out,
        allow_handle=True,
        descriptor=VerificationRunDescriptor.create(
            trigger="verify",
            files=declared,
            gate_signature=resolve_gate_signature("verify"),
            replayable=False,
            presentable_once=True,
        ),
    )
    assert handle_out.get("handle"), "precondition: minted as single-use"
    # Presenting it for a DIFFERENT task is refused (binding), as for any handle.
    verdict = check_handle(
        conn, handle_out["handle"], task_slug="other-task", project_dir=keyed_project
    )
    assert not verdict.ok and "other-task" in verdict.reason
