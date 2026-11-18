#!/usr/bin/env python3
"""Warn-only PreToolUse nudge for fragile Windows shell one-liners.

Agents regularly burn turns on nested PowerShell quotes, arguments after
``-EncodedCommand``, ``gh --jq`` brace breakage, and CRLF-breaking SSH heredocs.
This hook does not refuse those commands — a false block trains circumvention —
it names the remediation once: write a ``.ps1`` / ``.cmd`` / ``.py`` file first.

Non-Windows hosts exit immediately (zero cost). Safe quoted paths and already
file-based invocations stay silent.
"""

from __future__ import annotations

import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.dirname(_HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_SHELL_TOOLS = frozenset({"Bash", "PowerShell", "mcp__windows-mcp__PowerShell"})

# Nested quote smells: outer double quotes wrapping inner double quotes, or
# PowerShell -Command/-c carrying a quoted payload that itself quotes.
_NESTED_DQ = re.compile(r'"[^"\n]*"[^"\n]*"')
_PS_COMMAND_NEST = re.compile(
    r"(?i)(?:powershell(?:\.exe)?|pwsh(?:\.exe)?)\s+(?:-[Cc]ommand|-c)\s+['\"].*['\"]"
)
_ENCODED_TRAILING = re.compile(
    r"(?i)-EncodedCommand\s+\S+\s+\S+"  # anything after the base64 blob
)
_GH_JQ_BRACES = re.compile(r"(?i)\bgh\b[^\n]*--jq\b[^\n]*[{}]")
_SSH_HEREDOC = re.compile(r"(?i)\bssh\b[^|;&\n]*<<\s*['\"]?\w+")
# Already writing a script file — the remediation is being followed.
_FILE_BASED = re.compile(
    r"(?i)(?:\.ps1|\.cmd|\.bat|\.py)\b|(?:Set-Content|Out-File|New-Item).*-(?:Path|LiteralPath)"
)

_REMEDIATION = (
    "[TAUSIK Windows shell] fragile one-liner detected ({reason}). "
    "Write a .ps1/.cmd/.py file and run that instead of nesting quotes; "
    "do not put args after -EncodedCommand; avoid gh --jq with braces in "
    "PowerShell; for SSH prefer a local script + scp (CRLF breaks bash heredocs)."
)


def findings(command: str) -> list[str]:
    """Return short reason tags for fragile patterns in ``command``."""
    text = command or ""
    if _FILE_BASED.search(text):
        return []
    reasons: list[str] = []
    if _ENCODED_TRAILING.search(text):
        reasons.append("EncodedCommand-trailing-args")
    if _GH_JQ_BRACES.search(text):
        reasons.append("gh-jq-braces")
    if _SSH_HEREDOC.search(text):
        reasons.append("ssh-heredoc")
    if _PS_COMMAND_NEST.search(text) or (text.count('"') >= 4 and _NESTED_DQ.search(text)):
        reasons.append("nested-quotes")
    return reasons


def main() -> None:
    if os.name != "nt":
        sys.exit(0)
    try:
        from _common import force_utf8_io

        force_utf8_io()
    except Exception:  # noqa: BLE001,S110
        pass
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except (ValueError, OSError):
        sys.exit(0)
    tool = str(payload.get("tool_name") or "")
    if tool not in _SHELL_TOOLS:
        sys.exit(0)
    command = str((payload.get("tool_input") or {}).get("command") or "")
    reasons = findings(command)
    if not reasons:
        sys.exit(0)
    print(_REMEDIATION.format(reason=", ".join(reasons)), file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
