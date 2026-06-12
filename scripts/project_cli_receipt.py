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
    if cmd == "export":
        _cmd_export(svc, args)
        return
    if cmd == "verify":
        _cmd_verify_file(args)
        return
    if cmd != "show":
        print(
            "Usage: tausik receipt {show,export} [--task <slug> | --run <id>] | "
            "receipt verify <file>",
            file=sys.stderr,
        )
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


def _cmd_export(svc, args) -> None:
    """`tausik receipt export` — portable artifact for PRs / external audit."""
    import crypto_keys
    from receipt_export import build_export, default_export_path, write_export
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
            f"No signed receipt for {target} — run `tausik verify --task <slug>` "
            "first (requires a project key, `tausik key init`).",
            file=sys.stderr,
        )
        sys.exit(2)

    project_dir = os.getcwd()
    try:
        public = crypto_keys.load_public(project_dir)
    except crypto_keys.KeyError_ as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

    import crypto_sign

    envelope = stored["envelope"]
    if not crypto_sign.verify_receipt(envelope, public=public):
        print(
            f"Refusing to export run #{stored['run_id']}: signature does not "
            "verify against the current project key (tampered row or rotated "
            "key). Re-run `tausik verify --task <slug>` to record a fresh one.",
            file=sys.stderr,
        )
        sys.exit(1)

    export = build_export(envelope, public)
    if getattr(args, "stdout", False):
        print(json.dumps(export, ensure_ascii=False, indent=2, sort_keys=True))
        return
    path = getattr(args, "out", None) or default_export_path(project_dir, envelope)
    write_export(export, path)
    print(
        f"Receipt exported: {path}\n"
        f"  run:         #{stored['run_id']}\n"
        f"  fingerprint: {export['key_fingerprint']}\n"
        f"Verify anywhere: tausik receipt verify {path}"
    )


def _cmd_verify_file(args) -> None:
    """`tausik receipt verify <file>` — offline check, no DB/keystore."""
    from receipt_export import ExportError, verify_export

    try:
        with open(args.file, encoding="utf-8") as f:
            data = json.load(f)
    except OSError as e:
        print(f"Error: cannot read {args.file}: {e}", file=sys.stderr)
        sys.exit(2)
    except ValueError as e:
        print(f"Error: {args.file} is not valid JSON: {e}", file=sys.stderr)
        sys.exit(2)

    public = None
    raw_pub = getattr(args, "pub", None)
    if raw_pub:
        hexpart = raw_pub.split(":", 1)[1] if raw_pub.startswith("ed25519:") else raw_pub
        try:
            public = bytes.fromhex(hexpart)
        except ValueError:
            print("Error: --pub must be 'ed25519:<64 hex>' or raw hex.", file=sys.stderr)
            sys.exit(2)

    try:
        valid, detail = verify_export(data, public=public)
    except ExportError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)
    receipt = (data.get("envelope") or {}).get("receipt") or {}
    print(
        f"task: {receipt.get('task_slug', '?')}  passed: {receipt.get('passed')}  "
        f"ran_at: {receipt.get('ran_at', '?')}  git_sha: {str(receipt.get('git_sha') or '-')[:10]}"
    )
    if valid:
        print(f"Signature: {detail}")
    else:
        print(f"Signature: {detail}", file=sys.stderr)
        sys.exit(1)
