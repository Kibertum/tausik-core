#!/usr/bin/env python3
"""PreToolUse hook: block git push without explicit user confirmation.

The agent should use /ship or /commit which handle the push workflow.
Skills set TAUSIK_ALLOW_PUSH=1 to bypass this gate after user confirmation.
Direct git push without the env flag is blocked to prevent accidental pushes.
Exit codes: 0 = allow, 2 = block.
"""

import json
import os
import sys


def main() -> int:
    if os.environ.get("TAUSIK_SKIP_HOOKS"):
        return 0

    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    command = data.get("tool_input", {}).get("command", "").strip()
    if not command:
        return 0

    # Check if this is a git push command
    cmd_parts = command.split()
    if len(cmd_parts) < 2:
        return 0

    if cmd_parts[0] != "git" or cmd_parts[1] != "push":
        return 0

    # Allow push if explicitly authorized by a skill (/ship or /commit)
    if os.environ.get("TAUSIK_ALLOW_PUSH") == "1":
        return 0

    # Block git push — agent should use /ship or /commit
    print(
        "BLOCKED: Direct git push is not allowed.\n"
        "Use /ship (review + gates + push) or /commit (commit + push).\n"
        "Both skills will ask for confirmation before pushing.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
