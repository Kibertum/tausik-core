#!/usr/bin/env python3
"""PreToolUse hook: block dangerous bash commands.

Blocks: rm -rf /, DROP TABLE, git reset --hard, git push --force to main.
Exit codes: 0 = allow, 2 = block.
Receives JSON on stdin with tool_name, tool_input.
"""

import json
import os
import sys

# Patterns that should ALWAYS be blocked
BLOCKED_PATTERNS = [
    ("rm -rf /", "Recursive delete from root"),
    ("rm -rf /*", "Recursive delete from root"),
    ("rm -rf .", "Recursive delete from current directory"),
    ("DROP TABLE", "SQL table drop"),
    ("DROP DATABASE", "SQL database drop"),
    ("TRUNCATE TABLE", "SQL table truncate"),
    (":(){:|:&};:", "Fork bomb"),
    ("mkfs.", "Filesystem format"),
    ("dd if=/dev/zero", "Disk wipe"),
    ("> /dev/sda", "Disk overwrite"),
]

# Patterns that need confirmation (exit 2 with explanation)
WARN_PATTERNS = [
    ("git reset --hard", "Discards all local changes permanently"),
    ("git push --force", "Force push can overwrite remote history"),
    ("git push -f", "Force push can overwrite remote history"),
    ("git clean -fd", "Removes untracked files permanently"),
    ("git checkout -- .", "Discards all unstaged changes"),
]


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

    cmd_lower = command.lower()

    for pattern, reason in BLOCKED_PATTERNS:
        if pattern.lower() in cmd_lower:
            print(f"BLOCKED: {reason}. Command: {command}", file=sys.stderr)
            return 2

    for pattern, reason in WARN_PATTERNS:
        if pattern.lower() in cmd_lower:
            print(
                f"BLOCKED: {reason}.\n"
                f"Command: {command}\n"
                f"If you really need this, ask the user for explicit confirmation first.",
                file=sys.stderr,
            )
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
