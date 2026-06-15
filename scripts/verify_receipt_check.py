"""QG-2 receipt validation — tamper-evidence for proof-of-done.

v15-receipt-check-on-done: when task_done satisfies verify-first via a
cached verify run, the run's signed receipt (verification_runs.receipt_json,
tausik-signed/v1) is re-verified before the close is allowed:

  BLOCK   invalid ed25519 signature, or receipt bound to a different
          task_slug / ran_at than the cached run row (substituted receipt).
  WARN    no receipt on the row (pre-v29 or keyless project), no public
          key to verify with, or receipt git_sha differing from current
          HEAD (committing mid-task is legitimate) — close proceeds.

Graceful degradation is deliberate: projects without `tausik key init`
must keep closing tasks exactly as before.
"""

from __future__ import annotations

import logging
import sqlite3

_log = logging.getLogger("tausik.receipt")


def check_receipt_for_hit(
    conn: sqlite3.Connection,
    run_id: int,
    task_slug: str,
    project_dir: str = ".",
) -> tuple[bool, str]:
    """Validate the signed receipt of a cache-hit verify run.

    Returns (ok_to_close, note). ok_to_close=False means the caller must
    add a blocking failure; the note always carries the human-readable
    outcome for task notes. Never raises.
    """
    try:
        return _check(conn, run_id, task_slug, project_dir)
    except Exception as e:  # noqa: BLE001 — QG-2 must never crash on this path
        _log.warning("receipt check crashed for run #%s", run_id, exc_info=True)
        return True, f"receipt check skipped (internal error: {e})"


def _check(
    conn: sqlite3.Connection,
    run_id: int,
    task_slug: str,
    project_dir: str,
) -> tuple[bool, str]:
    import crypto_keys

    row = conn.execute(
        "SELECT task_slug, ran_at, receipt_json FROM verification_runs WHERE id = ?",
        (run_id,),
    ).fetchone()
    if row is None:
        return True, f"receipt: verify run #{run_id} row not found — check skipped"
    run_slug, run_ran_at, raw = row[0], row[1], row[2]

    if not raw:
        return True, (
            f"receipt: none on verify run #{run_id} (pre-v29 row or keyless "
            "project) — close allowed, `tausik key init` enables attestation"
        )

    try:
        public = crypto_keys.load_public(project_dir)
    except crypto_keys.KeyError_:
        return True, (
            f"receipt: present on run #{run_id} but no public key to verify "
            "with — close allowed (restore .tausik/keys to re-enable checks)"
        )

    import json

    try:
        envelope = json.loads(raw)
    except (TypeError, ValueError):
        return False, (
            f"receipt: corrupt receipt_json on verify run #{run_id} — "
            "cannot prove the cached green is authentic"
        )

    import crypto_sign

    if not crypto_sign.verify_receipt(envelope, public=public):
        return False, (
            f"receipt: INVALID ed25519 signature on verify run #{run_id} — "
            "the recorded verify result was modified after signing"
        )

    receipt = envelope.get("receipt") or {}
    if receipt.get("task_slug") != task_slug or receipt.get("task_slug") != run_slug:
        return False, (
            f"receipt: signed for task '{receipt.get('task_slug')}' but closing "
            f"'{task_slug}' (run #{run_id} row says '{run_slug}') — substituted receipt"
        )
    if receipt.get("ran_at") != run_ran_at:
        return False, (
            f"receipt: ran_at {receipt.get('ran_at')!r} does not match verify "
            f"run #{run_id} row ({run_ran_at!r}) — substituted receipt"
        )

    from verify_receipt_emit import current_git_sha

    head = current_git_sha(project_dir)
    if head and receipt.get("git_sha") and receipt["git_sha"] != head:
        return True, (
            f"receipt: VALID (run #{run_id}), note git_sha drift "
            f"{str(receipt['git_sha'])[:10]} -> {head[:10]} (commit since verify)"
        )
    return True, f"receipt: VALID ed25519 signature (run #{run_id})"
