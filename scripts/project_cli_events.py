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
        "emit-supervision": cmd_events_emit_supervision,
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


def cmd_events_emit_supervision(svc: Any, args: Any) -> None:
    """`events emit-supervision` — record a supervision bypass/degradation row.

    Cross-harness parity (l26-bypass-telemetry-opencode-parity): the OpenCode JS
    plugin runs in a Node process and cannot call the in-process Python emitter,
    so it shells out to this command. Routing through the SAME
    `hook_supervision` helper the Claude hooks use is deliberate — the row's
    contract (entity_type/action/chain-safe raw INSERT) is defined in exactly
    one place, never re-implemented in JS where it would silently diverge.

    project_dir is derived from the service's own `.tausik/` dir (the project
    THIS service speaks for), never the cwd — same read-path discipline as the
    gate toggles.
    """
    import os
    import sys

    hooks_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hooks")
    if hooks_dir not in sys.path:
        sys.path.insert(0, hooks_dir)
    from hook_supervision import emit_supervision_bypass, emit_supervision_degradation

    project_dir = os.path.dirname(svc.tausik_dir())
    if args.kind == "degradation":
        wrote = emit_supervision_degradation(
            project_dir, args.vector, args.sup_source, args.details
        )
        action = f"fail_open_{args.vector}"
    else:
        wrote = emit_supervision_bypass(project_dir, args.vector, args.sup_source, args.details)
        action = f"bypass_{args.vector}"
    # Honesty over reassurance (s128 review HIGH-1): the emitter is best-effort
    # and swallows write failures. Claiming "Recorded" on a swallowed miss makes
    # a failed telemetry write indistinguishable from a success at the one place
    # a script/human can check — the opposite of the falsifiability this exists
    # for. Report the actual outcome; exit non-zero on a miss so a caller (the
    # JS plugin, CI) can tell.
    if wrote:
        print(f"Recorded supervision event: {args.sup_source} / {action}")
    else:
        print(
            f"WARNING: supervision event NOT recorded (best-effort write failed): "
            f"{args.sup_source} / {action}",
            file=sys.stderr,
        )
        raise SystemExit(1)


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


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
