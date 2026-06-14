"""Signed receipt emission for verify runs.

v15-receipt-emit-on-verify: every recorded verification_run with a task
slug gets a canonical receipt (crypto_receipt) signed with the project
key (crypto_sign) and stored in `verification_runs.receipt_json` as a
tausik-signed/v1 envelope. The verify flow itself must never fail because
of receipt problems — a missing key degrades to "no-key", everything else
to "error", both logged and reported, never raised.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import subprocess
from typing import Any

_log = logging.getLogger("tausik.receipt")

# Emission outcome markers, also printed by the verify CLI.
STATUS_SIGNED = "signed"
STATUS_NO_KEY = "no-key"
STATUS_ERROR = "error"


def current_git_sha(cwd: str | None = None) -> str | None:
    """HEAD sha for receipt binding; None outside a repo / on git failure."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,  # MCP-reachable (verify): never read the JSON-RPC stdin pipe
            timeout=5,
            cwd=cwd,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return None
    return out.decode("ascii", "replace").strip() or None


def emit_signed_receipt(
    conn: sqlite3.Connection,
    run_id: int,
    *,
    task_slug: str,
    scope: str,
    gate_results: list[dict[str, Any]],
    passed: bool,
    files_hash: str,
    project_dir: str = ".",
) -> tuple[str, str | None]:
    """Build + sign + persist a receipt for an existing verification_run row.

    Returns (status, key_fingerprint). status is one of STATUS_SIGNED /
    STATUS_NO_KEY / STATUS_ERROR; never raises — verify must stay usable
    on projects without a key (graceful degradation per AC).
    """
    import crypto_keys

    try:
        public = crypto_keys.load_public(project_dir)
    except crypto_keys.KeyError_:
        return STATUS_NO_KEY, None
    fp = crypto_keys.fingerprint(public)

    try:
        from crypto_receipt import build_receipt
        from crypto_sign import sign_receipt

        row = conn.execute(
            "SELECT ran_at FROM verification_runs WHERE id = ?", (run_id,)
        ).fetchone()
        if row is None:
            _log.warning("receipt emit: verification_run #%s not found", run_id)
            return STATUS_ERROR, fp
        ran_at = row[0] if not isinstance(row, dict) else row["ran_at"]

        # A receipt attests gates that actually RAN — a skipped gate carries
        # passed=True for the verdict but proves nothing, so it stays out.
        ran_gates = [g for g in gate_results if not g.get("skipped")]
        receipt = build_receipt(
            task_slug=task_slug,
            git_sha=current_git_sha(project_dir),
            scope=scope,
            gates=ran_gates,
            passed=passed,
            ran_at=str(ran_at),
            files_hash=files_hash,
            key_fingerprint=fp,
        )
        envelope = sign_receipt(project_dir, receipt)
        conn.execute(
            "UPDATE verification_runs SET receipt_json = ? WHERE id = ?",
            (json.dumps(envelope, ensure_ascii=True, sort_keys=True), run_id),
        )
        conn.commit()
    except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
        _log.warning("receipt emit failed for run #%s", run_id, exc_info=True)
        return STATUS_ERROR, fp
    return STATUS_SIGNED, fp


def load_receipt(
    conn: sqlite3.Connection,
    *,
    run_id: int | None = None,
    task_slug: str | None = None,
) -> dict[str, Any] | None:
    """Latest stored receipt envelope, by run id or by task slug.

    Returns {"run_id", "ran_at", "envelope"} or None when nothing matches.
    Corrupt JSON returns None (and logs) — readers never crash on bad rows.
    """
    if run_id is not None:
        row = conn.execute(
            "SELECT id, ran_at, receipt_json FROM verification_runs "
            "WHERE id = ? AND receipt_json IS NOT NULL",
            (run_id,),
        ).fetchone()
    elif task_slug:
        row = conn.execute(
            "SELECT id, ran_at, receipt_json FROM verification_runs "
            "WHERE task_slug = ? AND receipt_json IS NOT NULL "
            "ORDER BY id DESC LIMIT 1",
            (task_slug,),
        ).fetchone()
    else:
        return None
    if row is None:
        return None
    rid, ran_at, raw = row[0], row[1], row[2]
    try:
        envelope = json.loads(raw)
    except (TypeError, ValueError):
        _log.warning("receipt load: corrupt receipt_json on run #%s", rid)
        return None
    if not isinstance(envelope, dict):
        return None
    return {"run_id": int(rid), "ran_at": ran_at, "envelope": envelope}
