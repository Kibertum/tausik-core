#!/usr/bin/env python3
"""PreToolUse hook: block git push without an explicit, single-use ticket.

The agent should use /ship or /commit, which (after user "y" confirmation)
run `tausik push-ok && git push`. `tausik push-ok` writes a 60-second TTL
ticket at `.tausik/.push_ticket.json`, bound to the current HEAD SHA and
branch. This hook consumes the ticket on a valid match and allows the push;
otherwise it blocks.

Why a ticket file instead of an env flag — Claude Code, Cursor and Qwen Code
all run PreToolUse hooks in the harness process, not the Bash subprocess.
Inline `VAR=val git push` env never reaches the hook, so the historical
TAUSIK_ALLOW_PUSH path was broken in every IDE. A file-based ticket works
identically across all of them.

Single-use + short TTL + bound-to-HEAD reduce the accidental-push risk
window. Determined agents can still call `tausik push-ok` themselves; the
ticket is a discipline rail, not a malicious-agent firewall — that role
belongs to `bash_firewall.py` (force-push to main) and IDE permissions.

Env knobs:
- TAUSIK_SKIP_PUSH_HOOK=1 — debug bypass (CI / local debugging only).
- TAUSIK_PUSH_TICKET_PATH — override ticket file location (tests).

Exit codes: 0 = allow, 2 = block.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_GIT_PUSH_RE = re.compile(
    r"(?:^|[\s;&|()`])(?:[/\w.\\-]*[/\\])?git(?:\s+-c\s+\S+)*\s+push\b",
    re.IGNORECASE,
)

TICKET_FILENAME = ".push_ticket.json"
SCHEMA_VERSION = 1


def _find_tausik_dir() -> Path | None:
    """Walk up from CWD looking for a .tausik directory."""
    cur = Path.cwd().resolve()
    for parent in (cur, *cur.parents):
        candidate = parent / ".tausik"
        if candidate.is_dir():
            return candidate
    return None


def _ticket_path() -> Path | None:
    override = os.environ.get("TAUSIK_PUSH_TICKET_PATH")
    if override:
        return Path(override)
    tdir = _find_tausik_dir()
    if tdir is None:
        return None
    return tdir / TICKET_FILENAME


def _git_head_sha() -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            timeout=3,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return None
    return out.decode("utf-8", "replace").strip()


def _consume_ticket() -> tuple[bool, str]:
    """Return (allow, reason). On allow, the ticket file has been deleted."""
    path = _ticket_path()
    if path is None:
        return False, "no .tausik directory found — run `tausik init` first"
    if not path.exists():
        return False, "no push ticket — run `tausik push-ok` first to authorize"
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as e:
        return False, f"cannot read push ticket: {e}"
    try:
        ticket = json.loads(raw)
    except json.JSONDecodeError:
        return False, "push ticket is malformed JSON — re-run `tausik push-ok`"
    if not isinstance(ticket, dict):
        return False, "push ticket has unexpected shape"
    if ticket.get("schema_version") != SCHEMA_VERSION:
        return (
            False,
            f"push ticket schema_version != {SCHEMA_VERSION} — re-run `tausik push-ok`",
        )
    expires_str = ticket.get("expires_at", "")
    try:
        expires = datetime.fromisoformat(expires_str)
    except (TypeError, ValueError):
        return False, "push ticket expires_at is not a valid ISO datetime"
    now = datetime.now(timezone.utc)
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if now >= expires:
        try:
            path.unlink()
        except OSError:
            pass
        return False, "push ticket expired — re-run `tausik push-ok`"
    head = _git_head_sha()
    ticket_sha = ticket.get("commit_sha", "")
    if head and ticket_sha and ticket_sha != head:
        return False, (
            f"push ticket SHA mismatch (HEAD {head[:8]}, ticket {ticket_sha[:8]}) "
            "— re-run `tausik push-ok` after committing"
        )
    try:
        path.unlink()
    except OSError as e:
        return False, f"cannot consume push ticket: {e}"
    return True, "ok"


def main() -> int:
    if os.environ.get("TAUSIK_SKIP_PUSH_HOOK") == "1":
        return 0

    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    command = data.get("tool_input", {}).get("command", "")
    if not command:
        return 0
    if not _GIT_PUSH_RE.search(command):
        return 0

    allow, reason = _consume_ticket()
    if allow:
        return 0

    print(
        "BLOCKED: git push requires a TAUSIK push ticket.\n"
        f"Reason: {reason}\n"
        "Use /ship (review + gates + push) or /commit (commit + push). "
        "Both skills run `tausik push-ok && git push` after your 'y' "
        "confirmation. The ticket is single-use, expires in 60 seconds, "
        "and is bound to the current commit SHA.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
