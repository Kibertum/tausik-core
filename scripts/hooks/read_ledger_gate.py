#!/usr/bin/env python3
"""PreToolUse hook for Read: refuse a re-read of a file that has not changed.

The mechanism and every number behind it live in `read_ledger`. This file is the
harness edge: read the payload, ask, answer, count. It denies through the same
route `memory_pretool_block` and `git_push_gate` use — exit code 2 with the
reason on stderr.

OFF BY DEFAULT (`read_ledger.enabled` in .tausik/config.json). When off it does
exactly nothing: no ledger file is created, no fingerprint is taken, no counter
moves. That is asserted by a test rather than promised here.

THE DENY NAMES ITS OWN ESCAPE. An agent that believes the content has left its
context must be able to say so and proceed; a refusal with no way past it turns a
saving into a wall. The message carries the override.
"""

from __future__ import annotations

import json
import os
import sys

# Own directory FIRST: the siblings below are imported by bare name, and
# scripts/hooks reaches sys.path only when this file is RUN as a script.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from _common import force_utf8_io  # noqa: E402
from read_ledger import (  # noqa: E402
    decide,
    fingerprint,
    is_enabled,
    load_ledger,
    save_ledger,
    window_calls,
)

#: Environment escape, named in the deny message. Deliberately an env var and not
#: a config key: it is for one call the agent believes it must make, not for a
#: standing preference.
OVERRIDE_ENV = "TAUSIK_READ_LEDGER_OVERRIDE"


def _payload() -> dict:
    try:
        raw = sys.stdin.read()
    except (OSError, ValueError):
        return {}
    if not raw or not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _session_id(project_dir: str):
    """Current session id, or None. None still works: the ledger simply resets."""
    db = os.path.join(project_dir, ".tausik", "tausik.db")
    if not os.path.exists(db):
        return None
    try:
        import sqlite3
        from pathlib import Path

        conn = sqlite3.connect(Path(db).absolute().as_uri() + "?mode=ro", uri=True, timeout=2)
        try:
            row = conn.execute(
                "SELECT id FROM sessions WHERE ended_at IS NULL ORDER BY id DESC LIMIT 1"
            ).fetchone()
            return int(row[0]) if row else None
        finally:
            conn.close()
    except Exception:  # noqa: BLE001 — a hook may not die on an unreadable DB
        return None


def main() -> int:
    force_utf8_io()
    if os.environ.get("TAUSIK_SKIP_HOOKS"):
        return 0
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    if not is_enabled(project_dir):
        return 0

    payload = _payload()
    if payload.get("tool_name") != "Read":
        return 0
    args = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    path = args.get("file_path")
    if not isinstance(path, str) or not path:
        return 0
    # A partial read asks for a slice, not the file. Denying it would refuse
    # something that was never in the context to begin with.
    if args.get("offset") is not None or args.get("limit") is not None:
        return 0

    key = os.path.abspath(path).replace("\\", "/").lower()
    ledger = load_ledger(project_dir, _session_id(project_dir))
    ledger["calls"] = int(ledger.get("calls", 0)) + 1
    now = fingerprint(path)
    deny, reason = decide(ledger, key, now, window_calls(project_dir))

    if deny and not os.environ.get(OVERRIDE_ENV):
        ledger.setdefault("saved_reads", 0)
        ledger["saved_reads"] = int(ledger["saved_reads"]) + 1
        save_ledger(project_dir, ledger)
        print(
            f"BLOCKED: {path} was already read in this session and is {reason}. "
            "Its content is already in your context — scroll back rather than "
            f"paying for it again. If it is NOT in your context any more (a "
            f"compaction dropped it), set {OVERRIDE_ENV}=1 for that one call and "
            "say why.",
            file=sys.stderr,
        )
        return 2

    if now is not None:
        record = dict(now)
        record["call_no"] = ledger["calls"]
        ledger.setdefault("files", {})[key] = record
    save_ledger(project_dir, ledger)
    return 0


if __name__ == "__main__":
    sys.exit(main())
