#!/usr/bin/env python3
"""PreToolUse hook: block Write/Edit if no active task in TAUSIK.

Exit codes: 0 = allow, 2 = block.
Receives JSON on stdin with tool_name, tool_input.
Skipped via TAUSIK_SKIP_HOOKS=1 env var.
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import is_tausik_project  # noqa: E402


def main() -> int:
    if os.environ.get("TAUSIK_SKIP_HOOKS"):
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

    # v1.3.4 (med-batch-1-hooks #4): detect TAUSIK by .tausik/ dir, not
    # tausik.db file — closes the bootstrap-but-not-init bypass window.
    if not is_tausik_project(project_dir):
        return 0

    # Check for active task via CLI
    tausik_cmd = os.path.join(project_dir, ".tausik", "tausik")
    if not os.path.exists(tausik_cmd):
        return 0

    try:
        result = subprocess.run(
            [tausik_cmd, "task", "list", "--status", "active"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=project_dir,
        )
        output = result.stdout.strip()
        # "(none)" or empty means no active task
        if "(none)" in output or not output or output.startswith("slug"):
            # Only the header row, no tasks
            lines = [
                line
                for line in output.splitlines()
                if line.strip()
                and not line.startswith("slug")
                and not line.startswith("---")
            ]
            if not lines:
                print(
                    "BLOCKED: No active task. Start a task first:\n"
                    "  Say 'начинай работу' then describe your task, or use /go.\n"
                    "  TAUSIK requires a task before code changes (SENAR Rule 1).",
                    file=sys.stderr,
                )
                return 2
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        # If CLI fails, don't block — graceful degradation
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
