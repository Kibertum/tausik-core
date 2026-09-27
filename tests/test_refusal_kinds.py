"""A refusal to close says which of three it is and what to do next
(refusal-does-not-separate-stale-from-failed)."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import verify_refusal_kind as k
from project_backend import SQLiteBackend
from verify_handle_rules import _no


@pytest.mark.parametrize(
    "reason,kind",
    [
        ("verify-handle: expired at 2026-09-23T10:00:00Z (run #5).", k.STALE),
        ("verify-handle: this handle was already spent at X (run #5).", k.STALE),
        ("verify-handle: nonce does not match verify run #5.", k.STALE),
        ("verify-handle: the files this receipt covers have changed since verify run #5", k.STALE),
        ("verify-handle: the gate set changed since run #5 (signature a -> b).", k.STALE),
        ("verify-handle: verify run #5 did NOT pass (exit_code=1).", k.FAILED),
        ("verify-handle: INVALID ed25519 signature on run #5", k.FAILED),
        ("verify-handle: 'x' is not a handle. Expected ...", k.NOT_FOUND),
        ("verify-handle: no verify run #9 in this project's database.", k.NOT_FOUND),
        ("verify-handle: run #5 verified task 'a', but you are closing 'b'.", k.NOT_FOUND),
    ],
)
def test_each_handle_refusal_carries_its_kind_and_next_step(reason, kind):
    verdict = _no(reason)
    assert not verdict.ok
    assert verdict.reason.startswith(kind)
    assert "next:" in verdict.reason and reason in verdict.reason


def test_a_stale_refusal_is_still_a_refusal():
    assert _no("verify-handle: expired at X (run #1).").ok is False


def test_labelling_is_idempotent():
    once = k.labelled("verify-handle: expired at X (run #1).")
    assert k.labelled(once) == once


@pytest.fixture
def be(tmp_path):
    b = SQLiteBackend(str(tmp_path / "v.db"))
    yield b
    b.close()


def _run(be, exit_code):
    be._conn.execute(
        "INSERT INTO verification_runs(task_slug, scope, command, exit_code, files_hash, ran_at) "
        "VALUES ('t', 'manual', 'pytest', ?, 'h', '2026-09-23T10:00:00Z')",
        (exit_code,),
    )
    be._conn.commit()


def test_a_close_without_a_handle_says_never_ran_red_or_stale(be):
    assert k.last_run_kind(be, "t")[0] == k.NOT_FOUND
    _run(be, 1)
    kind, why = k.last_run_kind(be, "t")
    assert kind == k.FAILED and "did not pass" in why
    _run(be, 0)
    kind, why = k.last_run_kind(be, "t")
    assert kind == k.STALE and "passed" in why
