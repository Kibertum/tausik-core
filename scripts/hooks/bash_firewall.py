#!/usr/bin/env python3
"""PreToolUse hook: block dangerous shell commands, in every dialect.

Blocks: rm -rf /, Remove-Item -Recurse C:\\, DROP TABLE, Format-Volume,
git reset --hard, git push --force.
Exit codes: 0 = allow, 2 = block.
Receives JSON on stdin with tool_name, tool_input.

v1.3.4 (med-batch-1-hooks #1): WARN patterns now use regex with word
boundaries instead of substring match — `echo "git push --force"` and
`mygit-helper push --force` no longer false-positive. Shape mirrors
`git_push_gate.py:_GIT_PUSH_RE`: command-start anchor (line start, or
shell separator) + optional path prefix + literal subcommand.

`powershell-tool-bypasses-bash-firewall`: this file used to hold the policy, the
POSIX reader AND the verdict. It now holds only the verdict. WHAT is dangerous
is `danger_patterns`; HOW to read a line is a per-dialect scanner; WHICH dialect
a tool speaks is `shell_channel`. That last one matters most: the answer used to
be a literal `"Bash"` repeated across the gates, and when a second shell tool
appeared on the primary platform, every one of those literals kept quietly
saying "not my channel".
"""

import json
import os
import sys

# Re-exported for callers (and docs) that predate the split and still reach for
# these names at their old address.
from bash_cmd_scan import (  # noqa: F401
    _INTERPRETERS,
    _mentions_interpreter,
    _PAYLOAD,
    _split_subcommands,
    scan_target as _scan_target,
)
from danger_patterns import (  # noqa: F401
    BLOCKED_PATTERNS,
    WARN_PATTERNS_RE,
    _CMD_START,
    _git_subcmd_re,
    _RM_RE,
    wiped_root_any,
)
from shell_channel import scan_target


def main() -> int:
    # This hook's block messages now quote the offending operand and use an
    # em dash, so they are no longer pure ASCII — and a block message that
    # renders as mojibake is a block whose reason the reader has to guess.
    # Local import: hooks/ is sys.path[0] only when run as a script.
    from _common import force_utf8_io

    force_utf8_io()

    if os.environ.get("TAUSIK_SKIP_HOOKS"):
        from _common import emit_supervision_bypass

        emit_supervision_bypass(
            os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()), "skip_hooks", "bash_firewall"
        )
        return 0

    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    command = data.get("tool_input", {}).get("command", "").strip()
    if not command:
        return 0

    # Which SHELL wrote this line decides how to read it, and nothing else. On
    # win32 the agent is handed a separate `PowerShell` tool whose syntax the
    # POSIX lexer mis-reads at the first backslash: `shlex(posix=True)` treats
    # `\` as an escape, so `Remove-Item C:\` either loses its operand or raises.
    #
    # The tool -> dialect mapping is `shell_channel`'s, not a comparison written
    # out here. This line briefly WAS `== "PowerShell"`, which would have been a
    # second copy of the very list whose staleness caused the bug — found by
    # reviewing this fix rather than the code it replaced (convention #276).
    scanned = scan_target(str(data.get("tool_name") or ""), command)
    cmd_lower = scanned.lower()

    # Both dialect judges run, whichever tool sent the line: a
    # `powershell -Command "Remove-Item -Recurse C:\"` arrives through Bash and
    # a `bash -c 'rm -rf /'` through PowerShell, and each scanner joins the
    # other's payload back into the scanned text precisely so the other judge
    # can read it.
    wiped = wiped_root_any(scanned, command)
    if wiped is not None:
        print(
            f"BLOCKED: recursive force-delete of {wiped!r} — that is the whole "
            f"filesystem or the whole working directory. Command: {command}",
            file=sys.stderr,
        )
        return 2

    for pattern, reason in BLOCKED_PATTERNS:
        if pattern.lower() in cmd_lower:
            print(f"BLOCKED: {reason}. Command: {command}", file=sys.stderr)
            return 2

    for regex, reason in WARN_PATTERNS_RE:
        if regex.search(scanned):
            # The old line said "ask the user for explicit confirmation first",
            # describing a mechanism that was never built: there is no
            # post-confirmation path here, so the user says yes and the hook
            # blocks identically. A remediation that cannot be carried out
            # teaches the reader that the messages are decorative. Name the
            # escape that exists — and that leaves a countable trace.
            print(
                f"BLOCKED: {reason}.\n"
                f"Command: {command}\n"
                "Confirming with the user does NOT unblock this - the gate has no "
                "approval path. Use a non-destructive equivalent, or (with the user's "
                "agreement) re-run that one command with TAUSIK_SKIP_HOOKS=1 set; the "
                "bypass is recorded as a supervision event.",
                file=sys.stderr,
            )
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
