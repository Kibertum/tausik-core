"""CLI handler for `tausik receipt` — read + verify signed verify receipts.

v15-receipt-emit-on-verify: `tausik receipt show --task <slug>` (or
`--run <id>`) prints the latest stored tausik-signed/v1 envelope and
re-verifies its ed25519 signature against the project public key.
Exit codes: 0 valid, 1 signature INVALID, 2 not found / no key.
"""

from __future__ import annotations

import json
import os
import sys


def cmd_receipt(svc, args) -> None:
    cmd = getattr(args, "receipt_cmd", None)
    if cmd != "show":
        print("Usage: tausik receipt show [--task <slug> | --run <id>]", file=sys.stderr)
        sys.exit(2)

    from verify_receipt_emit import load_receipt

    task_slug = getattr(args, "task", None)
    run_id = getattr(args, "run", None)
    if not task_slug and run_id is None:
        print("Error: pass --task <slug> or --run <id>.", file=sys.stderr)
        sys.exit(2)

    stored = load_receipt(svc.be._conn, run_id=run_id, task_slug=task_slug)
    if stored is None:
        target = f"run #{run_id}" if run_id is not None else f"task '{task_slug}'"
        print(
            f"No signed receipt for {target}. Receipts are emitted by "
            "`tausik verify --task <slug>` when a project key exists "
            "(`tausik key init`).",
            file=sys.stderr,
        )
        sys.exit(2)

    envelope = stored["envelope"]
    if getattr(args, "json", False):
        print(json.dumps(envelope, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        receipt = envelope.get("receipt") or {}
        sig = envelope.get("signature") or {}
        gates = receipt.get("gates") or []
        gate_line = ", ".join(
            f"{g.get('name', '?')}={'PASS' if g.get('passed') else 'FAIL'}" for g in gates
        )
        print(
            f"Receipt (run #{stored['run_id']}, {receipt.get('schema', '?')}):\n"
            f"  task:        {receipt.get('task_slug', '?')}\n"
            f"  passed:      {receipt.get('passed')}\n"
            f"  scope:       {receipt.get('scope', '?')}\n"
            f"  ran_at:      {receipt.get('ran_at', '?')}\n"
            f"  git_sha:     {receipt.get('git_sha') or '-'}\n"
            f"  gates:       {gate_line or '-'}\n"
            f"  fingerprint: {sig.get('key_fingerprint', '?')}"
        )

    import crypto_sign

    try:
        valid = crypto_sign.verify_receipt(envelope, project_dir=os.getcwd())
    except crypto_sign.SignError as e:
        print(f"Signature: UNVERIFIABLE — {e}", file=sys.stderr)
        sys.exit(2)
    if valid:
        print("Signature: VALID (ed25519).")
    else:
        print("Signature: INVALID — payload or signature was modified.", file=sys.stderr)
        sys.exit(1)
