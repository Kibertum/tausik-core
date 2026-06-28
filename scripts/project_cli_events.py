"""TAUSIK CLI — `events verify` / `events anchor` / `events seal`.

v16r-audit-hashchain. Kept out of project_cli_ops.py (400-line gate).
project_dir is os.getcwd() to match `tausik key` resolution.
"""

from __future__ import annotations

import json
import os
from typing import Any

import crypto_keys
import events_chain


def cmd_events(svc: Any, args: Any) -> None:
    """`events` — list (default) or verify/anchor/seal subcommands."""
    sub = getattr(args, "events_cmd", None)
    dispatch = {
        "verify": cmd_events_verify,
        "anchor": cmd_events_anchor,
        "seal": cmd_events_seal,
    }
    if sub in dispatch:
        dispatch[sub](svc, args)
        return
    events = svc.events_list(entity_type=args.entity, entity_id=args.entity_id, n=args.limit)
    if not events:
        print("No events found.")
        return
    for ev in events:
        actor = f" by {ev['actor']}" if ev.get("actor") else ""
        print(f"[{ev['created_at']}] {ev['entity_type']}/{ev['entity_id']}: {ev['action']}{actor}")
        if ev.get("details"):
            print(f"  {ev['details']}")


def _recomputed_head_map(svc: Any) -> dict[int, str]:
    """id -> recomputed entry_hash, from genesis over all events."""
    rows = svc.be.events_all_ordered()
    links = events_chain.compute_links(rows)
    return {r["id"]: eh for r, (_prev, eh) in zip(rows, links)}


def cmd_events_seal(svc: Any, _args: Any) -> None:
    res = svc.be.events_seal()
    if res["head_id"] is None:
        print("Nothing to seal — event log is empty.")
        return
    print(f"Sealed {res['sealed']} event(s); chain head #{res['head_id']} ({res['total']} total).")


def cmd_events_verify(svc: Any, _args: Any) -> None:
    verdict = svc.be.events_verify(seal=True)
    status = verdict["status"]
    if verdict.get("sealed_now"):
        print(f"Sealed {verdict['sealed_now']} pending event(s).")
    if status == "ok":
        print(f"Chain OK — {verdict['length']} event(s) verified.")
    elif status == "empty":
        print("Chain empty — no events.")
    elif status == "unchained":
        print(f"Chain UNCHAINED — {verdict['reason']}")
    else:  # broken
        print(f"Chain BROKEN at event #{verdict['first_break']}: {verdict['reason']}")

    # Anchor cross-check: a signed head detects a fully-recomputed (rebased)
    # chain that the hash-walk alone would accept.
    anchor = svc.be.events_anchor_latest()
    if not anchor:
        print("No ed25519 anchor recorded (run `events anchor`).")
        return
    project_dir = os.getcwd()
    try:
        envelope = json.loads(anchor["envelope_json"])
    except (ValueError, TypeError):
        print("Anchor MALFORMED — stored envelope is not valid JSON.")
        return
    try:
        sig_ok = events_chain.verify_anchor(envelope, project_dir=project_dir)
    except events_chain.ChainError as e:
        print(f"Anchor signature UNVERIFIABLE — {e}")
        return
    recomputed = _recomputed_head_map(svc).get(anchor["head_id"])
    head_ok = recomputed == anchor["head_hash"]
    if sig_ok and head_ok:
        print(
            f"Anchor OK — head #{anchor['head_id']} signed & consistent ({anchor['created_at']})."
        )
    elif not sig_ok:
        print("Anchor INVALID — signature does not match payload.")
    else:
        print(
            f"Anchor MISMATCH — head #{anchor['head_id']} was re-hashed since "
            "anchoring (pre-anchor history tampered)."
        )


def cmd_events_anchor(svc: Any, _args: Any) -> None:
    res = svc.be.events_seal()
    if res["head_id"] is None:
        print("Nothing to anchor — event log is empty.")
        return
    project_dir = os.getcwd()
    try:
        envelope = events_chain.sign_head(
            project_dir,
            head_id=res["head_id"],
            head_hash=res["head_hash"],
            event_count=res["total"],
        )
    except crypto_keys.KeyError_:
        print(
            "No project key — anchoring skipped (chain verification still "
            "works). Run `tausik key init` to enable ed25519 anchors."
        )
        return
    except events_chain.ChainError as e:
        print(f"Anchoring failed — {e}")
        return
    svc.be.events_anchor_insert(
        head_id=res["head_id"],
        head_hash=res["head_hash"],
        event_count=res["total"],
        envelope_json=json.dumps(envelope, separators=(",", ":"), sort_keys=True),
    )
    fp = envelope["signature"]["key_fingerprint"]
    print(f"Anchored head #{res['head_id']} ({res['total']} events) with key {fp}.")
