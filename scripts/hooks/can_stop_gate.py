#!/usr/bin/env python3
"""Trusted Stop adapter: fail closed until deterministic can_stop allows termination."""

from __future__ import annotations

import argparse
import json
import os
import sys


def _block(reason: str) -> int:
    print(json.dumps({"decision": "block", "reason": reason}))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--trusted-host")
    args, _ = parser.parse_known_args()
    if os.environ.get("TAUSIK_SKIP_HOOKS") or args.trusted_host not in {"codex", "cursor"}:
        return 0
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            return _block("TAUSIK can_stop refused: malformed trusted Stop payload")
        thread_id = payload.get("session_id") or payload.get("thread_id")
        turn_id = payload.get("turn_id") or payload.get("request_id")
        if not isinstance(thread_id, str) or not thread_id:
            return _block("TAUSIK can_stop refused: trusted thread identity is missing")
        if not isinstance(turn_id, str) or not turn_id:
            return _block("TAUSIK can_stop refused: exact trusted turn identity is missing")
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from can_stop import decide_persisted_stop
        from project_backend import SQLiteBackend
        from project_service import ProjectService

        backend = SQLiteBackend(os.path.join(project_dir, ".tausik", "tausik.db"))
        try:
            decision = decide_persisted_stop(
                ProjectService(backend),
                host_instance=args.trusted_host,
                thread_id=thread_id,
                turn_id=turn_id,
            )
        finally:
            backend.close()
        if decision.code.startswith("ALLOW_"):
            return 0
        return _block(f"TAUSIK can_stop {decision.code}: {decision.action}")
    except BaseException as exc:  # noqa: BLE001 - even process-level adapter errors fail closed
        return _block(f"TAUSIK can_stop failed closed: {type(exc).__name__}")


if __name__ == "__main__":
    sys.exit(main())
