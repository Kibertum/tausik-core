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
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Fallback matcher, used only when the command cannot be tokenized (unbalanced
# quotes). Token-based detection (`_command_invokes_git_push`) is the primary
# path — it does not false-positive on a 'git push' mention inside a quoted
# argument, which the substring regex did (blocking e.g. `tausik memory add
# "...git push..."`).
_GIT_PUSH_RE = re.compile(
    r"(?:^|[\s;&|()`])(?:[/\w.\\-]*[/\\])?git(?:\s+-c\s+\S+)*\s+push\b",
    re.IGNORECASE,
)

# git global options that consume the FOLLOWING token as their value; they may
# sit between `git` and the `push` subcommand (`git -c k=v push`, `git -C repo
# push`). The `--opt=value` form is self-contained (one token) and needs no
# skip. Keeping this list lets a real push be detected even with global flags,
# while the token model still ignores quoted mentions.
_GIT_VALUE_OPTS = frozenset({"-c", "-C", "--git-dir", "--work-tree", "--namespace"})


def _tokens_invoke_git_push(tokens: list[str]) -> bool:
    """True iff the token stream invokes ``git ... push`` as a command.

    shlex keeps a quoted argument as a SINGLE token, so a 'git push' mention
    inside a quoted string (``tausik task log "...git push..."``) collapses to
    one token and never matches — this is the substring-false-positive fix.
    """
    n = len(tokens)
    for i, tok in enumerate(tokens):
        if tok != "git" and os.path.basename(tok) not in ("git", "git.exe"):
            continue
        j = i + 1
        while j < n and tokens[j].startswith("-"):
            opt = tokens[j]
            j += 1
            if opt in _GIT_VALUE_OPTS:  # '--opt=value' form is self-contained
                j += 1
        if j < n and tokens[j] == "push":
            return True
    return False


def _command_invokes_git_push(command: str) -> bool:
    """Detect a genuine ``git push`` invocation, ignoring quoted mentions.

    Primary: shlex-tokenize and look for ``git ... push`` in command position.
    Fallback: if the command cannot be tokenized (unbalanced quotes raise
    ValueError), use the substring regex — conservative, since a real push must
    not slip through on a parse failure.
    """
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        return bool(_GIT_PUSH_RE.search(command))
    return _tokens_invoke_git_push(tokens)


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
    # hook-stderr-encoding-locale-dependent: this hook's messages contain
    # non-ASCII, and their readability must not depend on how it was
    # launched. Local import: hooks/ is sys.path[0] only when run as a script.
    from _common import emit_supervision_bypass, force_utf8_io

    force_utf8_io()

    if os.environ.get("TAUSIK_SKIP_PUSH_HOOK") == "1":
        emit_supervision_bypass(
            os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()), "skip_push_hook", "git_push_gate"
        )
        return 0

    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    command = data.get("tool_input", {}).get("command", "")
    if not command:
        return 0
    if not _command_invokes_git_push(command):
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
