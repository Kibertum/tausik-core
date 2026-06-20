"""tausik push-ok — write a single-use push ticket consumed by git_push_gate.

Writes `.tausik/.push_ticket.json` (schema_version=1) with the current HEAD
SHA, branch, and an expires_at timestamp (default now+60s). The hook
consumes the ticket on a valid match; missing, expired, or HEAD-mismatched
tickets keep blocking. Use after the user has explicitly confirmed a push
in /commit or /ship — never preemptively.

CLI dispatch:
    cmd_push_ok(svc_unused, args) -> None  # exits with sys.exit(1) on error
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

TICKET_FILENAME = ".push_ticket.json"
SCHEMA_VERSION = 1
DEFAULT_TTL_SECONDS = 60


def _find_tausik_dir(start: Path | None = None) -> Path | None:
    cur = (start or Path.cwd()).resolve()
    for parent in (cur, *cur.parents):
        candidate = parent / ".tausik"
        if candidate.is_dir():
            return candidate
    return None


def _git(args: list[str]) -> str | None:
    try:
        out = subprocess.check_output(
            ["git"] + args,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,  # defense-in-depth: never read an inherited (MCP) stdin pipe
            timeout=3,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return None
    return out.decode("utf-8", "replace").strip()


def write_push_ticket(
    tausik_dir: Path,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    *,
    commit_sha: str | None = None,
    branch: str | None = None,
) -> Path:
    """Write a single-use ticket atomically. Returns the ticket path."""
    if commit_sha is None:
        commit_sha = _git(["rev-parse", "HEAD"]) or ""
    if branch is None:
        branch = _git(["rev-parse", "--abbrev-ref", "HEAD"]) or ""
    if branch == "HEAD":
        branch = ""  # detached
    now = datetime.now(timezone.utc)
    expires = now + timedelta(seconds=ttl_seconds)
    ticket = {
        "schema_version": SCHEMA_VERSION,
        "commit_sha": commit_sha,
        "branch": branch,
        "created_at": now.isoformat(),
        "expires_at": expires.isoformat(),
    }
    tausik_dir.mkdir(parents=True, exist_ok=True)
    path = tausik_dir / TICKET_FILENAME
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(ticket, indent=2), encoding="utf-8")
    os.replace(tmp, path)
    return path


def cmd_push_ok(_svc_unused: Any, args: Any) -> None:
    """CLI handler for `tausik push-ok`. Exits 1 on error, 0 on success."""
    raw_ttl = getattr(args, "ttl", None)
    ttl = DEFAULT_TTL_SECONDS if raw_ttl is None else raw_ttl
    if ttl <= 0:
        print("error: --ttl must be a positive number of seconds", file=sys.stderr)
        sys.exit(1)
    tausik_dir = _find_tausik_dir()
    if tausik_dir is None:
        print(
            "error: no .tausik directory found — run `tausik init` first",
            file=sys.stderr,
        )
        sys.exit(1)
    sha = _git(["rev-parse", "HEAD"])
    if not sha:
        print(
            "error: cannot determine HEAD commit (no git repo or no commits yet)",
            file=sys.stderr,
        )
        sys.exit(1)
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"]) or ""
    path = write_push_ticket(tausik_dir, ttl_seconds=ttl, commit_sha=sha, branch=branch)
    short = sha[:8]
    branch_str = branch if branch and branch != "HEAD" else "(detached)"
    print(f"push ticket written: {path.name} (commit {short}, branch {branch_str}, ttl {ttl}s)")
